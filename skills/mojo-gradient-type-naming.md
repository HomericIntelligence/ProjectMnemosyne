---
name: mojo-gradient-type-naming
description: 'Fix naming inconsistency between generic gradient containers and domain-specific
  backward pass results in Mojo ML code. Use when: backward functions return GradientPair
  with opaque grad_a/grad_b fields but callers know the semantic meaning (e.g. input
  vs kernel gradients).'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Language | Mojo |
| Domain | ML / Neural Network backward passes |
| Issue Type | Naming inconsistency across gradient container types |
| Scope | gradient_types.mojo, conv.mojo, __init__.mojo, tests |

## When to Use

- A `conv2d_no_bias_backward` or similar function returns `GradientPair` with `.grad_a`/`.grad_b`
  while the analogous biased version returns `GradientTriple` with `.grad_input`/`.grad_weights`/`.grad_bias`
- Call sites must track field-ordering conventions in comments rather than relying on field names
- A reviewer asks for semantic field names on gradient return structs
- Extending `GradientPair` with aliases is not possible in current Mojo (no computed properties)

## Verified Workflow

1. **Identify the inconsistency** — find all backward functions returning `GradientPair` where
   field semantics are known (e.g. conv input vs kernel gradient).

2. **Create domain-specific structs** in `gradient_types.mojo`:
   ```mojo
   struct Conv2dNoBiasGradient(Copyable, Movable):
       var grad_input: ExTensor
       var grad_weights: ExTensor

       fn __init__(out self, var grad_input: ExTensor, var grad_weights: ExTensor):
           self.grad_input = grad_input^
           self.grad_weights = grad_weights^
   ```
   Follow the same `(Copyable, Movable)` traits and `^` ownership-transfer pattern used by
   existing gradient types. Use `out self` constructor convention (Mojo v0.26.1+).

3. **Update return types** in `conv.mojo` — change `-> GradientPair` to
   `-> Conv2dNoBiasGradient` and update the `return` statement constructor call.

4. **Update all call sites** — search for `.grad_a`/`.grad_b` accesses on results of the
   updated functions and replace with `.grad_input`/`.grad_weights`.

5. **Update imports** in `conv.mojo` and `__init__.mojo` to export the new types.

6. **Update tests** — replace `.grad_a`/`.grad_b` with semantic field names.

7. **Keep `GradientPair` unchanged** — it remains correct for truly generic binary operations
   (e.g. `add_backward`, `matmul_backward`) where `grad_a`/`grad_b` are semantically appropriate.

## Key Patterns

### Struct definition pattern (Mojo v0.26.1+)

```mojo
struct Conv2dNoBiasGradient(Copyable, Movable):
    var grad_input: ExTensor
    var grad_weights: ExTensor

    fn __init__(out self, var grad_input: ExTensor, var grad_weights: ExTensor):
        self.grad_input = grad_input^
        self.grad_weights = grad_weights^
```

- Use `out self` (not `mut self`) for constructors
- Use `var` parameter prefix for owned inputs
- Use `^` to transfer ownership into struct fields

### Naming convention alignment

| Struct | Used for | Fields |
|--------|----------|--------|
| `GradientPair` | Generic binary ops (add, matmul) | `grad_a`, `grad_b` |
| `GradientTriple` | Ops with bias (conv2d, linear) | `grad_input`, `grad_weights`, `grad_bias` |
| `Conv2dNoBiasGradient` | conv2d without bias | `grad_input`, `grad_weights` |
| `DepthwiseConv2dNoBiasGradient` | depthwise conv without bias | `grad_input`, `grad_weights` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add computed property aliases to GradientPair | Add `grad_input` as alias for `grad_a` | Mojo v0.26.1 doesn't support computed properties / property getters on structs | Create a new domain-specific struct instead |
| Rename GradientPair fields globally | Change `grad_a`/`grad_b` to `grad_input`/`grad_weights` everywhere | Would break all non-conv callers (add_backward, etc.) that use generic names | Keep GradientPair generic; add new structs only for conv domain |
| Add option 3 (just comments) from issue | Document ordering in gradient_types.mojo | Doesn't solve the type-safety problem — callers still need to know ordering | Semantic field names are the right fix |

## Results & Parameters

### Files modified

```text
shared/core/gradient_types.mojo   # Add new structs
shared/core/conv.mojo             # Update imports, return types, call sites
shared/core/__init__.mojo         # Export new types
tests/shared/core/test_conv.mojo  # Update field access
```

### grep pattern to find call sites

```bash
grep -n "\.grad_a\|\.grad_b" shared/core/conv.mojo tests/
```

### Pre-commit hooks pass automatically

The mojo format pre-commit hook ran automatically on commit and passed — no manual formatting needed.
