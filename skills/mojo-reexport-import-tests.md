---
name: mojo-reexport-import-tests
description: 'Add import tests for Mojo package re-exports. Use when: adding exports
  to __init__.mojo, verifying package public API, or closing issues about missing
  package-level imports.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-reexport-import-tests |
| **Category** | testing |
| **Trigger** | Adding re-exports to `__init__.mojo`, package API verification issues |
| **Output** | Test functions in `test_imports*.mojo` covering both package and direct import paths |
| **Constraint** | ≤10 `fn test_` functions per file |

## When to Use

1. A GitHub issue requests exporting a type from a submodule via `__init__.mojo`
2. A package's public API has been extended and needs import test coverage
3. Verifying that re-exported symbols are importable at the parent package level
4. Validating both `from pkg import Symbol` and `from pkg.sub import Symbol` paths

## Verified Workflow

### Quick Reference

```
1. Check __init__.mojo for existing re-export (often already done)
2. Verify source module has the struct/fn
3. Check function count in split test files (≤10 per file)
4. Add test_<type>_imports() to test_imports_part1.mojo (if count ≤9)
5. Add test_<type>_imports() + test_<type>_direct_imports() to test_imports.mojo
6. Add both calls to main() in each file
7. Commit with "Closes #<issue>" in message
```

### Step 1: Check existing re-exports

Read `shared/<pkg>/__init__.mojo`. The export is often **already present** but
lacking test coverage — check for a comment like `# Issue #NNNN`:

```bash
grep -n "DataLoader\|DataBatch\|<TypeName>" shared/<pkg>/__init__.mojo
```

If missing, add:

```mojo
# Export <type> (Issue #NNNN)
from shared.<pkg>.<submodule> import (
    TypeName,
)
```

### Step 2: Verify source struct exists

```bash
grep -n "struct TypeName" shared/<pkg>/<submodule>.mojo
```

### Step 3: Check function count

```bash
grep -c "^fn test_" tests/shared/test_imports_part1.mojo
# Must be ≤ 9 before adding (limit is 10)
```

### Step 4: Add to test_imports_part1.mojo

Add the new function **before** the `# Main Test Runner` comment block:

```mojo
fn test_training_<typename>_imports() raises:
    """Test <TypeName> is importable from shared.<pkg> package.

    Verifies Issue #NNNN: <TypeName> exported from
    shared/<pkg>/__init__.mojo via the <submodule> submodule.
    """
    from shared.<pkg> import TypeName, OtherType

    print("✓ Training <TypeName> package imports test passed")
```

Add the call in `main()`:

```mojo
    test_training_<typename>_imports()
```

### Step 5: Add two functions to test_imports.mojo

Add both a package-level and a direct-submodule test:

```mojo
fn test_training_<typename>_imports() raises:
    """Test <TypeName> is importable from shared.<pkg> package.

    Verifies Issue #NNNN: <TypeName> exported from
    shared/<pkg>/__init__.mojo via the <submodule> submodule.
    """
    from shared.<pkg> import TypeName, OtherType

    print("✓ Training <TypeName> package imports test passed")


fn test_training_<typename>_direct_imports() raises:
    """Test <TypeName> is importable directly from <submodule>.

    Validates the direct import path as documented fallback:
        from shared.<pkg>.<submodule> import TypeName
    """
    from shared.<pkg>.<submodule> import TypeName, OtherType

    print("✓ Training <TypeName> direct imports test passed")
```

Add both calls to `main()`:

```mojo
    test_training_<typename>_imports()
    test_training_<typename>_direct_imports()
```

### Step 6: Commit and push

```bash
git add tests/shared/test_imports.mojo tests/shared/test_imports_part1.mojo
git commit -m "test(<pkg>): add import tests for <TypeName> package export

Add test coverage verifying <TypeName> are correctly exported
from shared.<pkg> package (via __init__.mojo re-export from <submodule>).

Tests added:
- test_imports_part1.mojo: test_training_<typename>_imports() - package import
- test_imports.mojo: test_training_<typename>_imports() - package import
- test_imports.mojo: test_training_<typename>_direct_imports() - direct submodule import

Closes #NNNN

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>
gh pr create --title "test(<pkg>): add import tests for <TypeName> package export" \
  --body "Closes #NNNN"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Modifying `__init__.mojo` | Tried to add re-exports from scratch | Export was already present (added in prior work with `# Issue #3851` comment) | Always check `__init__.mojo` first — the re-export is often done, only tests are missing |
| Callback re-export pattern | Assumed same limitation applied to all types | Callbacks have a specific Mojo v0.26.1 re-export limitation; `DataLoader`/`DataBatch` work fine | Check the docstring in `__init__.mojo` for existing limitation notes before assuming failure |
| Adding to test_imports.mojo only | Added tests to monolithic file only | Split files exist for a reason — part1 also needs coverage for CI split runs | Always update both `test_imports.mojo` AND `test_imports_part1.mojo` |

## Results & Parameters

### Issue #3851 — DataLoader/DataBatch export

- **Export location**: `shared/training/__init__.mojo` lines 93–97
- **Source module**: `shared/training/trainer_interface.mojo`
- **Types exported**: `DataLoader`, `DataBatch`
- **Test files modified**: `tests/shared/test_imports.mojo`, `tests/shared/test_imports_part1.mojo`
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4814
- **Test counts after**: part1 = 9 functions (within ≤10 limit)

### File placement pattern

```
tests/shared/
├── test_imports.mojo          # Full suite (all packages, 37 fns after)
├── test_imports_part1.mojo    # Split: Core + Training (9 fns, ≤10 fn test_ limit)
├── test_imports_part2.mojo    # Split: additional sections
└── test_imports_part3.mojo    # Split: additional sections
```
