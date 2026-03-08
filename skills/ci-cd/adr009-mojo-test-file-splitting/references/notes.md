# Session Notes: ADR-009 Mojo Test File Splitting

**Date**: 2026-03-07
**Issue**: #3466
**PR**: #4293
**Branch**: `3466-auto-impl`

## Objective

Fix intermittent Mojo CI heap corruption by splitting `test_early_stopping.mojo`
(16 `fn test_` functions) into two files of ≤8 tests each, complying with ADR-009.

## Context

- `tests/shared/training/test_early_stopping.mojo` had 16 `fn test_` functions
- ADR-009 mandates ≤10 per file due to Mojo v0.26.1 JIT heap corruption bug
- CI `Shared Infra` group was failing 13/20 recent runs non-deterministically
- Related issue: #2942, ADR-009 at `docs/adr/ADR-009-heap-corruption-workaround.md`

## Steps Taken

1. Read the original 474-line test file to understand all 16 test functions
2. Verified CI workflow uses glob `training/test_*.mojo` (no hardcoded filenames)
3. Checked `validate_test_coverage.py` — found hardcoded filename entry to update
4. Split 16 tests into two logical groups of 8:
   - Part 1: core behavior (initialization, patience, min_delta, monitor modes)
   - Part 2: edge cases + best value tracking + verbose mode
5. Added ADR-009 header comment to each new file
6. Deleted original file
7. Updated `validate_test_coverage.py` exclusion list
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4293 with auto-merge enabled

## Key Observations

- The CI workflow uses `training/test_*.mojo` glob — no workflow file changes needed
- `validate_test_coverage.py` uses exact filenames in exclusion list — must update
- Pre-commit hooks include a `Validate Test Coverage` hook that catches stale filenames
- `git add` on the deleted file path works correctly (stages the deletion)
- Logical grouping of tests (by category) makes the split easier to review

## Files Changed

- **Deleted**: `tests/shared/training/test_early_stopping.mojo`
- **Created**: `tests/shared/training/test_early_stopping_part1.mojo` (8 tests)
- **Created**: `tests/shared/training/test_early_stopping_part2.mojo` (8 tests)
- **Updated**: `scripts/validate_test_coverage.py`

---

# Session Notes: ADR-009 Test Split — test_reduction_edge_cases.mojo (Issue #3475)

**Date**: 2026-03-07
**Issue**: #3475
**PR**: #4316
**Branch**: `3475-auto-impl`

## Objective

Fix intermittent Mojo CI heap corruption by splitting `test_reduction_edge_cases.mojo`
(15 `fn test_` functions) into two files of ≤8 tests each, complying with ADR-009.

## Context

- `tests/shared/core/test_reduction_edge_cases.mojo` had 15 `fn test_` functions
- ADR-009 mandates ≤10 per file due to Mojo v0.26.1 JIT heap corruption bug
- CI `Core Tensors` group was failing intermittently
- Related issue: #2942, ADR-009 at `docs/adr/ADR-009-heap-corruption-workaround.md`

## Original Test Inventory

```text
fn test_empty_tensor_sum
fn test_empty_tensor_max
fn test_empty_tensor_min
fn test_empty_tensor_mean
fn test_scalar_tensor_operations
fn test_single_element_tensor
fn test_single_element_axis_reduction
fn test_same_values_tensor
fn test_2d_tensor_full_reduction
fn test_2d_tensor_axis0_reduction
fn test_2d_tensor_axis1_reduction
fn test_3d_tensor_reductions
fn test_4d_tensor_reductions
fn test_higher_dim_reduction
fn test_reduction_preserves_dtype
```

## Steps Taken

1. Read the original 281-line test file (15 test functions)
2. Checked CI workflow — `Core Tensors` group uses explicit filename list (not a glob)
3. Checked `validate_test_coverage.py` — uses glob patterns, no hardcoded filename to update
4. Split 15 tests into two logical groups:
   - Part 1 (8 tests): base edge cases — empty tensor ops, scalar, single-element, same-values
   - Part 2 (7 tests): dimensional cases — 2D axis reductions, 3D, 4D+, dtype preservation
5. Added ADR-009 header comment to each new file
6. Deleted original file
7. Updated `.github/workflows/comprehensive-tests.yml` (replaced old filename with 2 new filenames)
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4316 with auto-merge enabled

## Key Observations

- The CI workflow uses explicit filenames for `Core Tensors` group — workflow update required
- `validate_test_coverage.py` uses glob patterns — no script changes needed
- Pre-commit hooks all passed on first attempt
- `git add` on the deleted file path works correctly (stages the deletion)

## Complications

1. **Push timing**: Ran `git push` before background commit task finished; push failed silently
2. **Invalid label**: `gh pr create --label fix` failed — label `fix` does not exist; check `gh label list`
3. **PR create propagation**: `gh pr create` gave "must push first" error immediately after push;
   retried after brief pause and succeeded
4. **Untracked file warning**: `.claude-prompt-3475.md` was present; `gh pr create` warned
   about "1 uncommitted change" but PR created successfully since staged changes were already committed

## Files Changed

- **Deleted**: `tests/shared/core/test_reduction_edge_cases.mojo`
- **Created**: `tests/shared/core/test_reduction_edge_cases_part1.mojo` (8 tests)
- **Created**: `tests/shared/core/test_reduction_edge_cases_part2.mojo` (7 tests)
- **Updated**: `.github/workflows/comprehensive-tests.yml`
