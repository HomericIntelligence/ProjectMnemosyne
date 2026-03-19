---
name: mojo-param-gradient-check
description: 'Add numerical gradient validation for learnable parameters (gamma, beta)
  in Mojo backward passes. Use when: a backward pass returns multiple gradients, only
  input gradients are tested, or adding gradient checks for normalization layer parameters.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Layer** | Normalization (batch_norm2d) |
| **Parameters tested** | grad_gamma (index 1), grad_beta (index 2) |
| **Method** | Central finite differences on the parameter tensor |
| **Tolerance** | rtol=1e-2, atol=1e-4 |
| **Epsilon** | 1e-3 |
| **Scalar reduction** | `sum(output * grad_output)` via multiply + reduce_sum loop |

## When to Use

- A `backward` function returns a tuple/list: `(grad_input, grad_gamma, grad_beta, ...)`
  and only `grad_input` is numerically validated.
- Adding gradient coverage for `gamma` (scale) and `beta` (shift) in batch/layer norm.
- After any change to the backward pass formula for parameter gradients.
- PR review reveals partial gradient coverage (only input gradient tested).

## Verified Workflow

### 1. Identify the return indices of parameter gradients

```mojo
var result_bwd = batch_norm2d_backward(grad_output, x, gamma, ...)
var grad_gamma = result_bwd[1]   # index 1
var grad_beta  = result_bwd[2]   # index 2
```

### 2. Use non-uniform grad_output

Use a non-constant `grad_output` to avoid the pathological cancellation case
where `grad_output=ones` yields analytically-zero gradients (`sum(x_norm)=0`):

```mojo
var grad_output = zeros_like(output)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = Float32(i + 1) * 0.1
```

### 3. Write forward closure perturbing the parameter

The closure must produce a scalar (or be reduced to scalar) matching
the loss `L = sum(forward(x, param, ...) * grad_output)`:

```mojo
fn forward_for_gamma(g: ExTensor) raises -> ExTensor:
    var res = batch_norm2d(x, g, beta, running_mean, running_var,
                           training=True, epsilon=1e-5)
    var out = res[0]
    var weighted = multiply(out, grad_output)
    var result = weighted
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

### 4. Call `compute_numerical_gradient` on the parameter

```mojo
var numerical_grad_gamma = compute_numerical_gradient(
    forward_for_gamma, gamma, epsilon=1e-3
)
```

### 5. Assert with `assert_gradients_close`

```mojo
assert_gradients_close(
    grad_gamma_analytical,
    numerical_grad_gamma,
    rtol=1e-2,
    atol=1e-4,
    message="Batch norm gradient w.r.t. gamma",
)
```

### 6. Add new test to `main()`

Register the new test immediately after the existing gradient input test:

```mojo
test_batch_norm2d_backward_gradient_gamma()
print("test_batch_norm2d_backward_gradient_gamma")

test_batch_norm2d_backward_gradient_beta()
print("test_batch_norm2d_backward_gradient_beta")
```

## Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `epsilon` (finite diff) | `1e-3` | Matches existing grad_input test; stable for float32 |
| `rtol` | `1e-2` (2%) | Batch norm compounding across normalize/scale/shift |
| `atol` | `1e-4` | Handles near-zero gradients in outer channels |
| Tensor shape | `(2, 2, 2, 2)` | Small enough for O(n) finite-diff cost |
| `grad_output` pattern | `Float32(i + 1) * 0.1` | Non-uniform, breaks channel symmetry |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `grad_output = ones_like(output)` | Standard all-ones upstream gradient | For batch norm, `sum(x_norm)=0` by construction, so `grad_input` is analytically zero — the test would pass vacuously even with wrong code | Always use non-uniform `grad_output` for batch norm gradient tests |
| Running mojo tests locally | `pixi run mojo test tests/...` | GLIBC version mismatch — host has GLIBC 2.31, mojo requires 2.32+ | Mojo tests only run inside the Docker container; rely on pre-commit hooks and CI for validation |
| Perturbing `x` to test `grad_gamma` | Used `compute_numerical_gradient` on `x` with the `gamma`-perturbing closure | Wrong: the numerical gradient shape would be `x.shape` not `gamma.shape` | Each parameter's gradient must be validated by perturbing that specific parameter, not the input |

## Results & Parameters

The following two test functions were added to `tests/shared/core/test_normalization.mojo`
and registered in `main()`. All pre-commit hooks passed on commit.

```mojo
# Test function signatures
fn test_batch_norm2d_backward_gradient_gamma() raises
fn test_batch_norm2d_backward_gradient_beta() raises
```

PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3807
Issue: https://github.com/HomericIntelligence/ProjectOdyssey/issues/3246
