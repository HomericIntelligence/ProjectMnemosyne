---
name: mojo-circular-import-type-identity-fix
description: "Fix Mojo 'cannot implicitly convert X to X' errors caused by circular imports that trigger dual type compilation. Use when: (1) Mojo compiler reports 'cannot implicitly convert Type to Type' where both types have the same name, (2) cross-package imports create A->B->A cycles in Mojo, (3) struct operators delegate to external modules that import the struct back."
category: architecture
date: 2026-03-23
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - circular-imports
  - type-identity
  - operators
  - architecture
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Objective** | Fix 255+ CI compilation errors ("cannot implicitly convert 'AnyTensor' to 'AnyTensor'") caused by circular imports between shared/core/any_tensor.mojo and shared/tensor/tensor.mojo |
| **Outcome** | Successful. Moved AnyTensor to shared/tensor/, implemented operators inline, 590 files updated, build passes with --Werror |

## When to Use

- Mojo compiler reports `cannot implicitly convert 'X' value to 'X'` where both sides are the SAME type name
- Two Mojo modules import each other (directly or transitively), even via function-scoped imports
- A struct's operator methods (`__add__`, etc.) delegate to external module functions that import the struct type
- A Mojo package `__init__.mojo` re-exports types from another package that imports back
- Build worked before a refactoring that split types across packages

## Verified Workflow

### Quick Reference

```text
Root cause diagnosis:
  1. Grep for the type name in error: "cannot implicitly convert 'X' to 'X'"
  2. Find ALL files that define struct X (should be exactly 1)
  3. Trace the import chain: X.mojo -> Y.mojo -> ... -> X.mojo (cycle!)
  4. The cycle causes Mojo to compile X.mojo twice with different type identities

Fix strategy (in priority order):
  A. Co-locate: Move files into the same package (siblings can import each other)
  B. Inline operators: Implement math on the struct using internal data, not external functions
  C. Remove re-exports: Don't re-export types in __init__.mojo across package boundaries
  D. Function-scoped imports: ONLY works if the callee doesn't import back to the caller's package
```

### Detailed Steps

#### Step 1: Identify the circular import chain

```bash
# Find where the type is defined
grep -rn "struct AnyTensor" --include="*.mojo" .

# Find all files that import it
grep -rn "from.*import AnyTensor" --include="*.mojo" .

# Trace the cycle: if AnyTensor is in package A and imports from package B,
# check if package B imports AnyTensor
```

#### Step 2: Co-locate related types in the same package

Move the type definition to the same package as its dependencies. In our case:
- `any_tensor.mojo` (defines AnyTensor) moved from `shared/core/` to `shared/tensor/`
- `tensor.mojo` (defines Tensor[dtype]) was already in `shared/tensor/`
- Both types now use relative imports: `from .tensor import Tensor`, `from .any_tensor import AnyTensor`

#### Step 3: Implement operators as self-contained math

Following the Mojo stdlib pattern (SIMD uses `__mlir_op`, ComplexSIMD uses inline field math):

```mojo
# BAD: Delegates to external module (creates cycle if that module imports AnyTensor)
fn __add__(self, other: AnyTensor) raises -> AnyTensor:
    from shared.core.arithmetic import add  # CYCLE: arithmetic imports AnyTensor
    return add(self, other)

# GOOD: Self-contained using internal data + existing base imports
fn __add__(self, other: AnyTensor) raises -> AnyTensor:
    @always_inline
    fn _add[T: DType](x: Scalar[T], y: Scalar[T]) -> Scalar[T]:
        return x + y
    return _anytensor_binary_op[_add](self, other)
```

The `_anytensor_binary_op` helper uses only `shared.base.broadcasting` and `shared.base.dtype_ordinal` (no cycle).

#### Step 4: Remove cross-package re-exports from `__init__.mojo`

```mojo
# BAD: shared/core/__init__.mojo re-exports from shared.tensor
from shared.tensor.any_tensor import AnyTensor, zeros, ones  # Creates cycle!

# GOOD: Comment explaining where to import from
# AnyTensor is in shared.tensor.any_tensor. Import directly:
#   from shared.tensor.any_tensor import AnyTensor, zeros, ones
```

#### Step 5: Ensure public APIs use the runtime-typed tensor

Layer `forward()` methods should take `AnyTensor` (public API), not `Tensor[dtype]` (internal):

```mojo
# BAD: Exposes internal type in public API
fn forward(mut self, input: Tensor[Self.dtype]) raises -> Tensor[Self.dtype]:

# GOOD: Public API uses runtime-typed tensor
fn forward(mut self, input: AnyTensor) raises -> AnyTensor:
```

#### Step 6: Update all import paths

