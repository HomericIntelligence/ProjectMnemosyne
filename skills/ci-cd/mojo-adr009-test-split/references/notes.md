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

---

# Session Notes: ADR-009 Test Split for test_backward.mojo (Issue #3444)

## Context

- **Date**: 2026-03-07
- **Issue**: #3444 — `tests/shared/core/test_backward.mojo` contained 21 `fn test_` functions
- **ADR-009 limit**: ≤10 per file
- **CI failure**: Intermittent heap corruption in `Core Gradient` group
- **Root cause**: Same Mojo v0.26.1 heap corruption bug

## Initial State (found on the branch)

The file had been partially split into 3 files (split was prepared in advance but incomplete):

- test_backward_linear.mojo: present but had wrong ADR-009 header format (docstring note, not `#` comment)
- test_backward_conv_pool.mojo: present but had wrong ADR-009 header format
- test_backward_losses.mojo: present but had wrong ADR-009 header format
- test_backward.mojo.DEPRECATED: stale artifact (the original 21-test file)
- CI workflow: already updated (correct filenames listed) — no changes needed

Total tests in split files: 14 (7 missing — the gradient-checking tests)

## Actions Taken

1. Read the deprecated file (21 tests) and listed all `fn test_` functions
2. Compared against split files (14 tests total) — found 7 missing gradient-checking tests
3. Fixed ADR-009 header format in all 3 files (changed from docstring note to `#` comment block)
4. Added 7 missing tests to appropriate files:
   - test_backward_conv_pool.mojo: added `test_avgpool2d_backward_shapes`,
     `test_conv2d_backward_gradient`, `test_maxpool2d_backward_gradient`,
     `test_avgpool2d_backward_gradient`
   - test_backward_losses.mojo: added `test_cross_entropy_backward_gradient`,
     `test_binary_cross_entropy_backward_gradient`, `test_mean_squared_error_backward_gradient`
5. Deleted test_backward.mojo.DEPRECATED

## Final State

- 3 files, all ≤9 tests each:
  - test_backward_linear.mojo: 4 tests
  - test_backward_conv_pool.mojo: 9 tests
  - test_backward_losses.mojo: 8 tests
- 21 total test functions preserved
- CI workflow was already updated — no changes needed
- Pre-commit hooks all passed on first attempt

## PR

- PR #4238: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4238
- Auto-merge enabled with rebase strategy

## Key Gotchas (new learnings vs issue #3438)

1. Split file existence does NOT guarantee completeness — must verify test lists match
2. CI workflow being updated does NOT mean the split files are complete
3. `grep -c "fn test_"` over-counts when header contains the pattern — use `grep -n "fn test_"`
4. ADR-009 header format is `#` comment lines, NOT a note inside the module docstring
