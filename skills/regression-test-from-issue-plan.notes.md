# Session Notes: Issue #4088

## Date

2026-03-15

## Objective

Fix `as_contiguous()` to use stride-based indexing (GitHub issue #4088). The issue described adding a
regression test `test_contiguous_stride_correct_values` that was planned in issue #3392 but never added.

## Repository

ProjectOdyssey (`HomericIntelligence/ProjectOdyssey`)

## Files Changed

- `tests/shared/core/test_utility_part2.mojo` — added `test_contiguous_stride_correct_values`

## Key Findings

### The fix was already in main

`as_contiguous()` in `shared/core/shape.mojo` was fixed in commit `a894e5e6` to use stride-based
indexing. The issue was that the paired regression test `test_contiguous_stride_correct_values`
(specified in the issue #3392 plan) was never added.

### Existing PR #4746 had CI failures

PR #4746 existed for issue #4088 but CI failed on:

- pre-commit hook failures
- test coverage validation
- precommit-benchmark

The missing piece was the named regression test.

### Test file split constraint

`tests/shared/core/test_utility.mojo` had 43 tests — far exceeding the 10-test limit.
The fix added 8 tests to `test_utility_part2.mojo` (which had room remaining in its limit).

### How to find the expected values

Issue #3392 comments contained the exact hand-computed expected values for the `[2, 3]` tensor
with column-major strides `[1, 2]`. Reading cross-referenced issue comments is reliable for this
pattern.

### Stride arithmetic for the test

For a `[2, 3]` tensor with manually set strides `[1, 2]` (column-major):

- Element at logical position `[row, col]` is at offset `row*1 + col*2`
- Output `[0,0]` = src`[0]` = 0.0
- Output `[0,1]` = src`[2]` = 2.0
- Output `[0,2]` = src`[4]` = 4.0
- Output `[1,0]` = src`[1]` = 1.0
- Output `[1,1]` = src`[3]` = 3.0
- Output `[1,2]` = src`[5]` = 5.0

### Import requirements

```mojo
from shared.core import ExTensor, arange, as_contiguous
```

### Pre-commit validation

```bash
SKIP=mojo-format pixi run pre-commit run --files tests/shared/core/test_utility_part2.mojo
```

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4868
