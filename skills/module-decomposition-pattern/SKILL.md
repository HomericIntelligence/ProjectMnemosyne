---
name: module-decomposition-pattern
description: >
  Decompose large Python modules (1000+ lines) into focused sub-modules while
  preserving backward compatibility, updating all import sites, and fixing mock
  patch targets in tests. Use when a single file has 4+ logical clusters of
  functions with distinct responsibilities.
category: architecture
date: 2026-03-10
user-invocable: false
---

# Skill: Module Decomposition Pattern

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-10 |
| Project | ProjectScylla |
| Objective | Decompose `scylla/e2e/llm_judge.py` (1,488 lines, 35 functions) into 4 focused modules + slimmed orchestrator |
| Outcome | Success - 142-line orchestrator + 4 modules, all 4,788 tests pass, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1446 |

## When to Use

Use this skill when:
- A Python module exceeds ~500 lines with 4+ logical clusters of functions
- Functions within the module have distinct responsibilities (e.g., pipeline execution vs. log saving)
- Other modules use lazy imports (`from X import Y` inside function bodies) to access private functions
- The module has a large corresponding test file with many `patch()` targets
- You want to improve navigability without changing any behavior

## Key Decisions

### 1. Update import sites vs. re-export from original module

**Choose "update import sites"** (Option 2) when:
- There are a manageable number of import sites (< 20)
- Imports are lazy (inside function bodies), making updates safe
- You want to avoid the re-export anti-pattern

**Choose "re-export from original"** (Option 1) when:
- The module is a public API with many external consumers
- You cannot enumerate all import sites (e.g., third-party packages)

### 2. Handle circular imports with TYPE_CHECKING

When decomposing, circular imports often arise (e.g., Module A defines a model, Module B returns it, Module A calls Module B). Solve with:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from original_module import MyModel

def my_function() -> MyModel:  # String annotation via __future__
    from original_module import MyModel  # Runtime import
    return MyModel(...)
```

### 3. Keep public API exports in the original module

Models and orchestrator functions that are part of the public API (`__init__.py` exports) stay in the original module. Only move private implementation functions.

## Verified Workflow

### Step 1 - Map all import sites

Before writing any code, find every file that imports from the target module:

```bash
grep -rn "from package.module import" --include="*.py"
grep -rn 'patch("package.module.' --include="*.py"
```

Categorize each import into the target cluster (pipeline, context, execution, artifacts, etc.).

### Step 2 - Identify clusters and cross-dependencies

Group functions by responsibility. Check for cross-cluster calls:

```bash
grep -n "^def \|^class " module.py
```

Order extraction: start with modules that have no cross-cluster dependencies (leaf modules first).

### Step 3 - Create new modules one at a time

For each new module:
1. Write the file with moved functions and their imports
2. Update source import sites (`from new_module import func`)
3. Update test import sites (both `from` imports AND `patch()` targets)
4. Run tests: `pytest tests/unit/relevant/ -x -q`

### Step 4 - Update mock patch targets (CRITICAL)

`patch("old.module.func")` must change to `patch("new.module.func")`. Search for ALL occurrences:

```bash
grep -rn 'patch("package.old_module.' tests/
```

**Common mistake**: Only updating `test_old_module.py` but missing patch targets in `test_other.py` files that also mock functions from the decomposed module.

### Step 5 - Fix mypy type errors

Moving functions that return types defined in the original module often causes `no-any-return` errors. Fix with `TYPE_CHECKING` imports and proper return type annotations instead of `-> Any`.

### Step 6 - Final verification

```bash
pre-commit run --all-files
pytest tests/ -x -q
wc -l original_module.py new_module_*.py
```

## Results & Parameters

### Files created/modified

| File | Lines | Role |
|------|-------|------|
| `llm_judge.py` (was 1,488) | 142 | Orchestrator: JudgeResult model + run_llm_judge() |
| `build_pipeline.py` (new) | 548 | BuildPipelineResult + 13 pipeline functions |
| `judge_context.py` (new) | 334 | 7 workspace context/assembly functions |
| `judge_execution.py` (new) | 259 | 3 judge execution/parsing functions |
| `judge_artifacts.py` (new) | 295 | 10 log/script saving functions |

### Import sites updated

| File | Import changed |
|------|---------------|
| `stages.py` | 5 lazy imports |
| `stage_finalization.py` | 2 lazy imports |
| `rerun_judges.py` | 1 lazy import |
| `experiment_setup_manager.py` | 1 lazy import |
| `regenerate.py` | 1 lazy import |
| `judge_runner.py` | 1 TYPE_CHECKING import |
| `subtest_executor.py` | 2 imports |
| `__init__.py` | 0 (JudgeResult/run_llm_judge stayed) |

### Test files updated

| File | Changes |
|------|---------|
| `test_llm_judge.py` | Import block rewritten (4 source modules), 12 patch targets updated |
| `test_stages.py` | 10 patch targets updated |
| `test_stage_finalization.py` | 2 patch targets updated |
| `test_experiment_setup_manager.py` | 4 patch targets updated |
| `test_baseline_regression.py` | 1 import updated |
| `test_subtest_executor.py` | 1 import updated |

## Failed Attempts

### Attempt: Only searching test_llm_judge.py for patch targets

**What happened**: After updating all source imports and `test_llm_judge.py`, ran the e2e test suite. `test_stage_finalization.py` failed with `AttributeError: <module 'scylla.e2e.llm_judge'> does not have the attribute '_call_claude_judge'`.

**Root cause**: Other test files (`test_stages.py`, `test_stage_finalization.py`, `test_experiment_setup_manager.py`) also mock functions from `llm_judge` via `patch()`. Initial search only covered the main test file.

**Fix**: Always search ALL test files for `patch("old.module.` before declaring done:
```bash
grep -rn 'patch("package.old_module.' tests/
```

### Attempt: Using `-> Any` return type for functions with circular import

**What happened**: `_parse_judge_response` and `_execute_judge_with_retry` in `judge_execution.py` need to return `JudgeResult` (defined in `llm_judge.py`), but `llm_judge.py` imports from `judge_execution.py`. Used `-> Any` to avoid the circular import.

**Error**: mypy `no-any-return` error in `llm_judge.py` line 135 where `_execute_judge_with_retry` result is returned from `run_llm_judge() -> JudgeResult`.

**Fix**: Use `TYPE_CHECKING` guard with `from __future__ import annotations`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scylla.e2e.llm_judge import JudgeResult

def _parse_judge_response(response: str) -> JudgeResult: ...
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1446 - llm_judge.py decomposition | [notes.md](../references/notes.md) |
