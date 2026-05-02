---
name: debugging-slice-view-bad-free-destructor
description: "Diagnose and fix bad-free crashes from tensor view destructors that call free() on offset pointers. Use when: (1) ASAN reports 'attempting free on address which was not malloc()-ed', (2) the freed address is INSIDE a larger allocation, (3) a slice/view method offsets _data without guarding __del__, (4) CI crashes appear flaky with libKGENCompilerRTShared.so abort after many test functions."
category: debugging
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - asan
  - bad-free
  - view
  - slice
  - destructor
  - mojo
  - tensor
  - heap-corruption
  - ci-flakiness
---

# Slice View Bad-Free Destructor Bug

Diagnose and fix crashes caused by tensor view destructors calling `free()` on offset
pointers that were never returned by `malloc()`.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-24 |
| **Objective** | Find root cause of "flaky" test_training_loop.mojo CI crashes |
| **Outcome** | Success -- found 1-line bug in AnyTensor.__del__: missing _is_view check before pooled_free |
| **Repository** | ProjectOdyssey |
| **PR** | #5097 |
| **ADR** | ADR-013 |

## When to Use

- ASAN reports `attempting free on address which was not malloc()-ed`
- The freed address is N bytes INSIDE a larger allocation (e.g., "512 bytes inside of 1024-byte region")
- A `slice()`, `view()`, or similar method creates tensors with offset `_data` pointers
- The destructor calls `free(self._data)` without checking if it's a view
- CI tests crash "flakily" with `libKGENCompilerRTShared.so` abort after many sequential test functions
- Smaller test files pass but large monolithic files crash (heap corruption accumulates across functions)
- The crash happens even when running the crashing test ALONE (with ASAN)

## Verified Workflow

### Quick Reference

```bash
# Step 1: Build with ASAN to catch bad-free immediately
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/repro <test_file.mojo>
/tmp/repro

# Step 2: Look for "attempting free on address which was not malloc()-ed"
# Key: Check if address is INSIDE a larger allocation
# "0x519000001680 is located 512 bytes inside of 1024-byte region"
# This means _data was offset, not independently allocated

# Step 3: Check the __del__ destructor
# Does it call free/pooled_free unconditionally?
# Does it check _is_view / is_view() first?

# Step 4: Check the slice/view method
# Does it offset _data? (e.g., result._data = self._data + offset)
# Does it set an _is_view flag?
# Does __del__ respect that flag?
```

### Detailed Steps

#### Step 1: Reproduce with ASAN

ASAN catches bad-free immediately on the FIRST occurrence. Without ASAN, `free()` on
an invalid pointer silently corrupts heap metadata, and the crash only manifests after
enough corruption accumulates (~15-17 function calls).

```bash
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/test_asan tests/shared/training/test_training_loop.mojo
/tmp/test_asan
```

#### Step 2: Read the ASAN output

Key fields in the ASAN report:

```text
ERROR: AddressSanitizer: attempting free on address which was not malloc()-ed: 0x519000001680
                                                                               ^^^^^^^^^^^^
                                                                               This is the offset ptr

0x519000001680 is located 512 bytes inside of 1024-byte region [0x519000001480,0x519000001880)
                          ^^^^^^^^                               ^^^^^^^^^^^^
                          Offset into parent                     Parent's base (from malloc)

freed by thread T0 here:
    #4 shared::base::memory_pool::pooled_free    ← The free call
    #5 shared::tensor::any_tensor::AnyTensor::__del__  ← Destructor
    #6 test_training_loop::test_dataloader_4d_batch_slicing()  ← Test function

allocated by thread T0 here:
    #4 shared::tensor::any_tensor::AnyTensor::__init__  ← Original allocation
    #5 shared::tensor::any_tensor::ones()  ← Creator function
```

The "512 bytes inside of 1024-byte region" proves `_data` was offset into the parent's
allocation by `slice()`, not independently allocated.

#### Step 3: Find the bug

Check the slice method and destructor:

