# Session Notes: mojo-hash-shape-test

## Session Date

2026-03-07

## Issue

GitHub Issue #3380 — "Add __hash__ test for shape-different tensors same data"
Follow-up from #3164.

## Objective

Add `test_hash_different_shapes_differ` to `tests/shared/core/test_utility.mojo` verifying
that a `[3]` tensor with values `[1,2,3]` and a `[1,3]` tensor with the same values hash
differently.

## Steps Taken

1. Read `.claude-prompt-3380.md` to understand the task.
2. Read `tests/shared/core/test_utility.mojo` to learn existing hash test patterns.
3. Added `test_hash_different_shapes_differ` function after `test_hash_small_values_distinguish`.
4. Added call to `test_hash_different_shapes_differ()` in `main()`.
5. Staged and committed — all pre-commit hooks passed on first attempt.
6. Pushed branch and created PR #4054 with auto-merge enabled.

## Key Observations

- All hash tests use `raise Error(...)` pattern (not `assert_*` helpers) for inequality checks.
- `arange(1.0, 4.0, 1.0, DType.float32)` produces `[1, 2, 3]` (3 elements).
- `reshape` is called as `t2 = t2.reshape(shape)` (reassignment, not in-place).
- `List[Int]` must be built with `.append()` calls — no literal syntax.
- Mojo binary cannot run locally (GLIBC_2.32/2.33/2.34 not available on Debian 10); CI (Docker) validates.
- Pre-commit hooks include a test-count badge validator — adding a new test updated the badge automatically.

## Environment

- Branch: `3380-auto-impl`
- Working dir: `/home/mvillmow/Odyssey2/.worktrees/issue-3380`
- OS: Linux (Debian 10, GLIBC 2.28 — too old for Mojo binary)
- PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4054
