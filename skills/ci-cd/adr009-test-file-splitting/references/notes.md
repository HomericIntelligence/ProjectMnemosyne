# Session Notes: ADR-009 Test File Splitting (Issue #3397)

## Date

2026-03-07

## Problem

test_assertions.mojo (61 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
ADR-009 mandates ≤10 fn test_ per file.

## Initial State (already in main)

The file had been partially split into 7 files:

- test_assertions_bool.mojo: 5 tests
- test_assertions_comparison.mojo: 8 tests
- test_assertions_equality.mojo: 8 tests
- test_assertions_float.mojo: 10 tests (AT hard limit)
- test_assertions_shape.mojo: 9 tests
- test_assertions_tensor_props.mojo: 8 tests
- test_assertions_tensor_values.mojo: 11 tests (OVER hard limit)
- test_assertions.mojo.DEPRECATED (stale artifact)

## Actions Taken

1. Created test_assertions_int.mojo (2 tests) - moved assert_equal_int tests from float file
2. Updated test_assertions_float.mojo: 10 → 8 tests
3. Created test_assertions_tensor_type.mojo (3 tests) - moved assert_type + not_equal_fails
4. Updated test_assertions_tensor_values.mojo: 11 → 8 tests
5. Deleted test_assertions.mojo.DEPRECATED

## Final State

- 9 files, all ≤9 tests each
- 59 total test functions preserved
- CI glob testing/test_*.mojo covers new files automatically
- PR #4094 created, auto-merge enabled

## Key Insight

The ADR-009 comment in SKILL.md headers contains the text "fn test_" which matches
grep "^fn test_" if placed at line start. Always use "^fn test_[a-z]" for accurate counts.

---

# Session Notes: ADR-009 Test File Splitting (Issue #3456)

## Date

2026-03-07

## Problem

test_training_infrastructure.mojo (18 tests) was causing intermittent heap corruption in Mojo v0.26.1 CI.
CI group "Shared Infra & Testing" failing 13/20 recent runs on main. ADR-009 mandates ≤10 fn test_ per file.

## Initial State

Single file `tests/training/test_training_infrastructure.mojo` with 18 `fn test_` functions:

- 2 TrainerConfig tests
- 3 TrainingMetrics tests
- 2 DataLoader tests
- 1 TrainingLoop test
- 1 ValidationLoop test
- 7 BaseTrainer tests (init, factory, get_metrics, get_best_checkpoint, reset, databatch)
- 2 Integration tests

## Actions Taken

1. Read existing file to understand all 18 tests and their logical groupings
2. Created `test_training_infrastructure_part1.mojo` (7 tests) — TrainerConfig, TrainingMetrics, DataLoader
3. Created `test_training_infrastructure_part2.mojo` (6 tests) — TrainingLoop, ValidationLoop, BaseTrainer init/factory
4. Created `test_training_infrastructure_part3.mojo` (5 tests) — BaseTrainer lifecycle, DataBatch, integration
5. Deleted original `test_training_infrastructure.mojo`
6. Verified CI wildcard `training/test_*.mojo` picks up new files automatically — no workflow changes needed

## Final State

- 3 files: 7+6+5 = 18 tests total (all preserved)
- All ≤8 tests per file (≤ target)
- ADR-009 header in each file's docstring
- PR #4277 created, auto-merge enabled

## Key Insight for This Session

When the file is a clean unsplit original (not already partially split like #3397 was),
the split is straightforward: group by domain/responsibility. Tests in this file had
clear logical sections already marked with `# ====` dividers, making grouping trivial.

The CI workflow used `training/test_*.mojo` wildcard — confirmed by reading the workflow YAML.
No changes to `.github/workflows/comprehensive-tests.yml` were needed.

`validate_test_coverage.py` did not reference the original filename — confirmed by grep before deleting.
