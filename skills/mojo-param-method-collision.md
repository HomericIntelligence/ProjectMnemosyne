---
name: mojo-param-method-collision
description: "Fix Mojo v0.26.1 struct parameter-method name collision where a parametric struct's type parameter and a trait method share the same name. Use when: (1) CI fails with 'invalid redefinition' on a parametric struct method, (2) a trait requires fn dtype() but the struct has [dtype: DType] parameter, (3) typed overloads create 'no matching function' ambiguity with existing untyped functions."
category: debugging
date: 2026-03-22
version: 1.0.0
user-invocable: false
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-22 |
| **Objective** | Fix Mojo v0.26.1 compilation errors from struct parameter-method name collision and typed overload ambiguity |
| **Outcome** | Renamed trait method `dtype()` → `get_dtype()` and typed overloads to `_typed` suffix; 27 functions across 11 files |
| **Epic** | HomericIntelligence/ProjectOdyssey#4998 |
| **PRs** | #5028 (closed, had errors), #5029 (fix PR) |

## When to Use

1. CI fails with `error: invalid redefinition of 'X'` where X is both a struct parameter name and a method name
2. Mojo v0.26.1 parametric struct like `struct Foo[dtype: DType]` also needs `fn dtype(self) -> DType` for trait conformance
3. Adding typed function overloads (e.g., `fn add[dt: DType](a: Tensor[dt])`) alongside existing untyped functions (`fn add(a: AnyTensor)`) causes `no matching function in call` errors
4. A review agent claims the collision "doesn't exist" but CI proves otherwise — trust the compiler, not the reviewer

## Verified Workflow

### Quick Reference

```text
Problem 1: struct parameter name == trait method name
  Error: "invalid redefinition of 'dtype'"
  Fix: Rename the TRAIT METHOD (not the parameter)
       fn dtype() → fn get_dtype()

Problem 2: typed overload same name as existing function
  Error: "no matching function in call to 'relu'"
  Fix: Rename typed overloads to _typed suffix
       fn relu[dt]() → fn relu_typed[dt]()

Problem 3: Function reference ambiguity
  Error: "cannot form a reference to overloaded declaration of 'sum'"
  Fix: Use import alias
       from shared.core.reduction import sum as tensor_sum
```

### Step 1: Identify the collision type

Read the CI error message carefully:

- `invalid redefinition of 'X'` → Problem 1 (param-method collision)
- `no matching function in call to 'X'` → Problem 2 (overload ambiguity)
- `cannot form a reference to overloaded declaration of 'X'` → Problem 3 (reference ambiguity)

### Step 2: Fix Problem 1 (param-method collision)

Rename the **trait method**, not the struct parameter. The parameter name should match Mojo conventions (`dtype` is canonical for SIMD-like types).

```mojo
# BEFORE (broken):
trait TensorLike(Copyable, Movable):
    fn dtype(self) -> DType: ...  # Collides with struct parameter 'dtype'

struct Tensor[dtype: DType](TensorLike):
    fn dtype(self) -> DType:      # ERROR: invalid redefinition
        return Self.dtype

# AFTER (fixed):
trait TensorLike(Copyable, Movable):
    fn get_dtype(self) -> DType: ...  # Renamed to avoid collision

struct Tensor[dtype: DType](TensorLike):
    fn get_dtype(self) -> DType:      # No collision
        return Self.dtype
```

For backward compat on the runtime-typed struct (AnyTensor), keep BOTH methods:

```mojo
struct AnyTensor(TensorLike):
    fn dtype(self) -> DType: return self._dtype     # Backward compat
    fn get_dtype(self) -> DType: return self._dtype  # TensorLike conformance
```

### Step 3: Fix Problem 2 (overload ambiguity)

When a typed overload has the SAME name as an existing untyped function, calling the untyped version from inside the typed overload creates ambiguity.

```mojo
# BEFORE (broken):
fn relu(input: AnyTensor) -> AnyTensor: ...  # Existing

fn relu[dt: DType](input: Tensor[dt]) -> Tensor[dt]:
    return relu(input.as_any()).as_tensor[dt]()  # ERROR: ambiguous 'relu'

# AFTER (fixed):
fn relu_typed[dt: DType](input: Tensor[dt]) -> Tensor[dt]:
    return relu(input.as_any()).as_tensor[dt]()  # Unambiguous: calls AnyTensor version
```

