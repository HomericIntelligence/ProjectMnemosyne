# Session Notes: ADR-009 Test File Split

**Date**: 2026-03-08
**Issue**: ProjectOdyssey #3500
**PR**: ProjectOdyssey #4377

## Context

`tests/shared/integration/test_multi_precision_training.mojo` had 13 `fn test_` functions,
exceeding ADR-009's limit of ≤10 per file. This caused intermittent heap corruption crashes
(libKGENCompilerRTShared.so JIT fault) in Mojo v0.26.1 on CI.

## What Was Done

1. Counted test functions: `grep -c "^fn test_" <file>` → 13
2. Read the original file to understand test groupings
3. Created `test_multi_precision_training_part1.mojo` (8 tests: FP32/FP16/BF16/FP8 training,
   overflow recovery, config parsing, dynamic scaling)
4. Created `test_multi_precision_training_part2.mojo` (5 tests: master weights, FP16/BF16
   accuracy, memory savings, TOML config)
5. Both files: ADR-009 header comment, updated module docstring, updated `main()` with correct count
6. Deleted original file
7. Updated `tests/shared/integration/__init__.mojo` doc comment
8. Checked CI workflow — `pattern: "test_*.mojo"` auto-discovers new files, no changes needed
9. Committed, pushed, PR created with auto-merge enabled

## Pre-commit Results

All hooks passed on first attempt:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed

## Key Insight

The CI Integration Tests group used a glob pattern (`test_*.mojo`), so splitting the file
automatically made both new files discoverable with zero workflow changes. This is a common
pattern in the ProjectOdyssey CI setup — always check the pattern before editing workflows.
