# Session Notes: ADR-009 Test File Splitting

## Context

- **Issue**: #3398 — fix(ci): split test_arithmetic.mojo (58 tests) — Mojo heap corruption (ADR-009)
- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3398-auto-impl
- **PR**: #4102
- **Date**: 2026-03-07

## Problem

`tests/shared/core/test_arithmetic.mojo` had 58 `fn test_` functions in a single file.
ADR-009 mandates ≤10 `fn test_` functions per file to work around a Mojo v0.26.1 bug
where `libKGENCompilerRTShared.so` triggers a JIT fault under high test load.

CI impact: Core Tensors group was failing 13/20 recent runs non-deterministically.

## What Was Done

1. Read the original 1202-line test file to catalog all 58 tests
2. Counted tests by category:
   - Addition: 7 (test_add_shapes, test_add_values, test_add_same_shape_1d, test_add_same_shape_2d, test_add_zeros, test_add_negative_values, test_add_backward)
   - Subtraction: 7
   - Multiplication: 8
   - Division: 7
   - Floor divide: 5
   - Modulo: 5
   - Power: 6
   - Operator overloading (dunders): 5
   - DType preservation: 3
   - Shape preservation: 2
   - Error handling: 3
3. Grouped semantically into 8 parts, each ≤8 tests
4. Created 8 new files with ADR-009 header comment in each
5. Deleted original test_arithmetic.mojo
6. Updated CI workflow pattern in comprehensive-tests.yml
7. Updated tests/README.md example references
8. All 58 tests preserved, all pre-commit hooks passed

## Key Decisions

- **Semantic grouping over mechanical splitting**: Kept related tests together
  (e.g., all division tests + backward in part4) rather than alphabetical or equal-count splits
- **Conservative limit**: Used ≤8 per file despite ADR allowing ≤10, for safety margin
- **Delete original**: Cannot keep original alongside split files (would duplicate tests)
- **README update**: Updated doc example references to avoid broken examples

## Imports Optimization

Each split file imports only what it needs. For example:
- `test_arithmetic_part1.mojo` imports only `add` and `add_backward`
- `test_arithmetic_part8.mojo` imports only `add` and `multiply` (for error tests)

This keeps compilation units smaller, which also helps with the heap corruption issue.

## Pre-commit Hook Results

All hooks passed:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Markdown Lint: Passed
- All other hooks: Passed or Skipped

## Files Changed

- DELETED: `tests/shared/core/test_arithmetic.mojo`
- CREATED: `tests/shared/core/test_arithmetic_part1.mojo` (7 tests)
- CREATED: `tests/shared/core/test_arithmetic_part2.mojo` (7 tests)
- CREATED: `tests/shared/core/test_arithmetic_part3.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_part4.mojo` (7 tests)
- CREATED: `tests/shared/core/test_arithmetic_part5.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_part6.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_part7.mojo` (8 tests)
- CREATED: `tests/shared/core/test_arithmetic_part8.mojo` (5 tests)
- MODIFIED: `.github/workflows/comprehensive-tests.yml` (updated Core Tensors pattern)
- MODIFIED: `tests/README.md` (updated example references)
