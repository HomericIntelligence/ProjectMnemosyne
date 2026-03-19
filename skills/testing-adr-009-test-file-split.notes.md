# Session Notes: ADR-009 Test File Split

## Session Context

- **Date**: 2026-03-08
- **Issue**: #3625 — fix(ci): split test_parallel_loader.mojo (12 tests) — Mojo heap corruption (ADR-009)
- **Branch**: 3625-auto-impl
- **PR**: #4416

## Problem

`tests/shared/data/loaders/test_parallel_loader.mojo` had 12 `fn test_` functions, exceeding
ADR-009's limit of 10 per file. This caused intermittent heap corruption crashes in Mojo v0.26.1
(`libKGENCompilerRTShared.so` JIT fault), making the `Data Loaders` CI group non-deterministically
fail (13/20 recent runs on `main`).

## Approach

1. Read original file — confirmed 12 `fn test_` functions across 4 logical groups:
   - Creation (3 tests)
   - Correctness (3 tests)
   - Performance (3 tests)
   - Resource management (3 tests)

2. Split into part1 (creation + correctness = 6 tests) and part2 (performance + resource = 6 tests)

3. Each new file includes ADR-009 header comment and its own `fn main() raises:` runner

4. Deleted original file

5. Checked CI: `comprehensive-tests.yml` `Data` group uses `loaders/test_*.mojo` wildcard —
   no changes needed

6. `validate_test_coverage.py` pre-commit hook passed automatically

## Key Observations

- The `validate_test_coverage.py` pre-commit hook runs automatically and verifies coverage
- Wildcard CI patterns (`loaders/test_*.mojo`) automatically cover new split files
- Splitting by logical test group (creation, correctness, performance, resources) produces
  coherent, easy-to-navigate files
- 6 tests per file is a safe target under the 10-function limit

## Pre-commit Hook Results

```
Mojo Format..............................................................Passed
Check for deprecated List[Type](args) syntax.............................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```