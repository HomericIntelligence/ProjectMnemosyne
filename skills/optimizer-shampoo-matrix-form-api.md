---
name: optimizer-shampoo-matrix-form-api
description: "Use when: (1) implementing the matrix-form Shampoo optimizer (Anil et al. 2020) in Mojo, (2) calling shampoo_step or initialize_shampoo_state from projectodyssey.training.optimizers.shampoo, (3) wiring a mixed optimizer (Shampoo for rank-2 FC weight matrices, SGD/Lion fallback for conv kernels and biases), (4) adding per-parameter state buffers to a Mojo model struct for Shampoo-eligible parameters, (5) debugging wrong arity or wrong tuple-unpack errors from shampoo_step."
category: optimization
date: 2026-06-19
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - optimizer
  - shampoo
  - preconditioner
  - matrix-form
  - second-order
  - mixed-optimizer
  - anytensor
  - fc-layers
  - newton-schulz
---

# Matrix-Form Shampoo Optimizer API (Mojo)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Category** | optimization |
| **Language** | Mojo v1.0.0b2 |
| **Objective** | Canonical reference for calling the ProjectOdyssey matrix-form Shampoo optimizer correctly, including state initialization, per-step invocation, mixed-optimizer wiring, and model struct field layout |
| **Outcome** | Operational — verified-precommit (PR #5500 in flight) |
| **Verification** | verified-precommit |
| **Source file** | `src/projectodyssey/training/optimizers/shampoo.mojo` |

## When to Use

Use this skill when working with the Shampoo optimizer in ProjectOdyssey and any of these apply:

1. Implementing Shampoo (Anil et al. 2020) on FC weight matrices in a Mojo model
2. Calling `shampoo_step`, `shampoo_step_simple`, `initialize_shampoo_state`, or
   `is_shampoo_eligible` from the optimizers package
3. Designing a mixed optimizer where FC weights use Shampoo and conv kernels / biases use SGD or Lion
4. Adding per-parameter preconditioner state to a Mojo model struct
5. Getting a compile error about wrong number of return values or wrong tuple indexing from
   `shampoo_step`

Do NOT use when:

- The target parameter is a bias vector or conv kernel — use SGD/Lion for those (not Shampoo-eligible)
- The model has no rank-2 weight matrices (e.g., embedding-only or conv-only architectures)
- You need scalar-learning-rate-only optimizers with no second-order information

## Verified Workflow

### Quick Reference

| Task | Key Action |
| ---- | ---------- |
| Check eligibility | `is_shampoo_eligible(params)` — True only for rank-2, both dims ≥ 2 |
| Initialize state | `initialize_shampoo_state(params)` — returns 3-tuple `(L, R, momentum)` |
| Per-step update | `shampoo_step(params, grads, L, R, momentum, lr)` — returns 4-tuple |
| Unpack step result | `result[0]` params, `result[1]` L, `result[2]` R, `result[3]` momentum |
| Conv kernels (rank-4) | NOT eligible — use `sgd_step_simple(params, grads, lr)` |
| Bias vectors (rank-1) | NOT eligible — use `sgd_step_simple(params, grads, lr)` |
| Model struct layout | 4 fields per FC weight: `weights`, `weights_L`, `weights_R`, `weights_m` |
| Preconditioner algorithm | Newton-Schulz inverse fourth root (NOT a single Hessian matrix) |

```mojo
# Correct import
from projectodyssey.training.optimizers.shampoo import (
    shampoo_step, initialize_shampoo_state, is_shampoo_eligible
)
from projectodyssey.training.optimizers.sgd import sgd_step_simple
```

### Detailed Steps

#### A. Eligibility Check

`is_shampoo_eligible(params: AnyTensor) -> Bool` returns `True` only when:

- `params.rank() == 2`
- Both dimensions are ≥ 2

FC weight matrices (e.g., `[120, 256]`) are eligible. Everything else is NOT:

- Bias vectors (rank-1): `[120]` → False
- Conv2d kernels (rank-4): `[32, 1, 5, 5]` → False
- Embedding tables (rank-2 but may be huge) → True (eligible by API, but consider memory cost)

#### B. State Initialization

Call once before the training loop:

```mojo
# For a weight matrix of shape [m, n]:
var state = initialize_shampoo_state(params)
var L = state[0]        # AnyTensor shape [m, m] — identity matrix
var R = state[1]        # AnyTensor shape [n, n] — identity matrix
var momentum = state[2] # AnyTensor shape [m, n] — zeros
```

The function allocates two square identity matrices (one per dimension) plus a zero-filled
momentum buffer of the same shape as the parameter.

#### C. Per-Step Invocation

```mojo
# shampoo_step signature (5 state args + learning rate):
var result = shampoo_step(
    params,      # AnyTensor [m, n]  — current weights
    gradients,   # AnyTensor [m, n]  — gradient from backward pass
    L,           # AnyTensor [m, m]  — left preconditioner
    R,           # AnyTensor [n, n]  — right preconditioner
    momentum,    # AnyTensor [m, n]  — momentum buffer
    learning_rate  # Float64
)

# Unpack 4-tuple — ALWAYS update all four fields
params   = result[0]   # AnyTensor [m, n]  — updated weights
L        = result[1]   # AnyTensor [m, m]  — updated left preconditioner
R        = result[2]   # AnyTensor [n, n]  — updated right preconditioner
momentum = result[3]   # AnyTensor [m, n]  — updated momentum
```

`shampoo_step_simple` has the same signature and the same 4-tuple return — the "simple" suffix
does NOT imply a shorter return tuple (unlike `lion_step_simple`).

#### D. Model Struct Field Layout

For each Shampoo-eligible FC weight matrix, declare **four** fields in the model struct:

```mojo
struct MyModel:
    var fc1_weights: AnyTensor   # [120, 256] — the weight matrix
    var fc1_weights_L: AnyTensor # [120, 120] — left preconditioner
    var fc1_weights_R: AnyTensor # [256, 256] — right preconditioner
    var fc1_weights_m: AnyTensor # [120, 256] — momentum buffer

    var fc1_bias: AnyTensor      # [120] — bias (rank-1, NOT eligible)
    var conv1_weights: AnyTensor # [32,1,5,5] — conv kernel (rank-4, NOT eligible)
```

Initialize Shampoo state in the model constructor:

```mojo
fn __init__(out self) raises:
    self.fc1_weights = he_init([120, 256])
    var s1 = initialize_shampoo_state(self.fc1_weights)
    self.fc1_weights_L = s1[0]
    self.fc1_weights_R = s1[1]
    self.fc1_weights_m = s1[2]

    self.fc1_bias = zeros([120], DType.float64)
    self.conv1_weights = he_init([32, 1, 5, 5])
```

#### E. Mixed-Optimizer Training Loop

```mojo
# FC weight matrices — Shampoo
var fc1_res = shampoo_step(
    model.fc1_weights, fc1_grads.grad_weights,
    model.fc1_weights_L, model.fc1_weights_R, model.fc1_weights_m,
    lr64
)
model.fc1_weights   = fc1_res[0]
model.fc1_weights_L = fc1_res[1]
model.fc1_weights_R = fc1_res[2]
model.fc1_weights_m = fc1_res[3]

# Bias vectors — SGD fallback (rank-1, not Shampoo-eligible)
model.fc1_bias = sgd_step_simple(model.fc1_bias, fc1_grads.grad_bias, lr64)

# Conv kernels — SGD fallback (rank-4, not Shampoo-eligible)
model.conv1_weights = sgd_step_simple(
    model.conv1_weights, conv1_grads.grad_weights, lr64
)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Single-matrix Hessian call | Called `shampoo_step(params, grads, H, t, lr)` with one Hessian and a step counter | Shampoo requires two separate preconditioner matrices (L for rows, R for cols) — not a single Hessian | Matrix-form Shampoo ALWAYS has two preconditioners; the API takes L and R as independent args |
| Single momentum buffer per parameter | Model struct had only `_m` (momentum) field per parameter; missing `_L` and `_R` | FC weight matrices need THREE state buffers: L [m,m], R [n,n], AND momentum [m,n] | Declare four fields per eligible param: `weights`, `weights_L`, `weights_R`, `weights_m` |
| Assumed "simple" means 2-tuple return | Tried to unpack `shampoo_step_simple` as `(new_params, extra)` like `lion_step_simple` | `shampoo_step_simple` returns a 4-tuple identical to `shampoo_step` — the "simple" suffix refers to the update rule, not the return arity | Always unpack Shampoo step results as a 4-tuple regardless of which variant is used |
| Applying Shampoo to conv kernels | Called `shampoo_step` on a rank-4 conv weight | `is_shampoo_eligible` returns False for rank != 2; the function will fail or produce wrong shapes | Check eligibility first; conv kernels and bias vectors must use SGD/Lion fallback |
| Forgetting to update L and R | Only wrote back `result[0]` (params) and `result[3]` (momentum) | Stale L and R preconditioners cause the optimizer to degrade to momentum SGD over time | Always unpack and reassign all four elements of the result tuple on every step |

## Results & Parameters

### Shampoo State Shapes

Given a weight matrix `params` with shape `[m, n]`:

| Buffer | Shape | Initialized As |
| ------ | ----- | -------------- |
| `L` (left preconditioner) | `[m, m]` | Identity matrix |
| `R` (right preconditioner) | `[n, n]` | Identity matrix |
| `momentum` | `[m, n]` | Zeros |

### Eligibility Matrix

| Parameter Type | Shape | Eligible | Fallback Optimizer |
| -------------- | ----- | -------- | ------------------ |
| FC weight matrix | `[out, in]` | Yes | — |
| FC bias | `[out]` | No | `sgd_step_simple` |
| Conv2d kernel | `[out_ch, in_ch, kH, kW]` | No | `sgd_step_simple` |
| Depthwise conv kernel | `[ch, 1, kH, kW]` | No | `sgd_step_simple` |
| Embedding table | `[vocab, dim]` | Yes (by API) | Consider memory cost |

### Function Signatures

```mojo
# Initialize Shampoo state for a rank-2 parameter
fn initialize_shampoo_state(params: AnyTensor) raises -> (AnyTensor, AnyTensor, AnyTensor)

# Check if a tensor is eligible for Shampoo (rank-2, both dims >= 2)
fn is_shampoo_eligible(params: AnyTensor) -> Bool

# Perform one Shampoo update step — returns (new_params, new_L, new_R, new_momentum)
fn shampoo_step(
    params: AnyTensor,
    gradients: AnyTensor,
    L: AnyTensor,
    R: AnyTensor,
    momentum: AnyTensor,
    learning_rate: Float64,
) raises -> (AnyTensor, AnyTensor, AnyTensor, AnyTensor)

# Simplified update rule — SAME 4-tuple return as shampoo_step
fn shampoo_step_simple(
    params: AnyTensor,
    gradients: AnyTensor,
    L: AnyTensor,
    R: AnyTensor,
    momentum: AnyTensor,
    learning_rate: Float64,
) raises -> (AnyTensor, AnyTensor, AnyTensor, AnyTensor)
```

### Algorithm Note

The preconditioner update uses the Newton-Schulz inverse fourth root, NOT a direct matrix inverse.
The left preconditioner `L` approximates `(G G^T)^{-1/4}` and the right preconditioner `R`
approximates `(G^T G)^{-1/4}`, where `G` is the gradient matrix. This is consistent with
Anil et al. (2020) "Scalable Second Order Optimization for Deep Learning".

### Required Imports

```mojo
from projectodyssey.training.optimizers.shampoo import (
    shampoo_step,
    shampoo_step_simple,
    initialize_shampoo_state,
    is_shampoo_eligible,
)
from projectodyssey.training.optimizers.sgd import sgd_step_simple
from projectodyssey.core.any_tensor import AnyTensor, zeros
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5451 — Shampoo optimizer implementation; PR #5500 | Matrix-form Shampoo for FC layers in LeNet-style model; mixed optimizer (Shampoo + SGD); pre-commit hooks passing |

## References

- Anil et al. (2020) "Scalable Second Order Optimization for Deep Learning": <https://arxiv.org/abs/2002.09018>
- Source implementation: `src/projectodyssey/training/optimizers/shampoo.mojo`
- Related skill: [normuon-optimizer-patterns](normuon-optimizer-patterns.md) (pure functional optimizer design)
