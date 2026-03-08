# Session Notes: ADR-009 Test Split (Issue #3438)

## Context

- **Date**: 2026-03-07
- **Issue**: #3438 — `tests/shared/core/test_reduction.mojo` contained 22 `fn test_` functions
- **ADR-009 limit**: ≤10 per file
- **CI failure rate**: 13/20 recent runs on `main` (Core Tensors group)
- **Root cause**: Mojo v0.26.1 heap corruption in `libKGENCompilerRTShared.so` under high JIT load

## Original file test inventory

```text
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

---

# Session Notes: ADR-009 Optimizer Base Test Split (Issue #3457)

## Context

- **Date**: 2026-03-07
- **Issue**: #3457 — `tests/shared/autograd/test_optimizer_base.mojo` contained 18 `fn test_` functions
- **ADR-009 limit**: ≤10 per file
- **CI group**: Autograd
- **Root cause**: Same Mojo v0.26.1 heap corruption bug

## Initial State

Single file `tests/shared/autograd/test_optimizer_base.mojo` containing 18 tests (not previously split):

- `test_get_learning_rate`, `test_set_learning_rate`, `test_learning_rate_affects_training`
- `test_multiple_lr_updates`, `test_lr_boundary_values`, `test_lr_zero`
- `test_zero_gradients_basic`, `test_zero_gradients_multiple_params`, `test_zero_gradients_preserves_values`
- `test_clip_gradients_no_clipping_needed`, `test_clip_gradients_basic_clipping`, `test_clip_gradients_zero_threshold`
- `test_clip_gradients_multiple_params`, `test_clip_gradients_mixed`, `test_clip_gradients_large_threshold`
- `test_count_parameters_empty`, `test_count_parameters_single`, `test_optimizer_base_integration`

## Actions Taken

1. Read the original file and categorized all 18 tests into 3 logical groups.
2. Created `test_optimizer_base_part1.mojo` — 6 tests: LR get/set behavior
3. Created `test_optimizer_base_part2.mojo` — 6 tests: gradient zeroing + basic clipping
4. Created `test_optimizer_base_part3.mojo` — 6 tests: multi-param clipping, counting, integration
5. Deleted `test_optimizer_base.mojo` with `git rm`.
6. Added an ADR-009 explanatory comment to `.github/workflows/comprehensive-tests.yml` (no glob changes needed).
7. Verified `validate_test_coverage.py` had no direct filename references (uses glob patterns).
8. All pre-commit hooks passed: `mojo format`, `check-yaml`, `validate-test-coverage`.
9. Created PR #4278 with auto-merge enabled.

## Final State

- 3 files, each with exactly 6 tests
- 18 total test functions preserved
- CI glob `autograd/test_*.mojo` covers new files automatically

## PR

- PR #4278: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4278
- Auto-merge enabled with rebase strategy

## Key Gotchas (new learnings vs #3444)

1. When the CI group uses a glob (`autograd/test_*.mojo`), new `_part1/2/3` files are picked up automatically — no workflow edit needed
2. Equal splits (6/6/6) are simpler to reason about than asymmetric splits for 18-test files
3. `validate_test_coverage.py` uses glob patterns, so no script changes are needed when splitting

---

# Session Notes: ADR-009 Conv Test Split (Issue #3477)

## Context

- **Date**: 2026-03-07
- **Issue**: #3477 — `tests/shared/core/test_conv.mojo` title said 15 `fn test_` functions but actual count was 20
- **ADR-009 limit**: ≤10 per file
- **CI group**: Core Utilities (explicit filename pattern in workflow, not glob)
- **Root cause**: Same Mojo v0.26.1 heap corruption bug

## Key Discovery: Issue Description Undercount

The issue title stated "15 tests" but `grep -c "^fn test_" tests/shared/core/test_conv.mojo`
returned 20. A 2-way split of 20 would yield 10/10, which hits the hard limit exactly (not the
≤8 target). This forced a 3-way split.

**Lesson**: Always grep for the actual count before planning — issue descriptions can undercount.

## Original file test inventory (20 tests)

```text
fn test_conv2d_initialization
fn test_conv2d_shape_inference
fn test_conv2d_forward_shape
fn test_conv2d_stride_shape
fn test_conv2d_dilation_shape
fn test_conv2d_groups_shape
fn test_conv2d_padding_shape
fn test_conv2d_forward_values
fn test_conv2d_no_bias
fn test_conv2d_batched
fn test_conv2d_5x5
fn test_conv2d_backward_input_shape
fn test_conv2d_backward_weight_shape
fn test_conv2d_backward_bias_shape
fn test_conv2d_backward_input_gradient
fn test_conv2d_backward_weight_gradient
fn test_conv2d_backward_bias_gradient
fn test_conv2d_backward_no_bias
fn test_conv2d_full_backward_pass
fn test_conv2d_integration
```

## Split decision

- **part1** (7): initialization and shape tests — test_conv2d_initialization through test_conv2d_padding_shape
- **part2** (7): numerical correctness and batch tests — test_conv2d_forward_values through test_conv2d_5x5
- **part3** (6): backward pass and integration — test_conv2d_backward_input_shape through test_conv2d_integration

## CI workflow update

The `comprehensive-tests.yml` Core Utilities group used an explicit filename pattern (not a glob),
so a workflow update was required. Replaced `test_conv.mojo` with three filenames:
`test_conv_part1.mojo test_conv_part2.mojo test_conv_part3.mojo`.

## Pre-commit results

All hooks passed on first attempt.

## PR

- PR #4322: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4322
- Auto-merge enabled with rebase strategy

## Key Gotchas (new learnings vs #3457)

1. Issue descriptions can undercount tests — grep for `^fn test_[a-z]` to get accurate count before planning
2. A 2-way split of 20 tests yields 10/10 which hits the ADR-009 hard limit; use 3-way split to meet ≤8 target
3. Explicit filename patterns in CI workflow require manual update (unlike glob patterns that auto-match)

---

## Session Notes: ADR-009 Test Split (Issue #3498, PR #4373)

### Context

- **Date**: 2026-03-08
- **Issue**: #3498 — `tests/shared/testing/test_gradient_checker_meta.mojo` had 14 `fn test_` functions
- **ADR-009 limit**: ≤10 per file (target ≤8)
- **CI failure rate**: 13/20 recent runs on `main` (Testing Fixtures group)
- **Split result**: 2 files — part1 (8 tests), part2 (6 tests)

### Key Learnings vs Prior Sessions

1. **ADR-009 header placement**: The `# ADR-009:` comment block must appear at the absolute top of
   the file (line 1), before the triple-quoted module docstring. Placing it inside the docstring
   makes it a string literal, not a source comment.

2. **CI glob auto-coverage**: The `testing/test_*.mojo` glob in `comprehensive-tests.yml` already
   covers `test_gradient_checker_meta_part1.mojo` and `test_gradient_checker_meta_part2.mojo`.
   No workflow edits were needed. Always verify existing glob before editing CI YAML.

3. **validate_test_coverage.py is glob-based**: Confirmed once more that the pre-commit hook uses
   glob patterns (not hardcoded filenames), so no script changes needed after a split.

4. **Helper functions duplicated across parts**: Both part files needed the shared helper functions
   (`square_forward`, `square_backward_correct`, etc.) because Mojo has no intra-test imports.
   This is expected and acceptable.
