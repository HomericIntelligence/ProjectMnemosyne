# Session Notes: ADR-009 Comprehensive ExTensor Audit

**Date**: 2026-03-07
**Issue**: #3476 — fix(ci): split test_extensor_new_methods.mojo (15 tests) — Mojo heap corruption (ADR-009)
**PR**: #4317

## What Happened

The issue asked to split `test_extensor_new_methods.mojo` (15 tests) into 2 files.
However, checking git history revealed this was already done in commit `8a78d3aa`:
- `test_extensor_getset_float32.mojo` (6 tests)
- `test_extensor_randn.mojo` (9 tests)
- Original renamed to `test_extensor_new_methods.mojo.DEPRECATED`

So we audited all `test_extensor_*.mojo` files and found:
- `test_extensor_slicing.mojo`: **19 tests** (exceeds limit)
- `test_extensor_unary_ops.mojo`: **12 tests** (exceeds limit)
- No "Core ExTensor" CI group existed — extensor tests buried in "Core Utilities" (26 files)

## Files Created

```
tests/shared/core/test_extensor_slicing_1d.mojo   (8 tests)
tests/shared/core/test_extensor_slicing_2d.mojo   (6 tests)
tests/shared/core/test_extensor_slicing_edge.mojo (5 tests)
tests/shared/core/test_extensor_neg_pos.mojo      (5 tests)
tests/shared/core/test_extensor_abs_ops.mojo      (7 tests)
```

## Files Deprecated

```
tests/shared/core/test_extensor_slicing.mojo → .DEPRECATED
tests/shared/core/test_extensor_unary_ops.mojo → .DEPRECATED
```

## CI Change

Added "Core ExTensor" group with 10 files, all ≤10 tests.
Removed extensor files from "Core Utilities" group.

## Key Decision: Semantic vs Generic Split Names

The issue suggested `_part1`/`_part2` naming. We used semantic names instead:
- `_1d` (basic and strided 1D slicing)
- `_2d` (multi-dimensional slicing + batch extraction)
- `_edge` (edge cases + copy semantics)
- `_neg_pos` (__neg__ and __pos__ operators)
- `_abs_ops` (__abs__ and combined operations)

Semantic names make it immediately clear what's in each file without reading it.

## Pre-commit Hook Timing

The `git commit` command ran pre-commit hooks (mojo format) which took ~90 seconds.
Pushed and created PR only after confirming commit completed.
