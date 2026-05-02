---
name: batch-norm-gradient-testing
description: "Use when: (1) batch_norm backward gradient check fails with analytical ~0 vs numerical non-zero mismatch, (2) a gradient check test uses ones_like(output) as upstream gradient for a normalization layer, (3) upgrading ad-hoc non-uniform grad_output to a principled loss-based approach, (4) adding inference-mode (training=False) gradient checks for batch_norm2d_backward covering grad_gamma and grad_beta"
category: testing
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Batch Norm Gradient Testing

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated patterns for correctly designing and fixing batch normalization backward gradient tests |
| Outcome | Merged from 4 skills covering gradient analysis, test fix patterns, sum-squared loss approach, and inference-mode coverage |
| Verification | unverified |

## When to Use

- Batch norm backward test shows `analytical ≈ 0` but `numerical ≈ 0.009` mismatch
- A gradient check test is disabled with TODO: "still investigating"
- `grad_output = ones_like(output)` is used in normalization gradient checking
- Upgrading from non-uniform alternating `grad_output` to a principled `sum(output^2)` loss
- Existing gradient checks only cover `training=True` and need inference mode (`training=False`) coverage
- Issue requests validation of `grad_gamma` and `grad_beta` in inference mode
- CI shows: "Analytical: ~1e-7, Numerical: ~0.009, Tolerance: ~1e-4" for normalization backward test

## Verified Workflow

### Quick Reference

```mojo
# CORRECT: Non-uniform grad_output to avoid cancellation
var grad_output = zeros_like(output)
for i in range(output.numel()):
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    grad_output._data.bitcast[Float32]()[i] = val

# PREFERRED: Principled sum(output^2) loss
var two = full_like(output, 2.0)
var grad_output = multiply(two, output)

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var result = batch_norm2d(inp, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
    var out = result[0]
    var squared = multiply(out, out)  # L = sum(out^2)
    var r = squared
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r

assert_gradients_close(grad_input, numerical_grad, rtol=2e-2, atol=1e-4, message="...")
compute_numerical_gradient(forward_for_grad, x, epsilon=1e-3)
```

### Step 1: Understand the Pathological Cancellation

Batch normalization has a structural property: the sum of normalized values is always zero:
```
sum(x_norm) = sum((x - mean) / std) = 0
```

The PyTorch backward formula for batch norm:
```
dL/dx_i = gamma/sigma * [g_i - k/N - x_norm_i * dotp/N]
```
where `k = sum(g)` and `dotp = sum(g * x_norm)`.

**When `g = ones` (uniform gradient)**:
- `k = N`
- `dotp = sum(1 * x_norm) = sum(x_norm) = 0`
- Result: `(1 - N/N - x_norm * 0/N) * gamma/sigma = 0`

The analytical gradient is **exactly zero** — which is mathematically correct. BUT in float32, perturbing `x[i]` by ε=1e-4 causes rounding artifacts where numerical gradient ≈ 0.009. This is a **false test failure**: both are correct, but the test reports a 1000x mismatch.

### Step 2: Verify the Backward Implementation is Correct

Check the formula. PyTorch's consolidated formula (DO NOT change this):
```mojo
grad_input[i] = (grad_output[i] - k/N - x_norm[i] * dotp/N) * gamma * invstd
```
where:
- `k = sum(grad_output)`
- `dotp = sum(grad_output * x_norm)`
- `invstd = 1 / sqrt(var + eps)`

### Step 3: Fix the Test — Use sum(output^2) Loss (Preferred)

The principled approach uses `L = sum(output^2)` → `grad_output = 2 * output`:

```mojo
from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like, full_like

# Forward pass
var result = batch_norm2d(x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
var output = result[0]

# Upstream gradient for loss L = sum(output^2): dL/dY = 2 * output
var two = full_like(output, 2.0)
var grad_output = multiply(two, output)

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var result_nested = batch_norm2d(inp, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
    var out = result_nested[0]
    var squared = multiply(out, out)
    var result = squared
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

**Why `sum(output^2)`?**
- `dL/dY = 2 * output` is non-zero as long as normalized output is non-zero
- Closed-form derivative makes the test mathematically verifiable
- Avoids cancellation: squaring breaks the zero-mean symmetry

**Consistency requirement**: Both `grad_output` and `forward_for_grad` MUST derive from the same loss:
| | Must use |
|---|---|
| `grad_output` | `2 * output` (derivative of sum(output^2)) |
| `forward_for_grad` return | `sum(out * out)` reduced to scalar |

### Step 4: Alternative — Non-Uniform grad_output (Interim Approach)

If the principled approach is not yet needed, use alternating values:

```mojo
# Pattern that avoids uniform/symmetric values
var grad_output = zeros_like(output)
for i in range(output.numel()):
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    # Gives: [-0.3, -0.05, 0.2, 0.45, -0.3, -0.05, ...]
    grad_output._data.bitcast[Float32]()[i] = val

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var out = batch_norm2d(inp, ...)[0]
    var weighted = multiply(out, grad_output)
    var result = weighted
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

### Step 5: Add Inference Mode Coverage (training=False)

When adding gradient checks for `batch_norm2d_backward` in inference mode:

1. **Check existing test count**:
   ```bash
   grep -c "^fn test_" <file>.mojo
   ```

2. **Check the function signature** — `batch_norm2d_backward` requires positional `running_mean` and `running_var` with no defaults. Always match the full signature from the source.

