---
name: bf16-nan-canonicalization-test
description: 'Test and fix BFloat16 NaN canonicalization in Mojo tensor types. Use
  when: implementing __hash__ for float tensors, BF16 NaN hashing produces inconsistent
  results, or debugging NaN bit pattern preservation through dtype conversions.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | BFloat16 NaN canonicalization in `__hash__` could silently fail due to numeric cast path |
| **Root Cause** | `Float64(Float32(BFloat16))` may canonicalize unusual NaN bit patterns before the `isnan()` check |
| **Fix** | Raw bit manipulation: read UInt16, shift left 16 bits, bitcast to Float32, then convert to Float64 |
| **Test Strategy** | `make_bf16_nan_tensor` helper writes raw UInt16 bits via pointer cast to bypass `_set_float64` |
| **Verified** | Canonical NaN (0x7FC0), negative quiet NaN (0xFFC0), and cross-variant hash equality |

## When to Use

- You are implementing or debugging `__hash__` for a Mojo tensor/array type that stores BFloat16 data
- You see inconsistent hashing for BFloat16 NaN values (different NaN patterns hash differently)
- You need to test that unusual NaN bit patterns survive a multi-step dtype conversion pipeline
- You need to write raw float bit patterns to Mojo tensors, bypassing the typed setter

## Verified Workflow

### Quick Reference

| Step | What to Do |
| ------ | ------------ |
| 1 | Identify the `_get_float64` / dtype conversion path for BFloat16 |
| 2 | Replace numeric cast with raw bit manipulation |
| 3 | Add `make_bf16_nan_tensor` helper that writes raw UInt16 bits |
| 4 | Test canonical NaN (0x7FC0), negative quiet NaN (0xFFC0), and cross-variant equality |

### Step 1 — Diagnose the conversion path

BFloat16 shares the same sign+exponent layout as Float32 but occupies only the upper 16 bits.
The naive conversion `Float64(Float32(BFloat16))` goes through the numeric cast path, which
the CPU may silently canonicalize (setting mantissa to a canonical pattern), destroying the
original NaN bit signature.

```mojo
# WRONG — may canonicalize unusual NaN patterns
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[BFloat16]()
    return Float64(Float32(ptr[]))  # ❌ numeric cast
```

### Step 2 — Fix with raw bit manipulation

BF16 bits map directly to the upper 16 bits of Float32:
- BF16: `[sign:1][exp:8][mantissa:7]`
- F32:  `[sign:1][exp:8][mantissa:23]` — lower 16 mantissa bits are zero

```mojo
# CORRECT — preserves all NaN mantissa bits
elif self._dtype == DType.bfloat16:
    # Read raw UInt16 and shift left 16 to reconstruct Float32 bit pattern
    var raw_ptr = (self._data + offset).bitcast[UInt16]()
    var raw: UInt16 = raw_ptr[]
    var f32_bits: UInt32 = UInt32(raw) << 16
    var f32_val = UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[]
    return Float64(f32_val)
```

### Step 3 — Write a raw-bits test helper

Because `_set_float64` also goes through the numeric cast path, you cannot use the normal
tensor setter to inject unusual NaN values. Use a pointer cast to write raw UInt16 bits directly:

```mojo
fn make_bf16_nan_tensor(raw_bits: UInt16) -> ExTensor:
    var t = ExTensor(Shape(1), DType.bfloat16)
    # Write raw UInt16 bits directly — bypasses _set_float64 numeric cast
    var raw_ptr = t._data.bitcast[UInt16]()
    raw_ptr[0] = raw_bits
    return t
```

### Step 4 — Test three NaN invariants

```mojo
def test_bf16_nan_canonical_hash():
    """Canonical BF16 NaN (0x7FC0) should hash consistently."""
    var t1 = make_bf16_nan_tensor(0x7FC0)
    var t2 = make_bf16_nan_tensor(0x7FC0)
    assert_equal(hash(t1), hash(t2))

def test_bf16_nan_negative_hash():
    """Negative quiet BF16 NaN (0xFFC0) should hash consistently."""
    var t1 = make_bf16_nan_tensor(0xFFC0)
    var t2 = make_bf16_nan_tensor(0xFFC0)
    assert_equal(hash(t1), hash(t2))

def test_bf16_nan_cross_variant_hash():
    """Both NaN variants should canonicalize to the same hash."""
    var t_pos = make_bf16_nan_tensor(0x7FC0)
    var t_neg = make_bf16_nan_tensor(0xFFC0)
    assert_equal(hash(t_pos), hash(t_neg))
```

## BF16 NaN Bit Patterns Reference

| Pattern | Hex | Meaning |
| --------- | ----- | --------- |
| `0111 1111 1100 0000` | `0x7FC0` | Canonical positive quiet NaN |
| `1111 1111 1100 0000` | `0xFFC0` | Negative quiet NaN |
| `0111 1111 1000 0000` | `0xFF80` | ⚠️ Positive Infinity (NOT NaN — mantissa is zero!) |
| `1111 1111 1000 0000` | `0xFF80` | ⚠️ Negative Infinity (NOT NaN) |

**Key Rule**: BF16 NaN requires `exp=0xFF` AND `mantissa != 0`. The mantissa is bits [6:0].
`0x7FC0` has mantissa bit 6 set (quiet NaN bit). `0xFF80` has mantissa = 0 → Infinity.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test 0xFF80 as negative NaN | Used `0xFF80` as the "negative NaN" bit pattern | `0xFF80` is BF16 negative infinity (mantissa = 0), not NaN; the test would fail the isnan() check | Always verify NaN bit patterns: mantissa must be non-zero. Negative quiet NaN is `0xFFC0`. |
| Numeric cast for _get_float64 | `Float64(Float32(BFloat16))` | CPU numeric cast canonicalizes NaN before `isnan()` check, different NaN variants get different hashes | Use raw bit manipulation (UInt16 → UInt32 shift → Float32 bitcast) to preserve NaN bits |
| Use `_set_float64` to inject NaN | Called the typed setter with NaN to populate test tensor | `_set_float64` itself uses the same numeric cast path, immediately canonicalizing the injected value | Use pointer cast (`bitcast[UInt16]`) to write raw bits, bypassing the typed setter entirely |

## Results & Parameters

### Environment

```text
Mojo: 0.26.1
Tensor type: ExTensor (custom tensor implementation)
Platform: Linux / WSL2 (GLIBC 2.35)
```

### Test Output

```text
All tests passed.
3 NaN canonicalization tests: PASS
  - test_bf16_nan_canonical_hash: PASS
  - test_bf16_nan_negative_hash: PASS
  - test_bf16_nan_cross_variant_hash: PASS
```

### Files Changed

```text
shared/core/extensor.mojo           +10 -2   (fix _get_float64 BF16 path)
tests/shared/core/test_utility.mojo +89 -0   (add make_bf16_nan_tensor + 3 tests)
```

### Key Code Pattern (Copy-Paste)

```mojo
# _get_float64: BF16 raw bit preservation
var raw_ptr = (self._data + offset).bitcast[UInt16]()
var raw: UInt16 = raw_ptr[]
var f32_bits: UInt32 = UInt32(raw) << 16
var f32_val = UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[]
return Float64(f32_val)

# Test helper: inject raw BF16 NaN bits
fn make_bf16_nan_tensor(raw_bits: UInt16) -> ExTensor:
    var t = ExTensor(Shape(1), DType.bfloat16)
    t._data.bitcast[UInt16]()[0] = raw_bits
    return t
```
