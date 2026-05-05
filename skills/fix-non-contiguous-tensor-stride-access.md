---
name: fix-non-contiguous-tensor-stride-access
description: 'Fix tensor operations that silently produce wrong values for non-contiguous
  views by replacing flat index offset with stride-based multi-dimensional indexing.
  Use when: element access uses i*dtype_size instead of strides, as_contiguous or
  copy functions assume stride-1 layout. Also covers the concatenate() axis-0
  non-contiguous else-branch flat-index bug and result_elem_offset tracking.'
category: debugging
date: 2026-03-07
version: 1.1.0
user-invocable: false
absorbed:
  - fix-concatenate-noncontiguous-stride-bug
---
## Overview

| Field | Value |
| ------- | ------- |
| **Issue** | Tensor element access using flat offset `i * dtype_size` instead of stride-based indexing |
| **Symptom** | Silent wrong values for transposed/sliced (non-contiguous) tensors |
| **Root Cause** | `_get_float64(i)` assumes contiguous stride-1 layout |
| **Fix Pattern** | Decompose flat index to per-dimension coords, multiply by actual `_strides` |
| **Codebase** | ProjectOdyssey — `shared/core/shape.mojo`, `shared/core/extensor.mojo` |

## When to Use

- A tensor copy, flatten, or conversion function produces wrong values for transposed tensors
- An element access helper uses `index * dtype_size` as the byte offset (flat layout assumption)
- `is_contiguous()` is `False` but the function still reads as if stride-1
- Test: create `arange(0..12).reshape(3,4)`, transpose, call function — check if values match expected transpose

## Verified Workflow

### 1. Identify the Bug Pattern

Search for element access using flat offset:

```mojo
fn _get_float64(self, index: Int) -> Float64:
    var offset = index * dtype_size  # BUG: flat offset, ignores strides
```

Any function calling `_get_float64(i)` on a potentially non-contiguous tensor inherits this bug.

### 2. Confirm Non-Contiguous Path Exists

Check if the function has a contiguous / non-contiguous branch:

```mojo
if is_contiguous(tensor):
    # memcpy - correct
else:
    for i in range(numel):
        var val = tensor._get_float64(i)  # BUG HERE
        result._set_float64(i, val)
```

### 3. Apply the Fix — Stride-Based Decomposition

Replace flat access with stride-based multi-dimensional indexing.
The reference implementation lives in `ExTensor.slice()` (extensor.mojo:988-1002):

```mojo
else:
    # Non-contiguous - use stride-based indexing to read source elements
    var shape = tensor.shape()
    var ndim = len(shape)
    var result = ExTensor(shape, tensor.dtype())
    var numel = tensor.numel()
    var dtype_size = tensor._get_dtype_size()
    var src_ptr = tensor._data
    var dst_ptr = result._data

    for i in range(numel):
        # Convert flat output index i to multi-dimensional coords (C-order),
        # then compute source byte offset using the tensor's actual strides.
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

Key points:
- Iterate dimensions from **innermost to outermost** (`ndim-1` down to `0`) for C-order decomposition
- `remaining //= shape[d]` propagates quotient to next outer dimension
- `coord * tensor._strides[d]` uses actual strides (not shape-derived strides)
- Copy raw bytes to avoid dtype conversion overhead

### 4. Write a Regression Test

The existing test only checked `is_contiguous()` and strides, not element values.
Add a value-correctness test:

