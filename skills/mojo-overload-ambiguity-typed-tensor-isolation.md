---
name: mojo-overload-ambiguity-typed-tensor-isolation
description: "Fix Mojo overload resolution failures when parametric Tensor[dtype] and runtime-typed AnyTensor coexist in the same file. Use when: (1) getting 'cannot implicitly convert AnyTensor to AnyTensor' errors, (2) adding typed Tensor[dtype] overloads alongside AnyTensor functions, (3) Mojo compiler fails to resolve between two function signatures that both accept AnyTensor."
category: architecture
date: 2026-03-22
version: "1.0.0"
user-invocable: false
tags: [mojo, tensor, dtype, overload, ambiguity, compilation, architecture, type-isolation]
---

# Mojo Overload Ambiguity: Typed Tensor Isolation Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-22 |
| **Objective** | Fix 242 compilation errors caused by Tensor[dtype] and AnyTensor coexisting in operation files |
| **Outcome** | Isolating typed implementations into a separate package (`shared/tensor/typed/`) eliminates overload ambiguity |
| **Mojo Version** | 0.26.1 |

## When to Use

- Getting `cannot implicitly convert 'AnyTensor' value to 'AnyTensor'` errors (same type to same type — Mojo overload confusion)
- Adding parametric `Tensor[dtype]` typed implementations alongside existing runtime-typed `AnyTensor` functions
- Mojo compiler fails to resolve function calls when both `fn op(a: AnyTensor)` and `fn _op_impl[dt: DType](a: Tensor[dt])` are in the same file
- The error count is proportional to the number of typed functions in scope (each one pollutes overload resolution)
- Functions that call `.as_any()` or `.as_tensor[dt]()` trigger the ambiguity

## Verified Workflow

### Quick Reference

```text
Problem:  Tensor[dtype] import + AnyTensor functions in same file = 242 overload errors
Fix:      Move typed implementations to separate package (shared/tensor/typed/)
Pattern:  Core files use local-scope imports to call typed dispatch

# BEFORE (broken):
# shared/core/arithmetic.mojo
from shared.tensor.tensor import Tensor  # ← THIS CAUSES THE PROBLEM
fn _add_typed[dt: DType](a: Tensor[dt], b: Tensor[dt]) -> Tensor[dt]: ...
fn add(a: AnyTensor, b: AnyTensor) -> AnyTensor: ...  # ← compiler confused

# AFTER (works):
# shared/core/arithmetic.mojo — NO Tensor import
fn add(a: AnyTensor, b: AnyTensor) -> AnyTensor:
    from shared.tensor.typed.arithmetic import _dispatch_add  # local import
    return _dispatch_add(a, b)

# shared/tensor/typed/arithmetic.mojo — isolated typed code
from shared.tensor.tensor import Tensor
fn _add_typed[dt: DType](a: Tensor[dt], b: Tensor[dt]) -> Tensor[dt]: ...
fn _dispatch_add(a: AnyTensor, b: AnyTensor) -> AnyTensor: ...
```

### Step 1: Understand the Root Cause

Mojo 0.26.1's overload resolver fails when a file has BOTH:
- Functions taking/returning `AnyTensor`
- Functions taking/returning `Tensor[dtype]` (or `Tensor` imported in scope)

The error `cannot implicitly convert 'AnyTensor' value to 'AnyTensor'` is misleading — it actually means the compiler found multiple candidate overloads and couldn't pick one. Having `Tensor` in scope creates phantom candidates that confuse resolution.

Key evidence:
- 188 of 242 errors were this exact "AnyTensor to AnyTensor" message
- Errors appeared at `.as_any()` call sites in `_dispatch_*` functions
- Removing only the public `*_typed` wrappers was NOT sufficient — the private `_*_typed` cores and `_dispatch_*` helpers also caused ambiguity
- The error count was proportional to the number of functions with `Tensor[dtype]` in their signature

### Step 2: Create Isolated Typed Package

```bash
mkdir -p shared/tensor/typed
```

Create `shared/tensor/typed/__init__.mojo` with minimal package init.

### Step 3: Extract Typed Code from Each Operation File

For each operation file (arithmetic.mojo, elementwise.mojo, activation.mojo, etc.):

1. Find all functions that reference `Tensor[dtype]`:
   ```bash
   grep -n "Tensor\[" shared/core/arithmetic.mojo
   ```

2. Move ALL such functions to `shared/tensor/typed/arithmetic.mojo`

3. Give the typed file its own imports:
   ```mojo
   from shared.tensor.tensor import Tensor
   from shared.core.any_tensor import AnyTensor
   from shared.base.dtype_ordinal import dtype_to_ordinal, DTYPE_FLOAT32, ...
   ```

