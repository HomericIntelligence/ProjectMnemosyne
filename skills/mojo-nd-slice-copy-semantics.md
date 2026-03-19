---
name: mojo-nd-slice-copy-semantics
description: 'Fix Mojo multi-dimensional tensor slicing bugs caused by pointer-offset
  view approach on non-contiguous data. Use when: (1) N-D tensor slice tests are skipped/disabled,
  (2) __getitem__(*slices) returns wrong values for 2D/3D/ND slices, (3) multi-dim
  slicing uses self.copy() + data pointer offset which fails for non-contiguous results.'
category: debugging
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Multi-dimensional tensor slicing returns wrong values or is disabled with "needs debugging" comment |
| **Root Cause** | `__getitem__(*slices)` uses `self.copy()` (shallow refcount copy) + `result._data = self._data.offset(offset_bytes)` — valid only for first-axis slicing (contiguous rows) |
| **Fix** | Replace with explicit N-D element-wise copy using per-dimension starts + original strides |
| **Files** | `shared/core/extensor.mojo` — `__getitem__(self, *slices: Slice)` |
| **Issue** | #3190 (follow-up from #3086) |
| **PR** | #3691 |

## When to Use

Trigger this skill when:

1. Multi-dimensional slice tests (`test_slice_2d_*`, `test_slice_3d_*`, `test_batch_extraction_*`) are commented out with `# Skip for now - needs debugging`
2. `__getitem__(self, *slices: Slice)` returns a tensor with correct shape but wrong values
3. The implementation does `self.copy()` followed by `result._data = self._data.offset(...)` for N-D slicing
4. Batch extraction tests for training loops fail (e.g., `data[0:batch_size, :, :, :]`)
5. A pointer-offset view approach is used for non-contiguous multi-dimensional slices

## Root Cause Analysis

### Why Pointer-Offset Fails for N-D Slicing

For a 5×4 row-major tensor, `t[1:4, 1:3]` selects rows 1-3 AND columns 1-2:

```
Source (5x4):          Result (3x2):
[  0  1  2  3 ]       [  5  6 ]
[  4  5  6  7 ]  -->  [  9 10 ]
[  8  9 10 11 ]       [ 13 14 ]
[ 12 13 14 15 ]
[ 16 17 18 19 ]
```

The selected elements are at flat indices `[5, 6, 9, 10, 13, 14]` — NOT contiguous. A single `data_pointer + offset` cannot represent this selection. Only first-axis slicing (selecting contiguous rows) is representable as a pointer offset.

### The Buggy Pattern

```mojo
fn __getitem__(self, *slices: Slice) raises -> Self:
    var result = self.copy()          # shallow copy: shares data pointer
    result._is_view = True
    var offset_bytes = 0
    for dim in range(num_dims):
        # ...compute start, end...
        result._shape[dim] = end - start
        offset_bytes += start * result._strides[dim] * dtype_size
    result._data = self._data.offset(offset_bytes)  # ❌ only correct for dim 0
    result._numel = ...
    return result^
```

This works for `t[1:4, :, :]` (first dim only, remaining dims full) but fails for `t[1:4, 1:3]` because the inner dimension selection creates gaps.

### The `Copyable` Trait and `self.copy()`

`ExTensor` implements `Copyable`, giving a `.copy()` method backed by `__copyinit__`. This is a **shallow copy** — it shares the data pointer and increments the refcount. It is NOT a deep copy. The subsequent `result._data = self._data.offset(...)` overwrites the shared pointer with a correctly-offset pointer into the original buffer — this is valid for view semantics, but insufficient for non-contiguous N-D slices.

## Verified Workflow

### Step 1: Identify the Buggy Implementation

```bash
grep -n "__getitem__.*slices" shared/core/extensor.mojo
# Look for: self.copy() + result._data = self._data.offset(offset_bytes)
```

### Step 2: Replace with Element-wise N-D Copy

Replace the entire `__getitem__(self, *slices: Slice)` body:

```mojo
fn __getitem__(self, *slices: Slice) raises -> Self:
    """Get multi-dimensional slice — returns an independent copy."""
    var num_slices = len(slices)
    var num_dims = len(self._shape)

    if num_slices != num_dims:
        raise Error(
            "Number of slices ("
            + String(num_slices)
            + ") must match number of dimensions ("
            + String(num_dims)
            + ")"
        )

    # Compute per-dimension starts and result shape
    var starts = List[Int]()
    var result_shape = List[Int]()
    for dim in range(num_dims):
        var s = slices[dim]
        var size = self._shape[dim]
        var start = s.start.or_else(0)
        var end = s.end.or_else(size)
        if start < 0:
            start = size + start
        if end < 0:
            end = size + end
        start = max(0, min(start, size))
        end = max(0, min(end, size))
        starts.append(start)
        result_shape.append(max(0, end - start))

    # Allocate result tensor (independent copy, not a view)
    var result = Self(result_shape, self._dtype)
    result._is_view = False

    var result_numel = result._numel
    if result_numel == 0:
        return result^

    # Copy each element: map output flat index -> source flat index
    var dtype_size = self._get_dtype_size()
    var src_ptr = self._data
    var dst_ptr = result._data

    for out_flat in range(result_numel):
        var src_flat = 0
        var remaining = out_flat
        for dim in range(num_dims):
            var out_idx = remaining // result._strides[dim]
            remaining = remaining % result._strides[dim]
            var src_idx = starts[dim] + out_idx
            src_flat += src_idx * self._strides[dim]
        var src_offset = src_flat * dtype_size
        var dst_offset = out_flat * dtype_size
        for b in range(dtype_size):
            dst_ptr[dst_offset + b] = src_ptr[src_offset + b]

    return result^
```

