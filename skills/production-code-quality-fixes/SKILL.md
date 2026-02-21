# Skill: Production Code Quality Fixes

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | #757 |
| PR | #891 |
| Category | debugging |
| Objective | Fix two production code quality issues: (1) assert used for input validation in grading.py, (2) hardcoded /tmp path in llm_judge.py |
| Outcome | Success — both fixes applied, 241 tests pass, pre-commit clean, PR #891 created with auto-merge |

## When to Use

Trigger this skill when:

- A code review or issue flags `assert` statements in `scylla/` production code used for input validation
- A path like `/tmp/something` is hardcoded in production code rather than using `tempfile` utilities
- CI or grep finds `assert` statements outside of test files in `scylla/`
- Cross-platform portability concerns are raised about hardcoded system paths

## Verified Workflow

### 1. Locate the assert statement

```bash
grep -rn "^    assert\|^assert" scylla/ --include="*.py"
```

Asserts used for input validation (not for invariants/debugging) must be replaced with explicit exceptions.

### 2. Replace assert with ValueError

**Before:**
```python
assert 0.0 <= score <= 1.0, f"Score {score} is outside valid range [0.0, 1.0]"
```

**After:**
```python
if not (0.0 <= score <= 1.0):
    raise ValueError(f"score must be in [0.0, 1.0], got {score}")
```

**Why:** Python `-O` (optimized mode) strips all `assert` statements at compile time, creating a silent safety gap for input validation.

### 3. Locate hardcoded /tmp paths

```bash
grep -rn '"/tmp/' scylla/ --include="*.py"
```

### 4. Replace hardcoded /tmp with tempfile

**Before:**
```python
env["PYTHONPYCACHEPREFIX"] = "/tmp/scylla_pycache"
```

**After:**
```python
import tempfile
env["PYTHONPYCACHEPREFIX"] = str(Path(tempfile.gettempdir()) / "scylla_pycache")
```

Check existing imports first — `tempfile` and `Path` may already be imported.

### 5. Update tests expecting AssertionError

After replacing asserts with ValueError, search for tests expecting `AssertionError`:

```bash
grep -rn "AssertionError" tests/ --include="*.py"
```

Update any such tests to use `ValueError` with the new error message pattern:

```python
# Before
with pytest.raises(AssertionError, match="outside valid range"):
    assign_letter_grade(1.1)

# After
with pytest.raises(ValueError, match="score must be in"):
    assign_letter_grade(1.1)
```

### 6. Add new parametrized ValueError tests

Add to the relevant test class:

```python
@pytest.mark.parametrize("score", [-0.1, 1.1, -1.0, 2.0])
def test_invalid_score_raises_value_error(self, score: float) -> None:
    """Scores outside [0.0, 1.0] raise ValueError (not silently ignored)."""
    with pytest.raises(ValueError, match="score must be in"):
        assign_letter_grade(score)
```

### 7. Verify and commit

```bash
# Run affected tests
pixi run python -m pytest tests/unit/metrics/ tests/unit/test_grading_consistency.py --no-cov -q

# Run pre-commit on changed files
pre-commit run --files scylla/metrics/grading.py scylla/e2e/llm_judge.py \
  tests/unit/metrics/test_grading.py tests/unit/test_grading_consistency.py
```

## Failed Attempts

None in this session — the approach was straightforward.

**Pitfall to avoid**: Do not forget to search `tests/` for existing tests that assert `AssertionError` for the old assert-based validation. There was one in `tests/unit/test_grading_consistency.py::test_metrics_grading_validates_range` that caused 1 test failure after the production fix, requiring an update to expect `ValueError`.

## Results & Parameters

| File | Change |
|------|--------|
| `scylla/metrics/grading.py:131-132` | `assert` → `if not ... raise ValueError` |
| `scylla/e2e/llm_judge.py:370` | `"/tmp/scylla_pycache"` → `str(Path(tempfile.gettempdir()) / "scylla_pycache")` |
| `tests/unit/metrics/test_grading.py` | Added 4-case parametrized `ValueError` test |
| `tests/unit/test_grading_consistency.py` | Updated `AssertionError` → `ValueError` in existing test |

**Test results:** 241 passed, 0 failed
**Pre-commit:** All hooks passed (ruff, mypy, black, shellcheck, trim whitespace)
