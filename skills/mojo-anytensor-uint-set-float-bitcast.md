---
name: mojo-anytensor-uint-set-float-bitcast
description: "AnyTensor.set(UInt32/UInt64) silently drops writes to float32/float64
  tensors because _set_int64 has no float handler. Use when: (1) writing raw IEEE 754
  bit patterns (NaN, Inf, denormals) into float tensors via set(UInt32/UInt64), (2)
  test assertions about NaN bit patterns in float tensors silently fail, (3) any
  UInt32/UInt64 write to a float-dtype AnyTensor appears to have no effect."
category: debugging
date: '2026-04-07'
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - anytensor
  - bitcast
  - nan
  - float32
  - float64
  - silent-bug
  - set
---

# AnyTensor.set(UInt32/UInt64) Silent Write Bug for Float Tensors

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Session Context** | ProjectOdyssey `test_hash.mojo` NaN hash test failures |
| **Objective** | Write raw IEEE 754 bit patterns (NaN, Inf) into float32/float64 AnyTensor slots |
| **Outcome** | Success — use bitcast write path in `set(UInt32)` / `set(UInt64)` for float dtypes |
| **Files Modified** | `shared/tensor/any_tensor.mojo` (~line 1007) |
| **Root Cause** | `_set_int64` has no branch for `DType.float32` / `DType.float64`; writes silently dropped |

## When to Use

Use this skill when:

1. Writing raw IEEE 754 bit patterns into a float-dtype `AnyTensor` via `set(UInt32, ...)` or `set(UInt64, ...)`
2. Test failures like "Positive and negative quiet NaN (f32) must hash equal" appear, but the
   NaN was written via `tensor.set(idx, UInt32(0x7FC00000))`
3. `AnyTensor.set(index, UInt32(...))` appears to have no effect on a `DType.float32` tensor
4. `AnyTensor.set(index, UInt64(...))` appears to have no effect on a `DType.float64` tensor
5. You need to inject specific NaN/Inf bit patterns into float tensors for testing

### Trigger Conditions

- Test asserts on NaN content of a float `AnyTensor` silently fail (element reads back as 0.0)
- Hash tests comparing NaN tensors fail because the NaN was never written
- Any `UInt32` or `UInt64` write into a `float32` or `float64` `AnyTensor` is lost

## Problem Context

### Why set(UInt32) Silently Drops Writes to Float Tensors

`AnyTensor.set(mut self, index: Int, value: UInt32)` delegates entirely to `_set_int64`:

```mojo
# Before fix — in any_tensor.mojo
fn set(mut self, index: Int, value: UInt32) raises:
    var idx = self._validate_index(index)
    self._set_int64(idx, Int64(Int(value)))
```

`_set_int64` handles integer dtypes (int8 through uint64, bool) with explicit `elif` branches.
It has **no branch for `DType.float32` or `DType.float64`**. When the tensor dtype is float32,
every branch is skipped and the function returns silently with no write performed.

This means `tensor.set(0, UInt32(0x7FC00000))` on a float32 tensor does nothing. The element
remains at its initialized value (typically 0.0).

The same bug exists for `set(mut self, index: Int, value: UInt64)` writing to `DType.float64`.

### Why This Is Hard to Notice

- No error or exception is raised; the function returns normally
- The test that follows reads back the element as 0.0 (or whatever the initialized value is)
- If the test checks `isnan()` or hash equivalence, it will fail — but the failure message
  points to the hash/NaN logic, not the write path
- The bug only manifests for float dtypes; integer dtype writes work correctly

## Verified Workflow

### Step 1: Identify that the write is silently dropped

Add a temporary debug print to confirm the element is not being written:

```mojo
var t = AnyTensor(List[Int](), DType.float32)
t.set(0, UInt32(0x7FC00000))  # Attempt to write +qNaN
# Debug: read back as UInt32 via bitcast
var ptr = (t._data).bitcast[UInt32]()
print(ptr[])  # Prints 0, not 0x7FC00000 — confirms write was dropped
```

### Step 2: Apply the fix in any_tensor.mojo

Add a float dtype guard at the top of `set(UInt32)` before delegating to `_set_int64`:

```mojo
fn set(mut self, index: Int, value: UInt32) raises:
    var idx = self._validate_index(index)
    # _set_int64 has no handler for float dtypes; use direct bitcast write
    if self._dtype == DType.float32:
        var dtype_size = self._get_dtype_size()
        var offset = idx * dtype_size
        var ptr = (self._data + offset).bitcast[UInt32]()
        ptr[] = value
    else:
        self._set_int64(idx, Int64(Int(value)))
```

Apply the same pattern to `set(UInt64)` for `DType.float64`:

