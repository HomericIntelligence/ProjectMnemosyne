# Session Notes: ADR-009 Mojo Test File Splitting

**Date**: 2026-03-07
**Issue**: #3466
**PR**: #4293
**Branch**: `3466-auto-impl`

## Objective

Fix intermittent Mojo CI heap corruption by splitting `test_early_stopping.mojo`
(16 `fn test_` functions) into two files of ≤8 tests each, complying with ADR-009.

## Context

- `tests/shared/training/test_early_stopping.mojo` had 16 `fn test_` functions
- ADR-009 mandates ≤10 per file due to Mojo v0.26.1 JIT heap corruption bug
- CI `Shared Infra` group was failing 13/20 recent runs non-deterministically
- Related issue: #2942, ADR-009 at `docs/adr/ADR-009-heap-corruption-workaround.md`

## Steps Taken

1. Read the original 474-line test file to understand all 16 test functions
2. Verified CI workflow uses glob `training/test_*.mojo` (no hardcoded filenames)
3. Checked `validate_test_coverage.py` — found hardcoded filename entry to update
4. Split 16 tests into two logical groups of 8:
   - Part 1: core behavior (initialization, patience, min_delta, monitor modes)
   - Part 2: edge cases + best value tracking + verbose mode
5. Added ADR-009 header comment to each new file
6. Deleted original file
7. Updated `validate_test_coverage.py` exclusion list
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4293 with auto-merge enabled

## Key Observations

- The CI workflow uses `training/test_*.mojo` glob — no workflow file changes needed
- `validate_test_coverage.py` uses exact filenames in exclusion list — must update
- Pre-commit hooks include a `Validate Test Coverage` hook that catches stale filenames
- `git add` on the deleted file path works correctly (stages the deletion)
- Logical grouping of tests (by category) makes the split easier to review

## Files Changed

- **Deleted**: `tests/shared/training/test_early_stopping.mojo`
- **Created**: `tests/shared/training/test_early_stopping_part1.mojo` (8 tests)
- **Created**: `tests/shared/training/test_early_stopping_part2.mojo` (8 tests)
- **Updated**: `scripts/validate_test_coverage.py`
