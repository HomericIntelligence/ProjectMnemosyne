# Session Notes: extend-structural-test-with-value-assertions

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3842 — "Add as_contiguous() value-correctness test after transpose_view"
- **Parent issue**: #3274
- **PR**: #4812
- **Branch**: `3842-auto-impl`
- **Date**: 2026-03-15

## Problem Statement

`test_contiguous_on_noncontiguous()` in `tests/shared/core/test_utility.mojo`
only verified:

1. `t.is_contiguous() == False` (transposed tensor is non-contiguous)
2. `c.is_contiguous() == True` (result of `as_contiguous()` is contiguous)
3. `c._strides[0] == 3` and `c._strides[1] == 1` (correct row-major strides)

It did NOT verify that element values were correctly reordered. A broken
implementation that flat-copied memory bytes would pass all three checks
while producing wrong values.

## Solution

Appended 12 `assert_almost_equal` calls after the stride assertions. The
tensor was built as:

```mojo
var a = arange(0.0, 12.0, 1.0, DType.float32)  # [0..11]
var b = a.reshape(shape)   # (3, 4) row-major
var t = b.transpose(0, 1)  # (4, 3) non-contiguous
var c = as_contiguous(t)   # (4, 3) contiguous copy
```

Expected mapping (transpose stride formula: `c[j, i] = original[i, j]`):

```
Flat idx | Logical (j,i) | Original (i,j) | Expected value
---------|----------------|----------------|---------------
0        | c[0,0]         | orig[0,0]      | 0
1        | c[0,1]         | orig[1,0]      | 4
2        | c[0,2]         | orig[2,0]      | 8
3        | c[1,0]         | orig[0,1]      | 1
4        | c[1,1]         | orig[1,1]      | 5
5        | c[1,2]         | orig[2,1]      | 9
6        | c[2,0]         | orig[0,2]      | 2
7        | c[2,1]         | orig[1,2]      | 6
8        | c[2,2]         | orig[2,2]      | 10
9        | c[3,0]         | orig[0,3]      | 3
10       | c[3,1]         | orig[1,3]      | 7
11       | c[3,2]         | orig[2,3]      | 11
```

## Implementation Notes

- No new imports needed — `assert_almost_equal` already in scope
- Added a comment block explaining the mapping before the assertions
- Kept the change minimal: pure assertion additions, no refactoring
- The existing standalone tests (`test_as_contiguous_values_correct`,
  `test_as_contiguous_3d_values_correct`) were left unchanged

## Distinction from mojo-as-contiguous-stride-verification

The existing skill (`mojo-as-contiguous-stride-verification`) documents
creating a new test with manually overwritten strides (column-major `[1,2]`
for shape `[2,3]`). This session's pattern is different:

- **No stride manipulation** — uses the natural strides from `.transpose()`
- **Extends an existing test** — does not create a new test function
- **Simpler value derivation** — `arange + reshape + transpose` gives a
  fully predictable mapping without needing to reason about raw memory layout
