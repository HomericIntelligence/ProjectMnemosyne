# Session Notes: mojo-empty-tensor-shape-hash-differ

## Session Context

- **Date**: 2026-03-15
- **Issue**: HomericIntelligence/ProjectOdyssey#4067
- **Branch**: `4067-auto-impl` (worktree: `.worktrees/issue-4067`)
- **Follow-up from**: Issue #3384 (PR #4064) which added `test_hash_empty_tensor`

## Objective

Add `test_hash_empty_tensor_shapes_differ` to `tests/shared/core/test_utility.mojo` to verify
that empty tensors with shapes `[0]`, `[0,0]`, and `[0,1]` produce distinct hashes. The prior
test (`test_hash_empty_tensor`) only confirmed same-shape equality; this test exercises the
shape loop for multi-dimensional cases when `numel=0`.

## Investigation Steps

1. Reviewed `shared/core/extensor.mojo:2840` `__hash__` implementation — confirmed shape loop
   iterates over ALL dimensions regardless of `numel`. No production code change needed.
2. Confirmed prior test `test_hash_empty_tensor` only used shape `[0]` × 2 (equality check).
3. Searched for existing "shapes differ" coverage for empty tensors — none found.
4. Reviewed related skills `mojo-empty-tensor-hash-test` and `mojo-hash-shape-test` to ensure
   this skill is distinct (non-empty shapes were tested in the latter; 1D empty equality in
   the former).

## Implementation

Added to `tests/shared/core/test_utility.mojo`:

- Function `test_hash_empty_tensor_shapes_differ` (~28 lines)
- Call in `main()` after `test_hash_empty_tensor()`

Used the "raise on collision" pattern (`if hash(a) == hash(b): raise Error(...)`) consistent
with `test_hash_different_values_differ` at line 471.

## Key Decisions

- **3 shape pairs tested**: `[0]` vs `[0,0]`, `[0]` vs `[0,1]`, `[0,0]` vs `[0,1]`
  — covers both rank difference and same-rank different-dim scenarios
- **zeros() factory used**: signals intent clearly; `empty()` would also work since no data
  is accessed for numel=0 tensors
- **No production code changes**: `__hash__` already correct; pure test addition

## Test Results

- Pre-commit hooks: all passed (`mojo format`, trailing-whitespace, end-of-file-fixer)
- CI: `just test-mojo` filtered output showed all hash tests passing (`✅ ALL 8 TESTS PASSED`)
- Pre-existing failures in `tests/shared/test_imports*.mojo` are unrelated (known flaky)