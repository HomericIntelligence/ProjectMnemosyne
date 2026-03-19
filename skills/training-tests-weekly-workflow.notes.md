# Session Notes: training-tests-weekly-workflow

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #4457 — Add new training tests to weekly E2E workflow coverage
- **Follow-up from**: Issue #3640 (which added 9 new training test files to PR CI exclusion list)

## Problem Description

Nine training test files were added to the `exclude_training_patterns` list in
`scripts/validate_test_coverage.py` (via issue #3640) without being added to any periodic
workflow. This created a silent coverage gap: the files were excluded from per-PR CI *and*
not run anywhere else.

The files:
- `tests/shared/training/test_checkpoint.mojo`
- `tests/shared/training/test_config.mojo`
- `tests/shared/training/test_csv_metrics_logger.mojo`
- `tests/shared/training/test_exponential_scheduler.mojo`
- `tests/shared/training/test_gradient_clipping.mojo`
- `tests/shared/training/test_gradient_ops.mojo`
- `tests/shared/training/test_mixed_precision_simd.mojo`
- `tests/shared/training/test_multistep_scheduler.mojo`
- `tests/shared/training/test_warmup_composite_scheduler.mojo`

## Investigation

1. Read `comprehensive-tests.yml` — found comment: `NOTE: Training tests moved to weekly workflow (requires dataset downloads)`
2. Searched for existing weekly workflow — found `simd-benchmarks-weekly.yml` but NO training-focused weekly workflow
3. Confirmed all 9 files were already in `validate_test_coverage.py` exclusion list (lines 100-143)
4. Conclusion: Only need to create the weekly workflow; no changes to validator needed

## Implementation

- Created `.github/workflows/training-tests-weekly.yml`
- Runs `just test-group tests/shared/training "test_*.mojo"` on Sundays at 3 AM UTC
- Used same pinned action versions as `comprehensive-tests.yml`:
  - `actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8`
  - `extractions/setup-just@f8a3cce218d9f83db3a2ecd90e41ac3de6cdfd9b`
  - `actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f`
- `simd-benchmarks-weekly.yml` used as structural template (cron offset by 1 hour)
- `validate_test_coverage.py` exits 0 with no changes
- `check-yaml` pre-commit hook passes

## PR

- PR #4882 created, linked to issue #4457 with `Closes #4457`
- Auto-merge enabled with `gh pr merge --auto --rebase`
- Single-file change (just the new workflow)