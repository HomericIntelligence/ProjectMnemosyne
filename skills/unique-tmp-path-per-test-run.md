---
name: unique-tmp-path-per-test-run
description: 'Replace hardcoded /tmp test file paths with unique per-run paths to
  prevent stale state. Use when: a test writes a fixed temp path that can persist
  across aborted runs, or parallel runs may collide.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Tests using a hardcoded `/tmp/<name>.txt` path leave stale files if the test aborts before cleanup, causing false failures on subsequent runs |
| **Solution** | Generate a unique path per run using a timestamp or nanosecond counter suffix |
| **Language** | Mojo (Mojo v0.26.1) |
| **Pattern** | `from time import perf_counter_ns` → `String(perf_counter_ns())` suffix |
| **Effort** | Single targeted edit — 2-3 lines changed |

## When to Use

- A test file has a hardcoded `/tmp/<fixed-name>` path for a temporary file
- Parallel CI matrix runs could execute the same test simultaneously and collide
- A test aborted mid-run and left a stale `/tmp` file, causing the next run to fail
- Reviewing tests for cleanup hygiene as part of a PR or code review

## Verified Workflow

### Quick Reference

```mojo
# Before
var test_path = "/tmp/test_remove_safely_3283.txt"

# After
from time import perf_counter_ns
var suffix = String(perf_counter_ns())
var test_path = "/tmp/test_remove_safely_" + suffix + ".txt"
```

### Steps

1. **Find the hardcoded path** — search for the fixed `/tmp/` path in the test file:

   ```bash
   grep -r "test_remove_safely_3283" tests/
   ```

2. **Add the import** inside the test function (or at module level if other
   functions use it):

   ```mojo
   from time import perf_counter_ns
   ```

3. **Replace the fixed path** with a dynamic one:

   ```mojo
   var suffix = String(perf_counter_ns())
   var test_path = "/tmp/test_remove_safely_" + suffix + ".txt"
   ```

4. **Verify the existing `try/finally` cleanup is in place** — the `finally`
   block must call the removal function even on the unique path:

   ```mojo
   finally:
       _ = remove_safely(test_path)
   ```

5. **Confirm the old path is gone**:

   ```bash
   grep -r "test_remove_safely_3283" tests/   # should return nothing
   ```

6. **Run the test twice consecutively** to confirm no stale-state interference:

   ```bash
   just test-mojo tests/shared/utils/test_io_part2.mojo
   just test-mojo tests/shared/utils/test_io_part2.mojo
   ls /tmp/test_remove_safely_*.txt 2>/dev/null || echo "No stale files"
   ```

## Key Decisions

- **`perf_counter_ns()` over `uuid`**: Mojo v0.26.1 stdlib has no `uuid` module;
  `perf_counter_ns()` provides a monotonically increasing nanosecond integer that
  is unique per run on a single machine. Sufficient for serial test runs and most
  parallel runs (nanosecond granularity makes collisions extremely unlikely).

- **Import inside function is valid**: Mojo allows `from X import Y` at the start
  of a function body. Place it next to the existing inline imports already in the
  function to keep changes minimal.

- **`try/finally` structure is correct as-is**: The fix is the *path* only.
  The existing `try/finally` already guarantees cleanup — do not restructure it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `uuid` module | Tried `from uuid import uuid4` | Mojo v0.26.1 stdlib has no `uuid` module — compile-time error | Check Mojo stdlib availability before choosing a uniqueness strategy |
| Move import to module level | Considered adding `from time import perf_counter_ns` at the top of the file | Not needed — inline import works and minimises diff size | Prefer the smallest change that solves the problem |
| Add a new helper function | Considered extracting `make_tmp_path()` utility | YAGNI — only one call site, a helper adds complexity for no gain | Don't abstract one-off patterns; inline is cleaner |

## Results & Parameters

### Exact Edit Applied (Mojo)

```mojo
# File: tests/shared/utils/test_io_part2.mojo
# Function: test_safe_remove()

# Add after existing imports in the function:
from time import perf_counter_ns

# Replace hardcoded path:
var suffix = String(perf_counter_ns())
var test_path = "/tmp/test_remove_safely_" + suffix + ".txt"
```

### Verification Commands

```bash
# Confirm old path removed
grep -r "test_remove_safely_3283" tests/     # → no output

# Run test to confirm it passes
just test-mojo tests/shared/utils/test_io_part2.mojo

# Confirm no stale files left after run
ls /tmp/test_remove_safely_*.txt 2>/dev/null || echo "No stale files — good"
```