```mojo
# slice() creates offset pointer (any_tensor.mojo:754):
result._data = self._data + offset_bytes  # Offset INTO parent allocation
result._is_view = True                    # Flag is set...

# __del__ ignores the flag (any_tensor.mojo:491):
if self._refcount[] == 0:
    pooled_free(self._data, self._allocated_size)  # BOOM: frees offset ptr
    self._refcount.free()
```

#### Step 4: Apply the fix

```mojo
# Fixed __del__:
if self._refcount[] == 0:
    if not self._is_view:  # Views share parent's allocation
        pooled_free(self._data, self._allocated_size)
    self._refcount.free()  # Refcount is always independently allocated
```

#### Step 5: Verify

```bash
# Reproducer should now pass (only LeakSanitizer reports, no bad-free):
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . -o /tmp/repro <file>
/tmp/repro
# Expected: no "bad-free" errors

# Full monolithic test should pass all 19 tests:
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/training tests/shared/training/test_training_loop.mojo
/tmp/training
# Expected: "All training loop tests passed!" with no ASAN errors
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Classified as JIT compilation overflow | Assumed crash was before any test output (JIT can't compile) | Re-reading CI logs showed 17 tests PASSED before crash -- runtime error, not JIT | Always read the actual CI log output, don't trust initial classification |
| Assumed same root cause as Day 53 bitcast UAF | Same libKGENCompilerRTShared.so+0x3cb78b offset as the bitcast UAF | ASAN reported "bad-free" not "heap-use-after-free" -- different bug entirely | Same crash signature does NOT mean same root cause -- ASAN distinguishes them |
| Assumed allocation churn from prior tests was required | Blog's bitcast UAF needed ~15 prior functions for churn | Running the crash test ALONE with ASAN still triggered the bad-free | Always test the failing function in isolation first -- eliminates churn hypothesis |
| Explored agent claimed bitcast WRITE in training_loop.mojo:75 was the trigger | Agent reported line 75 as the UAF site | Line 75 is a bitcast READ (blog experiment 23 proved only writes trigger) | Verify agent findings by reading the actual code yourself |
| Investigated non-atomic refcount as possible crash cause | Explored thread safety of refcount++ and refcount-- | Mojo is single-threaded; refcount operations are safe | Don't investigate threading bugs in single-threaded runtimes |

## Results & Parameters

### 3-Line Minimum Reproducer

```mojo
from shared.tensor.any_tensor import AnyTensor, ones

fn main() raises:
    var data = ones([8, 2, 4, 4], DType.float32)  # 1024 bytes
    var batch = data.slice(4, 8)  # _data = data._data + 512 bytes
    # batch.__del__ → pooled_free(offset_ptr) → ASAN: bad-free
```

### ASAN Build Commands

```bash
# Build with ASAN
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . -o /tmp/repro <file.mojo>

# Run (ASAN catches bad-free immediately)
/tmp/repro
```

### The 1-Line Fix

```mojo
# In AnyTensor.__del__, before pooled_free:
if not self._is_view:
    pooled_free(self._data, self._allocated_size)
```

### Why It Appeared Flaky Without ASAN

| Condition | Behavior |
| ----------- | ---------- |
| With ASAN | Crashes immediately on first bad-free (100% reproducible) |
| Without ASAN, 1 test | Usually passes (heap corruption too minor to trigger abort) |
| Without ASAN, 15+ tests | Crashes ~50-80% of the time (corruption accumulates) |
| Without ASAN, different CI runner | Different heap layout = different crash threshold |
| Smaller test files | Usually pass (fewer tests = less corruption per file) |

### Three Bugs, One Crash Signature

All three produce identical `libKGENCompilerRTShared.so+0x3cb78b` crash output:

| Bug | Root Cause | ASAN Report | Our Code? |
| ----- | ----------- | ------------- | ----------- |
| Day 53 bitcast UAF | ASAP destruction frees tensor before bitcast write | heap-use-after-free | No (Mojo compiler bug) |
| Mojo "heap corruption" | Same bitcast UAF with more churn | heap-use-after-free | No (same Mojo bug) |
| This bug (slice view) | __del__ frees offset _data pointer from slice() | bad-free (attempting free on non-malloc'd address) | **Yes (our bug)** |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5097, ADR-013 | Fix + ADR + Day 61 blog post |
