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

# Session Notes: ADR-009 Test File Splitting (Issue #3422)

## Date

2026-03-07

## Problem

test_shape.mojo (26 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file. The Core Tensors CI group was failing 13/20 runs.

## Initial State

Single file: test_shape.mojo with 26 fn test_ functions covering:
reshape, squeeze, unsqueeze, expand_dims, flatten, ravel, concatenate, stack, split,
tile, repeat, broadcast_to, permute, dtype preservation, flatten_to_2d.

## Actions Taken

1. Split into 4 files of ≤10 tests each:
   - test_shape_part1.mojo (9 tests): reshape, squeeze, unsqueeze, flatten/ravel
   - test_shape_part2.mojo (8 tests): concatenate, stack, split, tile
   - test_shape_part3.mojo (7 tests): repeat, broadcast_to, permute, dtype, flatten_to_2d basic
   - test_shape_part4.mojo (2 tests): flatten_to_2d additional cases
2. Each file got ADR-009 header comment in top-level docstring
3. Deleted test_shape.mojo
4. Updated .github/workflows/comprehensive-tests.yml Core Tensors pattern:
   replaced `test_shape.mojo` with 4 explicit filenames

## Final State

- 4 files, all ≤9 tests each (9+8+7+2=26 total)
- All 26 original test cases preserved
- validate_test_coverage.py passed (Core Tensors uses explicit list, but new files were added)
- All pre-commit hooks passed
- PR #4187 created, auto-merge enabled

## Key Insight — Explicit vs. Glob CI Patterns

The Core Tensors CI group uses an **explicit space-separated filename list**, not a glob:

```yaml
pattern: "test_tensors.mojo test_arithmetic.mojo ... test_shape.mojo ..."
```

This means new split files are NOT auto-discovered. The original filename must be replaced
with all new split filenames in the pattern string. This is different from groups like
"Testing Fixtures" that use `pattern: "testing/test_*.mojo"` (glob, auto-discovers).

Always check the relevant test group's pattern before finishing to determine if a CI update
is needed.
