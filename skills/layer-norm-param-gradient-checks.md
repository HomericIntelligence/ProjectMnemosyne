---
name: layer-norm-param-gradient-checks
description: 'Add numerical gradient checks for layer_norm_backward grad_gamma and
  grad_beta using central finite differences. Use when: layer norm backward pass lacks
  parameter gradient validation, extending batch_norm gradient check pattern to layer
  norm, or validating result[1] and result[2] of layer_norm_backward.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Layer** | Layer Normalization (`layer_norm_backward`) |
| **Parameters tested** | `grad_gamma` (index 1), `grad_beta` (index 2) |
| **Method** | Central finite differences on the parameter tensor |
| **Tolerance** | `rtol=1e-2`, `atol=1e-4` |
| **Epsilon** | `1e-4` (finer than batch norm's `1e-3` due to layer norm's per-sample normalization) |
| **Scalar reduction** | `sum(output * grad_output)` via `multiply` + `reduce_sum` loop |
| **Input shape** | `(batch=2, features=4)` — small 2D tensor |
| **Param shape** | `(4,)` — one value per feature |
| **Issue** | #3810 (follow-up from #3246) |

## When to Use

- `layer_norm_backward` returns `(grad_input, grad_gamma, grad_beta)` but only `grad_input` is
  numerically validated.
- Issue asks to mirror batch_norm parameter gradient check pattern for layer norm.
- PR review reveals partial gradient coverage: `test_layer_norm_backward_gradient_input` exists
  but `test_layer_norm_backward_gradient_gamma` and `test_layer_norm_backward_gradient_beta` do not.
- Adding gradient coverage to `test_normalization.mojo` after batch norm gradient checks.

## Verified Workflow

### Quick Reference

| Step | Action |
| ------ | -------- |
| 1 | Locate `test_layer_norm_backward_gradient_input` in test file |
| 2 | Add `test_layer_norm_backward_gradient_gamma` extracting `result[1]` |
| 3 | Add `test_layer_norm_backward_gradient_beta` extracting `result[2]` with non-zero beta |
| 4 | Register both in `fn main()` after existing layer norm backward tests |
| 5 | Commit and push; create PR with `Closes #<issue>` |

### 1. Understand the backward function signature

`layer_norm_backward(grad_output, x, gamma, epsilon)` returns a tuple:

- `result[0]` — `grad_input` (already tested)
- `result[1]` — `grad_gamma` (add test)
- `result[2]` — `grad_beta` (add test)

### 2. Add `test_layer_norm_backward_gradient_gamma`

The closure perturbs `gamma`; `x`, `beta`, and `grad_output` are captured from the outer scope.

```mojo
fn test_layer_norm_backward_gradient_gamma() raises:
    """Test layer_norm_backward gradient w.r.t. gamma using numerical validation."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(4)

    var x = zeros(shape, DType.float32)
    for i in range(8):
        x._data.bitcast[Float32]()[i] = Float32(i) * 0.1 + 0.05

    var param_shape = List[Int]()
    param_shape.append(4)
    var gamma = ones(param_shape, DType.float32)
    gamma._data.bitcast[Float32]()[0] = 1.5
    gamma._data.bitcast[Float32]()[1] = 0.8
    gamma._data.bitcast[Float32]()[2] = 1.2
    gamma._data.bitcast[Float32]()[3] = 2.0
    var beta = zeros(param_shape, DType.float32)

    # Non-uniform grad_output: prevents algebraic cancellation (sum(x_hat)=0 per sample)
    var grad_output = zeros(shape, DType.float32)
    grad_output._data.bitcast[Float32]()[0] = 0.3
    grad_output._data.bitcast[Float32]()[1] = -0.5
    grad_output._data.bitcast[Float32]()[2] = 1.2
    grad_output._data.bitcast[Float32]()[3] = -0.8
    grad_output._data.bitcast[Float32]()[4] = 0.7
    grad_output._data.bitcast[Float32]()[5] = -0.2
    grad_output._data.bitcast[Float32]()[6] = 0.9
    grad_output._data.bitcast[Float32]()[7] = -1.1

    var result = layer_norm_backward(grad_output, x, gamma, epsilon=1e-5)
    var grad_gamma_analytical = result[1]

    fn forward_for_gamma(g: ExTensor) raises -> ExTensor:
        var out = layer_norm(x, g, beta, epsilon=1e-5)
        var weighted = multiply(out, grad_output)
        var result_inner = weighted
        while result_inner.dim() > 0:
            result_inner = reduce_sum(result_inner, axis=0, keepdims=False)
        return result_inner

    var numerical_grad_gamma = compute_numerical_gradient(
        forward_for_gamma, gamma, epsilon=1e-4
    )

    assert_gradients_close(
        grad_gamma_analytical,
        numerical_grad_gamma,
        rtol=1e-2,
        atol=1e-4,
        message="Layer norm gradient w.r.t. gamma",
    )
    print("✓ Layer norm backward gradient (gamma) validated numerically")
```

