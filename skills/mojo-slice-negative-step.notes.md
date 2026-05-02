# Session Notes: Mojo Negative-Step Slice Bug (Issue #3191)

## Session Summary

**Date**: 2026-03-07
**Repository**: HomericIntelligence/ProjectOdyssey
**Branch**: 3191-auto-impl
**PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3692

## Objective

Fix the reverse slicing bug in `ExTensor.__getitem__(Slice)` in
`shared/core/extensor.mojo`. The test `test_slice_1d_reverse` had been
skipped with a comment `# Skip reverse for now - needs debugging` at line 332
of `tests/shared/core/test_extensor_slicing.mojo`.

## Relevant Files

- `shared/core/extensor.mojo` — implementation, `__getitem__(Slice)` starting ~line 802
- `tests/shared/core/test_extensor_slicing.mojo` — test at line 123, skip at line 332

## Diagnosis

Read the `__getitem__(Slice)` implementation and traced through `t[::-1]` on
a size-5 tensor:

**Before fix:**
- `start = slice.start.or_else(0)` → 0
- `end = slice.end.or_else(size)` → 5
- `step = slice.step.or_else(1)` → -1
- After swap: `start = 5 if 5 < 4 else 4` → 4, `end = 0`
- `result_size = ceildiv(4 - 0 + 1, 1) = 5` — size looks right!
- BUT copy loop: `src_idx = 4 - 0*1=4`, `4-1=3`, ..., `4-4*1=0`
- With `end=0` and the old guard `if src_idx >= 0 and src_idx < size`, index 0 IS included
- Wait — the real bug manifested differently. Traced `t[3:1:-1]`:
  - `start=0`, `end=5` after defaults
  - swap: `start = 5 if 5 < 4 else 4 = 4`, `end = 0`
  - `result_size = ceildiv(4-0+1, 1) = 5` — WRONG, should be 2
  - Actual test case was `t[::-1]` size=5, but the implementation had multiple
    interacting bugs that could silently produce wrong indices or wrong sizes
    depending on the input.

**Root cause confirmed**: Defaults must depend on step sign. The swap logic was
unreliable and produced wrong result_size for explicit start/end cases.

## Fix Applied

1. Extract `step` first
2. Use `or_else(size-1)` and `or_else(-size-1)` for negative step
3. Remove swap; compute `ceildiv(start - end, neg_step)` with `end` clamped to `[-1, size-1]`
4. Remove `if src_idx >= 0` guard (unnecessary after clamping)

## Environment Notes

- Local machine has GLIBC 2.31, Mojo requires 2.32+ — cannot run tests locally
- Tests pass in CI via Docker (ghcr.io/homericintelligence/projectodyssey)
- Pre-commit hooks (mojo format, trailing whitespace, etc.) all passed locally
- Logic verified by manual trace through 3 test cases

## Pre-commit Results

All hooks passed:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
