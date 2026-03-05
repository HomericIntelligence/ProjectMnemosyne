---
name: mojo-extensor-utility-methods
description: "Implement standard utility methods on a Mojo tensor class. Use when: adding Python/NumPy-compatible dunder methods to a Mojo struct, implementing type-erased tensor accessors, or auditing existing methods before implementing new ones."
category: architecture
date: 2026-03-04
user-invocable: false
---

# Skill: Mojo ExTensor Utility Methods

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Objective** | Implement utility methods for ExTensor: `__setitem__`, `__int__`, `__float__`, `__str__`, `__repr__`, `__hash__`, `contiguous()` |
| **Outcome** | Successfully added 171 lines of implementation; PR #3161 created |
| **PRs** | [#3161](https://github.com/HomericIntelligence/ProjectOdyssey/pull/3161) |

## Overview

ExTensor is a type-erased, reference-counted tensor in Mojo with `UnsafePointer[UInt8]` storage. Many standard utility methods were already implemented when the issue was filed — the key lesson is to **audit first** before coding. The methods actually missing were `__setitem__`, `__int__`, `__float__`, `__str__`, `__repr__`, `__hash__`, and `contiguous()`.

## When to Use

1. Adding Python/NumPy-compatible dunder methods to a Mojo struct
2. Implementing mutable indexing (`__setitem__`) on a type-erased storage type
3. Computing a portable hash over a dynamically-typed tensor
4. Implementing `__str__`/`__repr__` on structs with runtime DType

## Verified Workflow

### Phase 1: Audit What Already Exists

Before writing a single line, grep for existing implementations:

```bash
grep -n "fn __setitem__\|fn __int__\|fn __float__\|fn __str__\|fn __repr__\|fn __hash__\|fn contiguous\|fn clone\|fn item\|fn tolist\|fn __len__\|fn diff\|fn is_contiguous" shared/core/extensor.mojo
```

In this session, `clone()`, `item()`, `tolist()`, `__len__`, `diff()`, and `is_contiguous()` were already present. Only 7 methods were actually missing.

### Phase 2: Implement `__setitem__` (two overloads)

Place after the last `__getitem__` overload. Use existing `_set_float64` / `_set_int64` internal helpers:

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_float64(index, value)

fn __setitem__(mut self, index: Int, value: Int64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_int64(index, value)
```

### Phase 3: Implement type conversion methods

Delegate to `item()` which already validates single-element requirement:

```mojo
fn __int__(self) raises -> Int:
    return Int(self.item())

fn __float__(self) raises -> Float64:
    return self.item()
```

### Phase 4: Implement `__str__` and `__repr__`

`String(dtype)` works directly for DType. Build string iterating over `_get_float64`:

```mojo
fn __str__(self) -> String:
    var s = String("ExTensor([")
    for i in range(self._numel):
        if i > 0:
            s += ", "
        s += String(self._get_float64(i))
    s += "], dtype="
    s += String(self._dtype)
    s += ")"
    return s
```

### Phase 5: Implement `__hash__`

Use `dtype_to_ordinal()` from `shared.core.dtype_ordinal` (already in the codebase). Avoid `Float64.to_bits()` — it may not exist. Use integer approximation:

```mojo
fn __hash__(self) -> UInt:
    from shared.core.dtype_ordinal import dtype_to_ordinal
    var h: UInt = 0
    for i in range(len(self._shape)):
        h = h * 31 + UInt(self._shape[i])
    h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
    for i in range(self._numel):
        var val = self._get_float64(i)
        var int_bits = Int(val * 1000000.0)
        h = h * 31 + UInt(int_bits)
    return h
```

### Phase 6: Implement `contiguous()`

For ExTensor with reference-counted storage, `contiguous()` can simply delegate to `clone()`:

```mojo
fn contiguous(self) raises -> ExTensor:
    return self.clone()
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `Float64.to_bits()` in `__hash__` | Used `val.to_bits()` to get exact IEEE bits | Method does not exist on `Float64` in Mojo v0.26.1 | Use `Int(val * 1000000.0)` as integer approximation, or bitcast via pointer |
| `DType._as_i8()` for hash ordinal | Called `self._dtype._as_i8().cast[DType.uint8]()` | Private/nonexistent method on DType | Use `dtype_to_ordinal()` from `shared.core.dtype_ordinal` |
| `Float32` overload for `__setitem__` | Planned both Float32 and Float64 overloads | Redundant — Float64 covers both cases; Float32 adds noise | Use Float64 + Int64 as the two canonical overloads |

## Results & Parameters

**Files modified**: `shared/core/extensor.mojo` (+171 lines)

**Methods added**:

| Method | Signature | Notes |
|--------|-----------|-------|
| `__setitem__` | `(mut self, index: Int, value: Float64) raises` | bounds-checked |
| `__setitem__` | `(mut self, index: Int, value: Int64) raises` | for integer dtypes |
| `__int__` | `(self) raises -> Int` | delegates to `item()` |
| `__float__` | `(self) raises -> Float64` | delegates to `item()` |
| `__str__` | `(self) -> String` | `ExTensor([...], dtype=...)` |
| `__repr__` | `(self) -> String` | includes shape metadata |
| `__hash__` | `(self) -> UInt` | shape + dtype + data |
| `contiguous` | `(self) raises -> ExTensor` | delegates to `clone()` |

**Key import for hash**:

```mojo
from shared.core.dtype_ordinal import dtype_to_ordinal
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #2722, PR #3161 | [notes.md](../../references/notes.md) |
