---
name: mojo-noncontiguous-reshape-fix
description: 'Fix flat-index bugs in Mojo tensor ops that ignore strides on non-contiguous
  inputs. Use when: debugging wrong element order after transpose/slice, or implementing
  copy loops that must respect non-C-order layouts.'
category: debugging
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Tensor ops using `_get_float64(i)` (flat byte offset) produce wrong element order when the source is non-contiguous (transposed, sliced with non-unit strides) |
| **Root Cause** | `_get_float64(i)` computes `offset = i * dtype_size`, ignoring `_strides` entirely |
| **Fix Pattern** | Branch on `is_contiguous()`: fast flat copy for contiguous, stride-based byte copy for non-contiguous |
| **Template** | `as_contiguous()` in `shared/core/shape.mojo` already has the correct non-contiguous pattern |
| **Scope** | `reshape()` in `shared/core/shape.mojo`; same bug may exist in other copy loops |

## When to Use

- A tensor operation produces wrong values after `transpose()` or stride manipulation
- Debugging "silent corruption" where values are in the wrong order but no error is raised
- Implementing any element-wise copy loop over a source tensor that may be non-contiguous
- Code review: any loop calling `_get_float64(i)` or `_set_float64(i)` on an arbitrary input tensor

## Verified Workflow

### Quick Reference

```mojo
# The correct pattern for any copy loop over a potentially non-contiguous source:
if is_contiguous(tensor):
    for i in range(total_elements):
        var val = tensor._get_float64(i)          # flat index OK
        result._set_float64(i, val)
else:
    var src_shape = tensor.shape()
    var ndim = len(src_shape)
    var dtype_size = tensor._get_dtype_size()
    var src_ptr = tensor._data
    var dst_ptr = result._data
    for i in range(total_elements):
        var remaining = i
        var src_elem_offset = 0
        for d in range(ndim - 1, -1, -1):
            var coord = remaining % src_shape[d]
            remaining //= src_shape[d]
            src_elem_offset += coord * tensor._strides[d]
        var src_byte_offset = src_elem_offset * dtype_size
        var dst_byte_offset = i * dtype_size
        for b in range(dtype_size):
            dst_ptr[dst_byte_offset + b] = src_ptr[src_byte_offset + b]
```

**Key invariant**: `_strides` values are in **elements** (not bytes). Multiply by `dtype_size`
to get byte offsets. The inner loop copies raw bytes to handle all dtypes uniformly.

### Step 1 — Identify the bug

Look for copy loops calling `_get_float64(i)` on a source tensor that could be non-contiguous:

```bash
grep -n "_get_float64(i)" shared/core/*.mojo
```

Any site that doesn't first call `is_contiguous()` is a potential bug.

### Step 2 — Understand stride semantics

`ExTensor._strides` is a `List[Int]` where `strides[d]` is the number of **elements** to skip
when advancing by 1 in dimension `d`. For a C-order (row-major) `(3,4)` tensor:
`strides = [4, 1]`. After transpose: `strides = [1, 4]`, `shape = [4, 3]`.

`_get_float64(i)` computes `offset = i * dtype_size` — a flat byte offset that only works
when `strides[d] == product(shape[d+1:])` (i.e., C-order contiguous).

### Step 3 — Apply the fix

Replace the flat copy loop with the two-path pattern from Quick Reference above.
The non-contiguous path converts flat output index `i` → multi-dim coords (via repeated `%`
and `//` against the source shape) → strided element offset → byte offset.

### Step 4 — Write regression tests

Simulate a transposed tensor by directly mutating `_shape` and `_strides`:

```mojo
# Simulate transpose of (3,4) row-major tensor → (4,3) view with strides (1,4)
var t = arange(0.0, 12.0, 1.0, DType.float64)
var t2 = reshape(t, [3, 4])
t2._shape[0] = 4
t2._shape[1] = 3
t2._strides[0] = 1
t2._strides[1] = 4
# Now reshape to [12] — must give [0,4,8,1,5,9,2,6,10,3,7,11]
var result = reshape(t2, [12])
```

Use `List[Float64]` with literal syntax: `var expected: List[Float64] = [0, 4, 8, ...]`
(NOT `List[Float64](0, 4, 8, ...)` — variadic constructor does not exist in Mojo 0.26.1).

### Step 5 — Compute expected values manually

For a transposed (4,3) view with strides (1,4) over data `[0..11]`:
- Flat output index `i` → coords `(row = i // 3, col = i % 3)`
- Source element offset `= row * 1 + col * 4`
- Values: `[0,4,8, 1,5,9, 2,6,10, 3,7,11]`

Always verify by hand before writing the assertion — wrong expected values mask the fix.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Wrong expected values in test | Used strides `(1,3)` on shape `(3,4)` expecting `[0,4,8,...]` | Stride formula gave `[0,3,6,9,1,4,...]` instead | Must compute expected values from actual stride formula, not intuitively |
| `List[Float64](0,4,8,...)` constructor | Tried variadic init for expected list | Mojo 0.26.1 has no variadic `List` constructor | Use literal syntax: `var x: List[Float64] = [0, 4, 8, ...]` |
| Calling `as_contiguous()` inside fix | Considered materializing contiguous copy first | Would allocate an extra tensor; also `as_contiguous()` had same flat-index bug | Implement stride loop inline; do not chain through another buggy function |
| Using `_get_float64_at_byte_offset` | Plan mentioned using a hypothetical method | Method doesn't exist on ExTensor | Use `_data` pointer + manual byte arithmetic for dtype-agnostic copy |

## Results & Parameters

**Issue**: #4084 — Fix flat-index bug in reshape() for non-contiguous inputs

**Files changed**:

- `shared/core/shape.mojo` — `reshape()` lines 239-244 replaced with contiguous/non-contiguous branch
- `tests/shared/core/test_reshape_noncontiguous.mojo` — 4 regression tests (new file)

**Test command**:

```bash
pixi run mojo build tests/shared/core/test_reshape_noncontiguous.mojo -o /tmp/test_reshape && /tmp/test_reshape
```

**All 4 tests pass**:

- `test_reshape_noncontiguous_column_major` — core regression from issue
- `test_reshape_contiguous_unchanged` — no regression on contiguous path
- `test_reshape_noncontiguous_2d_to_2d` — non-trivial output shape
- `test_reshape_noncontiguous_preserves_dtype` — dtype preservation

**Existing tests unaffected**:

- `test_shape.mojo` — all pass
- `test_shape_regression.mojo` — all pass
