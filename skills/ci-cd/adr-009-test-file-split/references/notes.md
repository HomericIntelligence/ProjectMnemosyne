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

---

# Session Notes: ADR-009 Test File Split (Issue #3503)

## Date

2026-03-08

## Context

- Repo: HomericIntelligence/ProjectOdyssey
- Branch: 3503-auto-impl
- Issue: #3503 - split test_pipeline.mojo (13 tests) per ADR-009
- PR created: #4381

## File split details

- Original: tests/shared/data/transforms/test_pipeline.mojo (13 fn test_)
- Part 1: test_pipeline_part1.mojo (8 tests: creation + execution + composition_start)
- Part 2: test_pipeline_part2.mojo (5 tests: append + error_handling + utilities)

## CI workflow observation

The Data group in comprehensive-tests.yml uses:

```text
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

The wildcard `transforms/test_*.mojo` picks up both split files automatically.
No workflow edit was needed.

## Pre-commit results

- mojo-format: Passed
- trailing-whitespace: Passed
- end-of-file-fixer: Passed
- validate-test-coverage: Passed (no reference to test_pipeline.mojo in the script)

## Shell environment notes

- `just` not available in worktree environments — use `pixi run` directly
- `pixi run pre-commit run` only accepts ONE hook name at a time
- Background tasks via run_in_background may not flush output during session
