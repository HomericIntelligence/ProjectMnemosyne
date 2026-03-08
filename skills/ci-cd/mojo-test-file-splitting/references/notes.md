# Session Notes: Mojo Test File Splitting (ADR-009)

## Context

- **Issue**: #3439 — `tests/shared/core/test_dtype_dispatch.mojo` had 22 `fn test_` functions
- **ADR**: ADR-009 limits test files to ≤10 `fn test_` functions to prevent Mojo v0.26.1 heap corruption
- **Branch**: `3439-auto-impl`
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4229
- **Date**: 2026-03-07

## Problem Details

Mojo v0.26.1 has a heap corruption bug in `libKGENCompilerRTShared.so` that triggers
non-deterministically under high test load. Files with many `fn test_` functions are
more likely to trigger the bug. CI was failing 13/20 recent runs non-deterministically.

## What Was Done

1. Read the original `test_dtype_dispatch.mojo` (531 lines, 22 tests)
2. Counted tests by section and planned a 3-way split
3. Created 3 new files:
   - `test_dtype_dispatch_part1.mojo` — 8 tests (unary + binary float)
   - `test_dtype_dispatch_part2.mojo` — 8 tests (binary int/mismatch, scalar, float-unary)
   - `test_dtype_dispatch_part3.mojo` — 6 tests (float-binary, float-scalar, 2D tensors)
4. Each file includes ADR-009 header comment
5. Each file redefines needed helper functions (identity_op, add_op, etc.)
6. Deleted original `test_dtype_dispatch.mojo`
7. Updated `.github/workflows/comprehensive-tests.yml` to reference 3 new filenames
8. Checked `validate_test_coverage.py` — no changes needed (uses glob patterns)
9. Committed and pushed; all pre-commit hooks passed
10. Created PR with auto-merge enabled

## Key Observations

- Helper functions (identity_op, add_op, mul_op, double_op) needed to be redefined in each part
- The CI workflow uses a `pattern:` field with space-separated filenames — simple string replacement
- `validate_test_coverage.py` did NOT reference the filename directly — no update needed
- Pre-commit hooks: mojo format, deprecated List syntax check, YAML check, test coverage validation all passed
- Grouping tests by logical category (unary, binary, scalar, float-only, 2D) makes the split intuitive

## Files Changed

```
tests/shared/core/test_dtype_dispatch.mojo          (deleted)
tests/shared/core/test_dtype_dispatch_part1.mojo    (created, 8 tests)
tests/shared/core/test_dtype_dispatch_part2.mojo    (created, 8 tests)
tests/shared/core/test_dtype_dispatch_part3.mojo    (created, 6 tests)
.github/workflows/comprehensive-tests.yml           (updated pattern)
```
