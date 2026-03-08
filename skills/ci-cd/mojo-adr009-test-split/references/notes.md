# Session Notes: ADR-009 Test Split (Issue #3438)

## Context

- **Date**: 2026-03-07
- **Issue**: #3438 — `tests/shared/core/test_reduction.mojo` contained 22 `fn test_` functions
- **ADR-009 limit**: ≤10 per file
- **CI failure rate**: 13/20 recent runs on `main` (Core Tensors group)
- **Root cause**: Mojo v0.26.1 heap corruption in `libKGENCompilerRTShared.so` under high JIT load

## Original file test inventory

```
fn test_sum_backward_shapes
fn test_sum_backward_gradient
fn test_mean_backward_shapes
fn test_mean_backward_gradient
fn test_max_reduce_backward_shapes
fn test_max_reduce_backward_gradient
fn test_min_reduce_backward_shapes
fn test_min_reduce_backward_gradient
fn test_var_forward_uniform
fn test_var_forward_simple
fn test_var_forward_with_ddof
fn test_var_forward_axis
fn test_var_backward_shapes
fn test_var_backward_gradient
fn test_std_forward_simple
fn test_std_backward_gradient
fn test_median_forward_odd
fn test_median_forward_even
fn test_median_backward_shapes
fn test_percentile_forward_p50
fn test_percentile_forward_p0_p100
fn test_percentile_backward_shapes
```

## Split decision

Grouped by operation family (not arbitrary index slicing):

- **part1** (8): sum + mean + max + min (related: basic reductions)
- **part2** (8): variance + std (related: moment-based)
- **part3** (6): median + percentile (related: order statistics)

## Key implementation details

1. Each split file imports only the symbols it uses (avoids compilation overhead)
2. Each split file has its own `fn main()` runner listing only its tests
3. ADR-009 comment goes on line 1-4 before the module docstring
4. CI pattern update is a simple find-and-replace of the old filename with three new filenames
5. `validate_test_coverage.py` validates coverage automatically in pre-commit

## Pre-commit results

All hooks passed on first attempt:
- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Check YAML: Passed
- All standard hooks: Passed

## PR

- PR #4223: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4223
- Auto-merge enabled with rebase strategy
