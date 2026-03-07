---
name: mojo-slice-negative-step
description: "Fix negative-step slice bugs in Mojo __getitem__(Slice). Use when: reverse slicing returns empty or wrong results, result_size is 0 for t[::-1], or slice defaults are wrong for negative step."
category: debugging
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-slice-negative-step |
| **Category** | debugging |
| **Language** | Mojo |
| **Component** | `__getitem__(Slice)` on 1D tensor/array types |
| **Issue** | Reverse slicing (`t[::-1]`, `t[3:1:-1]`) produces empty or wrong results |

## When to Use

- A Mojo tensor/array `__getitem__(Slice)` returns 0 elements for `t[::-1]`
- Reverse-sliced result has wrong values (e.g. forwards instead of backwards)
- A test for negative-step slicing is skipped with comment like "needs debugging"
- `result_size = ceildiv(start - end + 1, neg_step)` is producing 0 or off-by-one

## Root Cause Pattern

Two compounding bugs appear together in hand-written Mojo slice implementations:

**Bug 1 — Wrong defaults applied before step sign is known:**

```mojo
# WRONG: applies forward defaults unconditionally
var start = slice.start.or_else(0)
var end = slice.end.or_else(size)
var step = slice.step.or_else(1)
```

For `t[::-1]`, `start` becomes 0 and `end` becomes `size`, then the swap logic
corrupts them further. Python semantics require start=last, end=sentinel(-1) for
negative step.

**Bug 2 — Broken swap + off-by-one in result_size:**

```mojo
# WRONG: swap corrupts values; +1 in ceildiv produces wrong count
var temp = start
start = end if end < size - 1 else size - 1
end = temp
result_size = max(0, ceildiv(start - end + 1, neg_step))
```

The conditional `end if end < size-1 else size-1` silently discards the user's
explicit end, and `+1` in the ceildiv causes off-by-one when end is not `-1`.

## Verified Workflow

**Step 1 — Extract step first, use sign-correct defaults:**

```mojo
var step = slice.step.or_else(1)

var start: Int
var end: Int
if step < 0:
    # Python semantics: default start=last element, end=sentinel before index 0
    start = slice.start.or_else(size - 1)
    end = slice.end.or_else(-size - 1)   # resolves to -1 after normalization
else:
    start = slice.start.or_else(0)
    end = slice.end.or_else(size)
```

**Step 2 — Normalize negative indices (same for both directions):**

```mojo
if start < 0:
    start = size + start
if end < 0:
    end = size + end
```

**Step 3 — Clamp and compute result_size without any swap:**

```mojo
if step < 0:
    var neg_step = -step
    start = max(0, min(start, size - 1))
    end = max(-1, min(end, size - 1))
    # No swap — iterate src_idx = start - i * neg_step while src_idx > end
    result_size = max(0, ceildiv(start - end, neg_step))
```

**Step 4 — Copy loop (safe, no bounds check needed after clamping):**

```mojo
for i in range(result_size):
    var src_idx = start - i * neg_step
    var src_offset = src_idx * dtype_size
    var dst_offset = i * dtype_size
    for b in range(dtype_size):
        dst_ptr[dst_offset + b] = src_ptr[src_offset + b]
```

**Verification by trace:**

| Slice | size | start | end (after norm) | result_size | Indices |
|-------|------|-------|-------------------|-------------|---------|
| `[::-1]` | 5 | 4 | -1 | 5 | 4,3,2,1,0 |
| `[3:1:-1]` | 5 | 3 | 1 | 2 | 3,2 |
| `[::-2]` | 5 | 4 | -1 | 3 | 4,2,0 |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Apply `or_else(0)` / `or_else(size)` then handle negative step | Extract step after setting defaults, then swap start/end | For `[::-1]`, start=0, end=5 after defaults; swap set start=size-1=4, end=0 giving `ceildiv(5,1)=5` but wrong sentinel: end=0 excludes index 0 | Defaults must be chosen based on step sign before any normalization |
| `ceildiv(start - end + 1, neg_step)` | Add +1 to match "inclusive end" intuition | For `t[3:1:-1]`, produces `ceildiv(3,1)=3` instead of 2; Python slice end is exclusive | Python end is always exclusive — use `ceildiv(start - end, neg_step)` with end clamped to -1 for full reverse |
| Conditional swap `start = end if end < size-1 else size-1` | Preserve user's explicit end when within bounds | Silently discards explicit end for in-bounds values, making `t[3:0:-1]` and `t[3:1:-1]` behave identically | Never conditionally discard user-provided slice bounds |

## Results & Parameters

**Copy-paste fix for `__getitem__(Slice)` in Mojo:**

```mojo
fn __getitem__(self, slice: Slice) raises -> Self:
    if len(self._shape) != 1:
        raise Error("Single slice only supported for 1D tensors")

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

    if start < 0:
        start = size + start
    if end < 0:
        end = size + end

    var result_size: Int
    if step < 0:
        var neg_step = -step
        start = max(0, min(start, size - 1))
        end = max(-1, min(end, size - 1))
        result_size = max(0, ceildiv(start - end, neg_step))
        # ... allocate result, copy loop as above ...
        return result^
    else:
        start = max(0, min(start, size))
        end = max(0, min(end, size))
        result_size = max(0, ceildiv(end - start, step))
    # ... allocate result, forward copy loop ...
```

**Key formula difference:**

| Direction | result_size formula | end sentinel |
|-----------|---------------------|--------------|
| Forward (`step > 0`) | `ceildiv(end - start, step)` | `size` (exclusive) |
| Reverse (`step < 0`) | `ceildiv(start - end, neg_step)` | `-1` (exclusive, index 0 included) |
