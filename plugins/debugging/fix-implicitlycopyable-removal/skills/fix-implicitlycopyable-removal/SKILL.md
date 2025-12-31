---
name: fix-implicitlycopyable-removal
description: Systematic approach to removing ImplicitlyCopyable trait from Mojo structs and fixing resulting compilation errors
---

# Fix ImplicitlyCopyable Removal

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2025-12-29 |
| **Session Context** | PR #2962 - ExTensor ImplicitlyCopyable Bug Fix |
| **Objective** | Remove ImplicitlyCopyable trait from struct with List fields and fix compilation errors |
| **Outcome** | Success - 132 errors across 27 files resolved, all CI tests passing |
| **Files Modified** | 27 files (autograd, core, data, testing, training, layers) |

## When to Use This Skill

Use this skill when you need to:

1. **Remove ImplicitlyCopyable from a struct** that contains non-trivial fields (List, Dict, String, or other heap-allocated types)
2. **Fix compilation errors** after removing ImplicitlyCopyable trait from a widely-used type
3. **Debug memory corruption** caused by bitwise copies bypassing reference counting
4. **Systematically refactor** a codebase to use explicit copying instead of implicit copies

### Trigger Conditions

- Struct contains `List[T]`, `Dict[K,V]`, `String`, or other types with shared ownership
- Layer tests crash AFTER passing assertions (indicates destructor issues)
- Mojo compiler errors about "cannot implicitly copy" or "cannot transfer value"
- Memory corruption symptoms (use-after-free, double-free, segfaults)

## Problem Context

### The Bug

`ImplicitlyCopyable` on a struct with `List[Int]` fields causes Mojo to perform **bitwise copies** that bypass `__copyinit__`. This breaks reference counting:

1. Implicit copy creates bitwise duplicate (refcount pointer copied, not incremented)
2. Refcount stays at 1 even with 2+ copies sharing the data
3. First destructor decrements refcount to 0 and frees memory
4. Second destructor accesses freed memory → **CRASH**

### Example: ExTensor Bug

```mojo
# BEFORE (BUGGY)
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):
    var _shape: List[Int]      # Shared ownership
    var _strides: List[Int]    # Shared ownership
    var _refcount: UnsafePointer[Int]  # Manual refcount
```

Problem: Passing `ExTensor` by value triggers bitwise copy, not `__copyinit__`, so refcount isn't incremented.

## Verified Workflow

### Phase 1: Remove the Trait

```mojo
# Change from:
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

# To:
struct ExTensor(Copyable, Movable, Sized):
```

### Phase 2: Add Explicit Copy Method

Create a `copy()` method using struct literal construction:

```mojo
fn copy(self) -> Self:
    var result = Self {
        _data: self._data,
        _shape: self._shape.copy(),
        _strides: self._strides.copy(),
        _dtype: self._dtype,
        _numel: self._numel,
        _is_view: self._is_view,
        _refcount: self._refcount,
        _original_numel_quantized: self._original_numel_quantized,
        _allocated_size: self._allocated_size,
    }
    if result._refcount:
        result._refcount[] += 1  # Increment refcount
    return result^  # Transfer ownership
```

### Phase 3: Fix Compilation Errors Systematically

#### Pattern 1: List Indexing

```mojo
# BEFORE (implicit copy)
var tensor = tensor_list[i]

# AFTER (explicit copy)
var tensor = tensor_list[i].copy()
```

#### Pattern 2: Tuple Unpacking

```mojo
# BEFORE (doesn't work without ImplicitlyCopyable)
var images, labels = load_data()

# AFTER (use indexing)
var batch_data = load_data()
var images = batch_data[0].copy()
var labels = batch_data[1].copy()
```

#### Pattern 3: Function Returns

```mojo
# BEFORE (implicit copy on return)
fn get_tensor(self) -> ExTensor:
    return self._tensor  # Error!

# AFTER (explicit ownership transfer)
fn get_tensor(self) -> ExTensor:
    return self._tensor.copy()
```

#### Pattern 4: Ownership Transfer (Local Variables)

```mojo
# BEFORE
var result = some_tensor

# AFTER (transfer ownership, no copy needed)
var result = some_tensor^
```

#### Pattern 5: Tuple Returns

```mojo
# BEFORE
return (tensor1, tensor2)

# AFTER (transfer ownership)
return (tensor1^, tensor2^)
```

#### Pattern 6: Closure Captures

```mojo
# BEFORE (doesn't work - closures can't capture non-ImplicitlyCopyable)
var weights = get_weights()
fn forward(x: ExTensor) -> ExTensor:
    return conv2d(x, weights, ...)  # Error!

# AFTER (use UnsafePointer)
var weights_copy = get_weights().copy()
var weights_ptr = UnsafePointer.address_of(weights_copy)
fn forward(x: ExTensor) escaping -> ExTensor:
    return conv2d(x, weights_ptr[], ...)
```

#### Pattern 7: Function Parameters

```mojo
# BEFORE (var means owned/mutable)
fn argmax(var tensor: ExTensor) -> Int:
    ...

# AFTER (borrowed read-only)
fn argmax(tensor: ExTensor) -> Int:
    ...
```

### Phase 4: Batch Fix Strategy

For large codebases (27+ files), parallelize fixes by module:

1. **Autograd module** (backward_ops, functional, grad_utils, optimizers)
2. **Core module** (arithmetic, attention, conv, extensor, matrix, normalization)
3. **Data module** (datasets, cache, transforms, loaders)
4. **Testing/Training modules** (layer_testers, models, metrics)

### Phase 5: Verification

```bash
# Local compilation check
pixi run mojo build shared/core/extensor.mojo

# Run affected tests
pixi run mojo test tests/shared/core/layers/test_dropout.mojo

# Monitor CI
gh pr checks <PR-number> --watch
```

## Failed Attempts

| Attempt | What I Tried | Error | Why It Failed |
|---------|--------------|-------|---------------|
| Return self in copy() | `return self` | `cannot implicitly copy 'ExTensor'` | Returning self still requires implicit copy |
| Call __copyinit__ directly | `return Self.__copyinit__(self)` | `__copyinit__ is not directly callable` | Lifecycle methods can't be called directly |
| Tuple unpacking | `var a, b = load_data()` | `cannot synthesize __copyinit__` | Destructuring needs ImplicitlyCopyable |
| Capture in closure | Captured non-copyable in closure | `cannot synthesize __copyinit__` | Closures implicitly copy captures |
| Assign without .copy() | `var x = predictions` | `cannot implicitly copy` | Must use explicit .copy() |

## Results & Parameters

### Success Metrics

- **Files Modified**: 27 files across 5 modules
- **Compilation Errors Fixed**: 132 errors
- **CI Test Pass Rate**: 100% (45/45 test jobs passing)
- **Memory Corruption**: Eliminated

### Key Code Snippets

**ExTensor copy() method**:
```mojo
fn copy(self) -> Self:
    var result = Self {
        _data: self._data,
        _shape: self._shape.copy(),
        _strides: self._strides.copy(),
        # ... other fields
    }
    if result._refcount:
        result._refcount[] += 1
    return result^
```

**Closure capture workaround**:
```mojo
var w_copy = weights.copy()
var w_ptr = UnsafePointer.address_of(w_copy)
fn forward(x: ExTensor) raises escaping -> ExTensor:
    return conv2d(x, w_ptr[], ...)
```

## References

- [Mojo Copy Semantics](https://docs.modular.com/mojo/manual/values/lifetimes/copy)
- [Mojo Ownership Guide](https://docs.modular.com/mojo/manual/values/ownership)
- PR #2962: ExTensor ImplicitlyCopyable Removal
