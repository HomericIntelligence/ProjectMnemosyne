# Session Notes: Mojo ADR-009 Test File Split

**Date**: 2026-03-07
**Issue**: #3418
**Branch**: 3418-auto-impl
**PR**: #4174

## Context

`tests/shared/core/test_losses.mojo` contained 28 `fn test_` functions,
exceeding the ADR-009 limit of ≤10 per file. This caused intermittent CI
failures (13/20 recent runs) in the Core Loss group with Mojo v0.26.1
heap corruption (`libKGENCompilerRTShared.so` JIT fault).

## Files Changed

- DELETED: `tests/shared/core/test_losses.mojo` (28 tests)
- CREATED: `tests/shared/core/test_losses_part1.mojo` (7 tests: BCE/MSE forward)
- CREATED: `tests/shared/core/test_losses_part2.mojo` (7 tests: BCE/MSE backward + Smooth L1)
- CREATED: `tests/shared/core/test_losses_part3.mojo` (7 tests: Smooth L1 grad + Hinge + Focal)
- CREATED: `tests/shared/core/test_losses_part4.mojo` (7 tests: Focal + KL Divergence)
- UPDATED: `.github/workflows/comprehensive-tests.yml` (Core Loss group pattern)

## Key Decisions

1. **Target 7 tests/file** (not 8 or 10) — simple division of 28 tests
2. **Group by loss function type** — keeps related tests together for readability
3. **Remove `continue-on-error: true`** — was the existing workaround, no longer needed
4. **Full import block per file** — each file self-contained, imports trimmed to what's used

## Pre-commit Hook Results

All hooks passed:
- Mojo Format: Passed
- Check deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Check YAML: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Fix Mixed Line Endings: Passed

## ADR-009 Reference

`docs/adr/ADR-009-heap-corruption-workaround.md` — documents the Mojo v0.26.1
heap corruption bug and the ≤10 fn test_ per file mitigation strategy.

Related: #2942 (original heap corruption issue)
