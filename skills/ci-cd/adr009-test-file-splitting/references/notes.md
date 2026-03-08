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

# Session Notes: ADR-009 Test File Splitting (Issue #3408)

## Date

2026-03-07

## Problem

test_test_models.mojo (37 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file (target ≤8). CI failure rate was 13/20 recent runs.

## Split Plan

Distributed 37 tests across 5 new files by semantic grouping:

- test_test_models_part1.mojo: 8 tests — SimpleCNN (4) + LinearModel (4)
- test_test_models_part2.mojo: 6 tests — SimpleMLP init (2) + forward (4)
- test_test_models_part3.mojo: 7 tests — SimpleMLP params/state_dict/zero_grad
- test_test_models_part4.mojo: 8 tests — MockLayer (5) + SimpleLinearModel init/forward (3)
- test_test_models_part5.mojo: 8 tests — SimpleLinearModel (2) + Parameter (2) + factory (2) + integration (2)

## Actions Taken

1. Read original test_test_models.mojo (37 fn test_ functions) to enumerate all tests
2. Created 5 new part files with semantic groupings and ADR-009 headers
3. Deleted test_test_models.mojo
4. Verified no CI workflow changes needed — testing/test_*.mojo wildcard covers new files
5. All pre-commit hooks passed (mojo format, validate test coverage, deprecated syntax)
6. PR #4138 created, auto-merge enabled

## Key Observations

- The `testing/test_*.mojo` wildcard pattern in comprehensive-tests.yml automatically picks up
  `test_test_models_part*.mojo` — no workflow edits needed
- Semantic groupings (by model type) produce more maintainable split files than arbitrary splits
- The ADR-009 header comment must go in the module docstring area, not as a standalone comment,
  to avoid placement issues with mojo format
- The `mojo-format` pre-commit hook places the ADR-009 comment correctly inside the docstring