### Step 3: Re-enable Skipped Tests

In `tests/shared/core/test_extensor_slicing.mojo`, uncomment the skipped calls in `main()`:

```mojo
# Before (skipped):
# print("Testing multi-dimensional slicing...")
# test_slice_2d_single_dim()
# test_slice_2d_both_dims()
# test_slice_3d_partial()
# print("Multi-dimensional slicing: PASSED")

# After (enabled):
print("Testing multi-dimensional slicing...")
test_slice_2d_single_dim()
test_slice_2d_both_dims()
test_slice_3d_partial()
print("Multi-dimensional slicing: PASSED")
```

Also re-enable batch extraction tests and any other `# Skip for now` tests.

### Step 4: Verify

```bash
pixi run pre-commit run --files shared/core/extensor.mojo tests/shared/core/test_extensor_slicing.mojo
# All hooks should pass; CI will run the full test suite
```

## Key Insights

### Semantic Contract: Copy vs View

The 1D `__getitem__(Slice)` and the N-D `__getitem__(*slices: Slice)` should have **consistent copy semantics**:
- Both return `_is_view = False`
- Both allocate independent memory
- Mutations to the result do NOT affect the original

This is documented in `docs/adr/` and the module docstring comment block.

### When Pointer-Offset IS Correct

The view/pointer-offset approach IS correct and used in:
- `slice(start, end, axis)` — extracts a contiguous block along one axis only
- `reshape()` — same total elements, same memory layout (contiguous)

It is WRONG for `__getitem__(*slices)` when any inner dimension is non-trivially sliced.

### Strides Decomposition Algorithm

The index decomposition in the N-D copy loop is row-major standard:
```
for dim in range(num_dims):
    out_idx = remaining // result._strides[dim]
    remaining = remaining % result._strides[dim]
    src_idx = starts[dim] + out_idx
    src_flat += src_idx * self._strides[dim]
```
This correctly maps output flat index → per-dim index → source flat index using original strides.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pointer-offset view approach | `self.copy()` + `result._data = self._data.offset(offset_bytes)` | Only handles first-axis slices; inner dimension gaps are invisible to pointer arithmetic | N-D slicing is inherently non-contiguous; a single pointer offset cannot represent arbitrary dimension selections |
| Marking result as view | Setting `result._is_view = True` after shallow copy + pointer offset | View semantics imply shared memory, but test asserts `_is_view = False` for slice results; also doesn't fix the data correctness bug | Copy vs view semantics must be consistent across all `__getitem__` overloads |
| Diagnosing via local mojo run | Running `pixi run mojo test` locally | GLIBC version mismatch (`GLIBC_2.32/2.33/2.34` not found) — Mojo binary requires newer libc than available | Must rely on CI or Docker for test execution; code analysis + pattern matching is the primary debugging tool |

## Results & Parameters

### Test Coverage After Fix

| Test | Expected Result |
|------|----------------|
| `test_slice_2d_single_dim` | `t2d[1:4, :]` → shape `[3, 4]`, correct values |
| `test_slice_2d_both_dims` | `t2d[1:4, 1:3]` → shape `[3, 2]`, correct values |
| `test_slice_3d_partial` | `t3d[1:3, :, :]` → shape `[2, 3, 2]`, correct values |
| `test_batch_extraction_basic` | `data[0:16, :, :, :]` → shape `[16, 3, 32, 32]` |
| `test_batch_extraction_offset` | `data[16:32, :, :, :]` → shape `[16, 3, 32, 32]` |
| `test_batch_extraction_last_partial` | `data[48:50, :, :, :]` → shape `[2, 3, 32, 32]` |
| `test_slice_1d_reverse` | `t[::-1]` → reversed 1D tensor |

### Files Modified

| File | Change |
|------|--------|
| `shared/core/extensor.mojo` | Rewrote `__getitem__(self, *slices: Slice)` body |
| `tests/shared/core/test_extensor_slicing.mojo` | Uncommented 7 skipped test calls in `main()` |
