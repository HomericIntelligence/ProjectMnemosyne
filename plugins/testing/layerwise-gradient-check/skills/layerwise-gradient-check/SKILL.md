---
name: layerwise-gradient-check
description: "Layerwise gradient checking for neural network backward pass validation"
category: testing
source: ProjectOdyssey
date: 2025-12-28
---

# Layerwise Gradient Checking

Validate neural network backward pass implementations using numerical gradient checking.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-28 |
| Objective | Verify analytical gradients match numerical gradients |
| Outcome | Success |

## When to Use

- Implementing new neural network layer backward passes
- Debugging gradient computation errors
- TDD workflow for neural network components
- Validating custom activation function derivatives

## Verified Workflow

1. **Use FP-representable test values**:

   ```python
   # Values exactly representable in FP32/FP16
   test_values = [0.0, 0.5, 1.0, 1.5, -1.0, -0.5]
   ```

2. **Compute numerical gradient**:

   ```python
   def numerical_gradient(f, x, epsilon=1e-5):
       grad = np.zeros_like(x)
       for i in range(x.size):
           x_plus = x.copy()
           x_plus.flat[i] += epsilon
           x_minus = x.copy()
           x_minus.flat[i] -= epsilon
           grad.flat[i] = (f(x_plus) - f(x_minus)) / (2 * epsilon)
       return grad
   ```

3. **Compare with analytical gradient**:

   ```python
   analytical = layer.backward(upstream_grad)
   numerical = numerical_gradient(layer.forward, input)
   assert np.allclose(analytical, numerical, rtol=1e-2, atol=1e-5)
   ```

4. **Use small tensor sizes** to prevent timeout:

   ```python
   # 8x8 for conv layers, 16x16 for linear
   test_input = np.random.randn(1, 3, 8, 8)
   ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Random float inputs | Non-deterministic failures | Use seeded random (seed=42) |
| Large tensors (64x64) | Timeout in CI | Use 8x8 for conv layers |
| epsilon=1e-7 | Numerical instability | Use epsilon=1e-5 |
| atol=1e-7 | Too strict for float32 | Use atol=1e-5, rtol=1e-2 |

## Results & Parameters

```yaml
# Gradient checking config
epsilon: 1e-5
rtol: 1e-2
atol: 1e-5
random_seed: 42

# Tensor sizes (balance accuracy vs speed)
conv_input: [1, 3, 8, 8]
linear_input: [1, 16]
batch_norm_input: [4, 8, 4, 4]

# FP-representable test values
special_values: [0.0, 0.5, 1.0, 1.5, -1.0, -0.5]
```

## References

- CS231n gradient checking: https://cs231n.github.io/neural-networks-3/#gradcheck
- Related: testing/fp-representable-values
- Source: ProjectOdyssey testing strategy
