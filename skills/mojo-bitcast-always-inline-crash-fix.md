---
name: mojo-bitcast-always-inline-crash-fix
description: "Fix Mojo 0.26.1 UAF crashes from bitcast pointer writes. Use when: (1)
  libKGENCompilerRTShared.so crash in CI showing 3 fixed frames (0x3cb78b/0x3c93c6/0x3cc397),
  (2) heap corruption after bitcast writes in dtype conversion functions, (3) ASAP
  destruction invalidating pointers before write completes, (4) ADR-009 workaround marked
  Resolved but source still has UAF writes."
category: debugging
date: '2026-03-27'
version: "1.1.0"
user-invocable: false
tags:
  - mojo
  - bitcast
  - always-inline
  - heap-corruption
  - asap-destruction
  - uaf
  - asan
---

# Mojo Bitcast UAF / @always_inline Crash Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-27 |
| **Objective** | Fix Mojo 0.26.1 use-after-free crashes in bitcast write paths and dtype conversion functions |
| **Outcome** | Successful — two fix patterns: @always_inline on accessor methods; pointer arithmetic for direct UAF writes |

## When to Use

- CI crashes with `libKGENCompilerRTShared.so` stack traces showing the 3-frame fingerprint
- Heap corruption errors (`libc.so.6+0x45330` fortify_fail_abort) in Mojo code
- Methods that use `ptr.bitcast[T]()` to write tensor data crash intermittently
- Working `load[dtype]`/`store[dtype]` methods have `@always_inline` but similar methods without it crash
- Dtype conversion functions (`to_int8`, `to_fp8`, block packing functions) crash
- ADR-009 was marked "Resolved" but crashes persist — fix may have been applied to test callers, not source

## Verified Workflow

### Quick Reference — Two Fix Patterns

**Pattern 1: @always_inline for accessor methods**

```mojo
# BAD: Without @always_inline, ASAP destruction may destroy `self`
# before the bitcast pointer write completes
fn _set_float64(self, index: Int, value: Float64):
    var ptr = (self._data + offset).bitcast[Float32]()
    ptr[] = value.cast[DType.float32]()  # self may be destroyed here

# GOOD: @always_inline keeps self alive through the bitcast
@always_inline
fn _set_float64(self, index: Int, value: Float64):
    var ptr = (self._data + offset).bitcast[Float32]()
    ptr[] = value.cast[DType.float32]()  # self guaranteed alive
```

**Pattern 2: Pointer arithmetic for direct UAF writes**

```mojo
# UNSAFE write — triggers ASAN abort (UAF)
tensor._data.bitcast[T]()[i] = value

# SAFE read — OK
var v = tensor._data.bitcast[T]()[i]

# SAFE write — pointer arithmetic separates lifetime from write
var ptr = (tensor._data + offset).bitcast[T]()
ptr[] = value

# Also safe: use internal setters
tensor._set_float32(index, value)
tensor._set_int64(index, Int64(value))
```

### Detailed Steps

1. **Identify the crash pattern** — Look for `libKGENCompilerRTShared.so` stack traces
   with no symbols. The crash occurs in heap management code (malloc/free).

2. **Check the UAF write fingerprint** — The 3-frame ASAN signature is:

   ```text
   #0 ...libKGENCompilerRTShared.so+0x3cb78b
   #1 ...libKGENCompilerRTShared.so+0x3c93c6
   #2 ...libKGENCompilerRTShared.so+0x3cc397
   #3 ...libc.so.6+0x45330  -- __fortify_fail / heap corruption
   ```

3. **Audit ALL instances** — Do not just fix the test callers. Search the **source files**
   for UAF writes:

   ```bash
   grep -rn '._data.bitcast\[' shared/ tests/
   ```

   Common locations: dtype conversion functions (`to_int8`, `to_int16`, `to_int32`,
   `to_uint8/16/32/64`, `to_fp8`, `to_bf8`, `mxfp4`/`nvfp4` block packing).

