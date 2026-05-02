---
name: mojo-hash-testing-patterns
description: "Use when: (1) implementing or fixing __hash__ on a Mojo tensor/struct with float fields, (2) adding hash collision tests for shape/dtype/value sensitivity, (3) verifying hash stability for edge-case tensors (empty, large values, small values), (4) guarding against dtype regression in __hash__ when numel=0, (5) testing integer-dtype coverage through _get_float64 dispatch path"
category: testing
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# Mojo Hash Testing Patterns

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-29 |
| Objective | Consolidated patterns for implementing, fixing, and testing __hash__ on Mojo tensor/struct types, covering bitcast-based float hashing, collision resistance, dtype regression guards, shape sensitivity, stability, and integer dtype coverage |
| Outcome | Merged from 7 source skills |
| Verification | unverified |

## When to Use

- A Mojo struct's `__hash__` computes float contributions via `Int(val * N)` or similar approximation (lossy)
- Dict/set keys with float fields have unexpected collisions for large values (e.g., `1e15`) or small values (e.g., `1e-7` vs `2e-7`)
- Adding hash collision resistance tests to verify `__hash__` distinguishes tensors by shape, dtype, and values
- Verifying that `__hash__` encodes shape information (not just element values)
- A hash test suite covers equal-tensor and different-value cases but not shape differences
- Testing dtype differentiation: float32 vs float64 tensors with identical logical values
- You need to verify `__hash__` has no side effects (e.g., mutating internal state) for edge-case shapes
- A `__hash__` implementation includes `dtype_to_ordinal()` and you want to guard against regressions when numel=0
- Existing hash tests only cover float32/float64 tensors, leaving integer branches (int8, int16, int32, etc.) untested

## Verified Workflow

### Quick Reference

**Float bitcast pattern (fix lossy Int(float * N) hashing)**:
```mojo
fn __hash__(self) -> UInt:
    var h: UInt = 0
    for i in range(len(self._shape)):
        h = h * 31 + UInt(self._shape[i])
    h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
    for i in range(self._numel):
        var val = self._get_float64(i)
        var local_val = val  # local copy required before UnsafePointer.address_of
        var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
        h = h * 31 + UInt(int_bits)
    return h
```

**Collision test pattern**:
```mojo
if hash(a) == hash(b):
    raise Error("tensors should not collide on hash")
```

**Stability test pattern**:
```mojo
assert_equal_int(Int(hash(a)), Int(hash(a)), "hash must be stable across repeated calls")
```

**Integer dtype test**:
```mojo
var a = arange(0.0, 4.0, 1.0, DType.int32)
var b = arange(0.0, 4.0, 1.0, DType.int32)
assert_equal_int(Int(hash(a)), Int(hash(b)), "Integer-typed tensors with same values should have same hash")
```

### Step 1: Fix Lossy Float Hashing with Bitcast

The `Int(val * 1000000.0)` pattern causes:
1. **Int overflow** for large values: `1e15 * 1e6 = 1e21` overflows Int64
2. **False collisions** for small values: `1e-7 * 1e6 = 0.1` truncates to `0` — same as `2e-7 * 1e6 = 0.2`

Replace with `UnsafePointer.address_of(local_val).bitcast[UInt64][]` to read the exact IEEE 754 64-bit representation.

**Critical `local_val` pattern** — always assign to a local variable before taking its address:
```mojo
# WRONG - may result in dangling pointer from temporary
var int_bits = (UnsafePointer.address_of(self._get_float64(i))).bitcast[UInt64][]

# CORRECT - local variable has well-defined lifetime
var val = self._get_float64(i)
var local_val = val
var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
```

Always include shape dimensions and dtype in the hash:
```mojo
for i in range(len(self._shape)):
    h = h * 31 + UInt(self._shape[i])
h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
```

### Step 2: Add Collision Resistance Tests