```mojo
fn set(mut self, index: Int, value: UInt64) raises:
    var idx = self._validate_index(index)
    # _set_int64 has no handler for float64; use direct bitcast write
    if self._dtype == DType.float64:
        var dtype_size = self._get_dtype_size()
        var offset = idx * dtype_size
        var ptr = (self._data + offset).bitcast[UInt64]()
        ptr[] = value
    else:
        self._set_int64(idx, Int64(value))
```

### Step 3: Verify with a round-trip test

```mojo
fn test_anytensor_set_uint32_float32_bitcast() raises:
    """Verify that set(UInt32) writes raw bits into a float32 AnyTensor."""
    var shape = List[Int]()
    var t = AnyTensor(shape, DType.float32)
    var nan_bits = UInt32(0x7FC00000)  # IEEE 754 +quiet NaN
    t.set(0, nan_bits)
    # Read back via bitcast to confirm bit pattern
    var ptr = (t._data).bitcast[UInt32]()
    assert_equal(ptr[], nan_bits, "UInt32 bitcast write must preserve bit pattern")

fn test_anytensor_set_uint64_float64_bitcast() raises:
    """Verify that set(UInt64) writes raw bits into a float64 AnyTensor."""
    var shape = List[Int]()
    var t = AnyTensor(shape, DType.float64)
    var nan_bits = UInt64(0x7FF8000000000000)  # IEEE 754 +quiet NaN
    t.set(0, nan_bits)
    var ptr = (t._data).bitcast[UInt64]()
    assert_equal(ptr[], nan_bits, "UInt64 bitcast write must preserve bit pattern")
```

### Step 4: Where to find _get_dtype_size()

`AnyTensor` already has a `_get_dtype_size()` method used in other internal paths (e.g., the
read/bitcast helpers for bfloat16). It returns the byte width of each element for the current
dtype. The offset calculation `idx * dtype_size` is the same pattern used throughout the file.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `set(UInt32)` assuming bitcast semantics | Called `tensor.set(0, UInt32(0x7FC00000))` expecting raw bit write into float32 slot | Delegates to `_set_int64` which silently ignores float dtypes | Always check the implementation of `set()` overloads — numeric conversion ≠ bitcast |
| UnsafePointer read pattern (wrong direction) | `UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[]` | This is the read path (UInt32 → Float32), not the write path | Bitcast direction matters: for writes, start from the `_data` pointer, not from the value |
| Assuming `_set_int64` covers all dtypes | Trusted that `set(UInt32)` would route correctly for any dtype | `_set_int64` only handles integer DTypes — float dtypes silently fall through all branches | Always verify internal dispatch functions cover the dtypes you intend to write |

## Results & Parameters

### Quick Reference

```mojo
# WRONG: silently drops write for float32 tensor
tensor.set(0, UInt32(0x7FC00000))  # no-op if dtype == DType.float32

# CORRECT after fix: bitcast write path
# (applied inside any_tensor.mojo set(UInt32) implementation)
var ptr = (self._data + idx * self._get_dtype_size()).bitcast[UInt32]()
ptr[] = value

# For float64 / UInt64:
var ptr = (self._data + idx * self._get_dtype_size()).bitcast[UInt64]()
ptr[] = value
```

### Affected DType Pairs

| set() Overload | Affected Dtype | Symptom |
|----------------|---------------|---------|
| `set(UInt32)` | `DType.float32` | Write silently dropped |
| `set(UInt64)` | `DType.float64` | Write silently dropped |
| `set(UInt32)` | integer dtypes | Works correctly (handled by `_set_int64`) |
| `set(UInt64)` | integer dtypes | Works correctly (handled by `_set_int64`) |

### Common IEEE 754 Bit Patterns for Testing

| Pattern | Float32 (UInt32) | Float64 (UInt64) |
|---------|-----------------|-----------------|
| +Quiet NaN | `0x7FC00000` | `0x7FF8000000000000` |
| -Quiet NaN | `0xFFC00000` | `0xFFF8000000000000` |
| +Signaling NaN | `0x7F800001` | `0x7FF0000000000001` |
| +Infinity | `0x7F800000` | `0x7FF0000000000000` |
| -Infinity | `0xFF800000` | `0xFFF0000000000000` |
| -0.0 | `0x80000000` | `0x8000000000000000` |

### Outcome

- `set(UInt32)` on `DType.float32` tensors correctly writes raw bit patterns
- `set(UInt64)` on `DType.float64` tensors correctly writes raw bit patterns
- Integer dtype behavior unchanged
- NaN hash tests that failed due to the silent write now pass

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | `test_hash.mojo` NaN hash failures | `any_tensor.mojo` ~line 1007; fix applied, CI pending |
