# Session Notes: BF16 Precision Recommendation

## Context

- **Date**: 2026-03-07
- **Issue**: ProjectOdyssey #3202
- **PR**: ProjectOdyssey #3710
- **Branch**: `3202-auto-impl`
- **File Modified**: `shared/training/dtype_utils.mojo`
- **Test File Modified**: `tests/shared/training/test_dtype_utils.mojo`

## Problem

`recommend_precision_dtype()` returned `DType.float16` for BOTH medium (100-999 MB) and
large (>= 1000 MB) models. The large model branch was effectively dead code with a comment
saying "FP16 strongly recommended" but never using BF16 despite `bfloat16_dtype` being
natively supported in the file.

Issue #3202 is a follow-up to #3088 which added native `DType.bfloat16` support.

## Root Cause

The large model `else` branch was written as a placeholder before BF16 support was confirmed
and never updated:

```mojo
else:
    # Large model - FP16 strongly recommended
    return DType.float16  # should have been bfloat16
```

## Implementation

Added `hardware_has_bf16: Bool = True` parameter. Apple Silicon does not support BF16,
so callers on Apple hardware must pass `hardware_has_bf16=False`. The default `True` is
safe because most x86/CUDA hardware supports BF16.

## Environment

- Mojo v0.26.1 (via pixi)
- Local GLIBC: 2.31 — cannot run Mojo tests locally
- Tests validated via CI (Docker container with GLIBC 2.32+)
- Pre-commit hooks: all passed locally

## Files Changed

- `shared/training/dtype_utils.mojo` — added `hardware_has_bf16` param, updated large model branch
- `tests/shared/training/test_dtype_utils.mojo` — updated large model assertion, added 2 new test cases

## Commit

```
feat(training): enable BF16 in recommend_precision_dtype for large models
```

## Pre-commit Output

```
Mojo Format..............................................................Passed
Check for deprecated List[Type](args) syntax.............................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Fix Mixed Line Endings...................................................Passed
```
