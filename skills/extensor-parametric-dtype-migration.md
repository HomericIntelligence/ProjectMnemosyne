---
name: extensor-parametric-dtype-migration
description: "Documents why ExTensor needs compile-time dtype parameterization for SIMD-like subscript assignment. Use when: (1) designing tensor types with subscript assignment in Mojo, (2) debugging type conversion errors in ExTensor, (3) planning the parametric ExTensor migration."
category: architecture
date: 2026-03-21
version: "1.0.0"
user-invocable: false
---

# ExTensor Parametric DType Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-21 |
| **Objective** | Make `tensor[i] = value` work without casts, like Mojo's SIMD type |
| **Outcome** | Short-term workaround deployed; long-term parametric migration planned (issue #4998) |
| **Root Cause** | ExTensor stores dtype at runtime; Mojo requires compile-time type for lvalue assignment |

## When to Use

- Designing tensor or array types in Mojo that need subscript assignment
- Debugging "cannot implicitly convert" errors on ExTensor subscript assignments
- Planning the parametric ExTensor migration (issue #4998)
- Understanding why `__setitem__` overloads don't work in Mojo
- Choosing between runtime vs compile-time dtype for tensor implementations

## Verified Workflow

### Quick Reference

```text
SIMD behavior (what we want):
  var s = SIMD[DType.float32, 4](0.0)
  s[0] = 3.14159       # FloatLiteral -> works
  s[1] = Float32(2.0)  # Same type -> works
  s[2] = 42            # IntLiteral -> works
  s[3] = Float64(1.0)  # Different type -> ERROR (strict)

ExTensor today (broken):
  var t = zeros([4], DType.float32)
  t[0] = 3.14159       # FloatLiteral -> works (converts to Float32 via __getitem__ lvalue)
  t[1] = Float32(2.0)  # Same type -> works
  t[2] = Float64(1.0)  # ERROR: cannot convert Float64 to Float32
  t[3] = Float16(1.0)  # ERROR: cannot convert Float16 to Float32

ExTensor fix (parametric):
  var t = ExTensor[DType.float32]([4])
  t[0] = 3.14159       # FloatLiteral -> Scalar[float32] -> works
  t[1] = Float32(2.0)  # Same type -> works
  # Same strict behavior as SIMD
```

### Step 1: Understand Mojo's Subscript Semantics

Mojo's `obj[i] = val` does NOT call `__setitem__`. It:
1. Calls `__getitem__(i)` to get an lvalue reference
2. Assigns `val` to that lvalue
3. The value type must match or implicitly convert to `__getitem__`'s return type

This means `__setitem__` overloads are **dead code** for subscript assignment syntax.

### Step 2: Understand Why Runtime DType Fails

ExTensor stores `_dtype` as `var _dtype: DType` (runtime). This means:
- `__getitem__` must return a fixed type (currently `Float32`)
- Can't return `Scalar[self._dtype]` because dtype isn't known at compile time
- All RHS values in `tensor[i] = val` must be `Float32`

### Step 3: The Parametric Solution

Make ExTensor parametric: `struct ExTensor[dtype: DType]`

```mojo
struct ExTensor[dtype: DType]:
    var _data: UnsafePointer[UInt8, origin=MutAnyOrigin]  # byte array
    var _shape: List[Int]
    var _strides: List[Int]

    fn __getitem__(self, index: Int) raises -> Scalar[Self.dtype]:
        return self._data.bitcast[Scalar[Self.dtype]]()[resolved_index]
```

Now `__getitem__` returns `Scalar[Self.dtype]` and assignment works exactly like SIMD.

### Step 4: Short-Term Workaround (Current State)

Until the parametric migration:
- `tensor[i] = Float32(expr)` works (matches `__getitem__` return type)
- `tensor.set(i, Float64(expr))` for non-Float32 values (explicit method)
- `tensor._set_float64(i, val)` for `@parameter fn` / `parallelize[]` closures (can't raise)
- `_resolve_index` helper extracted for DRY bounds-check + stride logic
- `set()` overloads call `_set_float32`/`_set_float64`/`_set_int64` directly to avoid precision-losing round-trips

### Step 5: Migration Impact

Every function signature changes:
```mojo
# Before:
fn relu(tensor: ExTensor) raises -> ExTensor: ...
# After:
fn relu[dtype: DType](tensor: ExTensor[dtype]) raises -> ExTensor[dtype]: ...
```

Scope: ~100+ functions across all modules, plus all tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `__setitem__` overloads | Added 9 overloads for Float16, Int, Int8, etc. | Mojo never dispatches `obj[i]=val` to `__setitem__` -- dead code | `__setitem__` is not called via subscript assignment in Mojo |
| Change `__getitem__` to return Float64 | Wider type to accept more assignments | `Float32` can't implicitly convert to `Float64` in Mojo, broke 108 call sites | Mojo doesn't allow implicit widening between float types |
| Proxy/reference return type | Return a proxy struct from `__getitem__` | "expression must be mutable in assignment" -- Mojo ownership prevents mutable references | Can't return mutable references to internal data in Mojo |
| Route `set()` through `Float64` | All `set()` overloads called `__setitem__(index, Float64(value))` | Float32 -> Float64 -> Float32 round-trip changes values (3.14159 -> 3.141590118408203) | Never introduce precision-losing conversion round-trips |
| Sub-agents for bulk fixes (round 1) | Launched 8 parallel agents to fix all files | Agents only fixed ~60% of errors, missed Float16 paths and arithmetic mismatches | Sub-agents need explicit error line numbers and all categories enumerated |
| `Float32()` casts everywhere | Changed `result[i] = Float64(x)` to `result[i] = Float32(x)` | "cannot call function that may raise" in `@parameter fn` closures for `parallelize[]` | `Float32()` constructor raises; can't use in non-raising contexts |

## Results & Parameters

### Error Distribution (Before Fix)

```text
267 errors: cannot implicitly convert 'Float64' to 'Float32'
 24 errors: cannot implicitly convert 'Float16' to 'Float32'
 16 errors: invalid call to '__add__' (Float64/Float32 mismatch)
  6 errors: cannot implicitly convert 'Int64' to 'Float32'
```

### Three Fix Patterns Used

```text
Pattern 1: result[i] = Float32(expr)        -- for raising contexts, same-type
Pattern 2: result.set(i, expr)              -- for non-Float32 values, uses _set_float32/_set_float64 directly
Pattern 3: result._set_float64(i, expr)     -- for parallelize[] closures (can't raise)
```

### Key Mojo Facts Discovered

```text
- obj[i] = val uses __getitem__ lvalue, NOT __setitem__
- __setitem__ overloads are dead code for subscript syntax
- No implicit conversion between float types (Float16/32/64)
- FloatLiteral and IntLiteral implicitly convert to any Scalar[dtype]
- Parametric dtype (compile-time) is required for SIMD-like behavior
- Float32 -> Float64 -> Float32 round-trip is NOT lossless for all values
```

### GitHub References

```text
PR #4997: Short-term fix (set() method, tolerance adjustments)
Issue #4998: Long-term epic for parametric ExTensor migration
```
