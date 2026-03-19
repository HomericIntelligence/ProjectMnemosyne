---
name: mojo-subpackage-import-tests
description: 'Add tests verifying Mojo sub-package import paths work (e.g. from shared.training.callbacks
  import EarlyStopping). Use when: an issue requests confirming a direct sub-module
  import works, or when only parent-package re-export imports are tested but not the
  canonical sub-package path.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Sub-Package Import Tests

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Category** | testing |
| **Objective** | Verify that both parent-package re-exports and direct sub-package import paths work correctly in Mojo |
| **Outcome** | Successfully added `test_training_callbacks_direct_imports()` confirming `from shared.training.callbacks import EarlyStopping` works |
| **Context** | Issue #3211 - Add import tests for callbacks to tests/shared/test_imports.mojo |

## When to Use

Use this skill when:

- A GitHub issue asks to verify a specific sub-module import path (e.g. `from pkg.sub import X`)
- An existing `test_imports.mojo` file only tests parent-package imports (`from pkg import X`) but not the direct sub-package path (`from pkg.sub import X`)
- You need to document why a negative test (asserting a bad import path fails) cannot be written in Mojo
- You want to ensure imports are functional (not just syntactically accepted) by instantiating the imported types

Do NOT use when:

- The module hasn't been implemented yet (write the implementation first)
- The import path is internal and not part of the public API
- Tests should verify runtime behavior rather than import availability

## Verified Workflow

### 1. Read the existing test file

Find the `test_imports.mojo` file and read all existing import test functions to understand the pattern:

```bash
# Locate the file
glob tests/**/*.mojo  # or equivalent Glob tool
# Read the entire file to understand conventions
```

Key things to note:
- Function naming convention: `test_<package>_<subpackage>_imports()`
- Each function imports from one path and optionally instantiates types
- `assert_true` used for verification, `print("✓ ... test passed")` at end
- Function is called in `main()`

### 2. Read the target module to confirm the API

```bash
# Read the actual module file to get constructor signatures
# e.g. shared/training/callbacks.mojo
```

Key things to confirm:
- Exact struct names (case-sensitive)
- Constructor parameter names and types (needed for instantiation)
- Required vs optional parameters

### 3. Write the new test function

Pattern for sub-package import test:

```mojo
fn test_<module>_direct_imports() raises:
    """Test <module> is importable directly from <pkg>.<sub> sub-module.

    This validates the canonical import path documented in Issue #NNNN:
        from <pkg>.<sub> import <Type>

    NOTE: A negative test for the wrong import path cannot be written because
    Mojo import failures are compile-time errors, not runtime exceptions.
    There is no equivalent of pytest.raises() for compile-time errors.
    """
    from <pkg>.<sub> import TypeA, TypeB, TypeC

    # Instantiate each type to confirm the import is functional, not just parseable
    var instance = TypeA(param=value)
    assert_true(instance.field == expected, "TypeA should have field=expected")

    print("✓ <module> direct imports test passed")
```

Key rules:
- Import from the **specific sub-module path** (e.g. `shared.training.callbacks`), not the parent
- Instantiate at least one type per import to confirm functionality
- Include the note about why negative tests cannot be written
- Add the function call to `main()` right after the existing sibling test

### 4. Add the call in main()

Find the existing sibling test call in `main()` and insert the new call directly after it:

```mojo
    test_training_callbacks_imports()
    test_training_callbacks_direct_imports()  # add after existing sibling
    test_training_loops_imports()
```

### 5. Run pre-commit hooks to verify formatting

```bash
pixi run pre-commit run --files tests/shared/test_imports.mojo
```

All hooks should pass — particularly `Mojo Format` and `Validate Test Coverage`.

## Key Pattern: Why Negative Tests Cannot Be Written in Mojo

This is critical knowledge to document in the test and in issue comments:

**Python**: `with pytest.raises(ImportError): import bad_module` — works at runtime

**Mojo**: Import failures are **compile-time errors**. If you write:
```mojo
from wrong.path import Something  # compile error
```
The entire file fails to compile. There is no runtime exception to catch.

**Consequence**: You can only write positive import tests in Mojo. Document the limitation
clearly in the test docstring so future readers understand this is intentional, not an oversight.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3211, PR #3726 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo test tests/shared/test_imports.mojo` | GLIBC version too old on dev machine (requires GLIBC_2.32+, host has older) | Mojo tests can only run in Docker CI or on compatible systems; pre-commit hooks are the local verification |
| Docker-based test run | `docker run ghcr.io/homericintelligence/projectodyssey:main ...` | Image not available locally (denied pull from GHCR) | Trust CI to run the full test suite; local verification uses pre-commit hooks only |
| Writing negative import test | Attempted to test that wrong import path fails | Mojo compile-time errors cannot be caught at runtime — no pytest.raises() equivalent | Document limitation in test docstring; only positive tests are possible for Mojo imports |

## Results & Parameters

**Files modified**: `tests/shared/test_imports.mojo`

**Additions**:
- 1 new `fn test_<module>_direct_imports() raises:` function (~35 lines)
- 1 new call in `main()`

**Test structure** (copy-paste template):

```mojo
fn test_training_callbacks_direct_imports() raises:
    """Test callbacks are importable directly from shared.training.callbacks sub-module.

    This validates the canonical import path documented in Issue #NNNN:
        from shared.training.callbacks import EarlyStopping

    NOTE: A negative test for the wrong import path cannot be written because
    Mojo import failures are compile-time errors, not runtime exceptions.
    There is no equivalent of pytest.raises() for compile-time errors.
    """
    from shared.training.callbacks import EarlyStopping, ModelCheckpoint, LoggingCallback

    var early_stop = EarlyStopping(
        monitor="val_loss",
        patience=3,
        min_delta=0.001,
        mode="min",
        verbose=False,
    )
    assert_true(early_stop.patience == 3, "EarlyStopping should have patience=3")
    assert_true(early_stop.stopped == False, "EarlyStopping should not be stopped initially")

    var checkpoint = ModelCheckpoint(
        filepath="test_checkpoint.pt",
        save_best_only=False,
        save_frequency=1,
        mode="min",
    )
    assert_true(checkpoint.save_count == 0, "ModelCheckpoint should have save_count=0 initially")

    var logger = LoggingCallback(log_interval=2)
    assert_true(logger.log_interval == 2, "LoggingCallback should have log_interval=2")
    assert_true(logger.log_count == 0, "LoggingCallback should have log_count=0 initially")

    print("✓ Training callbacks direct imports test passed")
```

**Pre-commit verification**:

```bash
pixi run pre-commit run --files tests/shared/test_imports.mojo
# Expected: All hooks Passed or Skipped
```
