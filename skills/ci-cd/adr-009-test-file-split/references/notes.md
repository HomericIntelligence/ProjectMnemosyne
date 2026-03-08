# Session Notes: ADR-009 Test File Split

## Issue

GitHub issue #3483: `tests/shared/testing/test_layer_testers.mojo` had 14 `fn test_` functions,
exceeding ADR-009's limit of 10 per file. This caused intermittent heap corruption crashes
(~65% CI failure rate) in Mojo v0.26.1 via `libKGENCompilerRTShared.so` JIT faults.

## Root Cause

Mojo v0.26.1 has a known heap corruption bug triggered under high test load. ADR-009 documents
the workaround: keep ≤10 `fn test_` functions per `.mojo` file.

## Steps Taken

1. Read `.claude-prompt-3483.md` to understand the issue
2. Read `tests/shared/testing/test_layer_testers.mojo` — confirmed 14 test functions
3. Read `.github/workflows/comprehensive-tests.yml` to understand CI patterns
4. Checked `scripts/validate_test_coverage.py` for hardcoded filename references (none found)
5. Created `test_layer_testers_part1.mojo` (8 tests) with ADR-009 header
6. Created `test_layer_testers_part2.mojo` (6 tests) with ADR-009 header
7. Deleted original `test_layer_testers.mojo`
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4330

## Key Files

- `tests/shared/testing/test_layer_testers_part1.mojo` — 8 tests
- `tests/shared/testing/test_layer_testers_part2.mojo` — 6 tests
- `.github/workflows/comprehensive-tests.yml` — unchanged (glob pattern covers new files)
- `scripts/validate_test_coverage.py` — unchanged (no hardcoded references)

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4330

## Timing

2026-03-07
