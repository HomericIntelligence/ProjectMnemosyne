---
name: pydantic-none-coercion-pattern
description: Fix Pydantic ValidationError when None flows into non-Optional dict fields via dict.get() with a default value
category: debugging
date: 2026-02-19
tags: [pydantic, validation, none, dict, json, null, coercion, field_validator, checkpoint]
user-invocable: false
---

# Pydantic None Coercion Pattern

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-19 |
| **Objective** | Fix `ValidationError` from `criteria_scores=None` propagating into a non-Optional Pydantic field |
| **Outcome** | ✅ Fixed 8 vulnerable sites + added defense-in-depth Pydantic validator |
| **Project** | ProjectScylla |
| **PR** | [#760](https://github.com/HomericIntelligence/ProjectScylla/pull/760) |

## When to Use

Use this skill when you encounter:

- `pydantic_core._pydantic_core.ValidationError: Input should be a valid dictionary [type=dict_type, input_value=None]`
- A Pydantic field typed as `dict[K, V]` (non-Optional) is receiving `None` at construction time
- Symptoms: silent failures with `$0 cost + 8-22s duration + zero tokens` in E2E runs
- Data is loaded from JSON files (checkpoint/resume) where the field may be stored as `null`
- A `dict.get("field", {})` guard is in place but still passes `None`

## The Core Trap: `dict.get()` Does NOT Guard Against Explicit `null`

```python
# BROKEN: Only returns {} when the key is ABSENT
data = {"criteria_scores": None}  # key exists, value is null
data.get("criteria_scores", {})   # Returns None, NOT {}

# CORRECT: Returns {} both when key absent AND when value is None
data.get("criteria_scores") or {}  # Returns {}
```

This is the most common mistake when loading data from JSON files where a field may be stored as `null`.

## Problem

A type mismatch exists when data flows between two layers with different Optional-ness:

```python
# Source type (Optional - can be None):
class JudgeResult:
    criteria_scores: dict[str, dict[str, Any]] | None = None

# Destination type (non-Optional - must be dict):
class E2ERunResult(BaseModel):
    criteria_scores: dict[str, dict[str, Any]] = Field(default_factory=dict)
```

When `JudgeResult.criteria_scores = None` flows into `E2ERunResult` construction, Pydantic raises:
```
ValidationError: 1 validation error for E2ERunResult
criteria_scores
  Input should be a valid dictionary [type=dict_type, input_value=None, ...]
```

The error manifests as silent test failures — the entire run is marked as failed with $0 cost.

## Verified Workflow

### 1. Find All Vulnerable `.get()` Calls

```bash
# Find all dict.get() calls with a default that target the field
grep -rn '.get("criteria_scores", {})' <project-root>/
# Every match is vulnerable to explicit null values in JSON
```

### 2. Fix the `.get()` Pattern

```python
# BEFORE (vulnerable):
criteria_scores = data.get("criteria_scores", {})

# AFTER (safe):
criteria_scores = data.get("criteria_scores") or {}
```

### 3. Fix Direct Assignments From Optional Sources

```python
# BEFORE (can assign None to non-Optional field):
run.criteria_scores = judge_result.criteria_scores

# AFTER (guard at assignment):
run.criteria_scores = judge_result.criteria_scores or {}
```

### 4. Fix Upstream Producers (Prevent None From Entering the Dict)

When a consensus dict or similar intermediate structure is built and consumed downstream:

```python
# BEFORE (produces None in the dict):
primary_criteria_scores = closest_judge.criteria_scores  # can be None
consensus_dict = {"criteria_scores": primary_criteria_scores}

# AFTER (normalize at the source):
primary_criteria_scores = closest_judge.criteria_scores or {}
consensus_dict = {"criteria_scores": primary_criteria_scores}
```

### 5. Add a Pydantic Validator for Defense-in-Depth

Even after fixing all call sites, add a validator to the Pydantic model as a backstop:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any

class E2ERunResult(BaseModel):
    criteria_scores: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("criteria_scores", mode="before")
    @classmethod
    def coerce_none_criteria_scores(cls, v: Any) -> dict:
        """Coerce None to empty dict — upstream sources may return None."""
        return v if v is not None else {}
```

This catches any future callers that pass `None` without requiring all call sites to be perfect.

### 6. Fix Missing Writes in Update Functions

When a function updates stored JSON (e.g., `run_result.json`) but omits the field, stale data persists:

```python
# BEFORE (missing criteria_scores write):
run_data["judge_score"] = consensus_score
run_data["judge_passed"] = passed
run_data["judge_reasoning"] = representative_reasoning
# criteria_scores NOT updated — stale value persists!

# AFTER (include criteria_scores in every update):
run_data["judge_score"] = consensus_score
run_data["judge_passed"] = passed
run_data["judge_reasoning"] = representative_reasoning
run_data["criteria_scores"] = representative_criteria or {}
```

### 7. Run Tests

```bash
<package-manager> run python -m pytest tests/unit/ -v -k "criteria_scores"
pre-commit run --all-files
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| `dict.get("criteria_scores", {})` | Only returns `{}` when the key is **missing**; returns `None` when key exists with `null` value |
| Typing `criteria_scores` as `Optional[dict]` in destination model | Allows `None` but then downstream code using `.items()` or `.keys()` crashes with `AttributeError: 'NoneType'` |
| Only fixing the highest-visibility call site | The bug has 8+ manifestations across multiple files; must do a complete audit with `grep` |
| Relying on Pydantic's `default_factory=dict` | Default only applies when the field is **not provided** at construction time; explicit `None` overrides the default and causes ValidationError |

## Audit Checklist

When fixing this pattern, audit ALL locations where the affected field is:

1. Read from JSON/dict via `.get()` with a default
2. Assigned from an Optional-typed source to a non-Optional destination
3. Updated in stored JSON files (look for "update functions" that write some fields but not others)
4. Produced by consensus/aggregation functions and placed into intermediate dicts

```bash
# Find all occurrences of the field across the codebase:
grep -rn "criteria_scores" <project-root>/scylla/
grep -rn "criteria_scores" <project-root>/tests/

# Check each one: is the field Optional at the source? Non-Optional at the destination?
```

## Results & Parameters

### Vulnerability Map (ProjectScylla example)

| # | File | Pattern | Fix |
|---|------|---------|-----|
| 1 | `subtest_executor.py:360` | `.get("criteria_scores", {})` on checkpoint data | `or {}` |
| 2 | `subtest_executor.py:858` | `.get("criteria_scores", {})` on consensus dict | `or {}` |
| 3 | `regenerate.py:210` | `.get("criteria_scores", {})` on stored data | `or {}` |
| 4 | `regenerate.py:400` | `run.criteria_scores = judge_result.criteria_scores` | `or {}` |
| 5 | `rerun.py:740` | `.get("criteria_scores", {})` on judge result | `or {}` |
| 6 | `rerun_judges.py:606` | Missing write in update function | Add write with `or {}` |
| 7 | `judge_runner.py:246` | `primary_criteria_scores = closest_judge.criteria_scores` | `or {}` |
| 8 | `judge_runner.py:249` | `judges[0].criteria_scores if judges else None` | `or {}` |
| 9 | `models.py` | `E2ERunResult.criteria_scores` field | Add `field_validator` |

### Test Pattern

```python
def test_criteria_scores_coerces_none_to_empty_dict() -> None:
    """Test that criteria_scores=None is coerced to {} by the Pydantic validator."""
    result = MyModel(
        # ... other required fields ...
        criteria_scores=None,  # type: ignore[arg-type]
    )
    assert result.criteria_scores == {}


def test_criteria_scores_null_in_checkpoint_data() -> None:
    """Test that null in stored JSON does not raise ValidationError on resume."""
    data = {"criteria_scores": None, ...}  # Simulates run_result.json with null

    result = MyModel(
        # ... other fields ...
        criteria_scores=data.get("criteria_scores") or {},  # Safe pattern
    )
    assert result.criteria_scores == {}
```

## Key Learnings

1. **`dict.get(key, default)` trap**: The default is only used when the **key is absent**. If the key exists with value `None`, the default is ignored and `None` is returned. Always use `dict.get(key) or default` when the stored value can be `null`.

2. **Audit all 3 vulnerability types**: `.get()` calls, direct assignments from Optional sources, and missing writes in update functions.

3. **Defense-in-depth**: Fix all call sites AND add a Pydantic `field_validator`. The validator catches future regressions without requiring every caller to be perfect.

4. **Type mismatch root cause**: When an Optional source (`dict | None`) flows into a non-Optional destination (`dict`), every handoff point is a potential bug. Either make all types consistent, or add guards at every handoff.

5. **Symptom identification**: `$0 cost + 8-22s duration + zero tokens` in E2E evaluation results = Pydantic ValidationError in the framework, not a model failure.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #760 - 8 sites fixed after 2026-02-14 dry run revealed 13 failing tests | [notes.md](../../references/notes.md) |
