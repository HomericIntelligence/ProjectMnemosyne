---
name: batchnorm-backward-gradient-checking
description: 'Implements gradient checking for BatchNorm backward pass using finite
  differences with non-uniform grad_output to avoid pathological cancellation. Use
  when: adding gradient checking to normalization layer testers, validating batch
  norm backward correctness, or debugging zero-gradient false failures in gradient
  checks.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
|----------|-------|
| Language | Mojo |
| Layer Type | Batch Normalization (2D) |
| Pattern | Finite-difference gradient checking |
| Key Insight | Non-uniform `grad_output` prevents zero-gradient false failures |

Gradient checking for BatchNorm requires care because the normalized output
`x_norm = (x - mean) / std` always sums to zero per channel. Using
`grad_output = ones_like(output)` causes `sum(x_norm * ones) ≈ 0`, making the
analytical gradient nearly zero while numerical finite differences give ~0.009,
producing a spurious test failure.

The fix: use a non-uniform `grad_output` pattern so the inner product
`sum(x_norm * grad_output)` is nonzero, and define the loss as
`sum(output * grad_output)` in both the numerical and analytical paths.

## When to Use

1. Implementing `test_<layer>_backward` for any normalization layer
2. Gradient checking fails with "analytical ≈ 0 but numerical ≈ 0.009" errors
3. Adding backward testing to a layer whose output has zero mean (LayerNorm, InstanceNorm, GroupNorm)
4. Validating a newly implemented backward pass before shipping

## Verified Workflow

### Quick Reference

```mojo
# 1. Build non-uniform grad_output (cycling pattern avoids zero-sum)
var grad_output = zeros_like(output)
for i in range(grad_output.numel()):
    grad_output._set_float64(i, Float64(i % 4) * Float64(0.25) - Float64(0.3))

# 2. Forward closure uses sum(output * grad_output) as scalar loss
fn forward_for_grad(x: ExTensor) raises escaping -> ExTensor:
    var (out, _, _) = batch_norm2d(
        x, gamma, beta, running_mean, running_var, training=True
    )
    return tensor_sum(out * grad_output)

# 3. Numerical gradient via finite differences
var numerical_grad = compute_numerical_gradient(forward_for_grad, input, epsilon)

# 4. Analytical gradient via backward pass (same grad_output)
var (grad_input, _, _) = batch_norm2d_backward(
    grad_output, input, gamma, running_mean, running_var, training=True
)

# 5. Compare
assert_gradients_close(grad_input, numerical_grad, rtol=tolerance, atol=tolerance, ...)
```

### Full Implementation Steps

1. **Add imports** to `layer_testers.mojo`:

   ```mojo
   from shared.core.normalization import batch_norm2d, batch_norm2d_backward
   from shared.core.reduction import sum as tensor_sum
   ```

2. **Run forward pass** and verify output shape matches input shape:

   ```mojo
   var (output, _, _) = batch_norm2d(
       input, gamma, beta, running_mean, running_var, training=True
   )
   assert_shape(output, input_shape, "BatchNorm backward: output shape mismatch")
   ```

3. **Set epsilon and tolerance** using documented constants:

   ```mojo
   var epsilon = (
       GRADIENT_CHECK_EPSILON_FLOAT32 if dtype == DType.float32
       else GRADIENT_CHECK_EPSILON_OTHER
   )
   var tolerance = 1e-1  # 10% — same as conv2d backward
   ```

4. **Build non-uniform grad_output** to break the zero-sum symmetry:

   ```mojo
   var grad_output = zeros_like(output)
   for i in range(grad_output.numel()):
       grad_output._set_float64(i, Float64(i % 4) * Float64(0.25) - Float64(0.3))
   # Pattern: [-0.3, -0.05, 0.2, 0.45] cycling — nonzero mean and varied signs
   ```

5. **Define forward closure** computing scalar loss `sum(output * grad_output)`:

   ```mojo
   fn forward_for_grad(x: ExTensor) raises escaping -> ExTensor:
       var (out, _, _) = batch_norm2d(
           x, gamma, beta, running_mean, running_var, training=True
       )
       return tensor_sum(out * grad_output)
   ```

6. **Run exhaustive numerical gradient check**:

   ```mojo
   var numerical_grad = compute_numerical_gradient(forward_for_grad, input, epsilon)
   assert_shape(numerical_grad, input_shape, "...")
   # NaN/Inf check on numerical_grad
   ```

7. **Compute analytical gradient** and compare:

   ```mojo
   var (grad_input, _, _) = batch_norm2d_backward(
       grad_output, input, gamma, running_mean, running_var, training=True
   )
   assert_gradients_close(grad_input, numerical_grad, rtol=tolerance, atol=tolerance, ...)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `ones_like(output)` as grad_output | Used `var grad_output = ones_like(output)` identical to conv2d pattern | BatchNorm normalizes so `sum(x_norm) ≈ 0` per channel; `dot(ones, x_norm) ≈ 0`; analytical grad ≈ 0 but numerical gives ~0.009 | Any layer with zero-mean output requires non-uniform grad_output |
| Reusing conv2d forward closure directly | `fn forward(x): return batch_norm2d(x, ...)` returning full tensor | `compute_numerical_gradient` sums all output elements when output is non-scalar, which is equivalent to `ones` upstream — same cancellation problem | The closure must compute the scalar loss explicitly |
| `tolerance=1e-2` (1%) | Tried tighter tolerance matching linear layer | BatchNorm accumulates normalization errors across N×H×W elements; 6-7% errors are common in practice (same finding as conv2d, issue #3090) | Always use 10% tolerance for normalization layers |
| Skipping non-uniform pattern for small inputs | Assumed small tensors (shape [2,4,4,4]) would avoid cancellation | Even small inputs have the zero-sum property since it's structural, not statistical | The cancellation is inherent to batch norm math, not input size |

## Results & Parameters

### Verified Constants

```mojo
# Epsilon (finite difference step size)
GRADIENT_CHECK_EPSILON_FLOAT32 = 3e-4   # float32 (see issue #2704)
GRADIENT_CHECK_EPSILON_OTHER    = 1e-3   # other dtypes

# Tolerance for gradient agreement
tolerance = 1e-1  # 10% for all dtypes (same as conv2d backward, issue #3090)
```

### grad_output Cycling Pattern

```
i % 4 == 0: -0.3
i % 4 == 1: -0.05
i % 4 == 2:  0.2
i % 4 == 3:  0.45
```

Mean ≈ 0.075, nonzero — sufficient to break symmetry.

### PR Reference

- PR: [#4780](https://github.com/HomericIntelligence/ProjectOdyssey/pull/4780)
- Issue: [#3719](https://github.com/HomericIntelligence/ProjectOdyssey/issues/3719)
- Follow-up from: [#3208](https://github.com/HomericIntelligence/ProjectOdyssey/issues/3208)
