---
name: adr-009-test-file-split
description: "Split Mojo test files exceeding the ADR-009 limit of 10 fn test_ functions per file. Use when: (1) CI shows intermittent heap corruption crashes in a Mojo test group, (2) a test file has >10 fn test_ functions, (3) implementing ADR-009 compliance."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 has a heap corruption bug (`libKGENCompilerRTShared.so` JIT fault) triggered by high test load |
| **Workaround** | ADR-009 mandates ≤10 `fn test_` functions per `.mojo` test file |
| **Symptom** | CI group fails intermittently (~65% failure rate) with JIT fault crashes |
| **Fix** | Split offending file into part1/part2 files, each ≤8 tests (buffer below limit) |

## When to Use

- A Mojo test file has >10 `fn test_` functions
- CI workflow shows a test group with intermittent `libKGENCompilerRTShared.so` crashes
- Adding new tests to a file that is already near the 10-test limit
- Reviewing test files for ADR-009 compliance as part of code review

## Verified Workflow

### 1. Count tests in the offending file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Plan the split

- Target ≤8 tests per file (not 10 — leave buffer)
- Group logically related tests together
- Name files `test_<original>_part1.mojo` and `test_<original>_part2.mojo`

### 3. Create part1 file

Add the ADR-009 header comment at the very top (before the docstring):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Module docstring..."""
```

Copy ~8 test functions + their shared imports + an updated `fn main()`.

### 4. Create part2 file

Same ADR-009 header. Copy remaining test functions + imports + `fn main()`.

### 5. Delete the original file

```bash
git rm tests/path/to/test_file.mojo
```

### 6. Check the CI workflow glob pattern

The workflow typically uses `testing/test_*.mojo` — verify the split files are covered:

```bash
grep -n "test_" .github/workflows/comprehensive-tests.yml | grep -i testing
```

If the pattern already covers `test_*.mojo` in the right directory, **no workflow changes are needed**.

### 7. Commit

```bash
git add tests/path/to/test_<original>_part1.mojo tests/path/to/test_<original>_part2.mojo
git rm tests/path/to/test_<original>.mojo
git commit -m "fix(ci): split test_<original>.mojo into 2 files per ADR-009"
```

## Key Observations

- **The glob pattern saves you**: Workflows using `test_*.mojo` globs automatically discover split files — no workflow YAML edits needed in most cases
- **`validate_test_coverage.py`**: Check if it explicitly references the original filename; if it uses glob discovery it needs no changes
- **Buffer matters**: Use ≤8 tests per file, not exactly 10 — gives room for future test additions without immediately violating ADR-009
- **`fn main()` must be updated**: Each split file needs its own `fn main()` that only calls its own test functions
- **Pre-commit passes automatically**: Mojo format hook, deprecated syntax check, and test coverage validation all pass for split files without extra work

### Pre-commit hooks: run one at a time

```bash
pixi run pre-commit run mojo-format --files path/to/test_part1.mojo path/to/test_part2.mojo
pixi run pre-commit run trailing-whitespace --files path/to/test_part1.mojo path/to/test_part2.mojo
pixi run pre-commit run end-of-file-fixer --files path/to/test_part1.mojo path/to/test_part2.mojo
```

**Do NOT** pass multiple hook names in a single `pixi run pre-commit run` call — syntax error.
Use `pixi run pre-commit run` directly (not `just pre-commit`) — `just` is not installed in
worktree shell environments.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Editing the CI workflow pattern | Considered updating `testing/test_*.mojo` pattern to explicitly list new filenames | Not needed — the existing glob `testing/test_*.mojo` already matches `test_layer_testers_part1.mojo` and `test_layer_testers_part2.mojo` | Check the existing glob pattern before editing the workflow; it often already works |
| Checking `validate_test_coverage.py` for hardcoded references | Searched for the original filename in the script | No matches found — script uses dynamic discovery | Always check both the CI workflow AND validate scripts before assuming changes are needed |
| Multi-hook pre-commit | `pixi run pre-commit run hook1 hook2 --files ...` | pre-commit CLI doesn't accept multiple hook names in one call | Run hooks one at a time or use `pre-commit run --all-files` |
| Background pre-commit via run_in_background | Ran full pre-commit in background, checked output file | Output file remained 0 bytes during session (task still running) | Use foreground for pre-commit hooks; background only for genuinely independent long tasks |
| `just pre-commit` | Ran `just pre-commit` to use project's justfile recipe | `just` not installed in worktree shell environment | Use `pixi run pre-commit run` directly in worktrees |

## Results & Parameters

**Session context**: `tests/shared/testing/test_layer_testers.mojo` had 14 `fn test_` functions (limit: 10).

**Split**:

- `test_layer_testers_part1.mojo`: 8 tests (dtype consistency, invalid value checks, utility functions, relu/sigmoid backward)
- `test_layer_testers_part2.mojo`: 6 tests (tanh backward, linear backward, conv backward, batchnorm training/inference/backward)

**CI group**: `Shared Infra & Testing` — pattern `testing/test_*.mojo` — no workflow changes needed.

**Pre-commit results**: All hooks passed on first commit attempt.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3483, PR #4330 — split `test_layer_testers.mojo` (14 tests → 2 files, 8/6); CI glob auto-covered | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3503, PR #4381 — split `test_pipeline.mojo` (13 tests → 2 files, 8/5); CI glob auto-covered; no `validate_test_coverage.py` update needed | [notes.md](../../references/notes.md) |
