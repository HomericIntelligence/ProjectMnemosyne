---
name: mojo-python-interop-placeholder-replacement
description: 'Workflow for replacing Mojo stdlib-gap placeholders with Python interop.
  Use when: a Mojo function has a no-op placeholder body due to missing stdlib support
  (e.g. os.remove, os.rename), or when callers silently believe work was done when
  it was not.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Replace no-op `remove_safely()` placeholder in file_io.mojo with real file deletion |
| Outcome | Implemented using `Python.import_module("os").remove()` interop; pre-commit passes; PR created |
| Issue | ProjectOdyssey #3283 |

## When to Use

- A Mojo function body is a stub/placeholder because a stdlib operation doesn't exist in Mojo v0.26.1
- The placeholder returns `True`/`False` without actually performing the operation (silent failure risk)
- You need filesystem operations (`os.remove`, `os.rename`, `os.mkdir`, etc.) before Mojo adds them natively
- A NOTE comment in the code says "Mojo v0.26.1 doesn't have X"

## Verified Workflow

1. **Find the placeholder**: look for NOTE comments referencing Mojo version limitations
   ```bash
   grep -rn "NOTE (Mojo v0.26.1)" shared/
   ```

2. **Check existing Python interop usage** in the same file to find the established pattern:
   ```bash
   grep -n "Python.import_module" shared/utils/file_io.mojo
   ```

3. **Implement using the established pattern** (`safe_write_file` uses `os.rename` this way):
   ```mojo
   fn remove_safely(filepath: String) -> Bool:
       if not file_exists(filepath):
           return False
       try:
           var python = Python.import_module("os")
           python.remove(filepath)
           return True
       except:
           return False
   ```

4. **Replace the test stub** with a real test that verifies the operation actually occurred:
   ```mojo
   fn test_safe_remove() raises:
       var test_path = "/tmp/test_remove_<unique>.txt"
       var written = safe_write_file(test_path, "test content")
       assert_true(written)
       assert_true(file_exists(test_path))
       var removed = remove_safely(test_path)
       assert_true(removed)
       assert_false(file_exists(test_path))  # file is actually gone
       assert_false(remove_safely(test_path))  # nonexistent → False
   ```

5. **Run pre-commit hooks** to verify formatting:
   ```bash
   pixi run pre-commit run --files <changed files>
   ```

6. **Commit, push, and create PR** following conventional commits format with `Closes #<issue>`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run mojo tests locally | `pixi run mojo test tests/shared/utils/test_io.mojo` | GLIBC 2.32/2.33/2.34 not found on host OS (Debian Buster has GLIBC 2.31) | Mojo tests must run in Docker/CI; pre-commit hooks are the local verification boundary |
| Use Docker images | `docker run ghcr.io/homericintelligence/projectodyssey:main` | Project Docker images not pulled on local machine | CI is the authoritative test runner for Mojo; don't block PR on local Mojo execution |
| `just test-group` | `just test-group tests/shared/utils test_io.mojo` | `just` not installed on host | Same constraint as above; use `pixi run pre-commit` for local checks |

## Results & Parameters

**Pattern**: `Python.import_module("os").<method>(args)` inside a `try/except` block

**Imports required** (already at top of file_io.mojo):
```mojo
from python import Python, PythonObject
```

**Key design decisions**:
- Return `False` for nonexistent files *before* attempting removal (matches original guard)
- Catch all exceptions and return `False` (consistent with rest of file_io error handling)
- Do NOT add `raises` to the function signature — callers expect `Bool` return, not exception propagation

**Pre-commit verification** (works without GLIBC constraint):
```bash
pixi run pre-commit run --files shared/utils/file_io.mojo tests/shared/utils/test_io.mojo
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3283, PR #3874 | [notes.md](../references/notes.md) |