```mojo
fn test_as_contiguous_values_correct() raises:
    """Regression: as_contiguous() must use stride-based access for non-contiguous views."""
    var shape = List[Int]()
    shape.append(3)
    shape.append(4)
    var a = arange(0.0, 12.0, 1.0, DType.float32)
    var b = a.reshape(shape)
    var t = transpose_view(b)  # shape (4, 3), strides [1, 4] — non-contiguous

    var c = as_contiguous(t)

    # Row 0 of transpose = col 0 of original: 0, 4, 8
    assert_almost_equal(c._get_float64(0), 0.0, 1e-6, "c[0,0]")
    assert_almost_equal(c._get_float64(1), 4.0, 1e-6, "c[0,1]")
    assert_almost_equal(c._get_float64(2), 8.0, 1e-6, "c[0,2]")
    # Row 1: 1, 5, 9  — Row 2: 2, 6, 10  — Row 3: 3, 7, 11
    assert_almost_equal(c._get_float64(3), 1.0, 1e-6, "c[1,0]")
    assert_almost_equal(c._get_float64(11), 11.0, 1e-6, "c[3,2]")
```

### 5. Scan for Other Occurrences

The same bug may exist in other shape functions that call `_get_float64(i)` on source tensors:

```bash
grep -n "_get_float64(i)\|_get_float64(src_idx)\|_get_float64(adjusted_idx)" \
  shared/core/shape.mojo
```