### 3. Add `test_layer_norm_backward_gradient_beta`

The closure perturbs `beta`. Use non-zero beta values to verify the additive shift path.

```mojo
fn test_layer_norm_backward_gradient_beta() raises:
    """Test layer_norm_backward gradient w.r.t. beta using numerical validation."""
    # ... same x, gamma, grad_output setup as gamma test ...

    var beta = zeros(param_shape, DType.float32)
    beta._data.bitcast[Float32]()[0] = 0.5
    beta._data.bitcast[Float32]()[1] = -0.3
    beta._data.bitcast[Float32]()[2] = 0.2
    beta._data.bitcast[Float32]()[3] = -0.1

    var result = layer_norm_backward(grad_output, x, gamma, epsilon=1e-5)
    var grad_beta_analytical = result[2]

    fn forward_for_beta(b: ExTensor) raises -> ExTensor:
        var out = layer_norm(x, gamma, b, epsilon=1e-5)
        var weighted = multiply(out, grad_output)
        var result_inner = weighted
        while result_inner.dim() > 0:
            result_inner = reduce_sum(result_inner, axis=0, keepdims=False)
        return result_inner

    var numerical_grad_beta = compute_numerical_gradient(
        forward_for_beta, beta, epsilon=1e-4
    )

    assert_gradients_close(
        grad_beta_analytical,
        numerical_grad_beta,
        rtol=1e-2,
        atol=1e-4,
        message="Layer norm gradient w.r.t. beta",
    )
    print("✓ Layer norm backward gradient (beta) validated numerically")
```

### 4. Register in `fn main()`

Add after `test_layer_norm_backward_gradient_input`:

```mojo
    test_layer_norm_backward_gradient_gamma()
    print("✓ test_layer_norm_backward_gradient_gamma")

    test_layer_norm_backward_gradient_beta()
    print("✓ test_layer_norm_backward_gradient_beta")
```

### 5. Key differences from batch norm parameter checks

| Aspect | Batch Norm | Layer Norm |
| -------- | ------------ | ------------ |
| `epsilon` for finite diff | `1e-3` | `1e-4` (finer) |
| Normalization axis | Per-channel (C) | Per-sample (last N dims) |
| `beta` in forward closure | Required to check `grad_beta` | Required to check `grad_beta` |
| Result indices | `result[1]`, `result[2]` | `result[1]`, `result[2]` (same) |
| Training/inference flag | Required (`training=True/False`) | Not applicable |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Reuse batch norm epsilon `1e-3` | Used same finite diff epsilon as batch norm param checks | Would work, but `1e-4` gives tighter numerical agreement for layer norm's per-sample normalization | Prefer finer epsilon for layer norm to get better agreement |
| Zero beta in beta test | Used `beta = zeros(...)` without setting non-zero values | Beta gradient is `sum(grad_output)` and doesn't depend on beta values — still validates correctly, but non-zero beta documents intent | Use non-zero beta to signal the test exercises the additive shift path |
| Reusing same grad_output pattern as grad_input test | Copied the same non-uniform values `[0.3, -0.5, 1.2, -0.8, 0.7, -0.2, 0.9, -1.1]` | Works correctly — same values are valid since the closure fixes the parameter being perturbed | Non-uniform grad_output is the key property; exact values don't matter as long as they aren't uniform or all-zeros |

## Results & Parameters

```text
Test file: tests/shared/core/test_normalization.mojo
Functions added: 2
  - test_layer_norm_backward_gradient_gamma
  - test_layer_norm_backward_gradient_beta
main() calls added: 2

Tolerances: rtol=1e-2, atol=1e-4
Finite diff epsilon: 1e-4
Input shape: (2, 4)
Param shape: (4,)
grad_output: non-uniform, 8 distinct values

PR: #4806
Issue: #3810 (follow-up from #3246)
Pattern reference: skills/testing/mojo-param-gradient-check (batch norm)
```