**Same dtype, different shapes** (`[2,3]` vs `[6]`):
```mojo
fn test_hash_same_dtype_different_shapes() raises:
    var shape_2x3 = List[Int]()
    shape_2x3.append(2)
    shape_2x3.append(3)
    var shape_6 = List[Int]()
    shape_6.append(6)
    var a = full(shape_2x3, 1.0, DType.float32)
    var b = full(shape_6, 1.0, DType.float32)
    if hash(a) == hash(b):
        raise Error(
            "Tensors with same dtype/data but different shapes ([2,3] vs [6]) should not collide on hash"
        )
```

**Same values, different dtype** (float32 vs float64):
```mojo
fn test_hash_same_values_different_dtype() raises:
    var shape = List[Int]()
    shape.append(1)
    var tensor_f32 = full(shape, 1.0, DType.float32)
    var tensor_f64 = full(shape, 1.0, DType.float64)
    if hash(tensor_f32) == hash(tensor_f64):
        raise Error(
            "Hash collision: float32 and float64 tensors with same values should have different hashes"
        )
```

**Different dtypes, 2D shape** (`float32` vs `float64` with `[2,2]`):
```mojo
fn test_hash_different_dtypes_differ() raises:
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    var t_f32 = full(shape, Float64(1.0), DType.float32)
    var t_f64 = full(shape, Float64(1.0), DType.float64)
    if hash(t_f32) == hash(t_f64):
        raise Error(
            "float32 and float64 tensors with identical values should hash differently"
        )
```

**Same data, different shape** (`[3]` vs `[1,3]`):
```mojo
fn test_hash_different_shapes_differ() raises:
    var t1 = arange(1.0, 4.0, 1.0, DType.float32)
    var shape = List[Int]()
    shape.append(1)
    shape.append(3)
    var t2 = arange(1.0, 4.0, 1.0, DType.float32)
    t2 = t2.reshape(shape)
    if hash(t1) == hash(t2):
        raise Error(
            "Tensors with same data but different shapes should have different hashes"
        )
```

### Step 3: Add Dtype Regression Guard for Empty Tensors

When `numel=0`, the data loop in `__hash__` is skipped entirely. The `dtype_to_ordinal` contribution becomes the **only** differentiator for same-shape empty tensors. Guard against regressions:

```mojo
fn test_hash_empty_tensor_dtype_differs() raises:
    """Test that empty tensors with different dtypes produce different hashes.

    When numel=0, the data loop is skipped entirely, so dtype_to_ordinal is
    the only contributor that can distinguish them. This catches regressions
    where dtype contribution is accidentally dropped from __hash__.
    """
    var shape = List[Int]()
    shape.append(0)
    var a = zeros(shape, DType.float32)
    var b = zeros(shape, DType.float64)
    if hash(a) == hash(b):
        raise Error(
            "Empty tensors with different dtypes should have different hashes"
        )
```

Hash contributors for empty tensors:

| Component | Contributes to Hash | Notes |
| ----------- | --------------------- | ------- |
| Shape dimensions | YES | `hasher.update(self._shape[i])` — value is 0 |
| Dtype ordinal | YES | `hasher.update(dtype_to_ordinal(self._dtype))` — SOLE differentiator |
| Data elements | NO | `for i in range(0)` never executes |

### Step 4: Add Integer Dtype Coverage

The `_get_float64` helper casts integer dtypes to `Float64` before hashing. Cover this path explicitly:

```mojo
fn test_hash_integer_dtype_consistent() raises:
    """Test __hash__ for integer-typed tensors produces consistent hashes.

    _get_float64 casts integer values to Float64 before hashing. Two separate
    tensors with identical integer values must produce the same hash.
    """
    var a = arange(0.0, 4.0, 1.0, DType.int32)
    var b = arange(0.0, 4.0, 1.0, DType.int32)
    assert_equal_int(
        Int(hash(a)),
        Int(hash(b)),
        "Integer-typed tensors with same values should have same hash",
    )
```

### Step 5: Add Stability Test

Confirm `__hash__` has no side effects by hashing the same instance multiple times:

```mojo
fn test_hash_stability_repeated_calls() raises:
    """Test that hashing the same instance repeatedly returns equal values."""
    var shape = List[Int]()
    var a = full(shape, 0.0, DType.float32)
    assert_equal_int(
        Int(hash(a)),
        Int(hash(a)),
        "hash of empty tensor must be stable across repeated calls",
    )
    assert_equal_int(
        Int(hash(a)),
        Int(hash(a)),
        "hash of empty tensor must be stable on third call",
    )
```

