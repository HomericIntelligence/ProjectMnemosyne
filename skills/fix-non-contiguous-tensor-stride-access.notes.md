# Session Notes — fix-non-contiguous-tensor-stride-access

**Date**: 2026-03-07
**Issue**: ProjectOdyssey #3391
**PR**: ProjectOdyssey #4079

## Objective

Fix `as_contiguous()` in `shared/core/shape.mojo` which silently produced wrong results
for non-contiguous tensor views (e.g. transposed or sliced tensors) because the non-contiguous
branch called `_get_float64(i)` which uses flat offset `i * dtype_size` rather than
stride-based multi-dimensional indexing.

## Root Cause Analysis

`ExTensor._get_float64(self, index: Int)` (extensor.mojo:1006-1032):
```mojo
fn _get_float64(self, index: Int) -> Float64:
    var dtype_size = self._get_dtype_size()
    var offset = index * dtype_size  # ASSUMES stride-1 contiguous layout
    ...
```

This is correct only when the tensor's data is laid out contiguously with stride 1.
For a transposed (4,3) tensor with strides `[1, 4]`, element `(0,1)` is at byte
offset `1*4*dtype_size`, not `1*dtype_size`.

## Fix Applied

Replaced the non-contiguous branch of `as_contiguous()` with stride-based decomposition,
matching the existing pattern in `ExTensor.slice()` (extensor.mojo:988-1002):

```mojo
for i in range(numel):
    var src_elem_offset = 0
    var remaining = i
    for d in range(ndim - 1, -1, -1):
        var coord = remaining % shape[d]
        remaining //= shape[d]
        src_elem_offset += coord * tensor._strides[d]
    var src_byte_offset = src_elem_offset * dtype_size
    var dst_byte_offset = i * dtype_size
    for b in range(dtype_size):
        dst_ptr[dst_byte_offset + b] = src_ptr[src_byte_offset + b]
```

## Key Discovery

The existing test `test_contiguous_on_noncontiguous()` only checked:
1. `is_contiguous()` returns True on the result
2. `_strides` values are correct

It did NOT verify actual element values — so the bug was completely invisible to the
test suite. Added `test_as_contiguous_values_correct()` which checks all 12 element
values against expected transpose result.

## Scan Results

Other functions in shape.mojo that may have the same flat-index bug (future work):
- `tile()` line 1106: `var val = tensor._get_float64(adjusted_idx)` — uses recomputed index, likely OK
- `repeat()` line 1201: `var val = tensor._get_float64(src_idx)` — uses coordinate-based index, likely OK
- `broadcast_to()` line 1266: `var val = tensor._get_float64(src_idx)` — uses broadcast_strides, likely OK
- `concatenate()` lines 520-522: calls `_get_float64(i)` on non-contiguous tensors — potential bug
- `permute()` line 1367: uses coordinate-based source index, likely OK
- `reshape()` line 245: calls `_get_float64(i)` — may have same bug if called on non-contiguous

## Environment

- Local mojo execution: UNAVAILABLE (GLIBC mismatch on this host)
- Tests: Run in CI / Docker only
- Pre-commit hooks: All passed (mojo format, test count, whitespace)
