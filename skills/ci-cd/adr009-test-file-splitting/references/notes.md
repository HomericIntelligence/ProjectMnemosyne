# Session Notes: ADR-009 Test File Splitting

## Context

- **Issue**: #3458 - `tests/models/test_googlenet_layers.mojo` had 18 `fn test_` functions
- **ADR-009 limit**: ≤10 `fn test_` functions per file
- **CI failure rate**: 13/20 recent runs on `main` failing intermittently
- **Root cause**: Mojo v0.26.1 JIT heap corruption (`libKGENCompilerRTShared.so`) under high test load

## Approach

Read the original file, counted 18 tests, planned split into 3 groups:
- Part 1: 8 tests (inception module + branch forward passes)
- Part 2: 6 tests (concat values, initial conv, avgpool, FC)
- Part 3: 4 tests (backward passes)

## Key Discovery: CI Pattern Mismatch

The `Models` CI group uses pattern `test_*_layers.mojo`. New files like
`test_googlenet_layers_part1.mojo` do NOT match because they end in `_part1.mojo`.

Fix: Explicitly list the part files in the CI pattern alongside the glob.

## Pre-commit Hook Result

All hooks passed on first attempt:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Check YAML: Passed

## Files Changed

- DELETED: `tests/models/test_googlenet_layers.mojo`
- CREATED: `tests/models/test_googlenet_layers_part1.mojo` (8 tests)
- CREATED: `tests/models/test_googlenet_layers_part2.mojo` (6 tests)
- CREATED: `tests/models/test_googlenet_layers_part3.mojo` (4 tests)
- MODIFIED: `.github/workflows/comprehensive-tests.yml` (Models group pattern)

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4279
