---
name: nan-hash-canonicalization
description: 'Canonicalize NaN bit patterns in __hash__ for IEEE 754 float tensors
  to ensure hash stability. Use when: different NaN representations (sign bit, payload,
  signaling vs quiet) produce different hashes for semantically identical NaN content.'
category: debugging
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: NaN Canonicalization in __hash__ for Float Tensors

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Session Context** | Issue #3382 - ExTensor __hash__ NaN stability (follow-up to #3164) |
| **Objective** | Ensure NaN-containing tensors hash identically regardless of NaN bit pattern |
| **Outcome** | Success - all NaN variants (sNaN, qNaN, -NaN, different payloads) hash to same value |
| **Files Modified** | `<project>/shared/core/extensor.mojo`, `<project>/tests/shared/core/test_hash.mojo` |

## When to Use

Use this skill when:

1. A struct's `__hash__` uses IEEE 754 bitcast (e.g. after applying `mojo-hash-bitcast-floats`)
   but NaN-containing values still produce non-deterministic hashes
2. Tensors/structs containing `NaN` are used as dict/set keys and hash differently across runs
3. Two tensors that should be "logically equal" (both contain NaN) have different hashes
4. Following up on a bitcast-based hash fix: bitcast preserves all NaN bits, including
   sign and payload, which then differ between NaN representations

### Trigger Conditions

- Hash test failures like: "NaN and -NaN hash differently" or "signaling NaN != quiet NaN hash"
- Dict membership checks fail for NaN-containing tensor keys that should be identical
- Issue description mentions IEEE 754 NaN, signaling vs quiet NaN, NaN payloads, or `-NaN`
- Struct stores float16, float32, float64, or bfloat16 data and implements `__hash__`

## Problem Context

### Why Bitcast Alone Is Not Enough

After fixing float hash precision with bitcast (see `mojo-hash-bitcast-floats`):

```mojo
var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
hasher.update(int_bits)
```

This correctly distinguishes `1.0` from `2.0` and handles large/small values. However,
IEEE 754 defines many valid NaN bit patterns:

| NaN Type | Float32 Example | Float64 Example |
|----------|----------------|----------------|
| Quiet NaN (positive) | `0x7FC00000` | `0x7FF8000000000000` |
| Quiet NaN (negative) | `0xFFC00000` | `0xFFF8000000000000` |
| Signaling NaN | `0x7F800001` | `0x7FF0000000000001` |
| NaN with payload | `0x7FC00002` | `0x7FF8000000000002` |

All of these are `NaN` (not-a-number), but their bit patterns differ. Raw bitcast
hashes them differently, violating the principle: equal hash for equal values.

### The Fix

After bitcasting to `UInt64`, detect NaN and replace with a single canonical bit pattern
before calling `hasher.update()`. No stored data is modified.

**NaN detection for Float64**: `(bits & 0x7FFFFFFFFFFFFFFF) > 0x7FF0000000000000`

- `0x7FF0000000000000` = positive infinity (exponent all-ones, mantissa zero)
- Any value exceeding this (after sign-strip) has a non-zero mantissa → NaN
- Catches all NaN variants: positive, negative, quiet, signaling, any payload

## Verified Workflow

### Step 1: Locate the existing bitcast-based __hash__

```bash
grep -n "__hash__\|hasher.update\|bitcast" <project>/shared/core/extensor.mojo
```

### Step 2: Add NaN canonicalization after the bitcast

**Before (incomplete — NaN unstable)**:

```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    # ... shape and dtype hashing omitted ...
    for i in range(self._numel):
        var val = self._get_float64(i)
        var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
        hasher.update(int_bits)  # ❌ NaN bit patterns not canonicalized
```

**After (correct — NaN stable)**:

```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    """Compute hash based on shape, dtype, and data.

    NaN values are canonicalized to a single quiet NaN bit pattern before
    hashing, ensuring that different NaN representations (signaling NaN,
    negative NaN, different NaN payloads) all produce the same hash.
    """
    # Canonical quiet NaN for Float64 (IEEE 754: exp all-ones, MSB mantissa set,
    # zero payload, positive sign)
    alias CANONICAL_NAN_F64: UInt64 = 0x7FF8000000000000
    alias F64_INF_BITS: UInt64 = 0x7FF0000000000000
    alias F64_ABS_MASK: UInt64 = 0x7FFFFFFFFFFFFFFF

    # ... shape and dtype hashing ...

    for i in range(self._numel):
        var val = self._get_float64(i)
        var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
        # Canonicalize any NaN to a single stable bit pattern
        if (int_bits & F64_ABS_MASK) > F64_INF_BITS:
            int_bits = CANONICAL_NAN_F64
        hasher.update(int_bits)
```

### Step 3: Why this works for all float widths

If `_get_float64()` converts float16/float32/bfloat16 to Float64 before bitcast,
the NaN canonicalization happens in Float64 space and catches all NaN variants
regardless of the original dtype:

- `float32 NaN → Float64 NaN` (via `.cast[DType.float64]()`) → detected and canonicalized
- `float16 NaN → Float64 NaN` (via `.cast[DType.float64]()`) → detected and canonicalized
- `bfloat16 NaN → Float64 NaN` (via `Float64(Float32(ptr[]))`) → detected and canonicalized

