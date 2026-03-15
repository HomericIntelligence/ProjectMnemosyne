---
name: fix-concatenate-noncontiguous-stride-bug
description: "Fix the flat-index bug in concatenate() axis-0 non-contiguous path that ignores strides and reads wrong values for transposed/view tensors. Use when: (1) concatenate() produces wrong values for non-contiguous inputs, (2) the axis-0 else-branch calls _get_float64(i) on source tensors, (3) follow-on to fix-non-contiguous-tensor-stride-access for concatenate specifically."
category: debugging
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Issue** | `concatenate()` axis-0 non-contiguous else-branch uses `_get_float64(i)` (flat index), ignoring tensor strides |
| **Symptom** | Wrong values when concatenating transposed or sliced (non-contiguous) tensors along axis=0 |
| **Root Cause** | `_get_float64(i)` computes `offset = i * dtype_size` — valid only for stride-1 contiguous tensors |
| **Fix Pattern** | Stride-aware element loop: decompose flat index → multi-dim coords → byte offset via `_strides` |
| **Codebase** | ProjectOdyssey — `shared/core/shape.mojo`, `concatenate()` axis-0 branch |
| **Related Skill** | `fix-non-contiguous-tensor-stride-access` (covers `as_contiguous()` — same root cause) |

## When to Use

- `concatenate()` produces wrong values for any input where `is_contiguous()` returns `False`
- The source tensor was created via `transpose_view()`, slicing, or direct `_strides` mutation
- You see the pattern: `var val = t._get_float64(i)` in the non-contiguous else-branch of a loop
- After applying `fix-non-contiguous-tensor-stride-access` to `as_contiguous()`, audit `concatenate()` for the same bug (issue #4083 was exactly this follow-on)

## Verified Workflow

### 1. Identify the Bug Location

In `shared/core/shape.mojo`, `concatenate()`, the axis-0 branch:

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

### 2. Apply the Fix

Replace the buggy else-branch with stride-aware byte copy (same pattern as `as_contiguous()`):

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

Key points:
- `result_elem_offset = offset_bytes // dtype_size` — base element index in result for this tensor
- Dimensions iterated innermost-to-outermost (C-order): `range(t_ndim - 1, -1, -1)`
- Raw byte copy (`for b in range(dtype_size)`) works for ALL dtypes — no dtype dispatch needed
- `t._strides[d]` uses actual tensor strides, not shape-derived strides

### 3. Write Regression Tests

Simulate a non-contiguous tensor by directly mutating `_strides`:

```mojo
fn test_concat_noncontiguous_axis0() raises:
    """Regression: concatenating a non-contiguous tensor along axis=0."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(3)
    var t = zeros(shape, DType.float32)

    # Fill flat memory with known values: indices 0..5
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

    # With strides [1, 2] and shape (2, 3), C-order flat traversal reads:
    #   i=0: coords (0,0) → mem[0*1 + 0*2]=mem[0]=0.0
    #   i=1: coords (0,1) → mem[0*1 + 1*2]=mem[2]=1.0
    #   i=2: coords (0,2) → mem[0*1 + 2*2]=mem[4]=-1.0
    #   i=3: coords (1,0) → mem[1*1 + 0*2]=mem[1]=0.5
    #   i=4: coords (1,1) → mem[1*1 + 1*2]=mem[3]=-0.5
    #   i=5: coords (1,2) → mem[1*1 + 2*2]=mem[5]=1.5
    assert_value_at(result, 0,  0.0, 1e-6, "result[0]")
    assert_value_at(result, 1,  1.0, 1e-6, "result[1]")
    assert_value_at(result, 2, -1.0, 1e-6, "result[2]")
    assert_value_at(result, 3,  0.5, 1e-6, "result[3]")
    assert_value_at(result, 4, -0.5, 1e-6, "result[4]")
    assert_value_at(result, 5,  1.5, 1e-6, "result[5]")
```

**Test values to use**: `0.0`, `0.5`, `1.0`, `-0.5`, `-1.0`, `1.5` (FP-exact, no rounding noise).

**Why direct `_strides` mutation** instead of `transpose_view()`: `transpose_view()` may not be
available or may have its own bugs; `_strides` mutation isolates the test to the concatenate path.

### 4. Audit Other `concatenate()` Branches

The general-axis branch (non-zero `actual_axis`) in `concatenate()` also uses raw `memcpy` with
flat offsets — a separate bug for non-contiguous tensors on non-zero axes. Issue #4083 scope was
limited to axis-0; file a follow-on issue for the general-axis branch if needed.

### 5. Scan for Related Occurrences

After fixing `concatenate()`, scan for other functions with the same flat-index pattern:

```bash
grep -n "_get_float64(i)\|_get_float64(j)\|_get_float64(idx)" shared/core/shape.mojo
```

Functions to audit: `tile()`, `repeat()`, `broadcast_to()`, `permute()`, `stack()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed `as_contiguous()` had the bug | Read the issue description expecting both functions to be buggy | `as_contiguous()` was already fixed in a prior PR (issue #3391, PR #4079) — only `concatenate()` remained | Always read source before assuming — `as_contiguous()` was already correct |
| Assumed general-axis branch was also in scope | Issue description mentioned "non-contiguous else branch" (plural sense) | Issue explicitly scoped to axis-0 path (lines 519-522); general-axis branch is a separate bug | Match scope precisely to what the issue describes |
| Running tests locally | `pixi run mojo test ...` | GLIBC version mismatch — mojo test runtime unavailable on this host | Use `just test-group` which wraps the mojo runner correctly; or use CI |

## Results & Parameters

### Fix Summary

- **File**: `shared/core/shape.mojo`
- **Function**: `concatenate()`, axis-0 non-contiguous else-branch
- **Lines changed**: ~3 lines replaced with ~12-line stride-aware loop
- **Pattern source**: `as_contiguous()` (same file, already fixed) — copy the loop exactly
- **Test file**: `tests/shared/core/test_concatenate_noncontiguous.mojo` (3 test functions)

### Test Run Command

```bash
just test-group "tests/shared/core" "test_concatenate_noncontiguous.mojo"
# All 3 tests PASS
```

### PR Reference

- Issue: #4083 (ProjectOdyssey)
- PR: #4865 — follow-up to issue #3391 / PR #4079
- Branch: `4083-auto-impl`
