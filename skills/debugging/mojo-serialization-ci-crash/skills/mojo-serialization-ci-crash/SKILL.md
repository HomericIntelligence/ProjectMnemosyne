---
name: mojo-serialization-ci-crash
description: "Debug Mojo serialization CI crashes from dtype string conversion mismatches and Python interop crashes. Use when: (1) mojo test crashes during hex encoding or serialization roundtrip, (2) CI fails with libKGENCompilerRTShared crash in serialization tests, (3) dtype roundtrip produces wrong type after load, (4) load_named_tensors returns wrong ordering."
category: debugging
date: 2026-03-07
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| Issue | `test_serialization.mojo` crashes in CI with exit code 1 (non-zero, not a compile error) |
| Symptoms | `libKGENCompilerRTShared.so` crash during `test_hex_encoding()`, dtype roundtrip failures |
| Root Causes | (1) `String(dtype)` vs `dtype_to_string()` mismatch; (2) Python pathlib interop crash in `load_named_tensors` |
| Fix | Use `dtype_to_string(dtype)` in `save_tensor()`; replace Python pathlib with native Mojo `os.listdir` |
| Worktree Risk | Branch can be behind `origin/main` containing relevant fixes — always rebase before investigating |

## When to Use

- Mojo serialization test crashes with `mojo: error: execution crashed` and stack trace from `libKGENCompilerRTShared.so`
- CI shows exit code 1 on `test_serialization.mojo` specifically after "Testing hex encoding..." or "Testing dtype utilities..."
- `load_tensor()` returns wrong dtype (e.g., `DType.float32` becomes unknown after roundtrip)
- `load_named_tensors()` returns tensors in non-deterministic order causing flaky assertions
- Worktree branch has different `serialization.mojo` than `origin/main` (check `git diff origin/main`)

## Verified Workflow

### Step 1: Read CI failure logs to identify the crash location

```bash
gh run list --workflow="comprehensive-tests.yml" --branch main --limit 10 \
  --json status,conclusion,databaseId | python3 -c "
import json,sys; runs=json.load(sys.stdin)
[print(r['databaseId'], r['status'], r.get('conclusion','')) for r in runs if r.get('conclusion')=='failure']
"
gh run view <RUN_ID> --log-failed 2>&1 | grep -A 30 "test_serialization"
```

Look for: "Testing dtype utilities..." (passes), then "Testing hex encoding..." (crashes). This identifies the crash is in `test_hex_encoding()` or `bytes_to_hex`.

### Step 2: Check if worktree is behind origin/main

```bash
git diff origin/main -- shared/utils/serialization.mojo
```

If the diff shows `load_named_tensors` using Python pathlib (`pathlib.Path(dirpath).glob("*.weights")`), the worktree is missing the critical fix. Rebase:

```bash
git stash
git rebase origin/main
git stash pop
```

### Step 3: Fix dtype string serialization

In `save_tensor()`, find:

```mojo
var dtype_str = String(dtype)  # WRONG - relies on DType.__str__ format
```

Replace with:

```mojo
var dtype_str = dtype_to_string(dtype)  # CORRECT - canonical serialization
```

`dtype_to_string()` is the authoritative function that maps `DType.float32` → `"float32"`, etc., and is guaranteed to match what `parse_dtype()` accepts.

### Step 4: Verify load_named_tensors uses native Mojo os.listdir

The correct implementation uses `os.listdir` with insertion sort:

```mojo
import os

fn load_named_tensors(dirpath: String) raises -> List[NamedTensor]:
    var entries = os.listdir(dirpath)
    var weight_files: List[String] = []
    for i in range(len(entries)):
        var entry = entries[i]
        if entry.endswith(".weights"):
            weight_files.append(entry)
    # Insertion sort for deterministic alphabetical ordering
    for i in range(1, len(weight_files)):
        var key = weight_files[i]
        var j = i - 1
        while j >= 0 and weight_files[j] > key:
            weight_files[j + 1] = weight_files[j]
            j -= 1
        weight_files[j + 1] = key
    # ... load each file
```

This replaces the Python interop version that used `Python.import_module("pathlib")` which crashed in CI.

### Step 5: Commit, push, and PR

```bash
git add shared/utils/serialization.mojo
git commit -m "fix(serialization): use dtype_to_string() instead of String(dtype) in save_tensor"
git push -u origin <branch>
gh pr create --title "fix(serialization): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run test locally | `pixi run mojo tests/shared/test_serialization.mojo` | GLIBC version incompatibility on dev machine (`GLIBC_2.32` not found) | Can't reproduce Mojo crashes locally; must rely on CI logs |
| Assume crash is from `bytes_to_hex` string indexing | Examined `hex_chars[high]` and `result += hex_chars[low]` for bounds issues | The crash was actually caused by Python pathlib interop in `load_named_tensors`, not hex encoding | The crash location in logs ("Testing hex encoding...") is misleading — print statement precedes the crashing function call, but the actual crash may be from a different test that runs earlier |
| Check if `String(DType)` format is wrong | Checked if `String(DType.float32)` produces something other than `"float32"` | Test passed in recent CI even with `String(dtype)` — Mojo's DType `__str__` apparently produces `"float32"` format | Even if the existing code works, using `dtype_to_string()` is more explicit and defensive |
| Look for non-alphabetical ordering in test assertions | Checked if `loaded[0]` should be "weights" vs "bias" | Test already had correct alphabetical order (`bias` before `weights`) in assertions | Verify test assertions match expected sorted output before assuming they're wrong |

## Results & Parameters

### Key Insight: Two Separate Bugs

The CI failure had two independent root causes that must both be fixed:

**Bug 1 (dtype serialization)**:
- File: `shared/utils/serialization.mojo`
- Line: ~120 in `save_tensor()`
- Bug: `var dtype_str = String(dtype)`
- Fix: `var dtype_str = dtype_to_string(dtype)`

**Bug 2 (Python interop crash)**:
- File: `shared/utils/serialization.mojo`
- Function: `load_named_tensors()`
- Bug: `Python.import_module("pathlib")` → `p.glob("*.weights")` crashes CI
- Fix: Native Mojo `os.listdir()` + insertion sort

### Diagnosing From CI Logs

```
Testing dtype utilities...     ← PASSES (Bug 1 didn't manifest here)
Testing hex encoding...         ← CRASHES HERE (actually Bug 2 setup crash)
mojo: error: execution crashed
```

The crash prints "Testing hex encoding..." before crashing, but the real crash can be in a different part of the runtime from Python interop initialization.

### Worktree Sync Pattern

When a branch is created from an older main commit, it may be missing critical fixes merged after branch creation:

```bash
# Check what's different
git diff origin/main -- <file>

# Sync safely
git stash
git rebase origin/main
git stash pop

# Verify your change survived
git diff -- <file>
```
