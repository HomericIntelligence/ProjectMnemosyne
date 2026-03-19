# Session Notes — stale-ci-pattern-detection

## Context

- **Issue**: #3358 — validate_test_coverage.py: detect 0-file patterns as coverage gaps
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3358-auto-impl
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4008
- **Date**: 2026-03-07

## Problem

`scripts/validate_test_coverage.py` checked that every `test_*.mojo` file was covered by at
least one CI matrix pattern. It did NOT check the inverse: that each CI pattern actually
matched at least one file. After a file rename, old patterns silently passed.

## Implementation

1. Read `validate_test_coverage.py` to understand `expand_pattern()` and `parse_ci_matrix()`
2. Added `check_stale_patterns(ci_groups, root_dir) -> List[str]` — 8 lines, reuses `expand_pattern()`
3. Called it in `main()` after `check_coverage()`; printed warnings to stderr; no exit-code change
4. Updated module docstring to mention inverse check and clarify exit code 0 behaviour
5. Wrote `tests/scripts/test_validate_test_coverage.py` with 13 pytest tests using `tmp_path` fixture

## Files Changed

- `scripts/validate_test_coverage.py` — +52 lines (function + main() block + docstring)
- `tests/scripts/test_validate_test_coverage.py` — new, 142 lines, 13 tests

## Test Results

All 13 new tests passed. Pre-existing failures in other test files (test_dashboard.py,
test_fix_build_errors.py, test_lint_configs.py, test_implement_issues.py) were unrelated
and pre-existing before this change.

## Pre-Commit

Ruff auto-formatted both files on first commit attempt. Re-staged and committed; all hooks
passed on second attempt.

## Key Insight

The inverse coverage check is a 1:1 mirror of the forward check: instead of
`set(test_files) - all_covered`, check for groups where `expand_pattern()` returns `set()`.
Sorting the stale list makes test assertions stable.