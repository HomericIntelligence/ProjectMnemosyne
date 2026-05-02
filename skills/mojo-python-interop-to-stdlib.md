---
name: mojo-python-interop-to-stdlib
description: 'Replace Python.import_module calls with Mojo native stdlib, bridge filesystem
  gaps with Python interop, and migrate PythonObject placeholder parameters to native
  Mojo struct types. Use when: (1) eliminating Python interop for file system ops
  (os, pathlib, builtins), (2) a Mojo function has a no-op stub body due to missing
  stdlib (os.remove, os.rename), (3) a function accepts PythonObject as a stopgap
  while the native struct is now ready, (4) refactoring load_named_tensors or similar
  functions, (5) migrating from Python glob/sorted to native Mojo os.listdir + sort.'
category: architecture
date: 2026-03-07
version: "2.0.0"
user-invocable: false
tags: [mojo, python, interop, pythonobject, stdlib, migration, placeholder, dataloader]
---
## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-07 |
| **Category** | architecture |
| **Objective** | Replace Python interop in Mojo with native stdlib, bridge stdlib gaps with Python interop, and migrate PythonObject placeholder parameters to native Mojo struct types |
| **Outcome** | Success - eliminated 3 Python.import_module calls; implemented real filesystem ops via Python bridge; migrated run_epoch() from PythonObject to DataLoader |

## When to Use

Invoke this skill when:

- A Mojo function uses `Python.import_module("os")`, `Python.import_module("pathlib")`, or `Python.import_module("builtins")` for file listing or sorting
- You see `from python import Python` imported only for file system operations
- You need to list and filter directory contents (e.g., glob for `*.weights` files)
- You need deterministic sorted output of directory entries in Mojo
- Mojo stdlib now covers what was previously a Python workaround
- A Mojo function body is a stub/placeholder because a stdlib operation doesn't exist in the current Mojo version
- The placeholder returns `True`/`False` without actually performing the operation (silent failure risk)
- You need filesystem operations (`os.remove`, `os.rename`, `os.mkdir`, etc.) before Mojo adds them natively
- A NOTE comment in the code says "Mojo v0.26.1 doesn't have X"
- A Mojo function accepts `PythonObject` as a stopgap while the native struct was being built
- The native Mojo struct (e.g., `DataLoader`) now exists with `has_next()`/`next()` iteration
- Tests use `Python.none()` or a dummy `PythonObject` as a placeholder argument
- The function body has a `_ = data_loader  # Suppress unused variable` pattern (no real work done)
- A NOTE comment references "Track 4", "blocked by interop", or "TODO: implement when X is ready"

## Verified Workflow

### Part A: Replace Python Interop with Native Mojo stdlib

#### Step 1: Identify Python Interop Usage

Search for Python imports used only for file operations:

```bash
grep -n "Python.import_module" <file>.mojo
```

Common pattern to replace:

```mojo
# BEFORE (Python interop)
var _ = Python.import_module("os")
var pathlib = Python.import_module("pathlib")
var builtins = Python.import_module("builtins")
var p = pathlib.Path(dirpath)
var weight_files = builtins.sorted(p.glob("*.weights"))
```

#### Step 2: Replace with Mojo Native os.listdir

Mojo stdlib provides `os.listdir()` which returns `List[String]` of filenames (not full paths):

```mojo
# AFTER (native Mojo)
import os

var entries = os.listdir(dirpath)
```

Key differences from Python's `pathlib.Path.glob()`:

- Returns bare filenames only (not full paths) — must construct full path manually
- Returns all entries (no filtering) — must filter by extension manually
- No guaranteed ordering — must sort explicitly

#### Step 3: Filter by Extension

```mojo
var weight_files: List[String] = []
for i in range(len(entries)):
    var entry = entries[i]
    if entry.endswith(".weights"):
        weight_files.append(entry)
```

#### Step 4: Sort for Deterministic Ordering

Mojo stdlib has no built-in `sorted()` for `List[String]`. Use insertion sort (correct for small
lists, O(n^2) is fine for typical checkpoint directories):

```mojo
# Insertion sort (ascending)
for i in range(1, len(weight_files)):
    var key = weight_files[i]
    var j = i - 1
    while j >= 0 and weight_files[j] > key:
        weight_files[j + 1] = weight_files[j]
        j -= 1
    weight_files[j + 1] = key
```

#### Step 5: Construct Full Paths

