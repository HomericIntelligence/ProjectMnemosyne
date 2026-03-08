# Session Notes: Mojo Test File Split (Issue #3409)

## Session Context

- **Date**: 2026-03-07
- **Issue**: #3409 — fix(ci): split test_elementwise.mojo (37 tests) — Mojo heap corruption (ADR-009)
- **Branch**: `3409-auto-impl`
- **PR**: #4142

## Problem

`tests/shared/core/test_elementwise.mojo` contained 37 `fn test_` functions.
ADR-009 mandates ≤10 per file due to Mojo v0.26.1 heap corruption bug in
`libKGENCompilerRTShared.so`. CI failure rate was ~65% (13/20 recent runs).

## What Was Done

1. Read the original 1119-line test file to understand all 37 tests
2. Read `.github/workflows/comprehensive-tests.yml` to find the `Core Activations & Types` group
3. Read `scripts/validate_test_coverage.py` to understand coverage enforcement
4. Created 5 part files grouping tests by logical topic:
   - part1: abs, sign (5 tests)
   - part2: exp, log (8 tests)
   - part3: log10, log2, sqrt (8 tests)
   - part4: sin, cos (6 tests)
   - part5: clip, rounding, logical (10 tests)
5. Each file includes ADR-009 header comment and full imports
6. Deleted the original `test_elementwise.mojo`
7. Updated CI workflow pattern string to reference 5 new filenames
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4142 with `gh pr merge --auto --rebase`

## Key Observations

- `validate_test_coverage.py` uses `rglob("test_*.mojo")` to discover ALL test files
  on disk, then cross-references them against the CI workflow. The original file must
  be deleted, not just removed from the pattern.
- Mojo has no `#include` mechanism; imports must be duplicated in every part file.
- The `--label fix` flag on `gh pr create` failed because that label doesn't exist
  in the repo; dropped the flag.
- Pre-commit hooks automatically ran `mojo format` on all 5 new files and passed.
- `validate_test_coverage.py` pre-commit hook passed, confirming CI pattern update was correct.

## Files Changed

- `tests/shared/core/test_elementwise.mojo` — DELETED
- `tests/shared/core/test_elementwise_part1.mojo` — CREATED (5 tests)
- `tests/shared/core/test_elementwise_part2.mojo` — CREATED (8 tests)
- `tests/shared/core/test_elementwise_part3.mojo` — CREATED (8 tests)
- `tests/shared/core/test_elementwise_part4.mojo` — CREATED (6 tests)
- `tests/shared/core/test_elementwise_part5.mojo` — CREATED (10 tests)
- `.github/workflows/comprehensive-tests.yml` — UPDATED (pattern string)

---

# Session Notes: Mojo Test File Split (Issue #3424)

## Session Context

- **Date**: 2026-03-07
- **Issue**: #3424 — fix(ci): split test_utility.mojo (31 tests) — Mojo heap corruption (ADR-009)
- **Branch**: `3424-auto-impl`
- **PR**: #4189

## Problem

`tests/shared/core/test_utility.mojo` had 31 `fn test_` functions, exceeding ADR-009's limit of
≤10 per file. The issue description claimed 25 tests — actual count was 31. This caused
intermittent heap corruption crashes in Mojo v0.26.1 (`libKGENCompilerRTShared.so` JIT fault),
making CI non-deterministically fail.

## What Was Done

1. Grep'd actual `fn test_[a-z]` count (31, not 25 as issue stated)
2. Planned 4 logical groupings by functional area
3. Created `test_utility_part1.mojo` (7 tests): copy/clone, property accessors, strides
4. Created `test_utility_part2.mojo` (7 tests): contiguity, item(), tolist()
5. Created `test_utility_part3.mojo` (9 tests): `__len__`, `__setitem__`, `__bool__`, hash edge cases
6. Created `test_utility_part4.mojo` (8 tests): type conversions, str/repr, hash, diff()
7. Added ADR-009 header comment to each new file
8. Deleted original file with `git rm`
9. Updated `.github/workflows/comprehensive-tests.yml` Core Utilities pattern (explicit filename list)
10. All pre-commit hooks passed on first attempt

## Key Observations

- Issue description said 25 tests, actual was 31. Always grep to verify.
- This CI group used an explicit filename list (not a glob), so the workflow needed updating.
  Compare with issue #3409 where a glob auto-picked up new files automatically.
- Initial plan for part4 had 10 tests; redistributed 2 hash tests to part3 to achieve ≤8 target.
- `validate_test_coverage.py` automatically validates that all new test files appear in the CI
  workflow pattern — catches both missing files and missing workflow entries.

## Files Changed

- `tests/shared/core/test_utility.mojo` — DELETED
- `tests/shared/core/test_utility_part1.mojo` — CREATED (7 tests)
- `tests/shared/core/test_utility_part2.mojo` — CREATED (7 tests)
- `tests/shared/core/test_utility_part3.mojo` — CREATED (9 tests)
- `tests/shared/core/test_utility_part4.mojo` — CREATED (8 tests)
- `.github/workflows/comprehensive-tests.yml` — UPDATED (Core Utilities pattern)