No per-dtype NaN canonicalization is needed when using a `_get_float64()` helper.

### Step 4: Test all NaN variants

```mojo
fn make_f32_nan_tensor(bits: UInt32) raises -> ExTensor:
    """Inject specific NaN bit pattern into a float32 scalar tensor."""
    var shape = List[Int]()
    var t = ExTensor(shape, DType.float32)
    t._data.bitcast[UInt32]()[] = bits
    return t^

fn make_f64_nan_tensor(bits: UInt64) raises -> ExTensor:
    """Inject specific NaN bit pattern into a float64 scalar tensor."""
    var shape = List[Int]()
    var t = ExTensor(shape, DType.float64)
    t._data.bitcast[UInt64]()[] = bits
    return t^

# Test: +qNaN vs -qNaN (f32)
fn test_hash_f32_quiet_nan_equals_negative_nan() raises:
    var pos_nan = make_f32_nan_tensor(UInt32(0x7FC00000))  # +qNaN
    var neg_nan = make_f32_nan_tensor(UInt32(0xFFC00000))  # -qNaN
    assert_equal_int(Int(hash(pos_nan)), Int(hash(neg_nan)),
        "Positive and negative quiet NaN (f32) must hash equal")

# Test: different payloads (f32)
fn test_hash_f32_nan_payload_irrelevant() raises:
    var nan_a = make_f32_nan_tensor(UInt32(0x7FC00001))
    var nan_b = make_f32_nan_tensor(UInt32(0x7FC00002))
    assert_equal_int(Int(hash(nan_a)), Int(hash(nan_b)),
        "NaN payloads must not affect hash (f32)")

# Test: signaling NaN vs quiet NaN (f32)
fn test_hash_f32_signaling_nan_equals_quiet_nan() raises:
    var quiet    = make_f32_nan_tensor(UInt32(0x7FC00000))  # qNaN
    var signaling = make_f32_nan_tensor(UInt32(0x7F800001)) # sNaN
    assert_equal_int(Int(hash(quiet)), Int(hash(signaling)),
        "Signaling and quiet NaN (f32) must hash equal")
```

### Step 5: Canonical NaN bit patterns reference

| Type | Canonical Quiet NaN Bits | Infinity Bits | NaN Condition |
|------|--------------------------|---------------|---------------|
| Float16 | `0x7E00` | `0x7C00` | `(bits & 0x7FFF) > 0x7C00` |
| Float32 | `0x7FC00000` | `0x7F800000` | `(bits & 0x7FFFFFFF) > 0x7F800000` |
| Float64 | `0x7FF8000000000000` | `0x7FF0000000000000` | `(bits & 0x7FFFFFFFFFFFFFFF) > 0x7FF0000000000000` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Per-dtype NaN canonicalization | Add separate float16/float32/float64 branches in `__hash__`, canonicalize in each native width | More complex, and the `_get_float64()` helper already unifies all dtypes in float64 space | If there's a `_get_float64()` helper, canonicalize once in float64 space — no per-dtype branches needed |
| `math.isnan()` for detection | Import `isnan` from `math` and call `isnan(val)` | Works but requires an import; the bitwise test `(bits & mask) > inf_bits` is self-contained and avoids the import | Bitwise NaN detection is simpler and requires no additional imports |
| Canonicalize in stored data | Modify `_data` bytes to replace NaN with canonical form when calling `nan_tensor()` | Violates the principle that hash should not mutate stored data; also breaks roundtrip fidelity | NaN canonicalization is a hash-side concern only — never mutate tensor data |

## Results & Parameters

### Canonical NaN Bit Patterns (IEEE 754)

```mojo
# Float64 canonical quiet NaN (positive sign, zero payload)
alias CANONICAL_NAN_F64: UInt64 = 0x7FF8000000000000

# Float64 NaN detection (strip sign bit, compare to infinity)
alias F64_INF_BITS:  UInt64 = 0x7FF0000000000000
alias F64_ABS_MASK:  UInt64 = 0x7FFFFFFFFFFFFFFF
# NaN if: (bits & F64_ABS_MASK) > F64_INF_BITS
```

### Test Matrix

| Test | What It Verifies |
|------|-----------------|
| `+qNaN == -qNaN hash` | Sign bit doesn't affect hash |
| `NaN payload 1 == NaN payload 2 hash` | Mantissa payload doesn't affect hash |
| `sNaN == qNaN hash` | Quiet/signaling distinction doesn't affect hash |
| `mixed NaN+normal deterministic` | NaN values in a multi-element tensor hash consistently |
| `different NaN patterns, same logical tensor` | End-to-end stability |
| `shape sensitivity` | Shape still contributes to hash |
| `dtype sensitivity` | Dtype still contributes to hash |
| `integer types unaffected` | No regression for non-float dtypes |

### Outcome

- All NaN variants (positive/negative, quiet/signaling, any payload) hash identically
- Normal float values continue to hash by exact bit representation (no regression)
- Integer and bool tensors unaffected (bitcast path still used, no NaN possible)
- Implementation is 4 lines added to the existing hash loop — minimal change

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3382, PR #4058 | Follow-up to #3164 bitcast fix |
