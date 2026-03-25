---
name: mojo-bitcast-always-inline-crash-fix
description: "Fix Mojo runtime crashes from bitcast pointer access by adding @always_inline. Use when: (1) libKGENCompilerRTShared.so crash in CI, (2) heap corruption after bitcast operations, (3) ASAP destruction invalidating pointers."
category: debugging
date: '2026-03-25'
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - bitcast
  - always-inline
  - heap-corruption
  - asap-destruction
---

# Mojo Bitcast @always_inline Crash Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix intermittent CI crashes in gradient checking tests caused by bitcast pointer access |
| **Outcome** | Successful — added @always_inline to 7 runtime-dtype accessor methods |

## When to Use

- CI crashes with `libKGENCompilerRTShared.so` stack traces after bitcast operations
- Heap corruption errors (`libc.so.6+0x45330` fortify_fail_abort) in Mojo code
- Methods that use `ptr.bitcast[T]()` to read/write tensor data crash intermittently
- Working `load[dtype]`/`store[dtype]` methods have `@always_inline` but similar methods without it crash

## Verified Workflow

### Quick Reference

```mojo
# BAD: Without @always_inline, ASAP destruction may destroy `self`
# before the bitcast pointer write completes
fn _set_float64(self, index: Int, value: Float64):
    var ptr = (self._data + offset).bitcast[Float32]()
    ptr[] = value.cast[DType.float32]()  # ← self may be destroyed here

# GOOD: @always_inline keeps self alive through the bitcast
@always_inline
fn _set_float64(self, index: Int, value: Float64):
    var ptr = (self._data + offset).bitcast[Float32]()
    ptr[] = value.cast[DType.float32]()  # ← self guaranteed alive
```

### Detailed Steps

1. **Identify the crash pattern** — Look for `libKGENCompilerRTShared.so` stack traces with no symbols. The crash occurs in heap management code (malloc/free)

2. **Check if bitcast methods lack `@always_inline`** — Compare crashing methods against working ones. In this case:
   - `load[dtype]`/`store[dtype]` had `@always_inline` and worked
   - `_get_float64`/`_set_float64` lacked it and crashed

3. **Add `@always_inline` to all bitcast accessor methods**:
   - `_get_float64()`, `_set_float64()`
   - `_get_float32()`, `_set_float32()`
   - `_get_int64()`, `_set_int64()`
   - `_get_dtype_size()` (helper called by all accessors)

4. **Replace any local deep-copy functions** with `AnyTensor.clone()` to avoid duplicate bitcast code paths

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Removing debug_assert | Removed debug_assert from load/store/data_ptr (commit dbc94176c) | Fixed JIT buffer overflow but not the bitcast crash — different root cause | debug_assert removal and @always_inline fix address different crash mechanisms |
| ADR-009 file splitting | Split test files to ≤10 fn test_ functions | Reduced frequency but didn't eliminate crashes — the real issue is pointer lifetime, not file size | File splitting is a workaround, not a root cause fix for bitcast crashes |
| Local reproduction | Ran tests 20+ times locally to reproduce | All passed locally — crash is CI-only due to different JIT optimization levels | Mojo JIT behavior differs between local and CI environments |

## Results & Parameters

### The ASAP destruction mechanism

Mojo uses "As Soon As Possible" destruction — objects are destroyed as soon as they're last used. In a method like:

```mojo
fn _set_float64(self, index: Int, value: Float64):
    var offset = index * self._get_dtype_size()
    var ptr = (self._data + offset).bitcast[Float32]()
    # ← Mojo may destroy `self` here since it's no longer referenced
    ptr[] = value.cast[DType.float32]()  # ← writing to freed memory!
```

The JIT compiler may determine that `self` is no longer needed after computing the pointer, and destroy it (freeing `self._data`) before the write through `ptr` completes.

`@always_inline` prevents this by inlining the function body into the caller's scope, where `self` remains alive for the duration of the call.

### Crash signature

```
#0 0x00007fc7f5dcb78b (/workspace/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3cb78b)
#1 0x00007fc7f5dc93c6 (/workspace/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3c93c6)
#2 0x00007fc7f5dcc397 (/workspace/.pixi/envs/default/lib/libKGENCompilerRTShared.so+0x3cc397)
#3 0x00007fc7fe633330 (/lib/x86_64-linux-gnu/libc.so.6+0x45330)
```

The `libc.so.6+0x45330` offset corresponds to `__fortify_fail` / `__stack_chk_fail`, indicating heap corruption from use-after-free.

### Methods that need @always_inline

Any method on AnyTensor that:
1. Accesses `self._data` via bitcast
2. Is NOT parametric (can't use `load[dtype]`/`store[dtype]` which require compile-time dtype)
3. Is called in tight loops (gradient checking, element-wise operations)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | shared/tensor/any_tensor.mojo | [notes](./skills/mojo-bitcast-always-inline-crash-fix.notes.md) |
