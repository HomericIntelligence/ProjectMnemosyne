# Session Notes: ADR-009 Test Split (Issue #3447)

## Context

Issue #3447 required splitting `tests/shared/core/test_utils.mojo` which had 20 `fn test_` functions,
exceeding the ADR-009 limit of 10 per file.

## Root Cause

Mojo v0.26.1 has a heap corruption bug in the JIT compiler (`libKGENCompilerRTShared.so`) that
triggers under high test load. ADR-009 mandates ≤10 `fn test_` functions per file as a workaround.

## Implementation Details

- Original file: 20 tests across argmax scalar (3), argmax axis (4), top_k (6), argsort (7) categories
- Split: part1=8, part2=8, part3=4
- CI group: "Core Utilities" in `.github/workflows/comprehensive-tests.yml`
- PR: #4248

## Key Observations

1. The `main()` function in the original file said "18 tests" but grep showed 20 — always count directly
2. The validate_test_coverage.py pre-commit hook automatically verified the new files were in the CI pattern
3. Splitting by functional category (argmax/top_k/argsort) creates more maintainable test files than equal splits
4. Each new file needs its own `main()` that only calls its own tests