4. **Check if bitcast methods lack `@always_inline`** — Compare crashing methods against
   working ones:
   - `load[dtype]`/`store[dtype]` had `@always_inline` and worked
   - `_get_float64`/`_set_float64` lacked it and crashed

5. **Add `@always_inline` to all bitcast accessor methods**:
   - `_get_float64()`, `_set_float64()`
   - `_get_float32()`, `_set_float32()`
   - `_get_int64()`, `_set_int64()`
   - `_get_dtype_size()` (helper called by all accessors)

6. **Replace direct UAF writes** in source and test code with pointer arithmetic or
   internal setters.

7. **Replace any local deep-copy functions** with `AnyTensor.clone()` to avoid duplicate
   bitcast code paths.

### ADR-009 "Resolved" Trap

If ADR-009 is marked "Resolved" but crashes persist:

- The fix was likely applied only to **test callers**, not the **source functions**
- Source files like `any_tensor.mojo` can have 20+ UAF write sites in dtype conversion
- Test files can have direct `_data.bitcast[Float32]()[i] = value` writes in helpers
- Always audit the source, not just the test wrappers

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Removing debug_assert | Removed debug_assert from load/store/data_ptr (commit dbc94176c) | Fixed JIT buffer overflow but not the bitcast crash — different root cause | debug_assert removal and @always_inline fix address different crash mechanisms |
| ADR-009 file splitting | Split test files to 10 fn test_ functions | Reduced frequency but did not eliminate crashes — real issue is pointer lifetime | File splitting is a workaround, not a root cause fix |
| Local reproduction | Ran tests 20+ times locally to reproduce | All passed locally — crash is CI-only due to different JIT optimization levels | Mojo JIT behavior differs between local and CI environments |
| Fixing test callers only | Applied UAF fixes to test code while source functions still had the UAF writes | Source `any_tensor.mojo` had ~20 UAF writes in dtype conversion functions | Always search source files for UAF writes — do not trust "Resolved" ADR status |
| Retrying CI runs | Rerunning failed CI jobs | Retrying masks root causes; crashes recur on subsequent runs | Investigate and fix the actual UAF write site |

## Results & Parameters

### The ASAP destruction mechanism

Mojo uses "As Soon As Possible" destruction — objects are destroyed as soon as they are
last used. In a method like:

```mojo
fn _set_float64(self, index: Int, value: Float64):
    var offset = index * self._get_dtype_size()
    var ptr = (self._data + offset).bitcast[Float32]()
    # Mojo may destroy `self` here since it's no longer referenced
    ptr[] = value.cast[DType.float32]()  # writing to freed memory!
```

The JIT compiler may determine that `self` is no longer needed after computing the pointer,
and destroy it (freeing `self._data`) before the write through `ptr` completes.

`@always_inline` prevents this by inlining the function body into the caller's scope,
where `self` remains alive for the duration of the call.

### Crash signature

```text
#0 0x00007fc7f5dcb78b (libKGENCompilerRTShared.so+0x3cb78b)
#1 0x00007fc7f5dc93c6 (libKGENCompilerRTShared.so+0x3c93c6)
#2 0x00007fc7f5dcc397 (libKGENCompilerRTShared.so+0x3cc397)
#3 0x00007fc7fe633330 (libc.so.6+0x45330)
```

The `libc.so.6+0x45330` offset corresponds to `__fortify_fail` / `__stack_chk_fail`,
indicating heap corruption from use-after-free.

### Methods that need @always_inline

Any method on AnyTensor that:

1. Accesses `self._data` via bitcast
2. Is NOT parametric (can't use `load[dtype]`/`store[dtype]` which require compile-time dtype)
3. Is called in tight loops (gradient checking, element-wise operations)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | shared/tensor/any_tensor.mojo | [notes](./mojo-bitcast-always-inline-crash-fix.notes.md) |
