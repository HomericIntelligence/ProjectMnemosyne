---
name: mojo-python-interop-to-stdlib
description: 'Replace Python.import_module calls with Mojo native stdlib. Use when:
  eliminating Python interop for file system ops (os, pathlib, builtins), refactoring
  load_named_tensors or similar functions, or migrating from Python glob/sorted to
  native Mojo os.listdir + sort.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Category** | architecture |
| **Objective** | Replace Python interop in Mojo file-system operations with native Mojo stdlib |
| **Outcome** | Success - eliminated 3 Python.import_module calls, no Python import needed |

## When to Use

Invoke this skill when:

- A Mojo function uses `Python.import_module("os")`, `Python.import_module("pathlib")`, or `Python.import_module("builtins")` for file listing or sorting
- You see `from python import Python` imported only for file system operations
- You need to list and filter directory contents (e.g., glob for `*.weights` files)
- You need deterministic sorted output of directory entries in Mojo
- Mojo stdlib now covers what was previously a Python workaround

## Verified Workflow

### Step 1: Identify Python Interop Usage

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

### Step 2: Replace with Mojo Native os.listdir

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

### Step 3: Filter by Extension

```mojo
var weight_files: List[String] = []
for i in range(len(entries)):
    var entry = entries[i]
    if entry.endswith(".weights"):
        weight_files.append(entry)
```

### Step 4: Sort for Deterministic Ordering

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

### Step 5: Construct Full Paths

```mojo
for i in range(len(weight_files)):
    var filepath = dirpath + "/" + weight_files[i]
    # use filepath...
```

### Step 6: Update Imports

Remove `from python import Python` if it is no longer used elsewhere in the file.
Add `import os`.

### Step 7: Verify No Other Python Usage

```bash
grep -n "Python\." <file>.mojo
```

If no other uses remain, the `from python import Python` import can be removed entirely.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct Mojo execution for test verification | Ran `pixi run mojo test` to validate changes | GLIBC version mismatch (requires 2.32+, host has older) | Tests only runnable in CI via Docker; validate logic correctness by code review |
| Using `Path.glob()` from Mojo pathlib | Looked for a Mojo equivalent of Python's `Path.glob("*.weights")` | Mojo's pathlib.Path does not expose a glob() method; only listdir() is available | Use `os.listdir()` + manual extension filtering instead of glob |
| Importing `from pathlib import Path` for directory listing | Tried `Path(dirpath).listdir()` pattern | The method signature is `listdir(::Path)` — available but returns filenames, not full paths | Still works, but `import os; os.listdir(dirpath)` is simpler and equivalent |

## Results & Parameters

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

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3240, PR #3789 | [notes.md](../references/notes.md) |