```bash
# Bulk update absolute imports
find . -name '*.mojo' -exec sed -i 's/from shared\.core\.any_tensor import/from shared.tensor.any_tensor import/g' {} +

# Update relative imports in the old package
find shared/core/ -name '*.mojo' -exec sed -i 's/from \.any_tensor import/from shared.tensor.any_tensor import/g' {} +

# Verify no stale imports remain
grep -r "from shared.core.any_tensor import" --include="*.mojo" .
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Function-scoped imports in any_tensor.mojo | Changed `from shared.tensor.tensor import Tensor` from top-level to inside `as_tensor()` method | Mojo still resolves the module at package compilation time, triggering the cycle through `__init__.mojo` re-exports | Function-scoped imports do NOT prevent cycles if the target module is in a package whose `__init__.mojo` imports back |
| Remove re-exports from `__init__.mojo` only | Removed AnyTensor re-export from `shared/core/__init__.mojo` | Operators still called `from shared.core.arithmetic import add` (function-scoped), which triggered `shared.core` package compilation, which imported `shared.tensor.any_tensor` | Even removing re-exports is insufficient if the struct has function-scoped imports to modules in the other package |
| Move typed ops to `shared/tensor/typed/` | Created `shared/tensor/typed/` directory with typed implementations | The typed files imported from BOTH `shared.tensor.tensor` AND `shared.core.any_tensor`, plus some imported back into `shared.core` (conv, matrix, reduction) | Moving implementation files doesn't help if they create new cross-package import chains |
| Keep operators delegating to `shared.core.arithmetic` | Operators used `from shared.core.arithmetic import add` inside method bodies | `shared.core.arithmetic` imports `AnyTensor` at top level (needed in function signatures), creating `shared.tensor.any_tensor -> shared.core.arithmetic -> shared.tensor.any_tensor` cycle | Struct operators MUST be self-contained or delegate only to same-package functions |
| Create `factories.mojo` with imports from both `.tensor` and `.any_tensor` | `factories.mojo` imported from both sibling modules | Mojo compiled both modules when resolving the package, creating dual type identities for `Tensor[dtype]` | Even intra-package diamond dependencies (A->B, A->C, B->C) can cause type identity issues during package compilation |

## Results & Parameters

### Dependency DAG (no cycles)

```text
shared/base/          (zero dependencies on other shared packages)
  |
  v
shared/tensor/        (depends only on shared.base)
  |- tensor_traits.mojo   (no imports from shared.*)
  |- tensor.mojo          (imports .any_tensor, shared.base)
  |- any_tensor.mojo      (imports .tensor, .tensor_traits, shared.base)
  |- tensor_io.mojo       (imports .any_tensor)
  |- factories.mojo       (imports .tensor, .any_tensor)
  |
  v
shared/core/          (depends on shared.tensor and shared.base)
  |- arithmetic.mojo      (imports shared.tensor.any_tensor)
  |- activation.mojo      (imports shared.tensor.any_tensor)
  |- layers/*.mojo        (imports shared.tensor.any_tensor)
  |
  v
shared/tensor/typed/  (depends on shared.tensor, shared.base, function-scoped shared.core)
```

### Key Mojo Compiler Behavior

- **Type identity is per-compilation-unit**: If module A is compiled twice (via two different import paths), the types it defines are DIFFERENT types
- **Package `__init__.mojo` imports all submodules**: When any file in a package is imported, Mojo may compile the entire package including `__init__.mojo`
- **Function-scoped imports still trigger module compilation**: `from X import Y` inside a function body still causes X to be compiled, just deferred
- **Cross-package re-exports are the most dangerous pattern**: `shared/core/__init__.mojo` importing from `shared.tensor.any_tensor` means ANY import from `shared.core` can trigger `shared.tensor` compilation

### Mojo Stdlib Operator Pattern

```mojo
# SIMD.__add__: Uses MLIR intrinsic (self-contained)
fn __add__(self, rhs: Self) -> Self:
    return Self(mlir_value=__mlir_op.`pop.add`(self._mlir_value, rhs._mlir_value))

# ComplexSIMD.__add__: Inline math on fields (self-contained)
fn __add__(self, rhs: Self) -> Self:
    return Self(self.re + rhs.re, self.im + rhs.im)

# AnyTensor.__add__: Inline dtype dispatch (self-contained)
fn __add__(self, other: AnyTensor) raises -> AnyTensor:
    fn _add[T: DType](x: Scalar[T], y: Scalar[T]) -> Scalar[T]:
        return x + y
    return _anytensor_binary_op[_add](self, other)

# SIMD.__iadd__: Delegates to regular operator (self-contained)
fn __iadd__(mut self, rhs: Self):
    self = self + rhs
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5062 | Moved AnyTensor from shared/core/ to shared/tensor/, 590 files changed, build passes with --Werror, 233 tests pass |
