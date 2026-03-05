---
name: mojo-hash-bitcast-floats
description: "Fix Mojo __hash__ for float-containing structs using UnsafePointer bitcast for exact IEEE 754 bit representation. Use when: float hash collisions occur for large/small values, or __hash__ uses lossy integer approximation."
category: debugging
date: 2026-03-05
user-invocable: false
---

# Skill: Fix Mojo __hash__ with Bitcast for Float Exact Representation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Session Context** | Issue #3164 - ExTensor __hash__ float precision fix |
| **Objective** | Replace lossy `Int(val * 1000000.0)` hash with exact IEEE 754 bitcast |
| **Outcome** | Success - equal floats always hash identically, distinct values distinguished |
| **Files Modified** | `shared/core/extensor.mojo`, `tests/shared/core/test_utility.mojo` |

## When to Use

Use this skill when:

1. A Mojo struct's `__hash__` computes float contributions via `Int(val * N)` or similar approximation
2. Dict/set keys with float fields have unexpected collisions for large values (e.g., `1e15`)
3. Float hash is unstable for very small distinct values (e.g., `1e-7` vs `2e-7`)
4. Implementing `__hash__` on a tensor/matrix struct that stores float data

### Trigger Conditions

- `__hash__` contains `Int(float_val * 1000000)` or similar scaling
- Tests show equal tensors with the same float values hash differently across runs
- Large float values overflow `Int` during hash computation
- Small distinct float values produce identical hashes (false collisions)

## Problem Context

### The Bug

Mojo's `__hash__` with `Int(val * 1000000.0)` causes:

1. **Int overflow** for large values: `1e15 * 1e6 = 1e21` overflows Int64
2. **False collisions** for small values: `1e-7 * 1e6 = 0.1` truncates to `0` — same as `2e-7 * 1e6 = 0.2`
3. **Precision loss**: Two close but unequal floats can map to the same integer

### The Fix

Use `UnsafePointer.address_of(local_val).bitcast[UInt64][]` to read the exact IEEE 754
64-bit representation of the float. Equal floats always have identical bit patterns.

## Verified Workflow

### Step 1: Locate the existing __hash__

```bash
grep -n "__hash__" <project>/shared/core/extensor.mojo
```

### Step 2: Replace the implementation

**Before (buggy)**:
```mojo
fn __hash__(self) -> UInt:
    var h: UInt = 0
    for i in range(self._numel):
        var val = self._get_float64(i)
        h = h * 31 + UInt(Int(val * 1000000.0))
    return h
```

**After (correct)**:
```mojo
fn __hash__(self) -> UInt:
    """Compute hash based on shape, dtype, and data.

    Uses bitcast to get exact IEEE 754 bit representation of float values,
    ensuring equal floats always hash identically and avoiding collisions
    for large or very small values.

    Returns:
        Hash value suitable for use as dict key.
    """
    from <project>.core.dtype_ordinal import dtype_to_ordinal

    var h: UInt = 0
    # Hash shape
    for i in range(len(self._shape)):
        h = h * 31 + UInt(self._shape[i])
    # Hash dtype ordinal
    h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
    # Hash data using exact IEEE 754 bit representation
    for i in range(self._numel):
        var val = self._get_float64(i)
        var local_val = val  # local copy required before UnsafePointer.address_of
        var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
        h = h * 31 + UInt(int_bits)
    return h
```

### Step 3: Critical `local_val` Pattern

The `local_val` intermediate variable is **required**. Do NOT write:

```mojo
# WRONG - may result in dangling pointer from temporary
var int_bits = (UnsafePointer.address_of(self._get_float64(i))).bitcast[UInt64][]
```

Always assign to a local variable first:

```mojo
# CORRECT - local variable has well-defined lifetime
var val = self._get_float64(i)
var local_val = val
var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
```

### Step 4: Add comprehensive tests

```mojo
fn test_hash_immutable() raises:
    """Equal tensors must produce identical hashes."""
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var b = arange(0.0, 3.0, 1.0, DType.float32)
    assert_equal_int(Int(hash(a)), Int(hash(b)), "Equal tensors should have same hash")

fn test_hash_different_values_differ() raises:
    """Different values must produce different hashes."""
    var shape = List[Int]()
    shape.append(1)
    var a = full(shape, 1.0, DType.float64)
    var b = full(shape, 2.0, DType.float64)
    if hash(a) == hash(b):
        raise Error("Different values should have different hashes")

fn test_hash_large_values() raises:
    """Large values (1e15) must hash consistently without overflow."""
    var shape = List[Int]()
    shape.append(1)
    var a = full(shape, 1e15, DType.float64)
    var b = full(shape, 1e15, DType.float64)
    assert_equal_int(Int(hash(a)), Int(hash(b)), "Large values must hash consistently")

fn test_hash_small_values_distinguish() raises:
    """Small distinct values (1e-7 vs 2e-7) must hash differently."""
    var shape = List[Int]()
    shape.append(1)
    var a = full(shape, 1e-7, DType.float64)
    var b = full(shape, 2e-7, DType.float64)
    if hash(a) == hash(b):
        raise Error("Distinct small values should have different hashes with bitcast")
```

### Step 5: Include shape and dtype in hash

For correctness, always include shape dimensions and dtype in the hash computation.
Two tensors with the same data but different shapes (or dtypes) should hash differently:

```mojo
# Hash shape dimensions
for i in range(len(self._shape)):
    h = h * 31 + UInt(self._shape[i])
# Hash dtype to distinguish float32 vs float64 tensors
h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct address_of on return value | `UnsafePointer.address_of(self._get_float64(i)).bitcast[UInt64][]` | Dangling pointer — temporary has no stable address | Always assign to a named local variable before taking its address |
| `Int(val * 1000000.0)` for large values | Multiply float by 1e6 then truncate to Int | `1e15 * 1e6 = 1e21` overflows Int64, producing garbage hash | Use bitcast to avoid any arithmetic on the float value |
| `Int(val * 1000000.0)` for small values | Multiply float by 1e6 then truncate to Int | `1e-7 * 1e6 = 0.1` rounds to 0 — same as `2e-7`, false collision | Bitcast preserves all 64 bits, no rounding |
| Skipping dtype in hash | Hashed only shape and data | Tensors of same shape and data but different dtypes (float32 vs float64) would collide | Include `dtype_to_ordinal(self._dtype)` in the hash chain |

## Results & Parameters

### Key Parameters

```mojo
# Hash multiplier (standard polynomial rolling hash)
# 31 is a prime commonly used in hash functions (Java String, Python str)
var h: UInt = 0
h = h * 31 + contribution
```

### Outcome

- Equal tensors with any float values always hash identically
- Large values (`1e15`) hash without overflow (UInt can hold `UInt64` cast)
- Small distinct values (`1e-7` vs `2e-7`) produce different hashes
- Shape and dtype differences also produce different hashes

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3164, PR #3373 | [notes.md](../../references/notes.md) |
