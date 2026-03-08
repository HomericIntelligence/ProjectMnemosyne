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

# Session Notes: ADR-009 Test File Splitting (Issue #3423)

## Date

2026-03-07

## Problem

test_arithmetic_contiguous.mojo (26 tests) was causing intermittent heap corruption in Mojo
v0.26.1 CI. ADR-009 mandates ≤10 fn test_ per file, target ≤8.

## Actions Taken

1. Read original file (26 tests across 5 logical groups)
2. Split into 4 part files (7 + 7 + 7 + 5 tests)
3. Deleted original file with `rm` + `git rm` via staging
4. Updated `.github/workflows/comprehensive-tests.yml` Core Tensors `pattern:` field
   (explicit space-separated list — NOT a glob)
5. All pre-commit hooks passed on commit

## Final State

- 4 files: test_arithmetic_contiguous_part1-4.mojo
- 26 total test functions preserved (7+7+7+5)
- PR #4188 created, auto-merge enabled

## Key Insight

The `comprehensive-tests.yml` Core Tensors group uses an explicit space-separated file list
in the `pattern:` field, NOT a glob. New files must be added manually to the list.
This is different from the testing group which uses a glob.
