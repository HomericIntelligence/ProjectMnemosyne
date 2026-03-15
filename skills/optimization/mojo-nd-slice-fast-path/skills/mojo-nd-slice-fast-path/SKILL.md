---
name: mojo-nd-slice-fast-path
description: "Add a contiguous-memcpy fast-path for N-D tensor slices where only the first axis is non-trivially sliced. Use when optimizing batch-extraction in training loops."
category: optimization
date: 2026-03-15
user-invocable: false
---

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Replace O(numel × ndim) element-wise byte copy with a single `memcpy` for the common first-axis-only slice pattern (e.g. `data[0:16, :, :, :]`) |
| Outcome | Implemented and verified in ProjectOdyssey PR #4772 (issue #3697) |

## When to Use

- Adding a fast-path to an N-D tensor `__getitem__(*slices)` implementation in Mojo
- The tensor uses type-erased `UnsafePointer[UInt8]` storage in row-major (C-order) layout
- The common access pattern is first-axis-only slicing (batch extraction: `data[start:end, :, :, :]`)
- Profiling shows the element-wise inner loop is the bottleneck
- You want to keep a correct slow-path fallback for non-qualifying slices

## Verified Workflow

### Quick Reference

Detection condition (post-normalization):

```mojo
var is_first_axis_only = True
for dim in range(1, num_dims):
    if starts[dim] != 0 or result_shape[dim] != self._shape[dim]:
        is_first_axis_only = False
        break
```

Fast-path execution:

```mojo
if is_first_axis_only:
    var src_byte_offset = starts[0] * self._strides[0] * dtype_size
    var byte_count = result_numel * dtype_size
    memcpy(
        dest=dst_ptr,
        src=src_ptr + src_byte_offset,
        count=byte_count,
    )
else:
    # existing element-wise loop unchanged
    ...
```

### Step 1 — Confirm import availability

`memcpy` lives in the `memory` stdlib module. Add it to the existing import if not present:

```mojo
from memory import UnsafePointer, memset_zero, alloc, bitcast, memcpy
```

No other imports are needed.

### Step 2 — Identify variable names in your `__getitem__`

Before inserting the fast-path, read the existing implementation to confirm:

- `starts: List[Int]` — per-dimension start indices (post-normalization, post-clamping)
- `result_shape: List[Int]` — shape of the output tensor (= `end - start` per dim after clamping)
- `self._shape: List[Int]` — original tensor shape
- `self._strides: List[Int]` — row-major strides in elements
- `result_numel: Int` — total element count of the output
- `dtype_size: Int` — bytes per element (from `self._get_dtype_size()` or equivalent)
- `dst_ptr` / `src_ptr` — `UnsafePointer[UInt8]` to destination/source raw storage

### Step 3 — Detection condition

After computing `starts`, `result_shape`, and `result_numel` but **before** any element-wise loop:

```mojo
var is_first_axis_only = True
for dim in range(1, num_dims):
    if starts[dim] != 0 or result_shape[dim] != self._shape[dim]:
        is_first_axis_only = False
        break
```

**Why `result_shape[dim] != self._shape[dim]`?**
Since `result_shape[dim] = clamped_end - clamped_start` and we already checked `starts[dim] == 0`,
the full-dimension condition is exactly `result_shape[dim] == self._shape[dim]` — no need for a
separate `ends` list.

**Step does NOT handle step != 1.** If your implementation ignores `Slice.step` (as extensor.mojo
does for the multi-dim overload), no change is needed. If you support strided slices, add a step
check: `steps[dim] == 1` for dim >= 1.

### Step 4 — Fast-path memcpy branch

```mojo
if is_first_axis_only:
    var src_byte_offset = starts[0] * self._strides[0] * dtype_size
    var byte_count = result_numel * dtype_size
    memcpy(
        dest=dst_ptr,
        src=src_ptr + src_byte_offset,
        count=byte_count,
    )
else:
    for out_flat in range(result_numel):
        # ... existing element-wise loop unchanged ...
```

`src_ptr + src_byte_offset` works because `UnsafePointer[UInt8]` pointer arithmetic is in bytes.
`self._strides[0]` is in elements, so multiply by `dtype_size` to get bytes.

### Step 5 — Tests (ADR-009: ≤10 fn per file)

Five tests cover the critical cases:

| Test | What it checks |
|------|---------------|
| `test_fast_path_shape_4d` | Shape `[0:16, :, :, :]` on `[50, 3, 32, 32]` → `[16, 3, 32, 32]` |
| `test_fast_path_values_3d` | Byte values at key flat positions match expected sequential values |
| `test_fast_path_matches_element_wise` | Verify every element equals the expected source element |
| `test_slow_path_inner_dim_slice` | `[:, 1:3, :]` still produces correct results (slow-path regression) |
| `test_fast_path_dtype_float64` | Fast path works with 8-byte elements |

Key assertion pattern (accessing raw bytes via bitcast):

```mojo
var data_ptr = sliced._data.bitcast[Float32]()
assert_almost_equal(Float64(data_ptr[0]), 24.0, Float64(1e-5))
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Track separate `ends` list | Planned to track `ends[dim]` alongside `starts[dim]` in the loop to check `ends[dim] == self._shape[dim]` | Unnecessary — since `result_shape[dim] = clamped_end - clamped_start` and `starts[dim] == 0`, the check `result_shape[dim] == self._shape[dim]` is equivalent without adding another list | Exploit what's already computed; avoid new data structures when the detection can be derived from existing variables |
| Add `steps` tracking | Considered tracking `steps[dim]` to also guard against strided inner-dim slices | The existing multi-dim `__getitem__` ignores `Slice.step` entirely (it's unimplemented for N-D); adding step tracking would be dead code | Read the existing implementation before adding guards — only guard what the code actually supports |
| Place fast-path after `dtype_size` computation | Initial plan put the branch immediately before the element-wise loop but after `dtype_size` | The placement is correct and works; no issue here | Confirmed: insert after `result_numel`, `dtype_size`, `src_ptr`, `dst_ptr` are all declared |

## Results & Parameters

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4772, issue #3697 | [notes.md](../../references/notes.md) |

### Key Numbers

- Source tensor shape tested: `[50, 3, 32, 32]` (CIFAR-10 batch extraction)
- Slice pattern: `data[0:16, :, :, :]` → shape `[16, 3, 32, 32]`
- Fast-path condition: O(ndim) detection loop, O(1) byte offset, single `memcpy`
- Slow-path: unchanged element-wise loop with per-element byte copy

### Copy-Paste Config

```mojo
# 1. Import (add memcpy if not present)
from memory import UnsafePointer, memset_zero, alloc, bitcast, memcpy

# 2. Detection (after starts/result_shape/result_numel/dtype_size are computed)
var is_first_axis_only = True
for dim in range(1, num_dims):
    if starts[dim] != 0 or result_shape[dim] != self._shape[dim]:
        is_first_axis_only = False
        break

# 3. Branch
if is_first_axis_only:
    var src_byte_offset = starts[0] * self._strides[0] * dtype_size
    memcpy(dest=dst_ptr, src=src_ptr + src_byte_offset, count=result_numel * dtype_size)
else:
    for out_flat in range(result_numel):
        # ... unchanged element-wise loop ...
```