Functions to audit: `tile()`, `repeat()`, `broadcast_to()`, `permute()`, `concatenate()` (non-contiguous path), `reshape()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use `_get_float64(i)` directly | Called existing helper with flat index | Computes `offset = i * dtype_size` — correct only for stride-1 (contiguous) tensors; for transpose with strides [1,4] reads wrong positions | `_get_float64` is NOT stride-aware; never call it on non-contiguous source tensors |
| Check strides after `as_contiguous()` | Verified `_strides` and `is_contiguous()` return value | Strides are correctly set on the output (result is contiguous), but input was read with flat offsets | Contiguity of output does not validate correctness of input reads |
| Running mojo test locally | `pixi run mojo test tests/...` | GLIBC version mismatch (`GLIBC_2.32/2.33/2.34` not found) — tests only run in Docker/CI | Always verify logic via mental walkthrough and CI; local mojo execution unavailable on this host |

## Results & Parameters

### Fix Location

- **File**: `shared/core/shape.mojo`
- **Function**: `as_contiguous()`, lines 90-119 (non-contiguous else branch)
- **Reference implementation**: `ExTensor.slice()` in `shared/core/extensor.mojo:988-1002`

### Mental Verification

For a (3,4) arange tensor transposed to (4,3) with strides `[1, 4]`:

- Flat output index `i=1` → should be `t[0,1]` = original `b[1,0]` = 4
- `d=1`: `coord = 1 % 3 = 1`, `remaining = 0`, `src_elem_offset += 1 * 4 = 4`
- `d=0`: `coord = 0 % 4 = 0`, `remaining = 0`, `src_elem_offset += 0`
- Reads byte at `4 * dtype_size` → value 4 ✓

### PR Reference

- Issue: #3391 (ProjectOdyssey)
- PR: #4079 — all pre-commit hooks passed (mojo format, test count validation, trailing whitespace)

## Concatenate-Specific Non-Contiguous Fix

Absorbed from `fix-concatenate-noncontiguous-stride-bug` (2026-03-15, issue #4083, PR #4865).
This is a follow-on to the `as_contiguous()` fix above — the same flat-index bug in the
`concatenate()` axis-0 non-contiguous else-branch.

**Scope warning**: The general-axis branch (non-zero `actual_axis`) in `concatenate()` also uses
raw memcpy with flat offsets — a separate unaddressed bug. Issue #4083 was scoped to axis-0 only.

### Bug Location

In `shared/core/shape.mojo`, `concatenate()`, axis-0 branch:

```mojo
if actual_axis == 0:
    var offset_bytes = 0
    for tensor_idx in range(num_tensors):
        var t = tensors[tensor_idx]
        var t_numel = t.numel()
        var t_bytes = t_numel * dtype_size

        if is_contiguous(t):
            memcpy(...)      # correct
        else:
            for i in range(t_numel):
                var val = t._get_float64(i)      # BUG: flat offset, ignores strides
                result._set_float64(offset_bytes // dtype_size + i, val)

        offset_bytes += t_bytes
```

### Fix — Stride-Aware Byte Copy with `result_elem_offset` Tracking

Replace the buggy else-branch. Key addition over `as_contiguous()`: track `result_elem_offset`
to accumulate the base element index in the result for each tensor:

```mojo
else:
    var t_shape = t.shape()
    var t_ndim = len(t_shape)
    var result_elem_offset = offset_bytes // dtype_size
    for i in range(t_numel):
        var remaining = i
        var src_elem_offset = 0
        for d in range(t_ndim - 1, -1, -1):
            var coord = remaining % t_shape[d]
            remaining //= t_shape[d]
            src_elem_offset += coord * t._strides[d]
        var src_byte_offset = src_elem_offset * dtype_size
        var dst_byte_offset = (result_elem_offset + i) * dtype_size
        var src_ptr = t._data.bitcast[UInt8]()
        var dst_ptr = result._data.bitcast[UInt8]()
        for b in range(dtype_size):
            dst_ptr[dst_byte_offset + b] = src_ptr[src_byte_offset + b]
```

### Regression Test — Direct `_strides` Mutation

Use direct `_strides` mutation (not `transpose_view()`) to isolate the concatenate path:

```mojo
fn test_concat_noncontiguous_axis0() raises:
    """Regression: concatenating a non-contiguous tensor along axis=0."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(3)
    var t = zeros(shape, DType.float32)

    # Fill flat memory with FP-exact values (no rounding noise)
    t._set_float64(0, 0.0)
    t._set_float64(1, 0.5)
    t._set_float64(2, 1.0)
    t._set_float64(3, -0.5)
    t._set_float64(4, -1.0)
    t._set_float64(5, 1.5)

    # Override strides to column-major [1, 2]: non-contiguous
    t._strides[0] = 1
    t._strides[1] = 2

    var pad = zeros(shape, DType.float32)
    var tensors: List[ExTensor] = []
    tensors.append(t)
    tensors.append(pad)

    var result = concatenate(tensors, axis=0)
    # With strides [1, 2] and shape (2, 3), C-order flat traversal:
    #   i=0: coords (0,0) → mem[0]=0.0  i=1: coords (0,1) → mem[2]=1.0
    #   i=2: coords (0,2) → mem[4]=-1.0 i=3: coords (1,0) → mem[1]=0.5
    assert_value_at(result, 0,  0.0, 1e-6, "result[0]")
    assert_value_at(result, 1,  1.0, 1e-6, "result[1]")
    assert_value_at(result, 2, -1.0, 1e-6, "result[2]")
    assert_value_at(result, 3,  0.5, 1e-6, "result[3]")
```

**Why `_strides` mutation vs `transpose_view()`**: isolates the test to the concatenate path
without depending on `transpose_view()` availability or correctness.

### Audit Command for Other Flat-Index Occurrences

```bash
grep -n "_get_float64(i)\|_get_float64(j)\|_get_float64(idx)" shared/core/shape.mojo
```

Functions to audit after fixing concatenate: `tile()`, `repeat()`, `broadcast_to()`, `permute()`, `stack()`.

### Concatenate-Specific Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assumed `as_contiguous()` had the same bug | Read issue expecting both functions to be buggy | `as_contiguous()` was already fixed (issue #3391, PR #4079) | Always read source before assuming — check what was already fixed |
| Assumed general-axis branch was in scope | Issue said "non-contiguous else branch" (plural) | Issue explicitly scoped to axis-0 path; general-axis is a separate bug | Match scope precisely to the issue description |
| Running tests locally | `pixi run mojo test ...` | GLIBC version mismatch — mojo test runtime unavailable on this host | Use `just test-group` or CI; local mojo execution unavailable |

### Concatenate PR Reference

- Issue: #4083 (ProjectOdyssey)
- PR: #4865 — follow-up to issue #3391 / PR #4079
- Test file: `tests/shared/core/test_concatenate_noncontiguous.mojo` (3 test functions)
- Run: `just test-group "tests/shared/core" "test_concatenate_noncontiguous.mojo"`
