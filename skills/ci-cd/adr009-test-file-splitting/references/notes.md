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

# Session Notes: ADR-009 Test File Splitting (Issue #3436)

## Date

2026-03-07

## Problem

tests/configs/test_validation.mojo had 23 fn test_ functions, exceeding ADR-009 ≤10 limit.
CI Configs group was failing non-deterministically (13/20 recent runs).

## Initial State

Single file: tests/configs/test_validation.mojo — 23 tests across 7 logical sections:
- Required key validation (3)
- Type validation (5)
- Range validation (4)
- Enum validation (3)
- Mutual exclusivity validation (3)
- Complex validation (3)
- Validator builder (2)

## Actions Taken

1. Created test_validation_part1.mojo (8 tests) — required key + type validation
2. Created test_validation_part2.mojo (7 tests) — range + enum validation
3. Created test_validation_part3.mojo (8 tests) — exclusive + complex + validator builder
4. Deleted tests/configs/test_validation.mojo
5. Updated tests/configs/__init__.mojo to reference new filenames
6. CI workflow uses `just test-group tests/configs "test_*.mojo"` — no changes needed

## Final State

- 3 files, all ≤8 tests each (8 + 7 + 8 = 23 total)
- All original test cases preserved
- CI glob test_*.mojo covers new files automatically
- PR #4221 created, auto-merge enabled

## Key Insight

When a test file is completely replaced (not just partially split), the workflow is:
delete original → create N new files → update any package __init__.mojo references.
The CI pattern glob handles discovery automatically.
No workflow YAML changes needed if the CI job already uses a test_*.mojo glob pattern.
