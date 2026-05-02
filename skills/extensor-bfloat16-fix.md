---
name: extensor-bfloat16-fix
description: 'Fix pattern for adding bfloat16 dtype support to Mojo ExTensor float
  I/O methods. Use when: _set_float64/_get_float64 silently write/read zeros for bfloat16
  tensors, or a new dtype is missing from _get_dtype_size_static.'
category: debugging
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| Issue | `ExTensor._set_float64`/`_get_float64` silently write/read zeros for `DType.bfloat16` |
| Root Cause | Missing `bfloat16` branch in float I/O methods + wrong byte size (4 instead of 2) |
| Fix | Add two-step cast branches `bf16 ↔ Float32 ↔ Float64` and correct size to 2 |
| Files | `shared/core/extensor.mojo`, `tests/shared/testing/test_special_values.mojo` |

## When to Use

- `ExTensor` operations on bfloat16 tensors silently produce zeros
- Adding a new float dtype to ExTensor that is missing from `_get_dtype_size_static`
- Re-enabling skipped bfloat16 tests after dtype I/O support is implemented
- Debugging "values read back as 0.0" from tensors with a non-standard dtype

## Verified Workflow

### Step 1: Find all three missing locations

```bash
grep -n "float16\|float32\|float64" shared/core/extensor.mojo | grep -v bfloat16 | grep "_get_dtype_size_static\|_get_float64\|_set_float64"
```

Three sites need updating:
1. `_get_dtype_size_static` — missing size entry (bfloat16 = 2 bytes)
2. `_get_float64` — missing read branch
3. `_set_float64` — missing write branch

### Step 2: Fix `_get_dtype_size_static`

```mojo
# Before (falls through to 4-byte default — WRONG for bfloat16):
if dtype == DType.float16:
    return 2
elif dtype == DType.float32:
    return 4

# After:
if dtype == DType.float16:
    return 2
elif dtype == DType.bfloat16:
    return 2
elif dtype == DType.float32:
    return 4
```

### Step 3: Fix `_get_float64`

```mojo
# Add BEFORE the float32 branch:
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[BFloat16]()
    return Float64(Float32(ptr[]))
```

Two-step cast `BFloat16 → Float32 → Float64` is required. Direct `BFloat16 → Float64`
produces incorrect values in Mojo 0.26.1.

### Step 4: Fix `_set_float64`

```mojo
# Add BEFORE the float32 branch:
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[BFloat16]()
    ptr[] = BFloat16(Float32(value))
```

Two-step cast `Float64 → Float32 → BFloat16` matches the read path.

### Step 5: Re-enable test

```mojo
# Uncomment 3 lines, remove `pass` placeholder:
var tensor = create_special_value_tensor([2, 2], DType.bfloat16, 1.0)
assert_dtype(tensor, DType.bfloat16, "Should be bfloat16")
verify_special_value_invariants(tensor, 1.0)
```

Also update the surrounding print message and comment if they say "skipped".

### Step 6: Run pre-commit to verify

```bash
pixi run pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct bf16↔f64 cast | `ptr[].cast[DType.float64]()` directly from BFloat16 | Produces incorrect values in Mojo 0.26.1 | Always use Float32 as intermediary for bf16 conversions |
| Skipping `_get_dtype_size_static` fix | Only adding I/O branches without fixing size | 4-byte default causes reads/writes at wrong offsets | All three sites must be fixed together |

## Results & Parameters

**Key invariant**: bfloat16 shares float32's exponent range. All bf16 ↔ float conversions must go through `Float32` as an intermediary in Mojo 0.26.1.

**Two-step cast pattern (copy-paste)**:
```mojo
# Read bfloat16
var ptr = (self._data + offset).bitcast[BFloat16]()
return Float64(Float32(ptr[]))

# Write bfloat16
var ptr = (self._data + offset).bitcast[BFloat16]()
ptr[] = BFloat16(Float32(value))
```

**Checklist for adding a new float dtype to ExTensor**:
1. `_get_dtype_size_static` — add size case
2. `_get_float64` — add read branch
3. `_set_float64` — add write branch
4. Check `__setitem__` float condition list (currently `float16 or float32 or float64`)
5. Re-enable any skipped tests
