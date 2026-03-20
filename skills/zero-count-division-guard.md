---
name: zero-count-division-guard
description: "Skill: Zero-Count Division Guard in Metric Collection Functions"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: Zero-Count Division Guard in Metric Collection Functions

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-02 |
| Project | ProjectScylla |
| Objective | Fix `ZeroDivisionError` in `check_readme_test_count()` when `collect_actual_test_count()` returns `0` in CI |
| Outcome | Success — 1-line fix + 2 new tests; all 3528 tests pass, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1226 |
| PR | HomericIntelligence/ProjectScylla#1315 (review feedback) |

## When to Use

Use this skill when:
- A function returns a numeric count from an external process (subprocess, API call, file parse)
- That count is later used as a **denominator** in a ratio or tolerance check
- Zero is a semantically invalid count (zero collected tests = collection failure, not an empty suite)
- CI fails with `ZeroDivisionError` only in automated contexts (not locally), because the collection step produces `0` due to environment differences

## Root Cause Pattern

```
collect_X() -> int   # Returns 0 on collection failure instead of None
check_Y(actual=0)    # Divides by actual without guarding against zero
  -> ZeroDivisionError
```

The bug has two compounding parts:
1. `collect_X()` treats "0 found" the same as "N found" — but zero means collection failed
2. `check_Y()` uses the count as a denominator with no zero-guard

## Verified Workflow

### Step 1: Identify the division site

Find where the count is used as a denominator:

```python
# Dangerous — no zero guard
if abs(doc_count - actual_count) / actual_count > tolerance:
```

### Step 2: Fix the collection function (preferred fix)

Return `None` when the parsed count is `0` — treat zero as "unavailable":

```python
# Before
if m:
    return int(m.group(1))
return None

# After — zero means collection failed, not "zero tests exist"
if m:
    count = int(m.group(1))
    return count if count > 0 else None
return None
```

This is the minimal fix: callers that check `if actual_count is None: skip` already handle this case correctly, so no changes are needed at the call site.

### Step 3: Add tests for zero-count inputs

```python
def test_zero_collected_returns_none(self, tmp_path: Path) -> None:
    """Should return None when pytest reports 0 tests (collection failure)."""
    mock_result = MagicMock()
    mock_result.stdout = "0 selected\n"
    mock_result.stderr = ""
    with patch(
        "scripts.check_doc_config_consistency.subprocess.run",
        return_value=mock_result,
    ):
        assert collect_actual_test_count(tmp_path) is None

def test_zero_tests_collected_returns_none(self, tmp_path: Path) -> None:
    """Should return None when pytest reports '0 tests collected' (collection failure)."""
    mock_result = MagicMock()
    mock_result.stdout = "0 tests collected\n"
    mock_result.stderr = ""
    with patch(
        "scripts.check_doc_config_consistency.subprocess.run",
        return_value=mock_result,
    ):
        assert collect_actual_test_count(tmp_path) is None
```

### Step 4: Verify

```bash
# Target test classes
pixi run python -m pytest tests/unit/scripts/test_check_doc_config_consistency.py \
    -v --override-ini="addopts=" \
    -k "TestCollectActualTestCount or TestCheckReadmeTestCount or TestMainIntegration"

# Full unit suite
pixi run python -m pytest tests/unit/ -v --override-ini="addopts="

# Pre-commit
pre-commit run --all-files
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Why Fix at the Collection Layer (Not the Check Layer)

Two options exist:

| Option | Location | Change |
|--------|----------|--------|
| A (chosen) | `collect_actual_test_count()` | Return `None` when count == 0 |
| B (rejected) | `check_readme_test_count()` | Add `if actual_count == 0: return [error]` |

Option A is preferred because:
- `None` is already the established sentinel for "count unavailable"
- The caller (`main()`) already skips Check 4 when count is `None`
- No change needed at the call site — the existing `if actual_count is not None:` guard handles it
- Semantically correct: zero collected tests is always a collection error in this context

## Key Insight: CI vs. Local Divergence

This bug only surfaces in CI (not locally) because:
- Locally, `pytest --collect-only -q tests/` runs against the full repo and returns `>0`
- In CI, the pre-commit hook or unit step runs in an environment where pytest cannot import all test modules (missing conftest, import errors, or restricted path), returning `"0 selected"`
- The regex correctly matches `"0 selected"` — the bug is that `0` is treated as valid

Always test collection functions with `0` as a possible output, especially when they shell out to external tools.

## Files Modified

| File | Change |
|------|--------|
| `scripts/check_doc_config_consistency.py:273-275` | Return `None` when parsed count == 0 |
| `tests/unit/scripts/test_check_doc_config_consistency.py` | +2 tests for zero-count inputs |
