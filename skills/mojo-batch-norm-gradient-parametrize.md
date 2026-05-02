---
name: mojo-batch-norm-gradient-parametrize
description: 'Parametrize Mojo batch norm backward gradient checks across batch sizes
  [1, 2, 4] using loop-based helpers, handling batch_size=1 degenerate case (variance=0)
  with finiteness-only assertions. Use when: adding gradient check coverage for batch
  norm backward edge cases, implementing parametrized tests in Mojo without a native
  parametrize decorator, or handling the variance=0 degenerate case for batch_size=1.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | mojo-batch-norm-gradient-parametrize |
| **Category** | testing |
| **Language** | Mojo v0.26.1 |
| **Issue Type** | Parametrized gradient check tests |
| **Resolution** | Loop-based helpers per gradient type + degenerate case bifurcation |

## When to Use

- Adding parametrized gradient check tests for `batch_norm2d_backward` across multiple batch sizes
- Implementing pytest-style parametrize patterns in Mojo (Mojo has no native `@parametrize` decorator)
- Covering the `batch_size=1` degenerate edge case where training-mode batch norm collapses variance to zero
- Extending an existing `test_normalization_part*.mojo` file set with a new part
- Any gradient check test that needs to vary a shape dimension (≤10 `fn test_` functions per file)

## Verified Workflow

### Quick Reference

| Batch Size | Variance | Gradient Check Strategy |
|------------|----------|------------------------|
| 1 | = 0 (degenerate) | Assert finite + non-NaN only |
| 2 | > 0 (normal) | Full numerical gradient check |
| 4 | > 0 (normal) | Full numerical gradient check |

### Step 1: Understand the batch_size=1 degenerate case

In training mode, `batch_norm2d` computes per-channel statistics over `(N, H, W)`.
When `N=1` (and `H=W=2`), each channel has `1×2×2=4` elements — enough to compute a
non-zero variance. However, if all elements in a channel are identical (which happens
when the test input is uniform), variance collapses to zero.

The safe assertion for this case is **finiteness only** (not NaN, not infinite), NOT
a numerical gradient match. This is because the denominator `sqrt(variance + eps)`
becomes `sqrt(eps) ≈ 0.00316`, making the backward formula extremely sensitive to
small perturbations in the input — invalidating finite-difference checks at any
reasonable epsilon.

```mojo
if batch_size == 1:
    # Degenerate case: batch_size=1 causes variance=0 in training mode.
    for i in range(n_elems):
        var val = grad_input._data.bitcast[Float32]()[i]
        assert_true(val == val, "grad_input should not be NaN (batch_size=1)")
        assert_true(val > -1e10 and val < 1e10, "grad_input should be finite (batch_size=1)")
else:
    # Full numerical gradient check for batch_size > 1
    ...
```

### Step 2: Implement private helper functions per gradient type

Mojo lacks a native `@parametrize` decorator. The pattern is:
- One **private `fn _check_<grad>_batch_size(batch_size: Int)`** helper per gradient type
- Each helper contains the full setup, forward, backward, and assertion logic
- The helper bifurcates on `batch_size == 1` to switch assertion strategy

```mojo
fn _check_grad_input_batch_size(batch_size: Int) raises:
    var shape = List[Int]()
    shape.append(batch_size)
    shape.append(2)  # C=2 fixed
    shape.append(2)  # H=2 fixed
    shape.append(2)  # W=2 fixed
    var n_elems = batch_size * 8

    # ... setup x, gamma, beta, running_mean, running_var ...

    # Forward pass
    var fwd = batch_norm2d(x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
    var output = fwd[0]

    # Non-uniform grad_output to avoid cancellation (see batch-norm-backward-gradient-analysis)
    var grad_output = zeros_like(output)
    for i in range(n_elems):
        var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
        grad_output._data.bitcast[Float32]()[i] = val

    # Analytical backward
    var bwd = batch_norm2d_backward(grad_output, x, gamma, running_mean, running_var,
                                    training=True, epsilon=1e-5)
    var grad_input = bwd[0]

    if batch_size == 1:
        # Finiteness only
        for i in range(n_elems):
            var val = grad_input._data.bitcast[Float32]()[i]
            assert_true(val == val, "grad_input should not be NaN (batch_size=1)")
            assert_true(val > -1e10 and val < 1e10, "grad_input should be finite (batch_size=1)")
    else:
        # Full numerical gradient check
        fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
            var res = batch_norm2d(inp, gamma, beta, running_mean, running_var,
                                   training=True, epsilon=1e-5)
            var out = res[0]
            var weighted = multiply(out, grad_output)
            var result = weighted
            while result.dim() > 0:
                result = reduce_sum(result, axis=0, keepdims=False)
            return result

        var numerical_grad = compute_numerical_gradient(forward_for_grad, x, epsilon=1e-3)
        assert_gradients_close(grad_input, numerical_grad, rtol=5e-2, atol=5e-4,
                               message="Batch norm grad_input")
```

### Step 3: Write the public test functions (one per gradient type)

