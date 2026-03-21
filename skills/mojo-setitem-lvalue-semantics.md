---
name: mojo-setitem-lvalue-semantics
description: "Documents Mojo subscript assignment semantics: obj[i]=val uses __getitem__ lvalue, not __setitem__. Use when: (1) debugging 'cannot implicitly convert' errors on ExTensor/subscript assignments, (2) designing subscript APIs in Mojo structs, (3) encountering 'cannot call function that may raise' after wrapping subscript assignments."
category: debugging
date: 2026-03-21
version: "1.0.0"
user-invocable: false
tags: [mojo, type-errors, subscript, setitem, getitem, lvalue, ExTensor, Float32, Float64, Float16]
---

# Mojo __setitem__ Lvalue Semantics

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-21 |
| **Objective** | Fix 314 type errors after replacing bitcast UAF writes with subscript assignment |
| **Outcome** | All errors resolved; discovered Mojo `obj[i]=val` uses lvalue, not `__setitem__` |
| **Mojo Version** | 0.26.1 |

## When to Use

- Debugging `cannot implicitly convert 'Float64' value to 'Float32'` errors on subscript assignments
- Designing Mojo structs that need to accept multiple types via subscript assignment
- Migrating from direct pointer writes (`bitcast[T]()[i] = val`) to safe assignment APIs
- Encountering `cannot call function that may raise in a context that cannot raise` after wrapping subscript assignments in type constructors

## Verified Workflow

### Quick Reference

```text
Problem:  tensor[i] = Float64(x)  -> ERROR: cannot convert Float64 to Float32
Fix 1:    tensor[i] = Float32(x)  -> OK (matches __getitem__ return type)
Fix 2:    tensor.set(i, Float64(x))  -> OK (explicit method call with overloads)
Fix 3:    tensor._set_float64(i, Float64(x))  -> OK (for non-raising contexts)
```

### Step 1: Understand the Semantics

In Mojo, `obj[i] = val` is syntactic sugar for lvalue assignment through `__getitem__`, NOT a call to `__setitem__`. The compiler:

1. Calls `__getitem__(i)` to get an lvalue reference
2. Assigns `val` to that reference
3. Since `__getitem__` returns `Float32`, `val` must be `Float32`

This means `__setitem__` overloads for `Float64`, `Float16`, `Int64`, etc. are **dead code** -- they are never invoked via `obj[i] = val` syntax.

### Step 2: Choose the Right Fix Pattern

| Context | Pattern | Example |
|---------|---------|---------|
| RHS is same type as `__getitem__` return | Direct assignment | `result[i] = Float32(expr)` |
| RHS is different type, in `raises` context | `set()` method | `result.set(i, Float64(expr))` |
| Inside `@parameter fn` / `parallelize[]` closure | Direct pointer write | `result._set_float64(i, Float64(expr))` |
| Accumulating with mixed types | Cast before arithmetic | `Float64(tensor[i]) + float64_val` |

### Step 3: Implement the `set()` Method

Add overloaded `set()` methods that delegate to `__setitem__`:

```mojo
@always_inline
fn set(mut self, index: Int, value: Float64) raises:
    self.__setitem__(index, value)

@always_inline
fn set(mut self, index: Int, value: Float32) raises:
    self.__setitem__(index, Float64(value))

@always_inline
fn set(mut self, index: Int, value: Float16) raises:
    self.__setitem__(index, Float64(Float32(value)))

@always_inline
fn set(mut self, index: Int, value: Int) raises:
    self.__setitem__(index, Float64(value))
# ... more overloads for Int64, Int32, Int16, Int8, UInt8, etc.
```

### Step 4: Handle Non-Raising Contexts

`parallelize[]` closures use `@parameter fn` which cannot raise. In these contexts:

```mojo
# ERROR: .set() raises, can't use in @parameter fn
@parameter
fn parallel_work(b: Int) capturing:
    output.set(idx, val)  # Cannot call function that may raise

# FIX: Use internal non-raising method
@parameter
fn parallel_work(b: Int) capturing:
    output._set_float64(idx, Float64(val))  # Does not raise
```

### Step 5: Fix Mixed-Type Arithmetic

When `__getitem__` returns Float32 but you need Float64 arithmetic:

```mojo
# ERROR: Float32 + Float64 -> __add__ type mismatch
grad_beta.set(f, grad_beta[f] + grad_out)  # grad_beta[f] is Float32, grad_out is Float64

# FIX: Cast __getitem__ result to match
grad_beta.set(f, Float64(grad_beta[f]) + grad_out)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `__setitem__` overloads | Added 9 new `__setitem__` overloads for Float16, Int, Int8, etc. | Mojo never dispatches `obj[i] = val` to `__setitem__` -- these are dead code | `__setitem__` in Mojo is not called via subscript assignment syntax |
| Wrap all RHS in `Float32()` | Changed `result[i] = Float64(x)` to `result[i] = Float32(x)` everywhere | Introduced "cannot call function that may raise" errors in `@parameter fn` closures | `Float32()` constructor raises; can't use in non-raising contexts like `parallelize[]` |
| Delegate to sub-agents (round 1) | Launched 8 parallel agents to fix all files | Agents only fixed ~60% of errors; missed Float16 paths and arithmetic mismatches | Sub-agents need explicit error line numbers and all error categories enumerated |
| Use `.set()` in `parallelize[]` | Replaced direct writes with `.set()` in parallel computation functions | `.set()` raises but `@parameter fn` closures cannot raise | Need separate non-raising internal method (`_set_float64`) for parallel contexts |

## Results & Parameters

### Error Distribution

```text
267 errors: cannot implicitly convert 'Float64' to 'Float32'
 24 errors: cannot implicitly convert 'Float16' to 'Float32'
 16 errors: invalid call to '__add__' (Float64/Float32 mismatch)
  6 errors: cannot implicitly convert 'Int64' to 'Float32'
  1 error:  cannot call function that may raise
```

### Fix Pattern Distribution

```text
~200 sites: result[i] = Float32(expr)        -- simple same-type cast
 ~40 sites: result.set(i, expr)              -- explicit method for non-Float32 values
  ~8 sites: result._set_float64(i, expr)     -- for parallelize[] closures
  ~8 sites: Float64(tensor[i]) + expr        -- arithmetic type promotion
  ~5 sites: self._set_float64/int64()        -- internal constructors
```

### Files Affected

```text
shared/core/extensor.mojo       -- Added set() overloads, fixed constructors
shared/core/activation.mojo     -- 74 lines changed
shared/core/attention.mojo      -- 34 lines changed
shared/core/conv.mojo           -- 22 lines changed
shared/core/dropout.mojo        -- 26 lines changed
shared/core/dtype_cast.mojo     -- 18 lines changed
shared/core/layers/dropout.mojo -- 24 lines changed
shared/core/normalization.mojo  -- 187 lines changed (largest, most complex)
shared/core/pooling.mojo        -- 12 lines changed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4996 follow-up fix | Fixed 314 type errors across 9 files after bitcast UAF migration |
