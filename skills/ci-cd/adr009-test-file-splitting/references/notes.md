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

# Session Notes: ADR-009 Test File Splitting (Issue #3464)

## Date

2026-03-07

## Problem

test_optimizers.mojo (16 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI
(Shared Infra group, 13/20 recent run failures). ADR-009 mandates ≤10 fn test_ per file.

## Actions Taken

1. Read test_optimizers.mojo — confirmed 16 `fn test_` functions
2. Verified CI workflow: `training/test_*.mojo` glob pattern, no workflow changes needed
3. Confirmed `validate_test_coverage.py` references the original filename in excluded list
4. Created test_optimizers_part1.mojo (8 tests): SGD (6 tests) + Adam init/update (2 tests)
5. Created test_optimizers_part2.mojo (8 tests): Adam bias correction + AdamW + RMSprop +
   property tests + PyTorch numerical validation
6. Each file: ADR-009 `#` comment block at file top (above docstring)
7. Deleted original test_optimizers.mojo
8. Updated validate_test_coverage.py: replaced single entry with 2 new filenames
9. All pre-commit hooks passed (mojo format, mypy, ruff, validate_test_coverage)
10. PR #4291 created, auto-merge enabled

## Final State

- 2 files (part1, part2), each with exactly 8 tests
- 16 total test functions preserved (all original tests present)
- CI glob training/test_*.mojo covers new files automatically
- No workflow changes needed

## Key New Insight: ADR-009 Comment Placement

The ADR-009 header comment **must be placed at the top of the file** using `#` comment syntax,
NOT inside the module docstring (`"""..."""`). Mojo does not support `#` comments inside string
literals.

**Correct:**

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# ...
"""Module docstring."""
```

**Wrong:**

```mojo
"""
# ADR-009: ...  ← # is not a comment inside a string literal in Mojo
"""
```

## Key New Insight: validate_test_coverage.py

When the original file appears in the excluded files list in `scripts/validate_test_coverage.py`,
both new split filenames must be added and the original removed, or the pre-commit
`Validate Test Coverage` hook will fail with a "file not found" error.
