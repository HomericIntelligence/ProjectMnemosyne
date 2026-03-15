---
name: mojo-getitem-slice-multidim
description: "Pattern for extending a rank-restricted Mojo __getitem__(Slice) to N-D tensors with axis-0 semantics. Use when: a Mojo tensor raises an error for non-1D slicing but the logic generalises to higher ranks."
category: architecture
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-getitem-slice-multidim |
| **Category** | architecture |
| **Issue** | #3696 – Extend `__getitem__(Slice)` to support multi-dimensional slicing |
| **PR** | #4771 |
| **Repo** | HomericIntelligence/ProjectOdyssey |
| **Language** | Mojo 0.26.1 |

This skill documents the pattern used to extend a Mojo tensor's single-slice
`__getitem__(Slice)` from 1D-only to N-D (axis-0 semantics), matching NumPy
behaviour where `t[1:3]` on a 2D tensor returns rows 1 and 2.

## When to Use

- A Mojo method raises `Error("... only supported for 1D tensors")` but the
  intent applies to axis 0 of any rank.
- You need `t[start:end:step]` on tensors with rank > 1 where inner dims are
  preserved.
- You want to support strided/reverse slicing on multi-dimensional tensors
  without touching the existing `__getitem__(*slices: Slice)` variadic overload.
- You are writing tests for a Mojo tensor class and need the ADR-009 split
  (≤10 `fn test_` per file) to avoid heap corruption in Mojo v0.26.1.

## Verified Workflow

### Quick Reference

```text
1. Identify the rank guard (raise Error("... only supported for 1D tensors"))
2. Extract start/end/step + result_size computation above the guard
3. Branch on len(self._shape) == 1 vs else
4. In else: use _strides[0] * dtype_size as slab_bytes; copy per axis-0 index
5. Result shape: [result_size, shape[1], shape[2], ...]
6. Create new test file (≤10 fn test_ per ADR-009)
```

### Step-by-step

**1. Read the existing implementation first.**

Locate the `__getitem__(self, slice: Slice)` overload. Understand:

- How `start`, `end`, `step`, `result_size` are computed (they apply to
  axis 0 regardless of rank).
- How byte-level copying works (`dtype_size`, `src_offset`, `dst_offset`).
- Whether `_strides[0]` gives the number of elements per axis-0 slab
  (it does in row-major layout).

**2. Remove the rank guard and unify result_size computation.**

```mojo
# BEFORE
if len(self._shape) != 1:
    raise Error("Single slice only supported for 1D tensors")
var size = self._shape[0]
...

# AFTER – keep all the start/end/step/result_size logic, just remove the guard
var size = self._shape[0]   # axis 0 size — works for any rank
...
var result_size: Int
if step < 0:
    ...
    result_size = max(0, ceildiv(start - end, neg_step))
else:
    ...
    result_size = max(0, ceildiv(end - start, step))
```

**3. Branch on rank for the copy phase.**

```mojo
var dtype_size = self._get_dtype_size()
var src_ptr = self._data

if len(self._shape) == 1:
    # 1D path – unchanged element copy loop
    var shape = List[Int]()
    shape.append(result_size)
    var result = Self(shape, self._dtype)
    result._is_view = False
    var dst_ptr = result._data
    # ... element-by-element copy ...
    return result^
else:
    # N-D path – copy axis-0 slabs
    var result_shape = List[Int]()
    result_shape.append(result_size)
    for d in range(1, len(self._shape)):
        result_shape.append(self._shape[d])

    var result = Self(result_shape, self._dtype)
    result._is_view = False
    var dst_ptr = result._data

    var inner_numel = self._strides[0]   # elements per axis-0 slab
    var slab_bytes = inner_numel * dtype_size

    if step < 0:
        var neg_step = -step
        for i in range(result_size):
            var src_axis0 = start - i * neg_step
            var src_offset = src_axis0 * slab_bytes
            var dst_offset = i * slab_bytes
            for b in range(slab_bytes):
                dst_ptr[dst_offset + b] = src_ptr[src_offset + b]
    else:
        for i in range(result_size):
            var src_axis0 = start + i * step
            var src_offset = src_axis0 * slab_bytes
            var dst_offset = i * slab_bytes
            for b in range(slab_bytes):
                dst_ptr[dst_offset + b] = src_ptr[src_offset + b]

    return result^
```

