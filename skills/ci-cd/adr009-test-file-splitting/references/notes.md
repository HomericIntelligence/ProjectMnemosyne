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

# Session Notes: ADR-009 Test File Splitting (Issue #3404)

## Date

2026-03-07

## Problem

test_creation.mojo (40 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file, target ≤8.

## Challenge: Explicit CI Filenames

Unlike issue #3397 where the CI used a glob pattern (`testing/test_*.mojo`), the Core Tensors
CI group uses explicit filenames. This required updating `comprehensive-tests.yml` to list all
5 new filenames.

## Challenge: Arithmetic Tight Split

40 tests into 5 files with ≤8 target = 5×8=40 exactly. Any grouping that has 7+3=10 tests
at the end violates the ≤8 target (but satisfies the ≤10 hard limit). The dtype tests (7)
and edge cases (3) total 10, so Part 5 has 10 tests (at the hard limit, not the target).

## Final Split

- test_creation_part1.mojo: 8 tests — zeros() and ones()
- test_creation_part2.mojo: 8 tests — full(), empty(), from_array_1d() placeholder
- test_creation_part3.mojo: 8 tests — from_array_2d/3d placeholders, arange(), eye() square
- test_creation_part4.mojo: 6 tests — eye() rectangular/offset, linspace()
- test_creation_part5.mojo: 10 tests — dtype support and edge cases (at hard limit)

## CI Update Required

The Core Tensors pattern in comprehensive-tests.yml used explicit filenames. Updated:

```yaml
# Before:
pattern: "... test_creation.mojo ..."

# After:
pattern: "... test_creation_part1.mojo test_creation_part2.mojo test_creation_part3.mojo test_creation_part4.mojo test_creation_part5.mojo ..."
```

## Outcome

All pre-commit hooks passed (mojo format, validate-test-coverage, check-yaml).
PR #4126 created, auto-merge enabled.
