---
name: mojo-nested-fn-capture-fix
description: "Fix Mojo fieldwise init synthesis failure when nested fn captures non-copyable struct. Use when: getting 'cannot synthesize fieldwise init because field has non-copyable and non-movable type' errors."
category: debugging
date: 2026-03-15
user-invocable: false
---

# Mojo Nested Fn Capture Fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Objective | Fix `--Werror` compilation failures in Mojo when nested `fn` captures a non-copyable struct |
| Outcome | Inlined batch processing loop directly in the outer function, eliminating the need for a nested capturing fn |
| Category | debugging |

## When to Use

- Getting `cannot synthesize fieldwise init because field 'fieldN' has non-copyable and non-movable type 'X'` errors
- A nested `fn` defined inside another function captures a struct from the outer scope
- The captured struct contains heap-allocated fields (e.g., model weights, tensors) making it non-copyable
- Building with `--Werror` causes compilation to fail on implicit capture struct synthesis
- Looking for a pattern similar to training loop batch processing in ML models

## Verified Workflow

### 1. Identify the error

```text
examples/googlenet-cifar10/train.mojo:89:8: error: cannot synthesize fieldwise init
because field 'field0' has non-copyable and non-movable type 'GoogLeNet'
```

The line number points to the nested `fn` definition, not to the struct itself.

### 2. Locate the nested capturing fn

Find the `fn` defined inside another function that captures a variable from the outer scope:

```mojo
fn train_epoch(...) -> ...:
    var model = ...

    fn compute_batch_loss(batch: Tensor) -> Float32:
        # captures `model` from outer scope — this triggers the error
        return model.forward(batch)

    for batch in batches:
        var loss = compute_batch_loss(batch)
```

### 3. Inline the loop directly

Remove the nested fn and call the struct method directly in the loop body:

```mojo
fn train_epoch(...) -> ...:
    var model = ...

    for batch in batches:
        # call model directly — no capturing fn needed
        var loss = model.forward(batch)
```

### 4. Remove unused imports

After inlining, any imports that were needed only for the nested fn pattern
(e.g., `TrainingLoop`) can be removed:

```mojo
# Remove if no longer needed:
# from shared.training import TrainingLoop
```

### 5. Verify

```bash
pixi run mojo build examples/<model>-cifar10/train.mojo 2>&1 | grep "error:"
# Should return no output (zero errors)
```

## Why This Happens

In Mojo, when a nested `fn` captures variables from its enclosing scope, the compiler
synthesizes an implicit capture struct to hold those variables. The compiler then tries to
generate a fieldwise initializer for this capture struct. If any captured variable has a
non-copyable and non-movable type (like a model struct with heap-allocated weight tensors),
fieldwise init synthesis fails.

The fix avoids creating a nested capturing fn entirely, so no implicit capture struct is
synthesized.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add explicit `__init__` with `^` ownership | Pass model ownership into the nested fn | Would require significant restructuring of `train_epoch` signature | Over-engineered; inlining is simpler |
| Use `UnsafePointer[Model]` | Store model as unsafe pointer to avoid copyability requirement | Introduces unsafe code unnecessarily | Only appropriate when pointer semantics are needed |
| Add `@register_passable` | Mark the containing struct as register-passable | Not appropriate for complex structs with heap-allocated fields like model weights | `@register_passable` is for simple value types |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Files fixed | 2 (`examples/googlenet-cifar10/train.mojo`, `examples/mobilenetv1-cifar10/train.mojo`) |
| Lines changed per file | ~10-15 (remove nested fn, inline loop) |
| Compilation errors after fix | 0 |
| Reference pattern | `examples/resnet18-cifar10/train.mojo` (already uses the correct inlined approach) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR fixing GoogLeNet and MobileNetV1 training examples | [notes.md](../../references/notes.md) |
