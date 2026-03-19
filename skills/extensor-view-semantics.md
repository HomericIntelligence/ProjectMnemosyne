---
name: extensor-view-semantics
description: 'Add view/zero-copy semantics to tensor operations in Mojo ExTensor.
  Use when: implementing stride-based tensor views, adding ravel()/transpose() view
  support, or debugging non-contiguous tensor access.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | extensor-view-semantics |
| **Category** | architecture |
| **Repo** | HomericIntelligence/ProjectOdyssey |
| **Issue** | #3236 |
| **PR** | #3794 |
| **Branch** | `3236-auto-impl` |

## When to Use

- Implementing zero-copy tensor views (transpose, reshape, slice) in Mojo ExTensor
- Adding stride-aware element access that works for both contiguous and non-contiguous tensors
- Debugging incorrect values from tensor operations that use raw buffer access on view tensors
- Designing reference-counted tensor views with shared ownership

## Verified Workflow

### 1. Understand the existing ExTensor structure

Key fields in `ExTensor`:

- `_data: UnsafePointer[UInt8]` — raw byte buffer
- `_is_view: Bool` — marks shared-ownership views
- `_refcount: UnsafePointer[Int]` — shared reference count
- `_strides: List[Int]` — element strides per dimension (in elements, not bytes)
- `_shape: List[Int]` — dimension sizes
- `__copyinit__`: increments `_refcount[]`
- `__del__`: decrements `_refcount[]`, frees if hits zero

### 2. Add `_nd_index_to_flat_offset` for stride-aware index conversion

```mojo
fn _nd_index_to_flat_offset(self, linear_idx: Int) -> Int:
    var dtype_size = self._get_dtype_size()
    var ndim = len(self._shape)
    var remaining = linear_idx
    var element_offset = 0
    for i in range(ndim - 1, -1, -1):
        var coord = remaining % self._shape[i]
        remaining //= self._shape[i]
        element_offset += coord * self._strides[i]
    return element_offset * dtype_size
```

This converts a flat linear index → ND coordinates → byte offset using per-dimension strides.

### 3. Add `view_with_strides` to create zero-copy views

```mojo
fn view_with_strides(self, new_shape: List[Int], new_strides: List[Int]) -> ExTensor:
    var result = self  # __copyinit__ increments refcount
    result._is_view = True
    result._shape = List[Int]()
    for i in range(len(new_shape)):
        result._shape.append(new_shape[i])
    result._strides = List[Int]()
    for i in range(len(new_strides)):
        result._strides.append(new_strides[i])
    var n = 1
    for i in range(len(new_shape)):
        n *= new_shape[i]
    result._numel = n
    return result^
```

`var result = self` triggers `__copyinit__`, incrementing refcount.
`return result^` moves the value out without an extra copy.

### 4. Update all `_get_*` / `_set_*` accessors to branch on contiguity

```mojo
fn _get_float32(self, index: Int) -> Float32:
    var offset: Int
    if self.is_contiguous():
        var dtype_size = self._get_dtype_size()
        offset = index * dtype_size
    else:
        offset = self._nd_index_to_flat_offset(index)
    return self._data.offset(offset).bitcast[Float32]()[]
```

Apply the same pattern to `_get_float64`, `_get_int64`, `_set_float32`, `_set_float64`, `_set_int64`.

### 5. Implement `transpose()` as a view using `view_with_strides`

```mojo
fn transpose(tensor: ExTensor, perm: Optional[List[Int]] = None) -> ExTensor:
    var ndim = len(tensor._shape)
    var resolved_perm: List[Int]
    # ... resolve default perm as reversed axes ...

    var input_shape = tensor._shape
    var result_shape = List[Int](capacity=ndim)
    for axis in resolved_perm:
        result_shape.append(input_shape[axis])
    var result_strides = List[Int](capacity=ndim)
    for axis in resolved_perm:
        result_strides.append(tensor._strides[axis])
    return tensor.view_with_strides(result_shape, result_strides)
```

### 6. Contiguify inputs in `matmul()` for kernel correctness

The flat-buffer matmul kernel assumes contiguous layout (`a_ptr[i * a_cols + k]`). Non-contiguous views produce wrong results.

```mojo
fn matmul(a: ExTensor, b: ExTensor) -> ExTensor:
    var a_cont = a if a.is_contiguous() else as_contiguous(a)
    var b_cont = b if b.is_contiguous() else as_contiguous(b)
    # ... rest of kernel uses a_cont, b_cont ...
```

Import `as_contiguous` from `shared.core.shape`.

### 7. Fix tests that read raw buffer directly

Tests using `result._data.bitcast[Float32]()[i]` bypass stride logic and give wrong values for views. Replace with `result._get_float32(i)` which is stride-aware.

### 8. Update `ravel()` view test

Remove the stale TODO comment and add an explicit `assert_true(b._is_view, ...)`:

```mojo
fn test_ravel_view(ctx: TestContext) raises:
    var a = ExTensor[DType.float32]([2, 3])
    # ... fill data ...
    var b = ravel(a)
    assert_true(b._is_view, "ravel of contiguous tensor should return a view")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Raw buffer access in test | `result._data.bitcast[Float32]()[i]` to read transposed view | Reads underlying buffer in original (non-permuted) order, gives wrong values | Always use `_get_float32(i)` for stride-aware access in view tests |
| Flat index in `_get_float32` without contiguity check | `offset = index * dtype_size` always | Non-contiguous tensors (after transpose) have wrong element offsets | Add `is_contiguous()` branch; use `_nd_index_to_flat_offset` otherwise |
| Calling `as_contiguous` in matmul directly on `a` | Forgot matmul uses pointer arithmetic assuming flat layout | Transposed view has correct strides but kernel still read wrong positions | Must materialize to contiguous buffer before passing to flat-buffer kernels |
| Double-transpose raw buffer test concern | Worried `transpose(transpose(a))` might still be non-contiguous | Mathematical verification: default perm reversal twice = identity, strides restored to C-order | Safe to use raw buffer access only after verifying contiguity is restored |

## Results & Parameters

### Files Modified

```text
shared/core/extensor.mojo   - Added _nd_index_to_flat_offset, view_with_strides, updated 6 accessors
shared/core/matrix.mojo     - transpose() now returns view, matmul() contiguifies inputs
tests/shared/core/test_shape.mojo   - Removed stale TODO, added _is_view assertion
tests/shared/core/test_matrix.mojo  - Fixed raw buffer access, added 5 new view tests
```

### New Tests Added

```text
test_transpose_returns_view       - assert _is_view is True
test_transpose_view_strides       - assert permuted strides correct
test_transpose_view_values        - assert stride-aware element access correct
test_transpose_view_refcount      - assert refcount incremented on view creation
test_transpose_chained_views      - assert chained transpose(transpose(x)) gives original values
```

### Key Insight: `view_with_strides` refcount safety

```mojo
var result = self    # __copyinit__ → refcount++
result._is_view = True
# ... mutate shape/strides/numel in place ...
return result^      # move (no copy) → refcount stays at incremented value
```

The original tensor still holds its refcount. When both go out of scope, refcount correctly
reaches zero and memory is freed once.
