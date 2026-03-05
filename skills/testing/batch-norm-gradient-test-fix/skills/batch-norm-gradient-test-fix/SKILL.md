---
name: batch-norm-gradient-test-fix
description: "Fix batch norm backward gradient tests failing with uniform upstream gradients. Use when: batch_norm_backward gradient check fails with analytical~=0 but numerical!=0 due to sum(x_norm)=0 cancellation."
category: testing
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Problem | `test_batch_norm2d_backward_gradient_input` fails: Analytical ~0, Numerical ~0.009 |
| Root Cause | Using `grad_output = ones_like(output)` causes analytical gradient to cancel to exactly zero |
| Fix | Use non-uniform `grad_output` and compute weighted sum in `forward_for_grad` |
| Applies To | Any normalization layer backward pass using gradient checking |

## When to Use

1. Batch norm (or layer norm) backward gradient check fails with near-zero analytical but non-zero numerical
2. CI shows: "Analytical: ~1e-7, Numerical: ~0.009, Tolerance: ~1e-4" for normalization backward test
3. After un-skipping a normalization backward test that was previously commented out
4. When `grad_output = ones_like(output)` is used in normalization gradient checking

## The Pathological Cancellation Problem

Batch normalization has a structural property: the sum of normalized values is always zero:

```
sum(x_norm) = sum((x - mean) / std) = 0
```

The PyTorch backward formula for batch norm is:
```
dL/dx_i = gamma/sigma * [g_i - k/N - x_norm_i * dotp/N]
```
where `k = sum(g)` and `dotp = sum(g * x_norm)`.

**When `g = ones` (uniform gradient)**:
- `k = N`
- `dotp = sum(1 * x_norm) = sum(x_norm) = 0`
- Result: `(1 - N/N - x_norm * 0/N) * gamma/sigma = 0`

The **analytical gradient is exactly zero** — which is mathematically correct.

BUT in float32, the forward pass has rounding errors that make `sum(x_norm) ≠ 0` exactly.
When you perturb `x[i]` by ε=1e-4 for the numerical gradient:
- The mean shifts slightly: `delta_mean = ε/N`
- The variance shifts
- Floating-point cancellation is incomplete
- Numerical gradient ≈ 0.009 (not 0)

This creates a **false test failure**: both implementations are correct, but the test
incorrectly reports a 1000x mismatch.

## Verified Workflow

### Step 1: Diagnose the failure pattern

Look for this signature in CI logs:
```
Analytical: -3.62789904784222e-07
Numerical:  0.008940696716308594
Difference: 0.008941059506213378
Tolerance:  9.940696716308594e-05
```

Analytical is near-zero (correct!), Numerical is non-zero (float32 rounding artifact).

### Step 2: Verify the backward implementation is correct

Check the formula. PyTorch's consolidated formula:
```mojo
grad_input[i] = (grad_output[i] - k/N - x_norm[i] * dotp/N) * gamma * invstd
```
where:
- `k = sum(grad_output)`
- `dotp = sum(grad_output * x_norm)`
- `invstd = 1 / sqrt(var + eps)`

This is the correct formula — DO NOT change the backward implementation.

### Step 3: Fix the test

Replace `grad_output = ones_like(output)` with a non-uniform gradient:

```mojo
# BEFORE (pathological - causes cancellation):
var grad_output = ones_like(output)

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var out = batch_norm2d(inp, ...)[0]
    var result = out
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

```mojo
# AFTER (correct - non-uniform gradient breaks symmetry):
var grad_output = zeros_like(output)
for i in range(output.numel()):
    # Pattern that avoids uniform/symmetric values
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    grad_output._data.bitcast[Float32]()[i] = val

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var out = batch_norm2d(inp, ...)[0]
    # Compute weighted sum matching our non-uniform grad_output
    var weighted = multiply(out, grad_output)
    var result = weighted
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

The `forward_for_grad` must compute `sum(output * grad_output)` (weighted sum)
so the numerical gradient matches `dL/dx` with `dL/d(output) = grad_output`.

### Step 4: Verify the fix works

With non-uniform `grad_output`:
- `k = sum(grad_output) ≠ N` (breaks cancellation)
- `dotp = sum(grad_output * x_norm) ≠ 0` (breaks cancellation)
- `grad_input[i]` is genuinely non-zero
- Numerical gradient matches analytical (both ~same non-zero values)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Change tolerance | Increase `atol` from 1e-5 to 1e-2 | Hides the real issue without validating correctness | Masking float32 noise doesn't test the backward |
| Fix backward formula | Modify the grad_input formula to produce non-zero output for uniform grad | The formula IS correct; ~0 for uniform grad is mathematically right | Don't change correct code to pass a bad test |
| Use epsilon=1e-6 | Smaller perturbation for numerical gradient | Worsens float32 rounding; analytical vs numerical gap grows | Smaller epsilon increases numerical error in float32 |
| Debug forward pass | Investigate why sum(x_norm) ≠ 0 | Float32 accumulation error is inherent; fixing it would require float64 | Accept float32 precision limits; design tests that avoid pathological cases |

## Results & Parameters

### Working Test Configuration

```mojo
# Grad output pattern that avoids cancellation
var grad_output = zeros_like(output)
for i in range(output.numel()):
    var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
    # This gives: [-0.3, -0.05, 0.2, 0.45, -0.3, -0.05, ...]
    grad_output._data.bitcast[Float32]()[i] = val
```

### Tolerance Settings

```mojo
assert_gradients_close(
    grad_input,
    numerical_grad,
    rtol=1e-2,   # 1% relative tolerance (appropriate for float32 batch norm)
    atol=1e-5,   # absolute tolerance
    message="Batch norm gradient w.r.t. input",
)
```

### Key Numbers

- Shape: (2, 2, 2, 2) — small enough for O(n²) gradient checking
- Epsilon for numerical gradient: 1e-4 (optimal for float32)
- Expected analytical gradient magnitude: ~0.01-0.1 (non-trivially non-zero)

## General Principle

**For any normalization layer (BatchNorm, LayerNorm, GroupNorm):**

> When gradient checking a normalization backward pass, NEVER use `grad_output = ones_like(output)` as the upstream gradient. The normalization property `sum(x_norm) = 0` causes perfect cancellation in the backward formula, making the test insensitive to implementation errors.

Instead, use a non-uniform gradient that produces non-zero testable gradients, and ensure `forward_for_grad` computes `sum(output * grad_output)` (not just `sum(output)`).
