---
name: mojo-closures-capturing-numerical-forward-trait
description: "Workaround for Mojo 0.26.3: capturing closures cannot be passed to def(T) raises -> T parameters. Use when: (1) a nested def captures outer variables and must be passed to a higher-order function, (2) compiler gives 'capturing nested functions must be declared unified' or 'cannot pass unified closure to escaping parameter'."
category: debugging
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Mojo 0.26.3: Capturing Closures → NumericalForward Trait Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-09 |
| **Objective** | Pass capturing closures (that close over runtime variables) to higher-order functions in Mojo 0.26.3 |
| **Outcome** | Successful — struct + trait pattern compiles with zero `--Werror` errors |
| **Verification** | verified-local — CI pending |

## When to Use

- A nested `def` captures outer variables and must be passed to a function expecting `def(T) raises -> T`
- Compiler error: `capturing nested functions must be declared 'unified'`
- Compiler error after adding `unified {read}`: `cannot pass non-escaping closure to escaping parameter`
- You need a higher-order function that works with both capturing and non-capturing forwards

## Verified Workflow

### Quick Reference

```mojo
# 1. Define trait in your module
trait NumericalForward(Copyable, Movable):
    def __call__(self, x: AnyTensor) raises -> AnyTensor: ...

# 2. Wrap closure in struct
@fieldwise_init
struct MyForward(NumericalForward):
    var param1: SomeType
    def __call__(self, x: AnyTensor) raises -> AnyTensor:
        return my_op(x, self.param1)

# 3. Add parametric overload to higher-order function
def compute_gradient[F: NumericalForward](forward_fn: F, x: AnyTensor) raises -> AnyTensor:
    ...

# 4. Call site
var fwd = MyForward(captured_value)
var grad = compute_gradient(fwd, input)
```

### Detailed Steps

1. Define a trait with `__call__` that matches the closure signature. Inherit `Copyable, Movable`
   so the struct can be stored/moved.
2. For each capturing closure, create a `@fieldwise_init` struct with fields for each captured
   variable.
3. Implement `__call__` on the struct, reading from `self.fieldname` instead of the captured
   variable.
4. Add a parametric overload `[F: TraitName]` to every higher-order function that previously
   took `def(T) raises -> T`.
5. At each call site, instantiate the struct with the captured values and pass it as a value
   argument.

**Note**: The existing `def(T) raises -> T` overload can coexist for non-capturing closures
(which remain escaping and can still be passed directly).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `capturing` keyword | `def f(x: T) capturing raises -> T` | `capturing` keyword removed in Mojo 0.26.3 | Use `unified {read}` instead — but see next row |
| `unified {read}` closure | `def f(x: T) raises unified {read} -> T` | Makes closure non-escaping; cannot pass to `def(T) raises -> T` parameter | `unified` closures are non-escaping by design — no cast exists |
| Compile-time param | `compute_gradient[forward](x)` | "cannot use a dynamic value in a parameter list" — closures that capture runtime vars are not compile-time values | Compile-time params only work for module-scope non-capturing functions |
| `AnyType` param | `def f[T: AnyType](fn: T, x: AnyTensor)` | Closures don't conform to `AnyType` or user-defined traits directly | Must use struct wrapper; closures are not first-class trait implementors |
| Module-scope function | Extract closure to top-level `def` | Cannot capture runtime values at module scope | Only works if the function needs no captured context |

## Results & Parameters

**Struct template** (copy-paste):

```mojo
@fieldwise_init
struct _MyLayerForward(NumericalForward):
    var field1: AnyTensor
    var field2: Int

    def __call__(self, x: AnyTensor) raises -> AnyTensor:
        return my_layer_op(x, self.field1, field2=self.field2)
```

**Trait definition** (copy-paste, place near top of module):

```mojo
trait NumericalForward(Copyable, Movable):
    def __call__(self, x: AnyTensor) raises -> AnyTensor: ...
```

**Parametric overload** (copy-paste):

```mojo
def compute_numerical_gradient[F: NumericalForward](
    forward_fn: F, x: AnyTensor, epsilon: Float64 = 3e-4
) raises -> AnyTensor:
    # dispatch to internal implementation
    ...
```

**Example — conv2d case**:

```mojo
# BEFORE (broken in 0.26.3):
def forward(x: AnyTensor) raises -> AnyTensor:
    return conv2d(x, weights, bias, stride=stride, padding=padding)
var grad = compute_numerical_gradient(forward, input, epsilon)

# AFTER (works in 0.26.3):
@fieldwise_init
struct Conv2DForward(NumericalForward):
    var weights: AnyTensor
    var bias: AnyTensor
    var stride: Int
    var padding: Int
    def __call__(self, x: AnyTensor) raises -> AnyTensor:
        return conv2d(x, self.weights, self.bias, stride=self.stride, padding=self.padding)

var fwd = Conv2DForward(weights, bias, stride, padding)
var grad = compute_numerical_gradient(fwd, input, epsilon)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo 0.26.3 migration, branch fix-ci-root-causes | 4 closures in layer_testers.mojo replaced with structs; package compiles --Werror clean |