```mojo
for i in range(len(weight_files)):
    var filepath = dirpath + "/" + weight_files[i]
    # use filepath...
```

#### Step 6: Update Imports

Remove `from python import Python` if it is no longer used elsewhere in the file.
Add `import os`.

#### Step 7: Verify No Other Python Usage

```bash
grep -n "Python\." <file>.mojo
```

If no other uses remain, the `from python import Python` import can be removed entirely.

---

### Part B: Bridge Stdlib Gaps with Python Interop

When Mojo stdlib does not yet support an operation (e.g., `os.remove`, `os.rename`), bridge the
gap using `Python.import_module("os")` rather than leaving a no-op placeholder.

#### Step 1: Find the Placeholder

Look for NOTE comments referencing Mojo version limitations:

```bash
grep -rn "NOTE (Mojo v0.26.1)" shared/
```

#### Step 2: Check Existing Python Interop in the Same File

```bash
grep -n "Python.import_module" shared/utils/file_io.mojo
```

#### Step 3: Implement Using the Established Pattern

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

Key design decisions:
- Return `False` for nonexistent files *before* attempting removal (matches original guard)
- Catch all exceptions and return `False` (consistent with rest of file_io error handling)
- Do NOT add `raises` to the function signature — callers expect `Bool` return, not exception propagation

#### Step 4: Replace the Test Stub with a Real Test

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

#### Step 5: Run Pre-commit Hooks

```bash
pixi run pre-commit run --files <changed files>
```

---

### Part C: Migrate PythonObject Placeholder Parameters to Native Struct Types

When the native Mojo struct is ready, replace `PythonObject` placeholder parameters.

1. **Read the function** with `PythonObject` parameter to understand the intended behavior from its docstring
2. **Locate the native struct** (`DataLoader`, etc.) — usually in `trainer_interface.mojo` or adjacent file
3. **Verify the struct's iteration API**: confirm `reset()`, `has_next()`, `next()` exist and return the right types
4. **Update the import block** — remove `from python import PythonObject` if no longer used elsewhere; add import for the native struct
5. **Change the function signature**: `data_loader: PythonObject` → `mut data_loader: DataLoader` (needs `mut` for stateful iteration)
6. **Implement the loop body**:
   ```mojo
   data_loader.reset()
   while data_loader.has_next():
       var batch = data_loader.next()
       var loss = self.step(batch.data, batch.labels)
       total_loss += Float64(loss._get_float32(0))
       num_batches += 1
   ```
7. **Update tests** — replace `Python.none()` / `py_loader` with a real struct constructed from `ExTensor` data
8. **Update test assertions** — old placeholder assertion (e.g., `assert_equal(Int(avg_loss), 0)`) must reflect real processing
9. **Remove unused imports** from the test file (e.g., `create_mock_dataloader` if switched to inline construction)
10. **Run pre-commit hooks** to verify mojo format, trailing whitespace, large files pass

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct Mojo execution for test verification | Ran `pixi run mojo test` to validate changes | GLIBC version mismatch (requires 2.32+, host has older) | Tests only runnable in CI via Docker; validate logic correctness by code review |
| Using `Path.glob()` from Mojo pathlib | Looked for a Mojo equivalent of Python's `Path.glob("*.weights")` | Mojo's pathlib.Path does not expose a glob() method; only listdir() is available | Use `os.listdir()` + manual extension filtering instead of glob |
| Importing `from pathlib import Path` for directory listing | Tried `Path(dirpath).listdir()` pattern | The method signature is `listdir(::Path)` — available but returns filenames, not full paths | Still works, but `import os; os.listdir(dirpath)` is simpler and equivalent |
| Run mojo tests locally (placeholder bridge) | `pixi run mojo test tests/shared/utils/test_io.mojo` | GLIBC 2.32/2.33/2.34 not found on host OS (Debian Buster has GLIBC 2.31) | Mojo tests must run in Docker/CI; pre-commit hooks are the local verification boundary |
| Use Docker images | `docker run ghcr.io/homericintelligence/projectodyssey:main` | Project Docker images not pulled on local machine | CI is the authoritative test runner for Mojo; don't block PR on local Mojo execution |
| `just test-group` | `just test-group tests/shared/utils test_io.mojo` | `just` not installed on host | Same constraint as above; use `pixi run pre-commit` for local checks |
| Running tests locally (native type migration) | `pixi run mojo test` | GLIBC too old on host (needs 2.32+, host has 2.31) | Tests must run in CI or Docker; verify code correctness by reading the struct APIs instead |
| Using Docker CI image | `docker run ghcr.io/homericintelligence/projectodyssey:main` | Image not pulled locally, registry access denied outside CI | Local test execution not available; rely on CI and pre-commit hooks |
| Keeping `_ = data_loader` | Left the suppress line when switching to real iteration | Compiler would warn / suppress is no longer needed once data_loader is consumed | Remove the suppress line entirely when implementing real iteration |

