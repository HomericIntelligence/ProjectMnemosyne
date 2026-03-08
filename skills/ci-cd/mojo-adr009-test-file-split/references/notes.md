# Session Notes: Mojo ADR-009 Test File Split

## Date

2026-03-07

## Issue

GitHub Issue #3406: `fix(ci): split test_io.mojo (39 tests) — Mojo heap corruption (ADR-009)`

## Problem

`tests/shared/utils/test_io.mojo` contained 39 `fn test_` functions, exceeding ADR-009's ≤10
limit. This caused intermittent `libKGENCompilerRTShared.so` JIT faults in Mojo v0.26.1,
making the "Shared Infra" CI group fail on ~65% of runs (13/20 recent runs on main).

## Solution Applied

Split into 5 files of ≤8 tests each:

- `test_io_part1.mojo` — 8 tests (checkpoint save/load + serialization)
- `test_io_part2.mojo` — 8 tests (tensor serialization + safe file ops)
- `test_io_part3.mojo` — 8 tests (directory + binary file ops)
- `test_io_part4.mojo` — 8 tests (text file ops + path operations)
- `test_io_part5.mojo` — 7 tests (error handling + compression + integration)

## Key Discovery: Wildcard CI Patterns

The `comprehensive-tests.yml` "Shared Infra & Testing" group used:

```
utils/test_*.mojo
```

This wildcard automatically matched all 5 new `test_io_part*.mojo` files.
No CI workflow changes were needed.

## Pre-commit Hook Validation

The `validate-test-coverage` pre-commit hook confirmed all new files were covered
before the commit was accepted. This is the safety net that catches uncovered test files.

## PR

PR #4130: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4130

## Commit

`fix(ci): split test_io.mojo into 5 files per ADR-009 (≤8 tests each)`

6 files changed: 1 deleted (test_io.mojo), 5 created (test_io_part1-5.mojo)

---

# Session Notes — Issue #3425 (Second Application)

## Date

2026-03-07

## Issue

GitHub Issue #3425: `fix(ci): split test_shape_edge_cases.mojo (25 tests) — Mojo heap corruption (ADR-009)`

## Problem

`tests/shared/core/test_shape_edge_cases.mojo` contained 25 `fn test_` functions, exceeding ADR-009's ≤10
limit. This caused intermittent `libKGENCompilerRTShared.so` JIT faults in Mojo v0.26.1,
making the "Core Tensors" CI group fail on 13/20 recent runs on main.

## Key Difference from Issue #3406

- The CI group (`Core Tensors`) used **explicit filenames** in the pattern, not wildcards
- This meant the CI workflow **had** to be updated to list the 4 new files
- `validate_test_coverage.py` script (not just pre-commit hook) also validates coverage

## Solution Applied

Split into 4 files of ≤8 tests each, grouped by operation type:

- `test_shape_edge_cases_part1.mojo` — 6 tests (reshape edge cases)
- `test_shape_edge_cases_part2.mojo` — 8 tests (squeeze + unsqueeze)
- `test_shape_edge_cases_part3.mojo` — 5 tests (concatenate)
- `test_shape_edge_cases_part4.mojo` — 6 tests (stack + dimension preservation)

## CI Pattern Update Required

The `comprehensive-tests.yml` "Core Tensors" group used explicit filenames:

```yaml
# Before
pattern: "... test_shape_edge_cases.mojo ..."

# After
pattern: "... test_shape_edge_cases_part1.mojo test_shape_edge_cases_part2.mojo test_shape_edge_cases_part3.mojo test_shape_edge_cases_part4.mojo ..."
```

## PR

PR #4193: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4193

---

# Session Notes — Issue #3488 (Fourth Application)

## Date

2026-03-08

## Issue

GitHub Issue #3488: `fix(ci): split test_slicing.mojo into 2 files per ADR-009`

## Problem

`tests/shared/core/test_slicing.mojo` contained 14 `fn test_` functions (357 lines),
exceeding ADR-009's ≤10 limit. The "Core Tensors" CI group used explicit filenames in
the pattern, requiring a direct workflow update.

## Solution Applied

Split into 2 files of ≤8 tests each, grouped by functionality:

- `test_slicing_part1.mojo` — 8 tests (basic functionality, view semantics, reference counting, one edge case)
- `test_slicing_part2.mojo` — 6 tests (remaining edge cases, batch extraction)

## Test Distribution

### Part 1 (8 tests)

- test_slice_basic_1d
- test_slice_2d_axis0
- test_slice_4d_batch
- test_slice_full_range
- test_slice_is_marked_as_view
- test_slice_refcount_increments
- test_multiple_slices_share_refcount
- test_slice_empty_range

### Part 2 (6 tests)

- test_slice_single_element
- test_slice_out_of_bounds_start
- test_slice_out_of_bounds_end
- test_slice_invalid_axis
- test_batch_extraction_uses_view
- test_batch_extraction_pair

## CI Pattern Update Required

