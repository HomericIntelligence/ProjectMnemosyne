---
name: mojo-numerical-gradient-test
description: 'Add numerical gradient validation for Mojo ML backward passes using
  central finite differences. Use when: adding backward pass gradient tests, avoiding
  grad_output=ones cancellation, verifying analytical vs numerical gradient agreement.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-numerical-gradient-test |
| **Category** | testing |
| **Applies To** | Mojo ML layer backward pass tests |
| **Key Tool** | `compute_numerical_gradient` + `assert_gradients_close` from `shared.testing` |
| **Issue** | ProjectOdyssey #3247 |

## When to Use

- Adding a numerical gradient check for a new Mojo backward pass (batch norm, layer norm, etc.)
- Existing tests only cover shapes/structural checks but not gradient correctness
- A backward pass has the algebraic cancellation risk (uniform `grad_output` makes certain terms vanish)
- Mirroring an existing gradient test pattern for a related layer

## Verified Workflow

1. **Identify the cancellation risk**: For normalization layers, `grad_output=ones` causes
   `sum(grad_output * x_hat) = sum(x_hat) = 0` by normalization, making the last backward
   term vanish regardless of implementation correctness. Always use non-uniform `grad_output`.

2. **Set up inputs**: Use small tensors (2x4 for layer norm, 2x2x2x2 for batch norm) with
   varying, non-zero, non-symmetric values. Avoid uniform inputs.

3. **Set non-trivial parameters**: Use distinct `gamma` values per feature (e.g., 1.5, 0.8, 1.2,
   2.0) so the scale is exercised fully.

4. **Define non-uniform `grad_output`**: Use alternating signs and varying magnitudes, e.g.:
   ```mojo
   grad_output._data.bitcast[Float32]()[0] = 0.3
   grad_output._data.bitcast[Float32]()[1] = -0.5
   grad_output._data.bitcast[Float32]()[2] = 1.2
   grad_output._data.bitcast[Float32]()[3] = -0.8
   ```

5. **Write the numerical closure**: The closure must compute `sum(forward(x) * grad_output)` so
   that its gradient w.r.t. x matches the analytical backward:
   ```mojo
   fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
       var out = layer_norm(inp, gamma, beta, epsilon=1e-5)
       var weighted = multiply(out, grad_output)
       var result = weighted
       while result.dim() > 0:
           result = reduce_sum(result, axis=0, keepdims=False)
       return result
   ```

6. **Call `compute_numerical_gradient`** with `epsilon=1e-4` (not 1e-3 — tighter for layer norm
   due to its simpler structure vs batch norm).

7. **Assert with `assert_gradients_close`**: Use `rtol=1e-2, atol=1e-5` for layer norm.
   Batch norm needs looser `atol=1e-4` due to more compounding intermediate steps.

8. **Register in `fn main()`**: Add the call after existing structural tests, before the
   closing print.

9. **Run pre-commit**: Mojo format hook runs automatically; verify it passes.

## Results & Parameters

### Layer Norm Gradient Test Parameters

```mojo
# Tensor shape
shape: [2, 4]  # (batch, features)

# Input values
x[i] = Float32(i) * 0.1 + 0.05  # i in range(8)

# gamma values
[1.5, 0.8, 1.2, 2.0]

# grad_output values (non-uniform, mixed signs)
[0.3, -0.5, 1.2, -0.8, 0.7, -0.2, 0.9, -1.1]

# Finite difference epsilon
epsilon = 1e-4

# Tolerance
rtol = 1e-2, atol = 1e-5
```

### Batch Norm Gradient Test Parameters (reference)

```mojo
# Tensor shape
shape: [2, 2, 2, 2]  # (batch, channels, H, W)

# gamma values
[1.5, 2.0]

# grad_output: alternating pattern
val = Float32(i % 4) * Float32(0.25) - Float32(0.3)

# Finite difference epsilon
epsilon = 1e-3

# Tolerance
rtol = 2e-2, atol = 1e-4
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `grad_output = ones(...)` | Using uniform all-ones grad_output as in structural tests | `sum(grad_output * x_hat) = sum(x_hat) = 0` by normalization — last backward term vanishes, masking bugs | Always use non-uniform grad_output for normalization backward tests |
| `epsilon = 1e-3` for layer norm | Using same finite-difference step as batch norm | Acceptable but 1e-4 gives tighter numerical gradients for the simpler layer norm structure | Use 1e-4 for layer norm; reserve 1e-3 for batch norm with more intermediate steps |
| `atol = 1e-4` for layer norm | Matching batch norm tolerance | Layer norm is simpler (fewer intermediate steps) so tighter tolerance 1e-5 is achievable | Match atol to layer complexity: layer norm 1e-5, batch norm 1e-4 |
| Running tests locally | `pixi run mojo test tests/...` | GLIBC 2.32/2.33/2.34 not available on host OS (Debian 10) | Mojo tests must run in Docker or CI; pre-commit hooks validate syntax locally |
