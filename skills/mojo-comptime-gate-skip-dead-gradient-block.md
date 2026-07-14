---
name: mojo-comptime-gate-skip-dead-gradient-block
description: "Use when: (1) a backward or compute-all op wastes work computing an unused gradient at a first layer, frozen backbone, or local-learning setup; (2) you want to skip a loop nest at zero runtime cost via a compile-time flag in Mojo; (3) writing a Mojo compile-time conditional and unsure whether it's `comptime if` vs `@parameter if`; (4) extracting a large loop to make it conditionally-compiled without hand-reindenting."
category: optimization
date: 2026-07-10
version: "1.0.0"
user-invocable: false
tags: [mojo, comptime-if, dead-code-elimination, conv2d-backward, grad-input, compile-time-gating, extract-refactor, loop-nest-elision, frozen-backbone, first-layer, dtype-instantiation, gradient-computation]
verification: verified-local
---

# Mojo Compile-Time Gate to Skip a Dead Gradient Loop Block

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-10 |
| **Objective** | Eliminate the wasted `conv2d_backward` grad_input loop nest at a network's first conv (where grad_input has no consumer), at zero runtime cost, without changing existing behavior |
| **Outcome** | Verified-local on ProjectOdyssey/Odyssey #5573, PR #5578: extracted grad_input loop verbatim into a helper, gated it behind a `comptime if compute_grad_input:` parameter, exposed `conv2d_backward_weights_only`; all conv tests pass in-container (float32/float64/stride2 parity), strict-review A-, CI settling |

## When to Use

Apply this skill when:

- A backward pass (or any "compute-all-outputs" op) always computes a gradient/output that a specific caller immediately discards — e.g. **grad_input at a network's FIRST conv layer**, a **frozen backbone** whose inputs need no gradient, or **local-learning rules** that only need a subset of gradients.
- You want to **skip an expensive loop nest at zero runtime cost** using a compile-time flag in Mojo (the block is fully elided from the compiled kernel, not merely branched-over at runtime).
- You are **writing a Mojo compile-time conditional** and are unsure whether this repo uses `comptime if` or the deprecated `@parameter if`.
- You need to **extract a large loop into a helper** so it can be conditionally compiled, without hand-reindenting error-prone index math.

Concrete trigger: `conv2d_backward`'s grad_input block `B·C_in·H_in·W_in·H_out·W_out` is the most expensive block in the backward pass (several× the useful grad_kernel work at first-layer geometries; tens of billions of iterations/batch at ImageNet scale) and is thrown away at the first layer.

## Verified Workflow

### Quick Reference

The **extract-then-comptime-gate** pattern, in three moves:

```mojo
# 1. EXTRACT the expensive optional block VERBATIM into a helper.
#    Byte-identical move: same index math, bounds checks, bitcast reads, _set_float64.
#    mut-param threads the writable tensor into the helper.
fn _conv2d_grad_input[dtype: DType](mut grad_input: AnyTensor, /* ...same args... */):
    # ... the 58-line loop nest, moved unchanged ...

# 2. Add a COMPILE-TIME parameter and gate the call with `comptime if` (NOT @parameter if).
fn _conv2d_backward_impl[dtype: DType, compute_grad_input: Bool](/* ... */) -> GradientTriple:
    var grad_input = zeros(...)   # keep the allocation so the returned triple is valid
    # ... grad_kernel / grad_bias work (always runs) ...
    comptime if compute_grad_input:
        _conv2d_grad_input[dtype](grad_input, /* ... */)   # fully elided when False
    return GradientTriple(grad_input, grad_kernel, grad_bias)

# 3. Thin public wrappers over the parametric impl.
fn conv2d_backward(/* ... */) -> GradientTriple:               # unchanged behavior
    return _conv2d_backward_impl[dtype, True](/* ... */)

fn conv2d_backward_weights_only(/* ... */) -> GradientTriple:  # new, export it
    return _conv2d_backward_impl[dtype, False](/* ... */)      # grad_input = all-zeros
```

### Detailed Steps