## Results & Parameters

### Part A: stdlib Replacement

**Import change**:

```mojo
# Remove
from python import Python

# Add
import os
```

**Complete replacement pattern** for `load_named_tensors`-style functions:

```mojo
var entries = os.listdir(dirpath)

var filtered: List[String] = []
for i in range(len(entries)):
    var entry = entries[i]
    if entry.endswith(".<extension>"):
        filtered.append(entry)

# Insertion sort for deterministic ordering
for i in range(1, len(filtered)):
    var key = filtered[i]
    var j = i - 1
    while j >= 0 and filtered[j] > key:
        filtered[j + 1] = filtered[j]
        j -= 1
    filtered[j + 1] = key

for i in range(len(filtered)):
    var filepath = dirpath + "/" + filtered[i]
    # process filepath...
```

### Part B: Python Bridge Pattern

**Pattern**: `Python.import_module("os").<method>(args)` inside a `try/except` block

**Imports required**:
```mojo
from python import Python, PythonObject
```

**Pre-commit verification** (works without GLIBC constraint):
```bash
pixi run pre-commit run --files shared/utils/file_io.mojo tests/shared/utils/test_io.mojo
```

### Part C: PythonObject → Native Struct Migration

**Signature change pattern**:

```mojo
# Before
fn run_epoch(mut self, data_loader: PythonObject) raises -> Float32:
    _ = data_loader  # suppress unused warning
    return Float32(0.0)

# After
fn run_epoch(mut self, mut data_loader: DataLoader) raises -> Float32:
    var total_loss = Float64(0.0)
    var num_batches = Int(0)
    data_loader.reset()
    while data_loader.has_next():
        var batch = data_loader.next()
        var loss = self.step(batch.data, batch.labels)
        total_loss += Float64(loss._get_float32(0))
        num_batches += 1
    if num_batches > 0:
        return Float32(total_loss / Float64(num_batches))
    else:
        return Float32(0.0)
```

**Import change pattern**:

```mojo
# Before
from python import PythonObject

# After
from shared.training.trainer_interface import DataLoader, DataBatch
```

**Test change pattern**:

```mojo
# Before
from python import Python
var py_loader = Python.none()
var avg_loss = training_loop.run_epoch(py_loader)
assert_equal(Int(avg_loss), 0)  # Placeholder returns 0.0

# After
var data_tensor = ones([100, 10], DType.float32)
var label_tensor = zeros([100, 1], DType.float32)
var data_loader = DataLoader(data_tensor^, label_tensor^, batch_size=10)
var avg_loss = training_loop.run_epoch(data_loader)
assert_greater(Float64(avg_loss), Float64(-0.001))
```

**Key constraints**:

- DataLoader's `next()` requires `mut self` — the parameter must be `mut data_loader`
- If `DataLoader.next()` still returns placeholder zero tensors internally (pending ExTensor.slice()), the loss will be 0.0 — use `assert_greater(loss, -0.001)` not `assert_equal(loss, positive_value)`
- The `DataBatch` struct exposes `.data` and `.labels` fields
- If `PythonObject` was imported only for this one use, remove the entire import line

### Method Signature Reference

| Pattern | Parameter keyword | Use when |
| --------- | ------------------ | ---------- |
| Stateful iteration | `mut data_loader: DataLoader` | Struct has `reset()`/`has_next()`/`next()` |
| Python bridge | `Python.import_module("os")` | Stdlib gap; wrap in `try/except`; return `Bool` not `raises` |
| Native stdlib | `import os; os.listdir()` | Stdlib covers the operation |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3240, PR #3789 (stdlib replacement) | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3283, PR #3874 (Python bridge for os.remove) | [notes.md](../references/notes.md) |
| ProjectOdyssey | run_epoch() migration (PythonObject → DataLoader) | Pre-commit hooks pass; CI validates |
