# Session Notes: mojo-transpose-view-contiguity

## Date
2026-03-07

## Issue
GitHub issue #3274 — "Add contiguous() / is_contiguous() assertions after transpose"

## Context
Tests `test_is_contiguous_after_transpose()` and `test_contiguous_on_noncontiguous()` in
`tests/shared/core/test_utility.mojo` had been implemented using direct `_strides` mutation
(e.g., `a._strides[0] = 1; a._strides[1] = 3`) rather than an actual transpose operation.

The issue plan requested adding `transpose_view()` to produce realistically non-contiguous
tensors for the tests.

## What Was Discovered

1. The tests were NOT commented out — a previous PR already implemented them with `_strides` hacks.
2. `transpose()` in `matrix.mojo` is copy-based (reorders data); it always returns contiguous tensors.
3. No `transpose_view()` existed anywhere in the codebase.
4. `_get_dtype_size()` and `_strides` are accessible on ExTensor from matrix.mojo (not fully private).

## Implementation

### `transpose_view()` design
- Copies raw bytes with `memcpy` (same flat data, no reordering)
- Overwrites strides with permuted C-order input strides
- Result: same data in memory, different stride interpretation → `is_contiguous() == False`

### Stride math for [3,4] → transpose_view → [4,3]
- Input C-order strides: `[4, 1]` (dim0 stride = 4 cols, dim1 stride = 1)
- Default perm: `[1, 0]`
- Result shape: `[4, 3]`
- Result strides: `[input_strides[1], input_strides[0]]` = `[1, 4]`
- C-order for `[4,3]` would be `[3, 1]` → `[1,4]` is non-contiguous ✓

### `as_contiguous` behavior on transpose_view result
- Shape is `[4,3]` (transposed)
- Non-contiguous path iterates flat indices and copies byte-by-byte
- Result: new ExTensor with shape `[4,3]`, C-order strides `[3, 1]`
- `is_contiguous()` returns True ✓

## Files Changed
- `shared/core/matrix.mojo` — added `transpose_view()` + `from memory import memcpy` import
- `shared/core/__init__.mojo` — exported `transpose_view`
- `tests/shared/core/test_utility.mojo` — updated two tests to use `transpose_view()`

## PR
https://github.com/HomericIntelligence/ProjectOdyssey/pull/3837