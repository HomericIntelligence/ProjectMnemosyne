# Session Notes: ADR-009 Test File Splitting (Issue #3433)

## Date

2026-03-07

## Problem

`tests/shared/training/test_schedulers.mojo` had 23 `fn test_` functions, exceeding the
ADR-009 ≤10 hard limit and ≤8 target per file. This caused intermittent heap corruption
(`libKGENCompilerRTShared.so` JIT fault) in the Shared Infra CI group — 13/20 recent runs
were failing.

## Initial State

Single monolithic file with 23 tests:

- 9 CosineAnnealingLR tests
- 12 ReduceLROnPlateau tests
- 2 integration tests

## Actions Taken

1. Read the issue to understand the split plan (3 files, ≤8 each)
2. Read the full original file to enumerate all 23 tests
3. Checked CI workflow (`comprehensive-tests.yml`) — existing glob `training/test_*.mojo`
   auto-discovers all files; no workflow changes needed
4. Checked `validate_test_coverage.py` — needed to update the hardcoded filename list
5. Created 3 replacement files with ADR-009 header comment:
   - `test_schedulers_part1.mojo`: 8 CosineAnnealingLR tests
   - `test_schedulers_part2.mojo`: 8 ReduceLROnPlateau tests
   - `test_schedulers_part3.mojo`: 7 edge case + integration tests
6. Deleted the original `test_schedulers.mojo`
7. Updated `scripts/validate_test_coverage.py` to reference the 3 new filenames
8. Committed — all pre-commit hooks passed (mojo format, mypy, ruff, validate-test-coverage)
9. Pushed and created PR #4216

## Key Difference vs Issue #3397

Issue #3397 (test_assertions) was an **incremental refinement** of an already-split file —
moving tests between existing split files that were still over the limit.

Issue #3433 (test_schedulers) was a **fresh wholesale split** of a single monolithic file —
simpler: read original, partition tests logically, create 3 new files, delete original.

## Final State

- 3 files, all ≤8 tests each (8 + 8 + 7 = 23 total, all preserved)
- CI glob `training/test_*.mojo` covers new files automatically — no CI changes needed
- `validate_test_coverage.py` updated with new filenames
- PR #4216 created on branch `3433-auto-impl`, auto-merge enabled

## Note on ADR-009 Header Placement

The ADR-009 comment was placed at the very top of the file (before the docstring),
consistent with the issue specification. This is correct — it documents the constraint
at the file level.