The `comprehensive-tests.yml` "Core Tensors" group (line 194) used explicit filenames:

```yaml
# Before
pattern: "... test_slicing.mojo"

# After
pattern: "... test_slicing_part1.mojo test_slicing_part2.mojo"
```

## Key Observations

1. `validate_test_coverage.py` does NOT reference individual filenames — uses directory-level patterns,
   so no update was needed there. Always verify before assuming.
2. CI workflow uses a space-separated string for `pattern:`, not a YAML list — simple string replacement.
3. Pre-commit hooks (Mojo format, YAML check, test count badge) all passed cleanly.
4. Git recognized the split as a rename for part1 (56% similarity threshold met).

## PR

PR #4347: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4347

## Commit

`fix(ci): split test_slicing.mojo into 2 files per ADR-009`

3 files changed: 1 deleted (test_slicing.mojo), 2 created (test_slicing_part1-2.mojo),
1 modified (comprehensive-tests.yml)

---

# Session Notes — Issue #3492 (Sixth Application)

## Date

2026-03-08

## Issue

GitHub Issue #3492: `fix(ci): split test_arg_parser.mojo (13 tests) — Mojo heap corruption (ADR-009)`

## Problem

`tests/shared/utils/test_arg_parser.mojo` contained 13 `fn test_` functions, exceeding ADR-009's ≤10
limit. This caused intermittent `libKGENCompilerRTShared.so` JIT faults in Mojo v0.26.1, making the
"Shared Infra & Testing" CI group fail on 13/20 recent runs.

## Solution Applied

Split into 2 files of ≤8 tests each:

- `test_arg_parser_part1.mojo` — 8 tests (ArgumentSpec creation, ParsedArgs getters, parser
  creation and add_argument)
- `test_arg_parser_part2.mojo` — 5 tests (add_flag, invalid type rejection, defaults, multiple
  values, parser populate defaults)

## CI Pattern

The "Shared Infra & Testing" group used wildcard `utils/test_*.mojo` — no workflow update needed.
`validate_test_coverage.py` had no hardcoded filename references either.

## Test Distribution

Part 1 (8 tests): test_argument_spec_creation, test_parsed_args_string, test_parsed_args_int,
test_parsed_args_float, test_parsed_args_bool, test_parsed_args_has, test_argument_parser_creation,
test_argument_parser_add_arguments

Part 2 (5 tests): test_argument_parser_add_flag, test_argument_parser_invalid_type,
test_argument_defaults, test_parsed_args_multiple_values, test_parser_populates_defaults

## PR

PR #4360: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4360

## Commit

`fix(ci): split test_arg_parser.mojo to comply with ADR-009 (≤10 tests/file)`

3 files changed: 1 deleted (test_arg_parser.mojo), 2 created (test_arg_parser_part1-2.mojo)

---

# Session Notes — Issue #3624 (Seventh Application)

## Date

2026-03-08

## Issue

GitHub Issue #3624: `fix(ci): split test_sequential.mojo (12 tests) — Mojo heap corruption (ADR-009)`

## Problem

`tests/shared/data/samplers/test_sequential.mojo` contained 12 `fn test_` functions, exceeding ADR-009's ≤10
limit. This caused intermittent `libKGENCompilerRTShared.so` JIT faults in Mojo v0.26.1, making the
"Data" CI group fail non-deterministically (13/20 recent runs on main).

## Solution Applied

Split into 2 files of ≤8 tests each, grouped by test type:

- `test_sequential_part1.mojo` — 8 tests (creation, iteration, range tests; includes StubSequentialSampler)
- `test_sequential_part2.mojo` — 4 tests (integration and performance tests; uses SequentialSampler directly)

## CI Pattern

The "Data" group in `comprehensive-tests.yml` uses wildcard `samplers/test_*.mojo` — no workflow update needed.
`validate_test_coverage.py` had no hardcoded filename references.

## Key Observation: Trim Imports Per File

Part 2 does not use `assert_true` (only `assert_equal`), so the import was trimmed vs. Part 1.
Only import what each split file's tests actually use — the pre-commit hooks will catch mismatches.

## Test Distribution

### Part 1 (8 tests)

- test_sequential_sampler_creation
- test_sequential_sampler_empty
- test_sequential_sampler_yields_all_indices
- test_sequential_sampler_order
- test_sequential_sampler_deterministic
- test_sequential_sampler_start_index
- test_sequential_sampler_end_index
- test_sequential_sampler_no_negative_indices

### Part 2 (4 tests)

- test_sequential_sampler_with_dataloader
- test_sequential_sampler_reusable
- test_sequential_sampler_iteration_speed
- test_sequential_sampler_memory_efficiency

## PR

PR #4413: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4413

## Commit

`fix(ci): split test_sequential.mojo into 2 files per ADR-009`

2 files changed: 1 deleted (test_sequential.mojo → part1 rename 67%), 1 created (test_sequential_part2.mojo)
