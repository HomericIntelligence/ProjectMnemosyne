---
name: fix-flaky-glob-ordering
description: 'Fix flaky tests caused by non-deterministic filesystem glob ordering.
  Use when: test passes sometimes and fails other times with identical code, and the
  test asserts on the order of files loaded from a directory.'
category: debugging
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Tests fail intermittently due to non-deterministic `pathlib.glob()` ordering |
| **Root Cause** | Filesystem glob order is OS/filesystem-dependent and not guaranteed |
| **Fix** | Sort glob results before iterating; update test assertions to match sorted order |
| **Mojo Gotcha** | `sorted()` is a Python builtin — use `Python.import_module("builtins").sorted()` |

## When to Use

- A test fails on some CI runs but passes on others with **identical code and compiler version**
- The test loads multiple files from a directory and asserts on index-based ordering (e.g. `loaded[0].name == "weights"`)
- The loading function uses `pathlib.glob()`, `os.listdir()`, or similar without sorting
- Failure is intermittent (e.g. passed Feb 10, failed Feb 14 — same code)

## Verified Workflow

1. **Confirm the root cause**: Check if the loading function iterates glob results without sorting
2. **Fix the source function** (not just the test):
   - In pure Python: `sorted(p.glob("*.weights"))`
   - In Mojo with Python interop: `Python.import_module("builtins").sorted(p.glob("*.weights"))`
3. **Determine the sorted order**: Alphabetically, `"bias.weights" < "weights.weights"`
4. **Update test assertions** to match the now-deterministic sorted order:
   - `loaded[0]` → first alphabetically (e.g. `"bias"`)
   - `loaded[1]` → second alphabetically (e.g. `"weights"`)
5. **Verify no other callers** of the fixed function are affected by the new ordering

### Mojo Python Interop Pattern

```mojo
# WRONG - sorted() is not a Mojo builtin
var weight_files = sorted(p.glob("*.weights"))

# CORRECT - access Python's sorted() via builtins module
var builtins = Python.import_module("builtins")
var weight_files = builtins.sorted(p.glob("*.weights"))
```

This pattern matches existing usage in the codebase (e.g. `shared/utils/config.mojo`, `shared/utils/toml_loader.mojo`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `sorted(p.glob("*.weights"))` | Called `sorted()` directly in Mojo as if it were a builtin | Mojo compiler error: `use of unknown declaration 'sorted'` — `sorted()` is a Python builtin, not Mojo | In Mojo, Python builtins must be accessed via `Python.import_module("builtins")` |
| Fix only the test assertions | Reorder test to match observed CI output | Doesn't fix the non-determinism; different filesystems may return different orders | Always fix the source of non-determinism, not just the test |

## Results & Parameters

### The Fix (two files)

**`shared/utils/serialization.mojo`** (source fix):

```mojo
# Before (non-deterministic)
var weight_files = p.glob("*.weights")

# After (deterministic)
var builtins = Python.import_module("builtins")
var weight_files = builtins.sorted(p.glob("*.weights"))
```

**`tests/shared/test_serialization.mojo`** (test fix):

```mojo
# Before (assumed filesystem ordering)
assert_equal(loaded[0].name, "weights", ...)  # numel=6
assert_equal(loaded[1].name, "bias", ...)     # numel=3

# After (matches alphabetical sorted order: "bias" < "weights")
assert_equal(loaded[0].name, "bias", ...)     # numel=3
assert_equal(loaded[1].name, "weights", ...)  # numel=6
```

### Diagnosing Flaky CI

Key signal: same commit hash passing on one date and failing on another is almost always ordering/timing non-determinism, not logic bugs.

```bash
# Check if a test is the culprit by looking at CI history
gh run list --workflow "Comprehensive Tests" --branch main --limit 5
```
