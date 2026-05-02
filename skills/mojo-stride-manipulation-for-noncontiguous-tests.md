---
name: mojo-stride-manipulation-for-noncontiguous-tests
description: 'Technique for testing non-contiguous tensor behavior in Mojo by directly
  manipulating _strides fields. Use when: testing is_contiguous()/as_contiguous()
  without transpose(), simulating column-major layout, or unblocking placeholder tests
  that depend on unimplemented higher-level ops.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Tests for `is_contiguous()` and `as_contiguous()` were placeholders blocked by missing `transpose()` |
| **Solution** | Directly mutate `_strides` on an `ExTensor` to produce a non-contiguous layout |
| **Context** | ProjectOdyssey Mojo ML framework, `shared/core/extensor.mojo` |
| **Issue** | #3166 (follow-up to #2722) |

## When to Use

- Placeholder tests comment out `transpose(a)` with `# TODO: implement transpose()`
- Need to verify `is_contiguous()` returns `False` for non-standard stride patterns
- Need to verify `as_contiguous()` produces row-major output from a stride-permuted tensor
- `transpose()` or other stride-permuting ops are not yet implemented but `_strides` is mutable

## Verified Workflow

### 1. Import `as_contiguous` if testing that function

```mojo
from shared.core import ExTensor, arange, as_contiguous
```

### 2. Create a normal contiguous tensor

```mojo
var a = arange(0.0, 12.0, 1.0, DType.float32)
var b = a.reshape([3, 4])  # row-major strides [4, 1]
```

### 3. Mutate strides to simulate column-major (non-contiguous)

```mojo
# Column-major for shape (3, 4): strides should be [1, rows] = [1, 3]
b._strides[0] = 1
b._strides[1] = 3
assert_false(b.is_contiguous(), "Column-major tensor should not be contiguous")
```

### 4. Call `as_contiguous()` and verify output

```mojo
var c = as_contiguous(b)
assert_true(c.is_contiguous(), "as_contiguous() result should be contiguous")
assert_equal_int(c._strides[0], 4, "Row-major stride for dim 0 (cols)")
assert_equal_int(c._strides[1], 1, "Row-major stride for dim 1")
# Values preserved in flat/linear order
for i in range(12):
    assert_value_at(c, i, Float64(i), 1e-6, "Values preserved")
```

### Key insight about `_get_float64`

`as_contiguous()`'s non-contiguous branch copies via `_get_float64(i)` which uses **flat index × dtype_size**
(not stride-based indexing). So mutating strides doesn't affect the values stored in memory — flat-order
values are preserved unchanged in the output.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use `transpose()` | Call `transpose(a)` to produce non-contiguous tensor | `transpose()` not yet implemented | Use direct stride mutation instead |
| Test without assertion | Original placeholder just called `t.is_contiguous()` without asserting | Tests that don't assert provide no value — no failure = no coverage | Always assert the expected return value |
| Assume `_get_float64` is stride-aware | Expected `as_contiguous()` to reorder values based on strides | `_get_float64` uses flat offset `index * dtype_size`, ignores strides | Flat-order values are preserved; stride mutation only affects contiguity check |

## Results & Parameters

### Strides for common shapes

| Shape | Row-major (contiguous) | Column-major (non-contiguous) |
| ------- | ------------------------ | ------------------------------- |
| (3, 4) | `[4, 1]` | `[1, 3]` |
| (2, 3) | `[3, 1]` | `[1, 2]` |
| (2, 3, 4) | `[12, 4, 1]` | `[1, 2, 6]` |

### `is_contiguous()` algorithm (extensor.mojo)

```mojo
fn is_contiguous(self) -> Bool:
    var expected_stride = 1
    for i in range(len(self._shape) - 1, -1, -1):
        if self._strides[i] != expected_stride:
            return False
        expected_stride *= self._shape[i]
    return True
```

Walks from innermost to outermost dim. Any deviation from row-major stride returns `False`.
