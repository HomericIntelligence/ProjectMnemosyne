# Session Notes: ADR-009 Test File Split

## Issue

GitHub issue #3483: `tests/shared/testing/test_layer_testers.mojo` had 14 `fn test_` functions,
exceeding ADR-009's limit of 10 per file. This caused intermittent heap corruption crashes
(~65% CI failure rate) in Mojo v0.26.1 via `libKGENCompilerRTShared.so` JIT faults.

## Root Cause

Mojo v0.26.1 has a known heap corruption bug triggered under high test load. ADR-009 documents
the workaround: keep ≤10 `fn test_` functions per `.mojo` file.

## Steps Taken

1. Read `.claude-prompt-3483.md` to understand the issue
2. Read `tests/shared/testing/test_layer_testers.mojo` — confirmed 14 test functions
3. Read `.github/workflows/comprehensive-tests.yml` to understand CI patterns
4. Checked `scripts/validate_test_coverage.py` for hardcoded filename references (none found)
5. Created `test_layer_testers_part1.mojo` (8 tests) with ADR-009 header
6. Created `test_layer_testers_part2.mojo` (6 tests) with ADR-009 header
7. Deleted original `test_layer_testers.mojo`
8. Committed — all pre-commit hooks passed on first attempt
9. Pushed and created PR #4330

## Key Files

- `tests/shared/testing/test_layer_testers_part1.mojo` — 8 tests
- `tests/shared/testing/test_layer_testers_part2.mojo` — 6 tests
- `.github/workflows/comprehensive-tests.yml` — unchanged (glob pattern covers new files)
- `scripts/validate_test_coverage.py` — unchanged (no hardcoded references)

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4330

## Timing

2026-03-07

---

# Session Notes: ADR-009 Test File Split (Issue #3503)

## Date

2026-03-08

## Context

- Repo: HomericIntelligence/ProjectOdyssey
- Branch: 3503-auto-impl
- Issue: #3503 - split test_pipeline.mojo (13 tests) per ADR-009
- PR created: #4381

## File split details

- Original: tests/shared/data/transforms/test_pipeline.mojo (13 fn test_)
- Part 1: test_pipeline_part1.mojo (8 tests: creation + execution + composition_start)
- Part 2: test_pipeline_part2.mojo (5 tests: append + error_handling + utilities)

## CI workflow observation

The Data group in comprehensive-tests.yml uses:

```text
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

The wildcard `transforms/test_*.mojo` picks up both split files automatically.
No workflow edit was needed.

## Pre-commit results

- mojo-format: Passed
- trailing-whitespace: Passed
- end-of-file-fixer: Passed
- validate-test-coverage: Passed (no reference to test_pipeline.mojo in the script)

## Shell environment notes

- `just` not available in worktree environments — use `pixi run` directly
- `pixi run pre-commit run` only accepts ONE hook name at a time
- Background tasks via run_in_background may not flush output during session

---

# Session Notes: ADR-009 Test File Split (Issue #3628)

## Context

- Date: 2026-03-08
- Issue: HomericIntelligence/ProjectOdyssey#3628
- PR: HomericIntelligence/ProjectOdyssey#4422

## Problem

`tests/models/test_resnet18_layers.mojo` had 12 `fn test_` functions,
exceeding the ADR-009 limit of 10. This caused intermittent heap corruption
crashes in the Mojo v0.26.1 JIT compiler (libKGENCompilerRTShared.so).

## Solution

Split into:

- `test_resnet18_layers_part1.mojo`: 8 tests (residual blocks, skip connections, BatchNorm)
- `test_resnet18_layers_part2.mojo`: 4 tests (BatchNorm effects, ReLU, integration)

## Key Discovery

The CI workflow used `pattern: "test_*_layers.mojo"` — this glob
automatically matches the split files. No workflow update was needed.

## Files Changed

- Deleted: `tests/models/test_resnet18_layers.mojo`
- Created: `tests/models/test_resnet18_layers_part1.mojo` (8 tests)
- Created: `tests/models/test_resnet18_layers_part2.mojo` (4 tests)

## Pre-commit Results

All hooks passed:

- Mojo Format: Passed
- Check for deprecated List syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed

---

# Session Notes: ADR-009 Test File Split (Issue #3631)

## Context

- Date: 2026-03-08
- Issue: HomericIntelligence/ProjectOdyssey#3631
- PR: HomericIntelligence/ProjectOdyssey#4431

## Problem

`tests/test_data_integrity.mojo` had 11 `fn test_` functions, exceeding the ADR-009 limit of 10.
This caused intermittent heap corruption crashes in the Mojo v0.26.1 JIT compiler
(libKGENCompilerRTShared.so).

## Original Test Functions

1. test_mxfp4_aligned_roundtrip
2. test_mxfp4_unaligned_roundtrip
3. test_mxfp4_various_unaligned_sizes
4. test_nvfp4_unaligned_roundtrip
5. test_fp8_bounds_checking
6. test_dtype_validation_fp8
7. test_dtype_validation_mxfp4
8. test_fp16_conversion_behavior
9. test_int_conversion_bounds
10. test_metadata_preservation
11. test_backwards_compatibility

## Solution

Split into:

- `test_data_integrity_part1.mojo`: 8 tests (roundtrip, dtype validation, FP16 behavior)
- `test_data_integrity_part2.mojo`: 3 tests (int bounds, metadata, backwards compat)

## Key Discovery

The CI workflow "Misc Tests" group uses `pattern: "test_*.mojo ..."` — the wildcard picks up
both split files automatically. No workflow edit was needed.

Issue prompt described the CI group as "Top-Level Tests" but the actual group in the workflow
was "Misc Tests". Always read the workflow file directly to verify CI group names.

## Documentation Updates

`docs/dev/phases.md` referenced `test_data_integrity.mojo` by name and was updated to reference
both new filenames.

## Pre-commit Results

All hooks passed:

- Mojo Format: Passed
- Validate Test Coverage: Passed
- Markdown Lint: Passed
