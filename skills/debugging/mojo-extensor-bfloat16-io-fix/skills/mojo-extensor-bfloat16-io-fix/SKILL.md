---
name: mojo-extensor-bfloat16-io-fix
description: "Fix ExTensor _set_float64/_get_float64 silent failures for bfloat16 dtype. Use when: ExTensor bfloat16 tensors return zeros after writes, or auditing dtype round-trip coverage reveals missing branches."
category: debugging
date: 2026-03-07
user-invocable: false
---

# Skill: Mojo ExTensor BFloat16 I/O Fix

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Category** | debugging |
| **Objective** | Audit and fix ExTensor float64 I/O path for all dtypes in `get_test_dtypes()` |
| **Outcome** | Fixed 3 bugs in bfloat16 support; documented int8 silent no-op limitation |
| **Context** | Issue #3301 — follow-up to #3088 bfloat16 workaround |

## When to Use

Use this skill when:

- `ExTensor` bfloat16 tensors return `0.0` after `_set_float64(i, value)` writes
- Auditing whether all dtypes in `get_test_dtypes()` correctly round-trip through the float64 I/O path
- `_get_dtype_size_static` returns wrong byte count for a dtype (causing wrong element offsets)
- A newly-added dtype needs to be wired into `_set_float64`, `_get_float64`, and `_get_dtype_size_static`
- Writing zero-guard tests to detect silent write failures

Do NOT use when:

- The failure is a compile-time error (different problem class)
- The dtype is correct but numerical precision is the issue (adjust tolerance instead)
- The underlying storage format is custom (e.g., bfloat16-as-uint16 workaround)

## Root Cause Pattern

Three functions must all have a matching branch for every supported dtype:

| Function | Missing branch symptom |
|----------|----------------------|
| `_get_dtype_size_static` | Wrong element offsets → corrupted reads/writes for all elements beyond index 0 |
| `_set_float64` | Silent no-op → value stays at zero-initialized memory |
| `_get_float64` | Reads bits via wrong path (e.g., `_get_int64`) → garbage or zero result |

For `DType.bfloat16`, all three were missing prior to issue #3301.

## Verified Workflow

### 1. Identify the Three Missing Branches

Search all three functions in `extensor.mojo`:

```bash
grep -n "_get_dtype_size_static\|_get_float64\|_set_float64" shared/core/extensor.mojo
```

For each function, check if a `bfloat16` (or target dtype) branch exists. It should look like:

```mojo
elif self._dtype == DType.bfloat16:
    ...
```

### 2. Fix `_get_dtype_size_static`

Bfloat16 is 2 bytes (same as float16). Add it to the float16 branch:

```mojo
# Before (wrong — falls through to default return 4):
if dtype == DType.float16:
    return 2

# After (correct):
if dtype == DType.float16 or dtype == DType.bfloat16:
    return 2
```

### 3. Fix `_get_float64`

Use `SIMD[DType.bfloat16, 1]` for the pointer type (Mojo has no `BFloat16` scalar alias):

```mojo
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[SIMD[DType.bfloat16, 1]]()
    return ptr[].cast[DType.float64]()
```

### 4. Fix `_set_float64`

Same SIMD pattern for writes:

```mojo
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[SIMD[DType.bfloat16, 1]]()
    ptr[] = value.cast[DType.bfloat16]()
```

### 5. Write Zero-Guard Tests

For each dtype, the critical test is the zero-guard — detecting silent write failures:

```mojo
fn test_bfloat16_set_get_float64_roundtrip() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_float64(0, 1.5)
    var got = t._get_float64(0)
    # Zero-guard: fails if _set_float64 silently did nothing
    assert_true(got != 0.0, "bfloat16 _get_float64 returned 0 after _set_float64(1.5)")
    # bfloat16 has ~2 decimal digit precision; 1.5 is exactly representable
    assert_almost_equal(got, 1.5, tolerance=1e-2)
```

Also add an offset correctness test (catches `_get_dtype_size_static` being wrong):

```mojo
fn test_bfloat16_dtype_size_is_2_bytes() raises:
    var t = zeros([4], DType.bfloat16)
    t._set_float64(0, 1.0)
    t._set_float64(1, 2.0)
    t._set_float64(2, 3.0)
    t._set_float64(3, 4.0)
    assert_almost_equal(t._get_float64(0), 1.0, tolerance=1e-2)
    assert_almost_equal(t._get_float64(1), 2.0, tolerance=1e-2)
    assert_almost_equal(t._get_float64(2), 3.0, tolerance=1e-2)
    assert_almost_equal(t._get_float64(3), 4.0, tolerance=1e-2)
```

### 6. Document int8 Limitation

`int8` is in `get_test_dtypes()` but `_set_float64` has no int8 branch — it is a documented
silent no-op. Document this explicitly:

```mojo
fn test_int8_set_float64_is_noop() raises:
    """int8: _set_float64 silently does nothing (no int8 branch in implementation).

    TODO(#3301): Consider adding int8 support to _set_float64 with truncation
    semantics, or raise an error for unsupported dtypes.
    """
    var t = zeros([1], DType.int8)
    t._set_float64(0, 1.0)
    # Documents current behavior: silent no-op leaves value at 0
    assert_almost_equal(t._get_float64(0), 0.0, tolerance=1e-9)
```

## Tolerance Reference

| DType | Mantissa bits | Recommended tolerance |
|-------|--------------|----------------------|
| float64 | 52 | 1e-9 |
| float32 | 23 | 1e-6 |
| float16 | 10 | 1e-3 |
| bfloat16 | 7 | 1e-2 |
| int8 | N/A (integer) | 1e-9 for integer-exact values |

Note: `1.5` is exactly representable in all float formats (binary: 1.1 × 2^0), making it
ideal for round-trip tests — any deviation is a true bug, not a precision artifact.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3301, PR #3908 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `Float16`-style pointer for bfloat16 | Looking for `BFloat16` scalar type similar to `Float16`/`Float32`/`Float64` | Mojo stdlib has no `BFloat16` scalar alias — only `SIMD[DType.bfloat16, 1]` | For bfloat16, use `SIMD[DType.bfloat16, 1]` as the pointer target, not a named scalar |
| Storing bfloat16 as uint16 | `dtype_cast.mojo` uses `cast_to_bfloat16` which stores as `DType.uint16` | This is a conversion helper, not how native `DType.bfloat16` tensors store data | Native `DType.bfloat16` ExTensors use direct `SIMD[DType.bfloat16, 1]` memory layout |
| Running tests locally with `pixi run mojo` | Attempted to validate bfloat16 behavior locally | GLIBC 2.32/2.33/2.34 not available on this Linux host — Mojo requires newer glibc | Tests must run in Docker CI; local validation via code review only |
