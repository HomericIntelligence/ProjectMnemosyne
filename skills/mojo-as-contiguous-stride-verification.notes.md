# Session Notes — mojo-as-contiguous-stride-verification

## Session Context

- **Date**: 2026-03-07
- **Issue**: ProjectOdyssey #3392 — "Add as_contiguous() test with stride-correct value verification"
- **Follow-up from**: Issue #3166 (as_contiguous() stride-indexing bug)
- **PR**: #4087
- **Branch**: `3392-auto-impl`
- **File modified**: `tests/shared/core/test_utility.mojo`

## Objective

Add a Mojo test that verifies `as_contiguous()` remaps tensor elements using
stride-based indexing, not flat-order indexing. The existing test
`test_contiguous_on_noncontiguous` only checked that the result was contiguous
and had correct strides — not that values were at the correct positions.

## Steps Taken

1. Read the issue prompt from `.claude-prompt-3392.md`
2. Located `tests/shared/core/test_utility.mojo` (641 lines)
3. Observed existing `test_contiguous_on_noncontiguous` uses `transpose_view`
   but doesn't assert value positions
4. Checked `shared/core/extensor.mojo` for `_set_float64` API
5. Checked `shared/core/__init__.mojo` to confirm `is_contiguous` export
6. Designed 2×3 column-major test tensor with manually overwritten strides
7. Hand-derived expected row-major output: `[0.0, 2.0, 4.0, 1.0, 3.0, 5.0]`
8. Added `test_contiguous_stride_correct_values()` function
9. Registered in `main()`
10. Committed (pre-commit hooks passed: mojo format, test count badge, etc.)
11. Pushed and created PR #4087 with auto-merge enabled

## Key Decision: Manually Overwrite `_strides`

Instead of relying on `transpose_view()` (which changes shape and makes value
tracing complex), we directly construct a tensor and overwrite `_strides`:

```mojo
t._strides[0] = 1
t._strides[1] = 2
```

This gives precise control over the non-contiguous layout and makes the
expected output trivially derivable from stride arithmetic.

## Why This Test Matters

The bug from #3166: `as_contiguous()` calls `_get_float64(i)` which reads
flat memory ignoring strides. The fix should use stride-based indexing to
read `_get_float64(row * stride[0] + col * stride[1])`. The new test catches
this difference — it will FAIL with the buggy implementation and PASS once
the fix from #3166 is applied.

## Environment Notes

- Mojo toolchain cannot run locally (GLIBC_2.32/2.33/2.34 not found on Debian 10)
- Tests run in CI via Docker (`ghcr.io/homericintelligence/projectodyssey:main`)
- Pre-commit hooks run via `pixi run pre-commit` and passed locally
