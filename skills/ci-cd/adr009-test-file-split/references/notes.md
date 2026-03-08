# Session Notes: ADR-009 Test File Split

## Context

- **Date**: 2026-03-08
- **Issue**: #3495 — fix(ci): split test_evaluation.mojo (13 tests) — Mojo heap corruption (ADR-009)
- **Branch**: `3495-auto-impl`
- **PR**: #4366

## Problem Description

`tests/shared/training/test_evaluation.mojo` contained 13 `fn test_` functions, exceeding the
ADR-009 limit of 10. This caused intermittent `libKGENCompilerRTShared.so` JIT fault crashes in
Mojo v0.26.1 under CI load. The "Shared Infra & Testing" CI group was failing 13/20 recent runs
non-deterministically.

## Discovery Process

1. Read `.claude-prompt-3495.md` for task description
2. Read `tests/shared/training/test_evaluation.mojo` — confirmed 13 `fn test_` functions
3. Grepped `comprehensive-tests.yml` for "Shared Infra" — found glob pattern `training/test_*.mojo`
4. Grepped `validate_test_coverage.py` for `test_evaluation` — found exact filename reference at line 85

## Key Decision: No CI Workflow Changes Needed

The `comprehensive-tests.yml` workflow uses pattern:
```
training/test_*.mojo
```
This glob automatically matches `test_evaluation_part1.mojo` and `test_evaluation_part2.mojo`,
so no changes to the workflow file were needed.

## Split Logic

- Part 1 (8 tests): grouped by function being tested (struct, main eval functions, simple eval, topk basic)
- Part 2 (5 tests): topk edge cases + integration tests
- Kept all imports identical in both files to avoid missed dependencies

## Pre-commit Hook Results

All hooks passed on first attempt:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Bandit Security Scan: Passed
- mypy: Passed
- Ruff Format Python: Passed
- Ruff Check Python: Passed
- Validate Test Coverage: Passed

## Commit Hash

`7b0d0441` → new commit on branch `3495-auto-impl`

## PR

`gh pr merge --auto --rebase 4366` — auto-merge enabled
