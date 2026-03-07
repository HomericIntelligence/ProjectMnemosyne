# Session Notes: Mojo N-D Slice Copy Semantics Fix

## Context

- **Issue**: #3190 — Enable multi-dimensional slicing tests in test_extensor_slicing.mojo
- **Parent Issue**: #3086 — Copy vs view semantics documentation
- **PR**: #3691
- **Date**: 2026-03-07
- **Branch**: `3190-auto-impl`

## Problem Statement

Tests `test_slice_2d_single_dim`, `test_slice_2d_both_dims`, `test_slice_3d_partial`, and
three batch extraction tests were commented out in `main()` with `# Skip for now - needs debugging`.

The tests themselves were well-written and correct. The underlying implementation of
`ExTensor.__getitem__(self, *slices: Slice)` had a fundamental bug.

## Investigation

### File: `shared/core/extensor.mojo`

ExTensor struct:
- `_data`: `UnsafePointer[UInt8]` — raw byte storage (type-erased)
- `_shape`: `List[Int]` — dimension sizes
- `_strides`: `List[Int]` — row-major strides in elements (NOT bytes)
- `_numel`: `Int` — total element count
- `_is_view`: `Bool` — whether this shares data with another tensor
- `_refcount`: `UnsafePointer[Int]` — shared reference count

ExTensor implements `Copyable` trait, which provides `.copy()` backed by `__copyinit__`.
The `__copyinit__` is a **shallow copy** — shares `_data` pointer, increments `_refcount`.

### Three `__getitem__` Overloads

1. `__getitem__(self, index: Int) -> Float32` — element access
2. `__getitem__(self, slice: Slice) -> Self` — 1D slice, proper copy, `_is_view = False`
3. `__getitem__(self, *slices: Slice) -> Self` — N-D slice, BUGGY view approach

### The Bug in Overload 3

```mojo
var result = self.copy()          # shallow copy, shared _data, refcount++
result._is_view = True
var offset_bytes = 0
for dim in range(num_dims):
    start = ...
    result._shape[dim] = end - start
    offset_bytes += start * result._strides[dim] * dtype_size
result._data = self._data.offset(offset_bytes)  # ❌
result._numel = ...
return result^
```

`self._data.offset(offset_bytes)` sets a pointer to the START of the slice region.
For first-axis-only slices (e.g., `t[1:4, :, :]`), data is contiguous after this offset.
For inner-dimension slices (e.g., `t[1:4, 1:3]`), selected elements have gaps — offset alone
cannot address them.

### Memory Layout Visualization

5×4 row-major tensor, bytes (float32, 4 bytes each):
```
Row 0: [0  4  8  12]   (bytes 0-15)
Row 1: [16 20 24 28]   (bytes 16-31)
Row 2: [32 36 40 44]   (bytes 32-47)
Row 3: [48 52 56 60]   (bytes 48-63)
Row 4: [64 68 72 76]   (bytes 64-79)
```

For `t[1:4, 1:3]` (rows 1-3, cols 1-2), selected elements at bytes:
`[20, 24, 36, 40, 52, 56]` — NOT contiguous, gaps of 8 bytes between pairs.

Pointer offset of `16 + 4 = 20` bytes gets to the first element, but then reading
sequentially gives bytes 20-44, which includes wrong elements (byte 28 = col 3, not wanted).

## Fix Applied

Replaced the body of `__getitem__(self, *slices: Slice)` with an explicit N-D element copy:

1. Parse all slices into `starts[]` + `result_shape[]`
2. Allocate fresh `ExTensor(result_shape, dtype)` — independent memory, `_is_view = False`
3. Early return for empty result
4. For each `out_flat` in `range(result_numel)`:
   - Decompose via `result._strides` into per-dim output indices
   - Map each dim: `src_idx = starts[dim] + out_idx`
   - Accumulate: `src_flat += src_idx * self._strides[dim]`
   - Copy `dtype_size` bytes from `src_data + src_flat * dtype_size` to `dst_data + out_flat * dtype_size`

## Environment Constraints

- Mojo binary not runnable locally (GLIBC version mismatch on the test host)
- Fix was validated through code analysis + pre-commit hooks + CI
- Pre-commit runs `mojo format` which validates syntax

## Pre-commit Result

All hooks passed:
- Mojo Format: PASSED
- Check for deprecated List[Type](args) syntax: PASSED
- Validate Test Coverage: PASSED
- Trim Trailing Whitespace: PASSED
- Fix End of Files: PASSED
- Check for Large Files: PASSED
- Fix Mixed Line Endings: PASSED
