# Raw Session Notes — Rubric Conflict Detection (#995)

## Problem Statement

`scylla/analysis/loader.py:load_rubric_weights()` originally returned weights from the **first** experiment found (early return pattern). The `load_all_experiments()` caller was noted as potentially loading experiments with conflicting rubric weights — when the same category appeared in two experiments with different weights, the loader silently kept whichever it encountered first (or last, depending on call site). This could corrupt any downstream cross-experiment comparison that assumed a single canonical weight per category.

## Implementation Walkthrough

### Step 1: Read the existing code

- `load_rubric_weights()` at line ~693 had an early-return: as soon as it found a `rubric.yaml` in any experiment, it parsed and returned weights from that one file only.
- `load_all_experiments()` did NOT call `load_rubric_weights()` internally — they are independent public functions. The conflict concern is that callers who call `load_rubric_weights()` separately might receive weights from one experiment while data from another experiment uses different weights.

### Step 2: Design decisions

1. **Where to add detection**: `load_rubric_weights()` is the right place because it already iterates rubric files. The function's new job is "load + validate consistency across all rubrics."

2. **Default = `"error"`**: A research pipeline should fail loudly on data integrity issues. Silent resolution (`'first'` or `'last'`) should be opt-in.

3. **Float tolerance**: `1e-6` chosen because it's well below any meaningful difference in rubric weights (which are typically integers or small decimals) while being large enough to absorb IEEE 754 round-trip noise.

4. **New categories don't conflict**: If experiment1 has `{"functional": 10}` and experiment2 has `{"code_quality": 5}`, these are merged without conflict. Only the same key with different values triggers the policy.

### Step 3: TDD order

Tests were written first:
- `test_rubric_conflict_raises_by_default` — smoke test for default `"error"` behavior
- `test_rubric_conflict_raises_explicitly` — explicit `rubric_conflict="error"` parameter
- `test_rubric_conflict_error_message_contains_details` — message quality
- `test_rubric_conflict_warn` — `"warn"` policy emits `UserWarning`
- `test_rubric_conflict_warn_message_contains_details` — warning message quality
- `test_rubric_conflict_first` — keeps first value
- `test_rubric_conflict_last` — keeps last value
- `test_rubric_no_conflict_identical_weights` — no false positives
- `test_rubric_conflict_float_tolerance` — `1e-10` difference is not a conflict
- `test_rubric_new_category_in_second_experiment` — merging without conflict
- `test_load_all_experiments_passes_rubric_conflict` — signature inspection

### Step 4: Implementation

Modified `loader.py`:
1. Added `import warnings` and `Literal` to imports
2. Added `RubricConflict` type alias
3. Added `RubricConflictError` class
4. Replaced early-return in `load_rubric_weights()` with accumulation loop
5. Added `rubric_conflict` parameter to `load_rubric_weights()` and `load_all_experiments()`

### Step 5: Pre-commit hook fixes needed

- **ruff-format** reformatted one file (minor whitespace)
- **ruff-check D107**: Missing `__init__` docstring in `RubricConflictError` — added `"""Initialize RubricConflictError with conflict details."""`
- **ruff-check D401**: `_write_rubric` helper docstring not imperative mood — changed from `"Helper to write..."` to `"Write a rubric.yaml file..."`
- **mypy**: `dict` without type parameters — changed to `dict[str, object]` in test file

### Step 6: Pre-push hook issue

The pre-push hook ran the full 3183-test suite and consistently failed at test #1689 (`test_run_single_with_mocks`). Investigation:
- Test passes in isolation ✓
- Test passes when running just the e2e module ✓
- Full suite run (outside hook) passes all 3183 tests ✓
- Conclusion: worktree was missing the `fix(tests): replace timing assertion with sleep mock in test_retry.py` commit that was on `main`
- Fix: `git fetch origin main && git rebase origin/main` — picked up the fix and push succeeded

## File List

| File | Action | Notes |
|------|--------|-------|
| `scylla/analysis/loader.py` | Modified | Core implementation |
| `tests/unit/analysis/test_rubric_conflict.py` | Created | 11 new tests |
| `tests/unit/analysis/test_loader.py` | Modified | 1 signature test updated |
