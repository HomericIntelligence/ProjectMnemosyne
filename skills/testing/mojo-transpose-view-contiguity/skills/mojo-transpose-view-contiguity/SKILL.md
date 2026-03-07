---
name: mojo-transpose-view-contiguity
description: "Add stride-based transpose_view() to Mojo ExTensor for testing contiguity contracts. Use when: tests use direct _strides mutation, needing realistic non-contiguous tensors for is_contiguous()/as_contiguous() tests."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Issue** | Tests for `is_contiguous()` and `as_contiguous()` used direct `_strides` mutation as a hack |
| **Root Cause** | No `transpose_view()` existed; tests simulated non-contiguous layout manually |
| **Solution** | Add `transpose_view()` that copies raw bytes + overwrites strides with permuted values |
| **Result** | Tests use realistic axis-permuted non-contiguous tensors |

## When to Use

- Tests simulate non-contiguous tensors by directly mutating `_strides` field
- Need to test `is_contiguous()` returns `False` for a realistically transposed tensor
- Need to test `as_contiguous()` produces a proper C-order copy from a non-contiguous tensor
- Implementing stride-based views without reordering data in memory

## Verified Workflow

### 1. Add `transpose_view()` to `shared/core/matrix.mojo`

Add `from memory import memcpy` to file-level imports (not inside function).

Implement `transpose_view(tensor, axes=None)`:
- Same axis validation as `transpose()` (check length, duplicates, bounds)
- Build permuted shape: `result_shape[i] = input_shape[perm[i]]`
- Compute C-order input strides: iterate from `ndim-1` to `0`, multiply shape dims
- Build permuted strides: `result_strides[i] = ordered_input_strides[perm[i]]`
- Allocate `ExTensor(result_shape, dtype)` — gets default C-order strides
- `memcpy` raw bytes from input to result (flat byte copy, no reordering)
- Overwrite `result._strides = result_strides^`
- Return `result^`

Key: for shape `[3,4]` transposed to `[4,3]`:
- Input C-order strides: `[4, 1]`
- Perm (reverse): `[1, 0]`
- Permuted strides: `[1, 4]`
- C-order strides for `[4,3]` would be `[3,1]` — so `[1,4]` is non-contiguous

### 2. Export from `shared/core/__init__.mojo`

```mojo
from shared.core.matrix import (
    matmul,
    transpose,
    transpose_view,   # add this
    dot,
    outer,
    matmul_backward,
    transpose_backward,
)
```

### 3. Update tests to use `transpose_view()`

Import in test file:
```mojo
from shared.core import (
    ...
    transpose_view,
)
```

Replace `_strides` hack in `test_is_contiguous_after_transpose`:
```mojo
fn test_is_contiguous_after_transpose() raises:
    var shape = List[Int]()
    shape.append(3)
    shape.append(4)
    var a = ones(shape, DType.float32)
    var b = transpose_view(a)
    assert_false(b.is_contiguous(), "Transposed tensor should not be contiguous")
```

Replace `_strides` hack in `test_contiguous_on_noncontiguous`:
```mojo
fn test_contiguous_on_noncontiguous() raises:
    var shape = List[Int]()
    shape.append(3)
    shape.append(4)
    var a = arange(0.0, 12.0, 1.0, DType.float32)
    var b = a.reshape(shape)
    var t = transpose_view(b)
    assert_false(t.is_contiguous(), "Transposed tensor should not be contiguous")

    var c = as_contiguous(t)
    assert_true(c.is_contiguous(), "as_contiguous() result should be contiguous")

    # Shape after transpose is [4,3]; C-order strides are [3,1]
    assert_equal_int(c._strides[0], 3, "Stride for dim 0 should be 3")
    assert_equal_int(c._strides[1], 1, "Stride for dim 1 should be 1")
```

**Critical stride math**: After `transpose_view` on `[3,4]`, result shape is `[4,3]`.
After `as_contiguous`, C-order strides for `[4,3]` are `[3,1]` — NOT `[4,1]`.

### 4. Pre-commit passes

The mojo format hook will auto-format. All hooks should pass cleanly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Inline `from memory import memcpy` inside function | Placed import inside `transpose_view` function body | Works but is bad style; inconsistent with rest of codebase | Always add imports at file top level |
| Keeping `_strides` mutation tests | Tests directly set `a._strides[0]=1; a._strides[1]=3` | Not a realistic test; doesn't exercise actual transpose code path | Use a real function that produces non-contiguous layout |
| Asserting `c._strides[0] == 4` after `as_contiguous` | Expected strides `[4,1]` for the result | After transpose `[3,4]→[4,3]`, C-order strides for `[4,3]` are `[3,1]` not `[4,1]` | Always recompute expected strides for the transposed shape, not the original |

## Results & Parameters

### transpose_view() — minimal implementation

```mojo
fn transpose_view(
    tensor: ExTensor, axes: Optional[List[Int]] = None
) raises -> ExTensor:
    var ndim = tensor.dim()
    var input_shape = tensor.shape()

    var perm = axes
    if perm is None:
        perm = List[Int](capacity=ndim)
        for i in range(ndim - 1, -1, -1):
            perm.value().append(i)

    # [validate perm — same logic as transpose()]

    var result_shape = List[Int](capacity=ndim)
    for axis in perm.value():
        result_shape.append(input_shape[axis])

    # Build C-order strides for input
    var input_strides = List[Int](capacity=ndim)
    var stride = 1
    for i in range(ndim - 1, -1, -1):
        input_strides.append(stride)
        stride *= input_shape[i]
    var ordered_strides = List[Int](capacity=ndim)
    for i in range(len(input_strides) - 1, -1, -1):
        ordered_strides.append(input_strides[i])

    var result_strides = List[Int](capacity=ndim)
    for axis in perm.value():
        result_strides.append(ordered_strides[axis])

    var result = ExTensor(result_shape, tensor.dtype())
    var total_bytes = tensor.numel() * tensor._get_dtype_size()
    memcpy(dest=result._data, src=tensor._data, count=total_bytes)
    result._strides = result_strides^
    return result^
```

### Key insight: `as_contiguous` on non-contiguous tensor

The non-contiguous path in `as_contiguous` (in `shape.mojo`) uses flat index copy:
```mojo
for i in range(numel):
    var val = tensor._get_float64(i)
    result._set_float64(i, val)
```

`_get_float64(i)` uses `offset = i * dtype_size` (flat byte address). For a `transpose_view`
result (same flat bytes, different strides), this copies the original flat data unchanged
into a new contiguous ExTensor. The result is contiguous with C-order strides for the
transposed shape.
