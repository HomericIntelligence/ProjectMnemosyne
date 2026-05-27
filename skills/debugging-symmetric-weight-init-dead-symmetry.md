---
name: debugging-symmetric-weight-init-dead-symmetry
description: "Diagnose and avoid the symmetric-weight-init pathology where uniform-fill weights make multi-layer gradients algebraically zero and produce false 'substrate bug' diagnoses. Use when: (1) a convergence test or training run plateaus at the uniform-distribution loss (e.g., ln(num_classes)), (2) gradients to early layers come back at fp32 cancellation noise magnitude (~1e-8) while later layers have normal-magnitude gradients, (3) writing self-contained test cases for autograd/backward correctness, (4) reviewing test code that initializes weights with a constant fill."
category: debugging
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - autograd
  - weight-init
  - dead-symmetry
  - convergence-test
  - backward
  - gradient-pathology
  - mojo
---

# Symmetric Weight Init Dead-Symmetry Pathology

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-26 |
| **Objective** | Recognize when "broken substrate" symptoms (tiny early-layer grads, loss plateau at ln(C)) are actually caused by uniform-fill weight init creating algebraically-zero gradients, not a real backward bug |
| **Outcome** | Success — switching to asymmetric per-element ramp init unmasks real substrate behavior and prevents 30+ minute misdiagnoses |
| **Verification** | verified-ci (ProjectOdyssey PR #5466) |

## When to Use

- Convergence test plateaus at chance loss (e.g., `ln(num_classes)`) after the first few steps
- Gradients to early (conv/embedding) layers are ~1e-8 in magnitude while later (FC) gradients are ~1e-1
- Tempted to write `_make_tensor(shape, 0.05)` or equivalent uniform-fill weight init in a test
- Reviewing a PR that uses constant-fill weights in any multi-layer test
- Diagnosing "the substrate seems broken but only in chained ops, not in isolation"

## Verified Workflow

### Quick Reference

```mojo
# WRONG — uniform init creates dead-symmetry, algebraically zeros gradients
var w = _make_tensor([4, 32], 0.05)  # every weight = 0.05

# RIGHT — asymmetric init with per-element ramp, breaks the symmetry
def _make_asymmetric(shape: List[Int], base: Float64, slope: Float64) raises -> AnyTensor:
    var t = zeros(shape, DType.float32)
    var n = 1
    for d in shape: n *= d
    for i in range(n):
        t._set_float64(i, base + Float64(i) * slope)
    return t^

var w = _make_asymmetric([4, 32], 0.05, 0.001)  # 0.050, 0.051, 0.052, ...
```

For DIAGNOSIS (when you see the symptom and want to confirm it's the pathology, not a real bug):

```bash
# Compare grads with asymmetric vs symmetric init; if they differ by orders of
# magnitude on the same input, the symmetric run was hitting dead-symmetry.
```

### Detailed Steps

1. **Identify the symptom**: convergence test loss plateaus at `ln(C)` for C classes, or earlier-layer gradients are ~7 orders of magnitude smaller than later-layer gradients.
2. **Don't immediately blame the substrate.** First, rerun with asymmetric weight init using `_make_asymmetric(shape, base, slope)` where `slope` is small but nonzero (e.g., 1% of `base`).
3. If the gradients now look healthy and the loss decreases, the original failure was the symmetric-init pathology, not a backward bug.
4. If gradients still look wrong, build a manual-vs-autograd direct comparison on the same input. The L2 difference between manual and autograd gradients should be exactly 0.0 if the substrate is correct.

### The Math (for the README of any test you write)

For a linear layer `y = Wx + b` with W uniformly initialized to constant `c`:

- Every column of W is identical
- Every output `y[i] = sum_k(c * x[k]) + b[i] = c * sum(x) + b[i]` — outputs differ only by bias
- After softmax, probability mass is near-uniform across classes
- Cross-entropy backward: `dL/d_logits = softmax - target` sums to exactly 0 across the class axis
- Backward through linear: `dL/dx = sum_k(dL/dy[k] * W[k, :]) = (sum dL/dy[k]) * c` because every W column is identical
- Since `sum(dL/dy) = 0`, the input gradient is **exactly zero** algebraically — only fp32 cancellation noise (~1e-8) survives
- All upstream layers (conv, etc.) see this near-zero upstream grad and produce near-zero kernel grads

The single-linear-layer case doesn't manifest because the FC layer's own grad is still nonzero (it's `dL/dy ⊗ x`, not the broken `sum(dL/dy) * c`). The pathology only shows up in multi-layer stacks where downstream layers need a nonzero `grad_input`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Initial substrate bug-hunt on autograd PR #5462 | Wrote a chained convergence test `conv → relu → flatten → linear → CE` with fcw initialized to 0.05 (uniform). Saw conv kernel grads come back at 1.7e-8 while FC grads were 0.09 | Symmetric fcw → uniform softmax → algebraically zero grad_input from FC → conv sees only fp32 noise. Cost: ~30 min misdiagnosis as "conv2d backward bug" | First step when diagnosing "substrate produces tiny gradients in stacks": rerun with asymmetric weight init before instrumenting backward kernels |
| Believed the test was "ill-conditioned" but the substrate was still likely buggy | After realizing symmetric init was the cause of the magnitude weirdness, was tempted to keep blaming the substrate because real training (with kaiming init) ALSO produced loss plateau at ln(47) | The training plateau and the test plateau had DIFFERENT root causes that happened to produce the same symptom. The training plateau was caused by an upstream batch-copy bug; the test plateau was caused by symmetric init. Same fingerprint, two bugs | When multiple symptoms point to "X is broken," verify each independently. A test failure and a production failure with similar symptoms can have different causes, especially when one of the symptoms is a pathological math case |
| Pasted `_make_tensor(shape, 0.0)` for bias and assumed it was harmless | The bias is small and not multi-channel, so I figured uniform-zero was fine | True — bias init doesn't cause the pathology because there's no symmetry to break across the bias's dimensions. The bug is specifically uniform across the *input axis* of a layer | The pathology requires uniform fill across the input dimension of a layer (so every output ends up identical). Uniform bias is fine; uniform weight matrix or kernel is not |
| Considered `_make_asymmetric(shape, 0.05, 0.0)` as a "subtle" asymmetry | Wanted to keep the init "almost uniform" to stay close to real-world Xavier/Kaiming magnitudes | slope=0.0 IS uniform — same pathology. Need actual nonzero slope | The slope must be measurably nonzero. A good rule: `slope = base / n` where n is the number of elements in the input dimension. That makes the per-element variation comparable in scale to a real random init |

## Results & Parameters

### Configuration

Default asymmetric-init recipe for autograd convergence tests:

| Layer type | base | slope | Comment |
|------------|------|-------|---------|
| Linear (out=10, in=84) — output projection | 0.005 | 0.0005 | Final classifier |
| Linear (out=120, in=256) — mid FC | 0.005 | 0.00005 | Slope scales with 1/n to keep magnitude reasonable |
| Conv2d (6, 1, 5, 5) — first conv | 0.05 | 0.003 | Larger base for first conv |
| Conv2d (16, 6, 5, 5) — second conv | 0.02 | 0.001 | Smaller base for downstream conv |

Input data should also be asymmetric — use a per-pixel ramp `base + i*slope` instead of constant fill, so conv kernels have spatial signal to lock onto.

### Expected Output

- Convergence test loss decreases monotonically from the chance baseline instead of plateauing at `ln(C)`
- Early-layer (conv/embedding) gradients come back at the same order of magnitude as later-layer gradients (no 7-orders-of-magnitude gap)
- Manual-vs-autograd L2 gradient diff is exactly 0.0 on identical input

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5466 — `tests/projectodyssey/autograd/test_autograd_convergence.mojo` `_make_asymmetric` helper. Originally hit the pathology in test 2 (loss plateau at ln(2)=0.694) which masked a separate upstream data-copy bug. Switching weights and inputs to asymmetric init made the substrate-correctness signal visible. After also fixing the upstream batch-copy bug, all 3 convergence tiers go GREEN | — |

## References

- [Symmetry breaking in neural networks](https://en.wikipedia.org/wiki/Symmetry_breaking)
- [Kaiming initialization paper](https://arxiv.org/abs/1502.01852)
