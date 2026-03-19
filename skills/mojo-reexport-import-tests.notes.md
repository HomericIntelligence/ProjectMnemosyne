# Session Notes: mojo-reexport-import-tests

## Date
2026-03-15

## Issue
GitHub Issue #3851: "Export DataLoader from shared.training package"

## Objective
Add `DataLoader` and `DataBatch` to `shared/training/__init__.mojo` exports so users
can `from shared.training import DataLoader` instead of the longer submodule path.

## What We Found

The re-export was **already present** in `__init__.mojo`:

```mojo
# Export data loader interfaces (Issue #3851, #3856)
from shared.training.trainer_interface import (
    DataBatch,
    DataLoader,
)
```

The issue was that **no test coverage existed** for these exports.

## Implementation Done

1. Added `test_training_dataloader_imports()` to `tests/shared/test_imports_part1.mojo`
   - Verifies `from shared.training import DataLoader, DataBatch`
   - ADR-009: file had 8 functions, now 9 (within ≤10 limit)

2. Added two functions to `tests/shared/test_imports.mojo`:
   - `test_training_dataloader_imports()` — package-level import
   - `test_training_dataloader_direct_imports()` — direct submodule import

3. Both files' `main()` functions updated to call new tests.

## Key Constraints Observed

- **ADR-009**: Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers
  under high test load. Split test files must stay ≤10 `fn test_` functions each.
- **Mojo compile-time imports**: Cannot write negative import tests (tests that expect
  an import to fail). Import failures are compile-time errors with no runtime exception
  handling. Only test valid imports that compile successfully.
- **Callback limitation**: Callbacks have a specific re-export limitation in Mojo v0.26.1
  where they must be imported directly from submodules. This does NOT affect structs like
  DataLoader/DataBatch.

## PR Created
https://github.com/HomericIntelligence/ProjectOdyssey/pull/4814
Branch: `3851-auto-impl`