1. **Extract verbatim.** Move the grad_input loop nest into `_conv2d_grad_input[dtype](mut grad_input, ...)` with a BYTE-IDENTICAL copy — same index math, bounds checks, bitcast reads, `_set_float64`. Extracting to a function is the *safe* refactor; re-indenting a 58-line loop by hand under a conditional invites transcription errors, so never hand-reindent.
2. **Grep the codebase for the compile-time idiom first.** This repo's Mojo uses **`comptime if`**. `@parameter if` is **deprecated** and errors: `'@parameter if' is deprecated; use 'comptime if'`. `comptime if` appears many times in this tree — match the existing idiom before writing any compile-time conditional.
3. **Add the compile-time parameter and gate.** Give the kernel a `compute_grad_input: Bool = True` parameter and wrap the extracted call in `comptime if compute_grad_input:`. When False the loop is fully elided from the instantiation — zero runtime overhead.
4. **Keep the `zeros()` allocation.** grad_input stays the `zeros(...)`-allocated tensor so the returned `GradientTriple` is still structurally valid (grad_input = all-zeros). Callers of the weights-only variant must not consume grad_input.
5. **Factor dtype dispatch into the parametric impl.** Put dtype dispatch inside `_conv2d_backward_impl[dtype, compute_grad_input]`, then expose two thin public wrappers: `conv2d_backward = impl[..., True]` (unchanged) and new `conv2d_backward_weights_only = impl[..., False]`. **Export the new function.**
6. **Test across dtypes and a strided geometry** (see Failed Attempts row 3 for why single-dtype tests are insufficient).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Inline `@parameter if` | Wrapped the 58-line grad_input loop inline with `@parameter if compute_grad_input:` | `@parameter if` is deprecated in this Mojo and errors: `'@parameter if' is deprecated; use 'comptime if'` | Use `comptime if`, and extract the block to a helper rather than gate it inline |
| Hand-reindent under conditional | Manually re-indented the loop body one level deeper to sit under the conditional | Error-prone transcription risk on 58 lines of index math / bounds / bitcasts | Extract the block verbatim into a function (provably identical) instead of reindenting by hand |
| Single-dtype test | Tested only float32 | Each dtype × `compute_grad_input=False` is a **distinct compile-time kernel instantiation**; float16/float64 `impl[False]` were never compiled or exercised | Test ≥2 dtypes (float32 AND float64) plus a stride>1 case so every instantiation is compiled |
| Skip the allocation | Made grad_input uninitialized / unallocated when skipped | Returned `GradientTriple` became invalid — downstream shape/validity assumptions broke | Keep the `zeros()` allocation so the returned triple is a valid all-zeros grad_input |

## Results & Parameters

### Configuration

Public API shape:

```mojo
# Unchanged full backward: computes all three gradients.
conv2d_backward(...)                 == _conv2d_backward_impl[dtype, True](...)

# New: skips grad_input entirely; grad_input returned as all-zeros.
conv2d_backward_weights_only(...)    == _conv2d_backward_impl[dtype, False](...)
```

The gate:

```mojo
comptime if compute_grad_input:      # comptime if — NOT @parameter if (deprecated)
    _conv2d_grad_input[dtype](grad_input, ...)
```

Cost-table intuition (why grad_input dominates at the first layer):

```
grad_input : B · C_in · H_in · W_in · H_out · W_out     <- elided when compute_grad_input=False
grad_kernel: C_out · C_in · kH · kW · B · H_out · W_out  <- always computed
```

At first-layer geometries `B·C_in·H_in·W_in·H_out·W_out` is several× the grad_kernel term (tens of billions of iterations/batch at ImageNet scale), all discarded — hence the win.

### Test contract

Assert, for the weights-only variant vs. the full backward on a shared fixture:

- grad_weights AND grad_bias are element-identical (tol 1e-6) between the two variants.
- weights-only grad_input is all-zeros.
- **Sanity (non-vacuous):** the FULL variant's grad_input is NON-zero for the fixture.
- Cover float32 AND float64, plus a strided geometry (stride=2) — each dtype × `compute_grad_input=False` is a separate compile-time instantiation.

### Expected Output

- Weights-only backward compiles for every tested dtype and returns grad_weights/grad_bias identical to the full path.
- The grad_input loop nest is absent from the `impl[False]` instantiation (zero runtime cost at the first layer).
- Full-path behavior is byte-for-byte unchanged (verbatim extraction).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey / Odyssey | Issue #5573, PR #5578 — all conv tests pass in-container (float32/float64/stride2 parity), strict-review A-, CI settling (not yet confirmed merged) | verified-local |

## References

- [mojo-tensor-unit-test-and-gradient-checking](mojo-tensor-unit-test-and-gradient-checking.md)
- [mojo-tensor-design-view-semantics-numeric-correctness](mojo-tensor-design-view-semantics-numeric-correctness.md)
- [googlenet-backward-pass-inception-gradients](googlenet-backward-pass-inception-gradients.md)
