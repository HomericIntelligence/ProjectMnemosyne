# Session Notes: Mojo ADR-009 Test File Split

## Date
2026-03-08

## Issue
GitHub issue #3632 — `tests/shared/training/test_step_scheduler.mojo` had 11 `fn test_` functions,
exceeding ADR-009's limit of 10 per file, causing intermittent heap corruption CI failures.

## What Was Done

1. Read existing `test_step_scheduler.mojo` (267 lines, 11 test functions)
2. Read CI workflow to understand the `Shared Infra & Testing` group pattern (`training/test_*.mojo`)
3. Read `validate_test_coverage.py` to find the file reference (line 98)
4. Created `test_step_scheduler_part1.mojo` (8 tests) with ADR-009 header
5. Created `test_step_scheduler_part2.mojo` (3 tests) with ADR-009 header
6. Ran `git rm` on original file
7. Updated `validate_test_coverage.py` to reference both new files
8. Committed — all pre-commit hooks passed on first try
9. Pushed and created PR #4432

## Key Observations

- The CI workflow glob `training/test_*.mojo` automatically covered both new files — no workflow edit needed
- `validate_test_coverage.py` had an explicit list of excluded training files that needed updating
- Pre-commit hook `Validate Test Coverage` would have caught a missed update to validate_test_coverage.py
- Splitting 11 → 8+3 gives comfortable buffer below the 10-test limit

## Files Changed

- `tests/shared/training/test_step_scheduler.mojo` — deleted
- `tests/shared/training/test_step_scheduler_part1.mojo` — created (8 tests)
- `tests/shared/training/test_step_scheduler_part2.mojo` — created (3 tests)
- `scripts/validate_test_coverage.py` — updated filename references

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4432