### Step 6: Register Tests and Run

Register each test in `main()` under the `# __hash__` comment block:
```mojo
    # __hash__
    print("  Testing __hash__...")
    test_hash_immutable()
    test_hash_different_values_differ()
    test_hash_large_values()
    test_hash_small_values_distinguish()
    test_hash_integer_dtype_consistent()
    test_hash_different_shapes_differ()
    test_hash_same_dtype_different_shapes()
    test_hash_same_values_different_dtype()
    test_hash_different_dtypes_differ()
    test_hash_empty_tensor_dtype_differs()
    test_hash_stability_repeated_calls()
```

Run tests:
```bash
just test-group "tests/shared/core" "test_utility.mojo"
# or
just test-group "tests/shared/core" "test_hash.mojo"
```

Note: Mojo tests cannot run locally on hosts with GLIBC < 2.32. Use CI or Docker.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct address_of on return value | `UnsafePointer.address_of(self._get_float64(i)).bitcast[UInt64][]` | Dangling pointer — temporary has no stable address | Always assign to a named local variable before taking its address |
| `Int(val * 1000000.0)` for large values | Multiply float by 1e6 then truncate to Int | `1e15 * 1e6 = 1e21` overflows Int64, producing garbage hash | Use bitcast to avoid any arithmetic on the float value |
| `Int(val * 1000000.0)` for small values | Multiply float by 1e6 then truncate to Int | `1e-7 * 1e6 = 0.1` rounds to 0 — same as `2e-7`, false collision | Bitcast preserves all 64 bits, no rounding |
| Skipping dtype in hash | Hashed only shape and data | Tensors of same shape and data but different dtypes collide | Include `dtype_to_ordinal(self._dtype)` in the hash chain |
| Two-instance comparison only | `hash(a) == hash(b)` with two separate instances | Passes even if hash has side effects that reset on each new instance | Single-instance repeated calls are a stronger stability guarantee |
| Asserting exact hash value | Hardcoding expected hash value in assertion | Hash seed or dtype ordinal may vary across builds/platforms | Assert equality between calls, not against a magic constant |
| Using `DType.float32` for integer test | Initial draft used float32 arange | Doesn't exercise the integer cast path that the issue targets | Use `DType.int32` explicitly to cover the `_get_float64` integer branch |
| Adding test after `main()` | Placed function after the `fn main()` block | Mojo sees it as dead code outside any callable | Always place helper test functions before `main()` |
| `pixi run mojo test` locally | Running tests on host Debian Buster | GLIBC_2.32/2.33/2.34 not found — host OS too old | Mojo tests require Docker or CI environment |
| `just test-mojo` locally | Running `just` outside Docker | `just` command not found outside container | Use CI to verify test execution |

## Results & Parameters

### Hash Multiplier

```mojo
# Standard polynomial rolling hash (31 is prime, used in Java String and Python str)
var h: UInt = 0
h = h * 31 + contribution
```

### Pattern Notes

- Shape setup: `var shape = List[Int](); shape.append(2); shape.append(3)` (not a literal, append each dim)
- Tensor creation: `full(shape, value, DType.float32)` or `arange(start, end, step, DType.int32)`
- Hash assertion for inequality: use `if hash_a == hash_b: raise Error(...)` — NOT `assert_not_equal`
- Hash assertion for equality: `assert_equal_int(Int(hash(a)), Int(hash(b)), "<message>")`
- Function signature: `fn test_hash_...() raises:`
- All representable integers up to 2^53 survive the int→float64→hash round-trip without collision

### Expected Test Outcomes

- Equal tensors with any float values always hash identically
- Large values (`1e15`) hash without overflow (UInt can hold UInt64 cast)
- Small distinct values (`1e-7` vs `2e-7`) produce different hashes
- Shape differences produce different hashes (`[3]` vs `[1,3]`)
- Dtype differences produce different hashes (float32 vs float64)
- Empty tensors with different dtypes produce different hashes
- Repeated hash calls on the same instance return equal values
