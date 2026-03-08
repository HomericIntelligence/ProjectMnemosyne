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

# Session Notes: ADR-009 Test File Splitting (Issue #3403)

## Date

2026-03-07

## Problem

test_generic_transforms.mojo (42 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file (target ≤8). CI Data Transforms group failed 13/20 recent runs.

## Approach: Complete Replacement

Unlike #3397 (partial split, source file kept), this used complete replacement:

- All 42 tests moved out of the original file
- Original file deleted (`git rm`)
- 6 brand-new `_partN.mojo` files created

## Split Distribution

| File | Tests | Contents |
|------|-------|----------|
| test_generic_transforms_part1.mojo | 7 | Identity + Lambda |
| test_generic_transforms_part2.mojo | 7 | Conditional + Clamp (first 3) |
| test_generic_transforms_part3.mojo | 6 | Clamp (last 3) + Debug |
| test_generic_transforms_part4.mojo | 7 | Type conversions + Sequential (first 3) |
| test_generic_transforms_part5.mojo | 7 | Sequential (last 2) + Batch |
| test_generic_transforms_part6.mojo | 8 | Integration + Edge cases |

## Actions Taken

1. Read source file to map all 42 tests across categories
2. Planned logical groupings (Identity+Lambda, Conditional+Clamp, etc.)
3. Created 6 new files, each with ADR-009 header comments BEFORE the docstring
4. Deleted original with `git rm`
5. Verified counts: `grep -c "^fn test_" <file>` for each part
6. Confirmed CI glob `transforms/test_*.mojo` covers new files — no workflow changes needed
7. All pre-commit hooks passed: mojo format, validate test coverage, etc.

## Key Insight

ADR-009 comment must be placed BEFORE the docstring (as `#` comments at file top), not inside
the `"""..."""` docstring. The issue template showed it inside the docstring, which is incorrect.

## Final State

- 6 files, all ≤8 tests each (max: 8, min: 6)
- 42 total test functions preserved
- CI glob transforms/test_*.mojo covers new files automatically
- PR #4122 created, auto-merge enabled