Apply `_typed` suffix to ALL typed overloads consistently.

### Step 4: Fix Problem 3 (reference ambiguity)

When code takes a function reference (`comptime f = sum`), adding an overload makes the name ambiguous.

```mojo
# BEFORE (broken):
comptime tensor_sum = sum  # Ambiguous: which 'sum'?

# AFTER (fixed):
from shared.core.reduction import sum as tensor_sum  # Explicit alias
```

### Step 5: Update tests

Find all test files that call the renamed functions and update:

```bash
grep -rn "from.*import.*add\b" tests/ --include="*.mojo"
# Change: from shared.core.arithmetic import add
# To:     from shared.core.arithmetic import add_typed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Rename struct parameter `dtype` → `dt` | Changed `struct Tensor[dt: DType]` to avoid collision with `fn dtype()` method | Cascades through ALL callers (`Self.dtype` → `Self.dt` in 32+ locations); non-idiomatic (Mojo stdlib uses `dtype`) | Rename the METHOD, not the parameter — method is called in fewer places |
| Rename trait method `dtype()` → `get_dtype()` in TensorLike only | Changed trait but not implementations | Implementations must also rename, AND AnyTensor needs both old+new for backward compat | When renaming trait methods, update ALL conforming types |
| Review agent claims collision doesn't exist | Agent said `struct Tensor[dtype]` + `fn dtype()` compiles fine in Mojo v0.26.1 | CI proved it DOES fail with `invalid redefinition of 'dtype'` | ALWAYS trust the compiler over review agent claims — test assumptions with `mojo build` |
| Keep same function names for typed overloads | `fn add[dt](Tensor[dt])` alongside `fn add(AnyTensor)` | Compiler can't resolve which `add` to call inside the typed overload body | Use `_typed` suffix to disambiguate; matches existing convention (`batch_norm2d_typed`, `maxpool2d_typed`) |
| Monolithic fix agent | Single agent to fix all compilation errors | Agent got stuck in plan mode, couldn't execute | Launch fix agents AFTER exiting plan mode; verify agent is in execution mode |
| Three parallel agents fix same struct | 3 agents independently "fixed" the dtype collision differently | Created merge conflicts; wasted work | Share design decisions: when one agent discovers a solution, communicate to others |

## Results & Parameters

### Naming Convention

```yaml
# Struct parameter: keep canonical Mojo name
struct_parameter: "dtype"  # e.g., struct Tensor[dtype: DType]
# NOT: dt, _dtype, tensor_dtype

# Trait method: use get_ prefix when colliding with parameter
trait_method: "get_dtype"  # e.g., fn get_dtype(self) -> DType
# NOT: dtype (collides), type (too generic), data_type (non-standard)

# Typed overload: use _typed suffix
overload_suffix: "_typed"  # e.g., fn add_typed[dt: DType](...)
# NOT: add_tensor, tensor_add, typed_add

# Import alias for reference ambiguity
import_pattern: "from module import func as alias"
# e.g., from shared.core.reduction import sum as tensor_sum
```

### Files Modified (typical)

```text
Trait definition:       1 file  (tensor_traits.mojo)
Parametric struct:      1 file  (tensor.mojo)
Runtime-typed struct:   1 file  (any_tensor.mojo)
Typed overloads:        7 files (arithmetic, activation, elementwise, matrix, reduction, comparison, shape)
Test files:             4 files (test_tensor_arithmetic/elementwise/matrix/shape_ops.mojo)
Reference ambiguity:    1 file  (variable.mojo)
Total:                 ~15 files
```

### Verification

```bash
# After fixes, ALL must pass:
just package                    # No compilation errors
just test-mojo                  # All tests pass
grep -rn "fn dtype(self)" shared/tensor/tensor.mojo  # Should NOT exist (renamed to get_dtype)
grep -rn "_typed\[" shared/core/ --include="*.mojo" | wc -l  # Should be 27 (typed overloads)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Epic #4998, PRs #5028-#5029 | ExTensor → Tensor[dtype] + AnyTensor migration |
