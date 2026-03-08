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