3. **Set up non-trivial running stats**:
   ```mojo
   var running_mean = zeros(param_shape, DType.float32)
   running_mean._data.bitcast[Float32]()[0] = 0.3
   running_mean._data.bitcast[Float32]()[1] = 0.7

   var running_var = ones(param_shape, DType.float32)
   running_var._data.bitcast[Float32]()[0] = 0.5
   running_var._data.bitcast[Float32]()[1] = 1.5
   ```

4. **Use sequential (non-uniform) grad_output**:
   ```mojo
   for i in range(16):
       grad_output._data.bitcast[Float32]()[i] = Float32(i + 1) * 0.1
   ```

5. **Inference mode numerical gradient closure**:
   ```mojo
   fn forward_for_gamma_infer(g: ExTensor) raises -> ExTensor:
       var res = batch_norm2d(x, g, beta, running_mean, running_var, training=False, epsilon=1e-5)
       var out = res[0]
       var weighted = multiply(out, grad_output)
       var result = weighted
       while result.dim() > 0:
           result = reduce_sum(result, axis=0, keepdims=False)
       return result

   var numerical_grad_gamma = compute_numerical_gradient(
       forward_for_gamma_infer, gamma, epsilon=1e-3  # larger than training-mode 1e-4
   )
   ```

6. **Use appropriate tolerances for inference mode**:
   ```mojo
   assert_gradients_close(
       grad_gamma_analytical, numerical_grad_gamma,
       rtol=1e-2, atol=1e-4,
       message="Batch norm gradient w.r.t. gamma (inference mode)",
   )
   ```

### Step 6: Commit with SKIP=mojo-format if GLIBC Mismatch

```bash
git add tests/shared/core/test_normalization*.mojo
SKIP=mojo-format git commit -m "fix(backward): enable backward pass tests"
# CI runs in Docker with correct GLIBC — mojo format will run there
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `grad_output = ones_like(output)` | Uniform upstream gradient in normalization backward check | `sum(output)` loss is pathological for zero-mean normalized layers; analytical gradient is exactly zero | Never use uniform grad_output for normalization backward tests |
| Change tolerance | Increase `atol` from 1e-5 to 1e-2 for the failing test | Hides the real issue without validating correctness | Masking float32 noise doesn't test the backward |
| Fix backward formula | Modify grad_input formula to produce non-zero output for uniform grad | The formula IS correct; ~0 for uniform grad is mathematically right | Don't change correct code to pass a bad test |
| Use epsilon=1e-6 for numerical gradient | Smaller perturbation for numerical gradient | Worsens float32 rounding; analytical vs numerical gap grows | Smaller epsilon increases numerical error in float32 |
| Non-uniform alternating pattern as final solution | Used `grad_output[i] = (i%4)*0.25 - 0.3` | Works correctly but is ad-hoc, not derived from a loss function | Use a real loss function (`sum(output^2)`) with a known derivative |
| Reuse existing test pattern without running stats | Called `batch_norm2d_backward(grad_output, x, gamma, epsilon=1e-5, training=False)` | Signature requires positional `running_mean`/`running_var` — no defaults exist | Always grep the actual function signature; existing tests in same file may be broken |
| Single `epsilon=1e-4` for float32 inference | Same epsilon as training mode tests | Running stat normalization amplifies perturbation sensitivity | Float32 + fixed running stats = larger finite-diff errors; use `epsilon=1e-3` |
| `full_like` not imported | Used `full_like` without adding it to the import line | Mojo compilation error: `full_like` undefined | Add `full_like` to extensor import before using it |
| Treating numerical gradient as ground truth | Assumed numerical 0.00894 was correct, analytical 0 was wrong | `sum(batch_norm(x))` with `beta=0` is identically 0, so numerical should also be ~0 | Always verify that the numerical gradient setup is appropriate for the operation being tested |

## Results & Parameters

### Tolerance Settings

```mojo
# Training mode (non-uniform grad_output approach)
assert_gradients_close(
    grad_input, numerical_grad,
    rtol=1e-2,  # 1% relative tolerance
    atol=1e-5,
    message="...",
)
compute_numerical_gradient(forward_for_grad, x, epsilon=1e-4)

# Training mode (sum(output^2) loss)
assert_gradients_close(
    grad_input, numerical_grad,
    rtol=2e-2,  # 2% — batch norm compound FP errors
    atol=1e-4,
    message="...",
)
compute_numerical_gradient(forward_for_grad, x, epsilon=1e-3)

# Inference mode
assert_gradients_close(
    grad_gamma_analytical, numerical_grad_gamma,
    rtol=1e-2, atol=1e-4,
    message="...",
)
compute_numerical_gradient(forward_for_gamma_infer, gamma, epsilon=1e-3)
```

### Required Imports

```mojo
from shared.testing import (
    compute_numerical_gradient,
    assert_gradients_close,
)
from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like, full_like
from shared.core.normalization import batch_norm2d, batch_norm2d_backward
from shared.core.arithmetic import multiply
from shared.core.reduction import sum as reduce_sum
```

### GradientTriple vs GradientPair Field Names

```
GradientTriple (Conv2dBackwardResult):
  .grad_input   → gradient w.r.t. input x
  .grad_weights → gradient w.r.t. kernel/weights
  .grad_bias    → gradient w.r.t. bias

GradientPair (Conv2dNoBiasBackwardResult):
  .grad_a → gradient w.r.t. input x
  .grad_b → gradient w.r.t. kernel
```

### General Principle

For any normalization layer (BatchNorm, LayerNorm, GroupNorm):

> When gradient checking a normalization backward pass, NEVER use `grad_output = ones_like(output)`. The normalization property `sum(x_norm) = 0` causes perfect cancellation in the backward formula. Use `sum(output^2)` loss with `grad_output = 2 * output`, or a non-uniform gradient that produces non-zero testable gradients.
