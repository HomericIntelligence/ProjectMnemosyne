# Session Notes: ADR-009 Test File Splitting (Issue #3397)

## Date

2026-03-07

## Problem

test_assertions.mojo (61 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file.

## Initial State (already in main)

The file had been partially split into 7 files:

- test_assertions_bool.mojo: 5 tests
- test_assertions_comparison.mojo: 8 tests
- test_assertions_equality.mojo: 8 tests
- test_assertions_float.mojo: 10 tests (AT hard limit)
- test_assertions_shape.mojo: 9 tests
- test_assertions_tensor_props.mojo: 8 tests
- test_assertions_tensor_values.mojo: 11 tests (OVER hard limit)
- test_assertions.mojo.DEPRECATED (stale artifact)

## Actions Taken

1. Created test_assertions_int.mojo (2 tests) - moved assert_equal_int tests from float file
2. Updated test_assertions_float.mojo: 10 → 8 tests
3. Created test_assertions_tensor_type.mojo (3 tests) - moved assert_type + not_equal_fails
4. Updated test_assertions_tensor_values.mojo: 11 → 8 tests
5. Deleted test_assertions.mojo.DEPRECATED

## Final State

- 9 files, all ≤9 tests each
- 59 total test functions preserved
- CI glob testing/test_*.mojo covers new files automatically
- PR #4094 created, auto-merge enabled

## Key Insight

The ADR-009 comment in SKILL.md headers contains the text "fn test_" which matches
grep "^fn test_" if placed at line start. Always use "^fn test_[a-z]" for accurate counts.

---

# Session Notes: ADR-009 Test File Splitting (Issue #3445)

## Date

2026-03-07

## Problem

test_callbacks.mojo (20 tests) was causing intermittent heap corruption in the Shared Infra CI
group (13/20 recent runs failing). ADR-009 mandates ≤10 fn test_ per file, target ≤8.

## Initial State

Single file `tests/shared/training/test_callbacks.mojo` with 20 fn test_ functions:

- 6 EarlyStopping tests
- 6 ModelCheckpoint tests
- 6 LoggingCallback tests
- 2 Integration tests

## Actions Taken

1. Created test_callbacks_part1.mojo (6 EarlyStopping tests)
2. Created test_callbacks_part2.mojo (6 ModelCheckpoint tests)
3. Created test_callbacks_part3.mojo (8 LoggingCallback + integration tests)
4. Deleted test_callbacks.mojo
5. Updated scripts/validate_test_coverage.py: replaced test_callbacks.mojo with 3 new filenames
   in the training exclusion list

## Final State

- 3 files, 6/6/8 tests each (all ≤8, well within ADR-009 limit)
- 20 total test functions preserved
- CI glob training/test_*.mojo covers new files automatically (no workflow change needed)
- PR #4244 created, auto-merge enabled

## Key Observation

When the original file is deleted (not just updated), validate_test_coverage.py must be updated
to remove the old filename and add the new filenames. The script uses an explicit exclusion list
for training tests, not a glob pattern.
