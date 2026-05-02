---
name: mojo-anytensor-copy-pointer-leak
description: "UnsafePointer.take_pointee() moves the value out of pointed-to memory but does NOT free the pointer allocation. Must call ptr.free() explicitly after take_pointee(). Use when: (1) implementing copy() methods that use mem_alloc + take_pointee(), (2) debugging ASAN pooled_alloc leaks traced to Mojo struct copy methods."
category: debugging
date: 2026-04-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Mojo UnsafePointer take_pointee() Memory Leak

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-10 |
| **Objective** | Fix ASAN-reported pooled_alloc memory leaks in `AnyTensor.copy()` caused by missing `ptr.free()` after `UnsafePointer.take_pointee()` |
| **Outcome** | Successful — ASAN tests pass after adding `ptr.free()` |
| **Verification** | verified-ci |
| **Project** | ProjectOdyssey — `shared/tensor/any_tensor.mojo` |
| **Fix Commit** | `9126cf99` |

## When to Use

- Implementing a `copy()` method that uses `mem_alloc[T](1)` + `take_pointee()` pattern
- ASAN reports `pooled_alloc` leaks traced to a struct's `copy()` or similar factory method
- Debugging memory leaks in Mojo structs that allocate temporary `UnsafePointer` slots
- Code review of any method that calls `take_pointee()` without a subsequent `ptr.free()`

## Verified Workflow

### Quick Reference

```mojo
# BUGGY — ptr allocation leaks after take_pointee()
def copy(self) -> Self:
    var ptr = mem_alloc[AnyTensor](1)
    # ... initialize *ptr fields ...
    var result = ptr.take_pointee()  # moves value out; ptr itself still allocated
    return result                    # BUG: ptr.free() never called → ASAN leak

# FIXED — free the pointer allocation after taking the value
def copy(self) -> Self:
    var ptr = mem_alloc[AnyTensor](1)
    # ... initialize *ptr fields ...
    var result = ptr.take_pointee()  # moves value out
    ptr.free()                       # REQUIRED: release the pointer allocation
    return result
```

### Detailed Steps

1. **Identify the leak source** — Run ASAN tests and look for `pooled_alloc` leak reports.
   The stack trace will point to a method that calls `mem_alloc` without a corresponding `free`.

2. **Locate the pattern** — Search for uses of `take_pointee()` that are NOT followed by `ptr.free()`:

   ```bash
   grep -n "take_pointee" shared/tensor/any_tensor.mojo
   # Check each call site: is ptr.free() called on the same pointer before return?
   ```

3. **Understand the semantics** — `take_pointee()` performs a move of the *value* stored at the
   pointer address. The pointer object itself (the heap allocation from `mem_alloc`) remains alive
   and must be freed explicitly. This is analogous to `Box::into_inner()` in Rust — the contained
   value is extracted but the box allocation is not freed automatically.

4. **Apply the fix** — Add `ptr.free()` immediately after `take_pointee()`, before any early
   returns or branches:

   ```mojo
   var result = ptr.take_pointee()
   ptr.free()   # ← add this line
   return result
   ```

5. **Verify with ASAN** — Run the ASAN test suite to confirm the leak is resolved:

   ```bash
   just test-group "tests/shared/core" "test_any_tensor*"
   # or trigger CI which runs ASAN checks
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assume `take_pointee()` frees the pointer | Relied on the assumption that moving the value out would also release the heap allocation | `take_pointee()` only moves the VALUE; the allocation backing the pointer is unrelated and must be freed separately with `ptr.free()` | `take_pointee()` and `ptr.free()` are orthogonal operations — always pair them |
| Rewrite to avoid `mem_alloc` entirely | Attempted to construct the value directly on the stack without a temporary pointer | Pattern is sometimes required for trait-based initialization where the object needs to be addressable during construction | Use the `mem_alloc` + `take_pointee()` + `ptr.free()` triple when in-place initialization is unavoidable |
| Ignore ASAN warnings as false positives | Dismissed `pooled_alloc` reports as noise from Mojo's internal allocator | ASAN accurately identified 18 genuine allocations (13944 bytes) that were never freed, tracing back exactly to `AnyTensor.copy()` | Never dismiss ASAN `pooled_alloc` warnings; they point to real allocation/free mismatches |

## Results & Parameters

**ASAN error before fix:**

```text
18 allocations of pooled_alloc (13944 bytes) traced back to AnyTensor::copy
Direct leak of 776 byte(s) in 1 object(s) allocated from:
    #0 mem_alloc
    #1 AnyTensor.copy
```

**ASAN output after fix:**

```text
ASAN: no leaks detected
```

**Key invariant to remember:**

```text
mem_alloc[T](n) + take_pointee()  →  must call ptr.free() before function exits
                                      (regardless of whether an exception occurs or
                                       return path is taken)
```

**File fixed in ProjectOdyssey:** `shared/tensor/any_tensor.mojo` — `AnyTensor.copy()` method.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5210 ASAN leak investigation | Fix commit `9126cf99`; CI ASAN tests passing after fix |