4. Remove `from shared.tensor.tensor import Tensor` from the source file

5. Wire public functions via local-scope import:
   ```mojo
   fn add(a: AnyTensor, b: AnyTensor) raises -> AnyTensor:
       from shared.tensor.typed.arithmetic import _dispatch_add
       return _dispatch_add(a, b)
   ```

### Step 4: Files That Keep Tensor Import

These files legitimately need `Tensor[dtype]` and should keep their import:
- `shared/tensor/tensor.mojo` — the struct itself
- `shared/tensor/factories.mojo` — factory functions
- `shared/core/any_tensor.mojo` — `as_tensor[dtype]()` method
- `shared/core/layers/linear.mojo` — `Linear[dtype]` parametric struct
- `shared/core/layers/conv2d.mojo` — `Conv2dLayer[dtype]` parametric struct
- `shared/core/layers/batchnorm.mojo` — `BatchNorm2dLayer[dtype]` parametric struct

### Step 5: Verify

```bash
# No Tensor import in core operation files (should return NOTHING):
grep -l "from shared.tensor.tensor import Tensor" \
  shared/core/arithmetic.mojo shared/core/elementwise.mojo \
  shared/core/activation.mojo shared/core/matrix.mojo

# Typed files exist:
ls shared/tensor/typed/*.mojo

# Build passes:
just package
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Public typed wrappers (`add_typed`, `relu_typed`) | Added public `fn add_typed[dt: DType](a: Tensor[dt]) -> Tensor[dt]` alongside `fn add(a: AnyTensor) -> AnyTensor` | 242 Mojo overload resolution errors — compiler couldn't disambiguate when both types were in scope | Having `Tensor[dtype]` in scope AT ALL (even in private functions) pollutes overload resolution |
| Removing only public wrappers | Removed `add_typed` etc. but kept internal `_add_typed` and `_dispatch_add` in same file | Same 242 errors persisted — even PRIVATE typed functions in the same file cause ambiguity | The issue is the `Tensor` TYPE being imported, not the function visibility |
| Renaming typed functions | Tried using different naming conventions to avoid collisions | Errors remained because the overload confusion is about TYPE resolution, not function NAME resolution | Mojo's issue is with `Tensor[dtype]` type being in the same compilation scope as `AnyTensor` functions |
| Fixing Self.dtype and removing exports | Fixed `dtype` → `Self.dtype`, removed typed exports from `__init__.mojo` | Reduced errors from 242 to ~200 but core ambiguity remained | Cosmetic fixes don't solve fundamental type scope pollution |

## Results & Parameters

### Architecture Pattern

```text
shared/tensor/typed/          ← ISOLATED: typed implementations
  arithmetic.mojo               _broadcast_binary_typed[dtype, op]()
  elementwise.mojo              _unary_typed[dt, op]()
  activation.mojo               _relu_typed[dt](), _dispatch_relu()
  matrix.mojo                   _matmul_typed[dt]()
  reduction.mojo                _sum_typed[dt]()
  ...

shared/core/                  ← CLEAN: AnyTensor-only operations
  arithmetic.mojo               fn add(a: AnyTensor, b: AnyTensor)
  elementwise.mojo              fn exp(tensor: AnyTensor)
  activation.mojo               fn relu(tensor: AnyTensor)
  ...
  any_tensor.mojo               struct AnyTensor (keeps Tensor import for as_tensor)
  layers/linear.mojo            struct Linear[dtype] (keeps Tensor import)

shared/tensor/                ← FOUNDATION: Tensor[dtype] struct
  tensor.mojo                   struct Tensor[dtype: DType]
  tensor_traits.mojo            trait TensorLike
  factories.mojo                zeros[dtype](), ones[dtype]()
```

### Key Configuration

```yaml
mojo_version: "0.26.1"
isolation_strategy: "separate package for typed implementations"
local_import_pattern: "from shared.tensor.typed.X import _dispatch_Y"
public_api: "AnyTensor-only (users never see Tensor[dtype])"
typed_implementations: "internal, behind ordinal-based dispatch"
```

### Mojo 0.26.1 Type Resolution Rules

```text
1. Importing Tensor[dtype] in a file pollutes overload resolution for ALL functions
2. Even private functions with Tensor[dtype] signatures cause ambiguity
3. .as_any() returning AnyTensor is seen as ambiguous when Tensor is in scope
4. Local-scope imports (inside function bodies) DO NOT pollute — they're deferred
5. The error message "cannot convert AnyTensor to AnyTensor" is MISLEADING —
   it means "multiple overload candidates found, can't pick one"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4998, PRs #5030-5058 | 242 build errors from typed ops, resolved by isolation |
