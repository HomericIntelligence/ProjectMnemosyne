---
name: batch-norm-sum-squared-loss-test
description: 'Replace trivial batch norm gradient test with sum(output^2) loss for
  real backward pass validation. Use when: upgrading ad-hoc grad_output to a principled
  closed-form loss derivative.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Problem | Gradient test uses ad-hoc non-uniform `grad_output` not derived from a real loss function |
| Root Cause | Non-uniform weights work but lack a closed-form derivative to verify correctness |
| Fix | Use `L = sum(output^2)` → `grad_output = 2 * output` + matching `forward_for_grad` |
| Applies To | Any normalization layer backward gradient check using gradient checker scaffolding |

## When to Use

1. A gradient check test constructs `grad_output` as arbitrary values (e.g. alternating pattern) rather than deriving it from a loss function
2. An issue requests "meaningful" or "non-trivial" gradient test using `sum(output^2)` loss
3. Upgrading from the `batch-norm-gradient-test-fix` approach (non-uniform weights) to a principled loss-based approach
4. You want the numerical and analytical gradients to be consistent via a well-defined loss with known closed-form derivative

## Why sum(output^2)?

- **Non-zero guarantee**: `dL/dY = 2 * output` is non-zero as long as the normalized output is non-zero (true when `gamma != 1` or `beta != 0`)
- **Closed-form derivative**: The upstream gradient is exactly `2 * output`, making the consistency check mathematically verifiable
- **Avoids cancellation**: Unlike `sum(output)` which gives `dL/dY = ones` (leading to zero gradient for zero-mean normalized outputs), squaring breaks the cancellation

## Contrast with Non-Uniform grad_output Approach

| Approach | grad_output | forward_for_grad loss | Principled? |
|----------|-------------|----------------------|-------------|
| Old (uniform) | `ones_like(output)` | `sum(output)` | Yes, but trivially zero |
| Interim (non-uniform) | Alternating `[0.5, -0.3, ...]` | `sum(output * grad_output)` | Works, but ad-hoc |
| Preferred (sum-squared) | `2 * output` | `sum(output^2)` | Yes, clean loss function |

## Verified Workflow

### 1. Import full_like

```mojo
from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like, full_like
```

### 2. Compute grad_output from loss derivative

```mojo
# Forward pass
var result6 = batch_norm2d(
    x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5
)
var output = result6[0]

# Upstream gradient for loss L = sum(output^2): dL/dY = 2 * output
var two = full_like(output, 2.0)
var grad_output = multiply(two, output)
```

### 3. Update forward_for_grad closure to use sum(out^2)

```mojo
fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var result_nested = batch_norm2d(
        inp, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5
    )
    var out = result_nested[0]
    # Loss: sum(output^2) — matches analytical grad_output = 2 * output
    var squared = multiply(out, out)
    var result = squared
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result
```

### 4. Run gradient check with appropriate tolerance

```mojo
assert_gradients_close(
    grad_input,
    numerical_grad,
    rtol=2e-2,   # 2% tolerance — appropriate for batch norm compound FP errors
    atol=1e-4,
    message="Batch norm gradient w.r.t. input (sum(output^2) loss)",
)
```

## Results & Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Loss function | `sum(output^2)` | Non-zero derivative for non-trivially normalized outputs |
| Analytical grad | `2 * output` | Closed-form derivative of sum(output^2) |
| Numerical epsilon | `1e-3` | Central finite differences, appropriate for float32 |
| rtol | `2e-2` | Batch norm has compound FP errors across normalize/scale/shift |
| atol | `1e-4` | Absolute floor for near-zero gradient elements |
| Input shape | `[2, 2, 2, 2]` | Small for O(n^2) gradient check cost |
| gamma | `[1.5, 2.0]` | Non-unit to ensure non-zero normalized outputs |

## Key Consistency Requirement

Both `grad_output` passed to `batch_norm2d_backward` AND the loss computed in `forward_for_grad`
must be derived from the **same** loss function. If they differ, the numerical and analytical
gradients will not agree even if both are correct.

| | Must use |
|---|---|
| `grad_output` | `2 * output` (derivative of sum(output^2)) |
| `forward_for_grad` return | `sum(out * out)` reduced to scalar |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Uniform `ones_like` grad_output | `grad_output = ones_like(output)`, `forward_for_grad = sum(output)` | Zero-mean batch norm gives dL/dx = 0 analytically; both gradients collapse to ~0, test trivially passes | `sum(output)` loss is pathological for zero-mean normalized layers |
| Non-uniform alternating pattern | `grad_output[i] = (i%4)*0.25 - 0.3`, `forward_for_grad = sum(output * grad_output)` | Works correctly but `grad_output` is ad-hoc, not derived from a loss — harder to explain and verify | Use a real loss function with a known derivative instead |
| `full_like` not imported | Used `full_like` without adding it to the import line | Mojo compilation error: `full_like` undefined | Add `full_like` to extensor import before using it |
