# Session Notes: ADR-009 Test File Splitting

## Date

2026-03-08

## Issue

GitHub Issue #3634: `tests/shared/training/test_logging_callback.mojo` had 11 `fn test_`
functions, exceeding ADR-009's limit of 10. This caused intermittent heap corruption
(`libKGENCompilerRTShared.so` JIT fault) in the `Shared Infra & Testing` CI group,
with a ~65% failure rate (13/20 recent runs on `main`).

## Raw Steps Taken

1. Read `.claude-prompt-3634.md` to understand the task
2. Read `tests/shared/training/test_logging_callback.mojo` — confirmed 11 `fn test_` functions
3. Searched `comprehensive-tests.yml` for `logging_callback` — no explicit filename found;
   CI uses the glob `training/test_*.mojo` which covers new files automatically
4. Searched `scripts/validate_test_coverage.py` — found explicit filename reference needing update
5. Created `test_logging_callback_part1.mojo` (8 tests: core, log count, train begin)
6. Created `test_logging_callback_part2.mojo` (3 tests: train end, edge cases)
7. Deleted `test_logging_callback.mojo`
8. Updated `validate_test_coverage.py` to list both new filenames
9. Staged, committed (all pre-commit hooks passed), pushed, created PR #4440, enabled auto-merge

## Key Decisions

- Split 11 → 8+3 (not 10+1 or 9+2) to stay well under the ≤10 limit
- Part1 grouped thematically: core logging + log count tracking + on_train_begin
- Part2 grouped thematically: on_train_end + edge cases (zero_interval, large_interval)
- No CI workflow edit needed — the glob pattern already matched new filenames
- ADR-009 header placed immediately before the module docstring in each file

## Files Modified

- `tests/shared/training/test_logging_callback.mojo` — DELETED
- `tests/shared/training/test_logging_callback_part1.mojo` — CREATED (8 tests)
- `tests/shared/training/test_logging_callback_part2.mojo` — CREATED (3 tests)
- `scripts/validate_test_coverage.py` — UPDATED (replaced 1 entry with 2)

## Pre-commit Hook Results

All passed: mojo format, deprecated-list-syntax check, bandit, mypy, ruff format,
ruff check, validate-test-coverage, trailing-whitespace, end-of-file-fixer,
check-yaml, large-files, mixed-line-ending.

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4440
Auto-merge enabled (rebase strategy).
