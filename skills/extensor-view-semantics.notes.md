# Session Notes: ExTensor View Semantics (Issue #3236)

## Date: 2026-03-07

## Objective

Implement view/zero-copy semantics for `ravel()` and `transpose()` in the Mojo ExTensor type.

- `ravel()`: already returned a view for contiguous tensors — remove stale TODO, add assertion
- `transpose()`: change from allocating new tensor to returning a stride-permuted view

## Repository

HomericIntelligence/ProjectOdyssey (worktree: `.worktrees/issue-3236`)

## Implementation Summary

### Core changes to `extensor.mojo`

Added two new methods:

1. `_nd_index_to_flat_offset(linear_idx)` — converts flat linear index to byte offset using strides
2. `view_with_strides(new_shape, new_strides)` — creates shared-ownership view via `__copyinit__`

Updated 6 accessors (`_get_float32/64/int64`, `_set_float32/64/int64`) to branch on `is_contiguous()`.

### Changes to `matrix.mojo`

- `transpose()`: now calls `tensor.view_with_strides(result_shape, result_strides)` instead of allocating
- `matmul()`: added contiguification guard for non-contiguous inputs (the flat-buffer kernel requires it)

### Test changes

- `test_shape.mojo`: removed stale TODO, added `assert_true(b._is_view, ...)`
- `test_matrix.mojo`:
  - Fixed 2 existing tests that read raw buffer directly (wrong for views)
  - Added 5 new view-specific tests

## Key Technical Decisions

### Why branch on `is_contiguous()` in accessors?

The existing code always computed `offset = index * dtype_size`, which only works when elements
are stored contiguously. After transpose creates a view with permuted strides, a flat linear
index maps to a different byte position than `index * dtype_size`. The fix branches to
`_nd_index_to_flat_offset()` for non-contiguous tensors.

### Why materialize in `matmul()`?

The matmul kernel uses pointer arithmetic: `a_ptr[i * a_cols + k]`. This assumes elements are
stored in C-order (row-major contiguous). A transposed view has correct logical values but
wrong physical layout for this access pattern. The fix materializes non-contiguous inputs to a
new contiguous buffer before the kernel runs.

### Refcount correctness in `view_with_strides`

The pattern `var result = self` triggers `__copyinit__`, which increments `_refcount[]`.
Then mutating `result._shape`, `result._strides`, etc. in place (not creating another copy)
keeps refcount at exactly N+1. `return result^` moves the value without another increment.

## Environment Constraints

- Mojo version: v0.26.1
- Cannot run tests locally (requires GLIBC_2.32+ not available on dev machine)
- CI handles test execution via GitHub Actions
- `as_contiguous` lives in `shared.core.shape` — verified no circular import before using in `matrix.mojo`

## PR

PR #3794 — linked to issue #3236