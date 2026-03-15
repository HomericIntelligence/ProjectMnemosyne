---
name: mojo-extensor-type-errors
description: "Fix Mojo ExTensor type errors: Int64 implicit conversion failures and missing __getitem__ overloads for List[Int] index. Use when: (1) test fails with 'cannot implicitly convert Int64 to Float32', (2) 'no matching method in call to __getitem__' for list-indexed assignment on ExTensor."
category: debugging
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Skill | mojo-extensor-type-errors |
| Category | debugging |
| Issue | #4524 |
| PR | #4891 |
| Files Changed | `shared/core/extensor.mojo` |

## When to Use

- Test file fails with `cannot implicitly convert 'Int64' value to 'Float32'` when calling `t[i] = Int64(val)`
- Test file fails with `no matching method in call to '__getitem__'` when using `t[[i, j]] = val` syntax
- Adding new `__setitem__` overloads to ExTensor without a matching `__getitem__` overload
- Any ExTensor indexing operation using `List[Int]` as the index type

## Verified Workflow

### Quick Reference

```mojo
# Fix 1: Int64 cast in __setitem__
# WRONG - Float64(Int64_val) does not compile in Mojo v0.26.1
self.__setitem__(index, Float64(value))

# CORRECT - use .cast[DType.float64]()
self.__setitem__(index, value.cast[DType.float64]())

# Fix 2: Add __getitem__ for List[Int] (required for t[[i,j]] = val syntax)
fn __getitem__(self, indices: List[Int]) raises -> Float32:
    if len(indices) != len(self._shape):
        raise Error("Number of indices (...) must match tensor rank (...)")
    var flat_idx = 0
    for i in range(len(indices)):
        if indices[i] < 0 or indices[i] >= self._shape[i]:
            raise Error("Index out of bounds at dimension " + String(i))
        flat_idx += indices[i] * self._strides[i]
    return self._get_float32(flat_idx)
```

### Step 1: Diagnose the error

The two error types have distinct root causes:

**Error A** - `cannot implicitly convert 'Int64' value to 'Float32'`:

Occurs in `__setitem__(index: Int, value: Int64)` which tries to construct `Float64(value)`.
In Mojo v0.26.1, `Float64(Int64_val)` is NOT a valid constructor call because `Int64`
(`Scalar[DType.int64]`) does not implicitly convert to `Float64` (`Scalar[DType.float64]`).
The fix is `value.cast[DType.float64]()`.

**Error B** - `no matching method in call to '__getitem__'` for `t[[i,j]] = val`:

Mojo decomposes `t[[i, j]] = val` into a `__getitem__` call (to get a reference/value)
followed by assignment. If no `__getitem__(List[Int])` overload exists, Mojo reports the
error as a missing `__getitem__` even though a `__setitem__(List[Int], ...)` exists.

### Step 2: Apply Fix A - Int64 cast

In `shared/core/extensor.mojo`, find `__setitem__(mut self, index: Int, value: Int64)`:

```mojo
# Before (broken):
fn __setitem__(mut self, index: Int, value: Int64) raises:
    self.__setitem__(index, Float64(value))  # FAILS: no Int64->Float64 constructor

# After (fixed):
fn __setitem__(mut self, index: Int, value: Int64) raises:
    self.__setitem__(index, value.cast[DType.float64]())  # OK: explicit SIMD cast
```

### Step 3: Apply Fix B - Add __getitem__ for List[Int]

Add the following method immediately after `__getitem__(self, index: Int)`:

```mojo
fn __getitem__(self, indices: List[Int]) raises -> Float32:
    """Get element at multi-dimensional index.

    Args:
        indices: Per-dimension indices (one per axis).

    Returns:
        The value at the given multi-dimensional index as Float32.

    Raises:
        Error: If number of indices doesn't match tensor rank,
               or any index is out of bounds.

    Example:
        ```mojo
        var t = zeros([3, 4], DType.float32)
        var val = t[[1, 2]]  # Get element at row 1, col 2
        ```
    """
    if len(indices) != len(self._shape):
        raise Error(
            "Number of indices ("
            + String(len(indices))
            + ") must match tensor rank ("
            + String(len(self._shape))
            + ")"
        )
    var flat_idx = 0
    for i in range(len(indices)):
        if indices[i] < 0 or indices[i] >= self._shape[i]:
            raise Error("Index out of bounds at dimension " + String(i))
        flat_idx += indices[i] * self._strides[i]
    return self._get_float32(flat_idx)
```

### Step 4: Verify the fixes compile

The test `tests/shared/core/test_extensor_setitem.mojo` covers both cases:

- `test_setitem_flat_int64` — exercises Fix A (Int64 cast)
- `test_setitem_multidim_2d` / `test_setitem_multidim_3d` — exercise Fix B (`__getitem__`)
- `test_setitem_getitem_roundtrip_multidim` — exercises both together

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `Float64(Int64_value)` constructor | Pass `Int64` directly to `Float64()` constructor | Mojo v0.26.1 does not support implicit `Scalar[DType.int64]` → `Scalar[DType.float64]` conversion via constructor | Always use `.cast[DType.float64]()` for Scalar type conversions in Mojo |
| Rely on `__setitem__(List[Int])` for `t[[i,j]] = val` | Assumed that having `__setitem__(List[Int], ...)` was sufficient | Mojo decomposes `t[x] = val` into `__getitem__(x)` + assign — both get and set overloads must exist | Whenever you add a `__setitem__` for a new index type, add a matching `__getitem__` too |

## Results & Parameters

**Mojo version**: 0.26.1

**Scalar type conversion pattern**:

```mojo
# Correct pattern for Scalar[DType.X] -> Scalar[DType.Y]:
value.cast[DType.target_dtype]()

# NOT:
TargetType(source_value)  # Fails for Scalar types
```

**`__getitem__` / `__setitem__` symmetry rule**:

In Mojo v0.26.1, when `t[x] = val` is used (subscript assignment), Mojo requires BOTH:
- `__getitem__(x)` — for read access
- `__setitem__(x, val)` — for write access

Even if you only intend to write, the absence of `__getitem__` causes a compile error.
