# Session Notes: ADR-009 Test File Splitting

---

## Session 2: Issue #3474 — Data Samplers Group (2026-03-07)

### Problem

`tests/shared/data/samplers/test_weighted.mojo` had 15 `fn test_` functions (limit: 10, target: ≤8),
causing intermittent heap corruption in the CI Data Samplers group (13/20 recent runs failing).

### Approach

Simple 2-way split: replaced the single file with two new files:

- `test_weighted_part1.mojo` (8 tests): creation, probability, replacement
- `test_weighted_part2.mojo` (7 tests): class balancing, determinism, error handling

### Actions Taken

1. Created `test_weighted_part1.mojo` (8 tests) with ADR-009 header
2. Created `test_weighted_part2.mojo` (7 tests) with ADR-009 header
3. Deleted original `test_weighted.mojo`
4. Confirmed CI glob pattern `samplers/test_*.mojo` covers new files — no workflow change needed
5. Pre-commit hooks passed: mojo format, validate_test_coverage, trailing-whitespace

### Final State

- 2 files, 8 and 7 tests each (≤8 target met)
- All 15 original test functions preserved
- CI workflow unchanged (glob auto-picks up new files)
- PR #4312 created

### Key Insight

When doing a clean 2-way split (not redistributing across existing files), the workflow is
simpler: create two new `_part1`/`_part2` files, delete the original, done. No need to
audit existing split state or check for `.DEPRECATED` artifacts.

---

## Session 1: Issue #3397 — Testing Fixtures Group (2026-03-07)

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
