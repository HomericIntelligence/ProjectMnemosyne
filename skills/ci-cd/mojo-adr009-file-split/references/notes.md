# Session Notes: ADR-009 File Split — test_comparison_ops.mojo (Issue #3454)

## Date

2026-03-07

## Problem

`tests/shared/core/test_comparison_ops.mojo` had 19 `fn test_` functions. ADR-009 mandates ≤10
per file to work around Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault).
The file was causing intermittent CI failures in the `Core Activations & Types` test group.

## Initial State

Single file: `tests/shared/core/test_comparison_ops.mojo` with 19 `fn test_` functions:

- equal: `test_equal_true`, `test_equal_false`, `test_equal_broadcast`
- not_equal: `test_not_equal_true`, `test_not_equal_false`, `test_not_equal_broadcast`
- less: `test_less_true`, `test_less_false`, `test_less_equal_values`, `test_less_broadcast`
- less_equal: `test_less_equal_true`, `test_less_equal_false`, `test_less_equal_broadcast`
- greater: `test_greater_true`, `test_greater_false`, `test_greater_broadcast`
- greater_equal: `test_greater_equal_true`, `test_greater_equal_false`, `test_greater_equal_broadcast`
- negatives: `test_comparison_with_negatives`

CI workflow referenced the file explicitly in `.github/workflows/comprehensive-tests.yml`
under the `Core Activations & Types` test group pattern.

## Actions Taken

1. Read original file to understand all 19 test functions
2. Read CI workflow to understand the pattern format for `Core Activations & Types` group
3. Split into 3 new files:
   - `test_comparison_ops_part1.mojo` — equal, not_equal (6 tests)
   - `test_comparison_ops_part2.mojo` — less, less_equal (6 tests)
   - `test_comparison_ops_part3.mojo` — greater, greater_equal, negatives (7 tests)
4. Added ADR-009 header comment to each new file's module docstring
5. Updated `.github/workflows/comprehensive-tests.yml` pattern from single filename to three
   space-separated filenames in the same pattern field
6. Deleted original `test_comparison_ops.mojo` with `git rm`
7. Ran `just pre-commit-all` — all hooks passed (mojo format, YAML, validate_test_coverage.py)
8. Committed and created PR #4270

## Final State

- 3 files, 6/6/7 tests each (all ≤8, well under the 10-test hard limit)
- 19 total test functions preserved
- CI workflow updated to reference all 3 new filenames
- PR #4270 created with auto-merge enabled

## Key Observations

- The CI workflow used explicit filenames (not a glob like `test_*.mojo`), so the workflow YAML
  needed updating. This is the distinguishing factor from the `adr009-test-file-splitting` skill
  which covers glob-pattern CI workflows that need no YAML changes.
- `validate_test_coverage.py` acts as a safety net: if new files are not added to the CI
  workflow, the pre-commit hook fails before the commit is created.
- Logical grouping by operation pair (equal/not_equal, less/less_equal,
  greater/greater_equal+negatives) produced clean semantic splits.
- All pre-commit hooks passed without any modifications on the first attempt.

## Commands Used

```bash
# Count tests in original file
grep -c "^fn test_[a-z]" tests/shared/core/test_comparison_ops.mojo

# Delete original after creating split files
git rm tests/shared/core/test_comparison_ops.mojo

# Verify counts in new files
grep -c "^fn test_[a-z]" tests/shared/core/test_comparison_ops_part*.mojo

# Run pre-commit validation
just pre-commit-all
```

## CI Workflow Change

```yaml
# Before (in comprehensive-tests.yml, Core Activations & Types group)
pattern: "core/test_comparison_ops.mojo"

# After
pattern: "core/test_comparison_ops_part1.mojo test_comparison_ops_part2.mojo test_comparison_ops_part3.mojo"
```
