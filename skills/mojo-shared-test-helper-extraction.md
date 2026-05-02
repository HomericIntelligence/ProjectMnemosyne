---
name: mojo-shared-test-helper-extraction
description: 'Move duplicated Mojo test helper functions from local test files into
  shared testing libraries. Use when: a parametric helper fn is copy-pasted across
  test files, a test file split requires the same utility, or conftest re-export pattern
  is needed.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill name** | mojo-shared-test-helper-extraction |
| **Category** | testing |
| **Trigger** | Parametric helper duplicated across Mojo test files or at risk of duplication after file splits |
| **Outcome** | Single canonical definition in `shared/testing/assertions.mojo`, re-exported via `tests/shared/conftest.mojo` |
| **Risk** | Low — purely mechanical move with no behavior change |

## When to Use

- A `fn` helper defined locally in a `test_*.mojo` file is (or will be) copied into sibling files
- A test file is being split (e.g. `test_matmul.mojo` → `part1/2/3`) and the helper must go somewhere
- A parametric function (`fn foo[dtype: DType](...)`) cannot be shared via a plain `conftest.mojo`
  test-file import due to Mojo v0.26.1 compile-time import constraints
- The helper is generic enough to belong to the shared testing infrastructure permanently

**NOT for**: Python test helpers (use `conftest.py`), or helpers that are truly one-off and won't recur.

## Verified Workflow

### Quick Reference

```text
1. Read local definition → copy to shared/testing/assertions.mojo
2. Add to module docstring function list
3. Add to re-export list in tests/shared/conftest.mojo
4. Add to import block in the source test file
5. Delete local definition + section comment from source test file
6. Verify with grep that no duplicate definition remains
```

### Step 1 — Locate the local definition

```bash
grep -rn "fn <helper_name>" tests/
```

Note the full function signature, docstring, and implementation. Also check whether it already
exists in `shared/testing/assertions.mojo`:

```bash
grep -n "fn <helper_name>" shared/testing/assertions.mojo
```

### Step 2 — Add to `shared/testing/assertions.mojo`

Append the function at the end of the file, under a new section comment if appropriate:

```mojo
# ============================================================================
# <Section Name>
# ============================================================================


fn <helper_name>[dtype: DType](...) raises:
    """<Docstring — note the Mojo v0.26.1 shared-import constraint if relevant>.

    Note: Mojo v0.26.1 does not support sharing helpers directly across test
    files via import. This function lives in a library module and is re-exported
    via tests/shared/conftest.mojo.
    ...
    """
    ...
```

Also update the module-level docstring `Functions:` list:

```mojo
    <helper_name>: Brief description
```

### Step 3 — Re-export from `tests/shared/conftest.mojo`

```mojo
from shared.testing.assertions import (
    ...
    <helper_name>,     # ← add here, keep list alphabetically sorted
)
```

### Step 4 — Update the source test file import

Add `<helper_name>` to the existing `from tests.shared.conftest import (...)` block.
Keep names sorted alphabetically within the block.

```mojo
from tests.shared.conftest import (
    ...
    <helper_name>,     # ← add here
    ...
)
```

### Step 5 — Remove the local definition

Delete the entire local function body **and** its preceding section comment block:

```
# ============================================================================
# Test Utilities - <Section Name>
# ============================================================================


fn <helper_name>[...
    ...
```

Use Edit tool with exact string match for the full block (comment + blank lines + fn body).

### Step 6 — Verify

```bash
# Confirm no remaining local definition
grep -n "fn <helper_name>" tests/shared/core/test_*.mojo

# Confirm import present in source file
grep -n "<helper_name>" tests/shared/core/test_<target>.mojo

# Confirm re-export present
grep -n "<helper_name>" tests/shared/conftest.mojo

# Confirm canonical definition present
grep -n "fn <helper_name>" shared/testing/assertions.mojo
```

## Mojo v0.26.1 Constraint — Why Library, Not conftest

Mojo v0.26.1 does **not** allow test files to import from each other, and `conftest.mojo`
is a test file. Parametric functions (`fn foo[dtype: DType](...)`) therefore cannot live
in `conftest.mojo` directly.

The workaround is:

1. Define the helper in a **library module** (`shared/testing/assertions.mojo`)
2. Re-export it from `conftest.mojo` (which imports from the library, not from another test)
3. Test files import from `tests.shared.conftest` as normal

This pattern is already established for all other shared assertion helpers in the project.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Put helper directly in `conftest.mojo` | Copy function body into `tests/shared/conftest.mojo` | Mojo v0.26.1 does not support generic functions shared across test files via conftest directly; compile errors | Always put parametric helpers in the library module (`shared/testing/`), then re-export |
| Duplicate helper in each split file | Leave local copy in part1 and copy to part2/part3 | Triplication creates drift risk — any fix must be applied 3× | Sharing is better; the library approach is the right fix |

## Results & Parameters

### Files Changed

| File | Change |
| ------ | -------- |
| `shared/testing/assertions.mojo` | Add canonical `fn assert_matrices_equal[dtype: DType]` + docstring entry |
| `tests/shared/conftest.mojo` | Add `assert_matrices_equal` to re-export import list |
| `tests/shared/core/test_matmul_part1.mojo` | Remove 84-line local definition + section comment; add import |

### Net diff

- **+92 lines** in shared library (function + section comment + docstring)
- **−85 lines** in test file (local definition removed)
- **+1 line** in conftest (re-export entry)

### Commit message format

```text
refactor(matmul): move assert_matrices_equal helper to shared testing library

Move the parametric assert_matrices_equal[dtype: DType] function from its
local definition in tests/shared/core/test_matmul_part1.mojo into the
shared testing infrastructure:

- Add assert_matrices_equal[dtype] to shared/testing/assertions.mojo
- Re-export via tests/shared/conftest.mojo
- Remove local duplicate from test file, import from conftest instead

Closes #<issue-number>
```
