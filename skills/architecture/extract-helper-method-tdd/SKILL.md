# Skill: Extract Helper Method (TDD Workflow)

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-19 |
| Issue | #712 |
| PR | #763 |
| Objective | Eliminate duplicate baseline-creation code across two methods in `scylla/e2e/runner.py` |
| Outcome | Success — 4 new tests, 2213 existing tests passing, all pre-commit hooks green |

## When to Use

Trigger this skill when you see:

- The same 3–8 line block appearing in two or more methods
- A follow-up issue referencing duplicate logic discovered during a prior refactor
- Issue title containing phrases like "consider extracting", "deduplicate", "helper method"
- Identical or near-identical `get_*` / `create_*` / `build_*` call sequences

## Verified Workflow

### 1. Read the duplicate sites first

Read the full method bodies — not just the cited lines — to understand the surrounding
guard conditions (`if best_subtest`, `if best_tier`, etc.) before designing the helper signature.

### 2. Design the helper signature

- Mirror the guard (`if not tier_result.best_subtest: return None`) inside the helper so callers
  don't need to repeat the guard.
- Return `Optional[T]` and let call sites use `or previous_value` for fallback logic.

### 3. Write tests first (TDD)

Write tests that fail with `AttributeError` (method doesn't exist yet), then implement.

Key test patterns for a helper like `_create_baseline_from_tier_result`:

```python
# Setup: runner.experiment_dir and runner.tier_manager must be set manually
runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp"))
runner.experiment_dir = Path("/tmp/exp")   # set after construction
runner.tier_manager = mock_tier_manager    # overwrite — __init__ wraps tiers_dir in TierManager()
```

**Gotcha**: `E2ERunner.__init__` takes `tiers_dir: Path` and wraps it in `TierManager(tiers_dir)`,
so passing a `MagicMock` as `tiers_dir` creates a real `TierManager` around the mock. Always
overwrite `runner.tier_manager` directly after construction in unit tests.

**Gotcha**: `runner.experiment_dir` starts as `None`; set it explicitly in tests that exercise
path construction logic.

### 4. Implement the helper — place it just before the first call site

```python
def _create_baseline_from_tier_result(
    self,
    tier_id: TierID,
    tier_result: TierResult,
) -> TierBaseline | None:
    """Create a baseline from a tier result's best subtest.

    Args:
        tier_id: The tier the result belongs to.
        tier_result: The result from which to derive the baseline.

    Returns:
        TierBaseline for the best subtest, or None if no best subtest exists.

    """
    if not tier_result.best_subtest:
        return None
    subtest_dir = self.experiment_dir / tier_id.value / tier_result.best_subtest
    return self.tier_manager.get_baseline_for_subtest(
        tier_id=tier_id,
        subtest_id=tier_result.best_subtest,
        results_dir=subtest_dir,
    )
```

### 5. Update call sites

**Sequential caller** (`_execute_single_tier`):

```python
# Before:
updated_baseline = previous_baseline
if tier_result.best_subtest:
    subtest_dir = self.experiment_dir / tier_id.value / tier_result.best_subtest
    updated_baseline = self.tier_manager.get_baseline_for_subtest(...)

# After:
updated_baseline = self._create_baseline_from_tier_result(tier_id, tier_result) or previous_baseline
```

**Group selector** (`_select_best_baseline_from_group`):

```python
# Before:
if best_tier and tier_results[best_tier].best_subtest:
    subtest_dir = ...
    baseline = self.tier_manager.get_baseline_for_subtest(...)
    logger.info(...)
    return baseline

# After:
if best_tier:
    baseline = self._create_baseline_from_tier_result(best_tier, tier_results[best_tier])
    if baseline:
        logger.info(...)
        return baseline
```

### 6. Run hooks and fix lint before committing

`pre-commit run --all-files` caught an E501 (line > 100 chars) in the `logger.info` f-string.
Fix by splitting the f-string across two continuation lines.

### 7. Commit only the implementation files

```bash
git add scylla/e2e/runner.py tests/unit/e2e/test_runner.py
git commit -m "refactor(e2e): extract duplicate baseline creation into _create_baseline_from_tier_result

Closes #712"
```

## Failed Attempts

| Attempt | What Went Wrong | Fix |
|---------|----------------|-----|
| Tests used `runner = E2ERunner(mock_config, mock_tier_manager, Path("/tmp/exp"))` assuming third arg becomes `experiment_dir` | Third arg is `results_base_dir`; `experiment_dir` is set later by `_create_fresh_experiment` | Pass `Path("/tmp")` as third arg and set `runner.experiment_dir = Path("/tmp/exp")` explicitly |
| Did not overwrite `runner.tier_manager` in tests | `__init__` wraps `tiers_dir` in `TierManager(tiers_dir)`, so the mock was never used | Always set `runner.tier_manager = mock_tier_manager` after construction |
| Kept logger.info as single f-string | E501 — 104 chars > 100 limit enforced by ruff | Split into two adjacent f-strings on separate lines |

## Results & Parameters

- **Files changed**: `scylla/e2e/runner.py`, `tests/unit/e2e/test_runner.py`
- **Net lines**: +101 / −21 (21 duplicate lines removed, 22-line helper + 4 tests added)
- **Test count**: 2213 passing (8 in `test_runner.py`, 4 new)
- **Coverage**: 73.37% (threshold: 73%)
- **Pre-commit**: all hooks green (ruff, mypy, black, shellcheck, trim-whitespace, end-of-files)