**Key invariant**: `_strides[0]` in row-major layout equals the product of all
dimensions except axis 0. This is the number of elements per axis-0 slab and
is always correct for contiguous tensors.

**4. Write tests — ADR-009 limit of ≤10 `fn test_` per file.**

Create a new `test_extensor_slicing_multidim.mojo` (do not add to existing
1D/2D test files). Cover:

| Test | What it checks |
|------|----------------|
| `test_slice_2d_axis0_basic` | `t[1:3]` on (4,5) → shape (2,5), correct values |
| `test_slice_2d_axis0_full` | `t[:]` on (3,4) → full copy, shape unchanged |
| `test_slice_2d_axis0_step2` | `t[::2]` on (6,3) → every-other-row |
| `test_slice_2d_axis0_reverse` | `t[::-1]` on (3,4) → reversed rows |
| `test_slice_3d_axis0_basic` | `t[1:3]` on (4,3,2) → shape (2,3,2) |
| `test_slice_2d_is_copy_not_view` | Mutating result does not affect original |
| `test_slice_2d_negative_start` | `t[-2:]` selects last two rows |
| `test_slice_2d_empty_result` | `t[3:1]` → shape (0, cols), numel 0 |
| `test_slice_1d_regression` | 1D forward, reverse, strided still work |

**5. Run tests before committing.**

```bash
pixi run mojo tests/shared/core/test_extensor_slicing_multidim.mojo
# Also run existing files to catch regressions:
pixi run mojo tests/shared/core/test_extensor_slicing_1d.mojo
pixi run mojo tests/shared/core/test_extensor_slicing_2d.mojo
pixi run mojo tests/shared/core/test_extensor_slicing_edge.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Declare `dst_ptr` before rank branch | `var dst_ptr: __type_of(self._data)` declared before `if/else`, assigned inside each branch | Mojo may not accept uninitialized pointer declarations; risky lifetime semantics | Declare `dst_ptr` inside each branch with `var dst_ptr = result._data` — simpler and safer |
| Reuse existing `__getitem__(*slices: Slice)` | Considered delegating to the variadic overload with a synthesised `Slice(0, size, 1)` for inner dims | Would require constructing `n-1` full-range slices dynamically; no clean way to do that in Mojo 0.26.1 with variadic args | Slab copy is simpler and more efficient for this axis-0 case |
| Keep guard, add separate `slice_axis0` method | Considered leaving `__getitem__(Slice)` 1D-only and adding a new method | Would break expected NumPy-style `t[1:3]` syntax; issue specifically asked for that syntax | Remove guard; extend in-place to preserve the expected operator interface |

## Results & Parameters

### Environment

```text
Mojo: 0.26.1 (pinned in pixi.toml)
Platform: Linux / WSL2 (GLIBC 2.35)
Test runner: pixi run mojo <file.mojo>
```

### Final implementation snippet (copy-paste ready)

```mojo
fn __getitem__(self, slice: Slice) raises -> Self:
    var size = self._shape[0]
    var step = slice.step.or_else(1)
    var start: Int
    var end: Int
    if step < 0:
        start = slice.start.or_else(size - 1)
        end = slice.end.or_else(-size - 1)
    else:
        start = slice.start.or_else(0)
        end = slice.end.or_else(size)
    if start < 0: start = size + start
    if end < 0:   end   = size + end
    var result_size: Int
    if step < 0:
        var neg_step = -step
        start = max(0, min(start, size - 1))
        end   = max(-1, min(end, size - 1))
        result_size = max(0, ceildiv(start - end, neg_step))
    else:
        start = max(0, min(start, size))
        end   = max(0, min(end, size))
        result_size = max(0, ceildiv(end - start, step))

    var dtype_size = self._get_dtype_size()
    var src_ptr = self._data
    if len(self._shape) == 1:
        # 1D element copy (unchanged)
        ...
    else:
        # N-D slab copy
        var result_shape = List[Int]()
        result_shape.append(result_size)
        for d in range(1, len(self._shape)):
            result_shape.append(self._shape[d])
        var result = Self(result_shape, self._dtype)
        result._is_view = False
        var dst_ptr = result._data
        var slab_bytes = self._strides[0] * dtype_size
        # copy slabs ...
        return result^
```

### Test counts

- 9 new `fn test_` functions in `test_extensor_slicing_multidim.mojo`
- 0 regressions in existing 3 test files
