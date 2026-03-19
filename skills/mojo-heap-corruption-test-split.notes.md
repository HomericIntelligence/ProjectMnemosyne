# Session Notes: Mojo Heap Corruption Test Split

## Session Context

- **Date**: 2026-03-08
- **Issue**: #3507 — fix(ci): split test_random.mojo (13 tests) — Mojo heap corruption (ADR-009)
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3507-auto-impl
- **PR**: #4386

## Problem

`tests/shared/data/samplers/test_random.mojo` had 13 `fn test_` functions, exceeding the ADR-009
limit of 10 per file. This caused intermittent heap corruption crashes in Mojo v0.26.1:
- `libKGENCompilerRTShared.so` JIT fault
- Data Samplers CI group failing 13/20 recent runs on main
- Non-deterministic failures consistent with load-dependent heap corruption

## Solution Applied

Split into 2 files:

**test_random_part1.mojo** (8 tests):
- test_random_sampler_creation
- test_random_sampler_with_seed
- test_random_sampler_empty
- test_random_sampler_shuffles_indices
- test_random_sampler_deterministic_with_seed
- test_random_sampler_varies_without_seed
- test_random_sampler_yields_all_indices
- test_random_sampler_no_duplicates

**test_random_part2.mojo** (5 tests):
- test_random_sampler_valid_range
- test_random_sampler_with_replacement
- test_random_sampler_replacement_oversampling
- test_random_sampler_with_dataloader
- test_random_sampler_shuffle_speed

## Key Decisions

1. **No CI workflow changes needed**: The existing pattern `samplers/test_*.mojo` in
   `comprehensive-tests.yml` automatically matches `test_random_part1.mojo` and
   `test_random_part2.mojo`. No explicit file references required.

2. **No validate_test_coverage.py changes needed**: The script uses `rglob("test_*.mojo")`
   which dynamically discovers all test files. Pre-commit hook `Validate Test Coverage` passed
   on commit without any script changes.

3. **ADR-009 header format**: Placed in the module docstring (not as a standalone comment)
   to avoid pre-commit whitespace issues.

4. **Target: ≤8 tests per file**: Conservative buffer below the 10-test limit.

## Pre-commit Hook Results

All hooks passed on commit:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
- Fix Mixed Line Endings: Passed

## File Sizes

- Original: 13 fn test_ functions
- Part 1: 8 fn test_ functions
- Part 2: 5 fn test_ functions
- Total preserved: 13/13 (100% coverage)