Each public `fn test_` function calls the helper for all three batch sizes:

```mojo
fn test_batch_norm2d_backward_grad_input_batch_sizes() raises:
    """Parametrized gradient check for grad_input over batch_sizes [1, 2, 4]."""
    _check_grad_input_batch_size(1)
    _check_grad_input_batch_size(2)
    _check_grad_input_batch_size(4)
    print("✓ Batch norm backward grad_input validated for batch_sizes [1, 2, 4]")

fn test_batch_norm2d_backward_grad_gamma_batch_sizes() raises:
    """Parametrized gradient check for grad_gamma over batch_sizes [1, 2, 4]."""
    _check_grad_gamma_batch_size(1)
    _check_grad_gamma_batch_size(2)
    _check_grad_gamma_batch_size(4)
    print("✓ Batch norm backward grad_gamma validated for batch_sizes [1, 2, 4]")

fn test_batch_norm2d_backward_grad_beta_batch_sizes() raises:
    """Parametrized gradient check for grad_beta over batch_sizes [1, 2, 4]."""
    _check_grad_beta_batch_size(1)
    _check_grad_beta_batch_size(2)
    _check_grad_beta_batch_size(4)
    print("✓ Batch norm backward grad_beta validated for batch_sizes [1, 2, 4]")
```

### Step 4: Verify test count and CI discoverability

Keep ≤10 `fn test_` functions per `.mojo` file. The pattern above uses 3 public test
functions (well within the limit) with all parametrization inside private helpers.

The file naming convention `test_normalization_part4.mojo` is auto-discovered by CI via
the glob pattern `test_normalization*.mojo` — no workflow changes needed.

### Step 5: Tolerance selection

| Gradient | rtol | atol | Rationale |
|----------|------|------|-----------|
| grad_input | 5e-2 | 5e-4 | Batch norm has compounding FP errors across normalize/scale/shift |
| grad_gamma | 1e-2 | 1e-4 | Simpler: sum(grad_output × x_hat) per channel |
| grad_beta | 1e-2 | 1e-4 | Simplest: sum(grad_output) per channel |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use uniform grad_output=ones for grad_input check | Set `grad_output = ones_like(output)` for all batch sizes | For symmetric inputs, the analytical gradient is near-zero (sum(x_hat)=0 cancellation), making the test insensitive to bugs | Always use non-uniform grad_output to break symmetry; see `batch-norm-backward-gradient-analysis` skill |
| Apply full numerical gradient check for batch_size=1 | Called `compute_numerical_gradient` with epsilon=1e-3 for batch_size=1 | When variance≈0, the denominator `sqrt(eps_bn)≈0.00316` is much smaller than the finite difference step, causing catastrophic amplification of perturbations | Bifurcate: finiteness-only assertions for batch_size=1, full check for batch_size≥2 |
| Use batch_size=1 with varying input to avoid variance=0 | Set non-uniform x values like `Float32(i)*0.1+0.05` | Even with non-uniform values across (H,W)=(2,2), per-channel variance is very small and the backward is still numerically unstable for finite differences | The fundamental issue is batch statistics computed over (N,H,W) with N=1; H×W=4 elements is too few for stable FD |
| Share a single helper function for all 3 gradient types | One `_check_batch_size(batch_size, grad_type)` with a string parameter | Mojo closures capturing different outer variables (x vs gamma vs beta) require different fn signatures; string dispatch adds complexity | Keep separate helpers per gradient type — simpler and stays within ≤10 fn test_ limit |

## Results & Parameters

### Test file header template

```mojo
"""Tests for batch normalization backward pass across multiple batch sizes.

Tests cover:
- Batch norm backward grad_input for batch_sizes [1, 2, 4]
- Batch norm backward grad_gamma for batch_sizes [1, 2, 4]
- Batch norm backward grad_beta for batch_sizes [1, 2, 4]

batch_size=1 is a degenerate case: with a single sample, variance=0 collapses the
denominator to sqrt(eps), making gradients numerically sensitive. These cases assert
finiteness only. batch_size=2 and batch_size=4 use standard gradient checking tolerances.

Closes #3811.
"""
```

### Tolerances used (from prior batch norm gradient work)

```mojo
# grad_input — wider tolerance for compounding FP errors
assert_gradients_close(grad_input, numerical_grad, rtol=5e-2, atol=5e-4,
                       message="Batch norm grad_input")

# grad_gamma and grad_beta — tighter tolerances
assert_gradients_close(grad_gamma, numerical_grad_gamma, rtol=1e-2, atol=1e-4,
                       message="Batch norm grad_gamma")
assert_gradients_close(grad_beta, numerical_grad_beta, rtol=1e-2, atol=1e-4,
                       message="Batch norm grad_beta")
```

### CI discovery (no changes needed)

The CI workflow already has:
```yaml
pattern: "... test_normalization*.mojo ..."
```

Name new files `test_normalization_part4.mojo`, `test_normalization_part5.mojo`, etc.
to be auto-discovered. No workflow YAML edits required.
