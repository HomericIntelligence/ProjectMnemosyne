# Session Notes — badge-count-drift-prevention

## Context

- **Issue**: ProjectOdyssey #3307 — "Automate test count badge to avoid drift"
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3307-auto-impl
- **PR**: #3923
- **Date**: 2026-03-07

## Objective

The `[![Tests](...tests-247%2B...)](tests/)` badge in README.md was manually updated
and had already drifted (actual: 223, badge: 247 = 10.8% over threshold). A CI step or
pre-commit hook should keep it accurate automatically.

## Files Created / Modified

- `scripts/check_test_count_badge.py` — new script (count, parse, check, update, main)
- `tests/scripts/test_check_test_count_badge.py` — 22 pytest tests
- `.pre-commit-config.yaml` — new `check-test-count-badge` hook
- `README.md` — badge updated 247+ → 223+, prose updated 247+ → 223+

## Test Results

```
22 passed in 1.11s
```

All pre-commit hooks passed on final commit.

## Key Numbers

- Actual test count at implementation time: 223
- Previous badge value: 247 (10.8% drift — just over 10% threshold)
- Tolerance chosen: 10%
- Time to first passing commit: ~3 attempts (ruff formatting issue on first two)

## Root Cause of Key Bug

`count_test_files` was returning 0 because the worktree root path
`/home/mvillmow/Odyssey2/.worktrees/issue-3307/` contains `worktrees/` as a substring,
so every absolute path returned by `find` matched the `worktrees/` exclusion pattern.

Fix: strip `repo_root + "/"` prefix from each path before checking exclusions.
