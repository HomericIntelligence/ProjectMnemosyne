---
name: layer-norm-4d-gradient-test
description: 'Pattern for writing numerical gradient tests for layer_norm_backward
  on 4D inputs in Mojo. Use when: extending 2D gradient validation to 4D (batch, channels,
  H, W), validating backward pass correctness when indexing/reduction logic differs
  by rank, or adding follow-up tests after a 2D gradient test.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Purpose** | Validate `layer_norm_backward` on 4D inputs via central finite differences |
| **Language** | Mojo v0.26.1 |
| **Target file** | `tests/shared/core/test_normalization.mojo` |
| **Input shape** | `[2, 2, 2, 4]` (batch=2, channels=2, H=2, W=4) |
| **Gamma shape** | `[16]` (flattened last 3 dims) |
| **Tolerances** | `rtol=1e-2`, `atol=1e-5` |
| **FD step** | `epsilon=1e-4` |

## When to Use

- A 2D numerical gradient test for `layer_norm_backward` already exists and a 4D follow-up is requested
- The backward pass uses different indexing/reduction paths depending on input rank
- Issue explicitly asks for `[2, 2, 2, 4]` shape validation (as in ProjectOdyssey #3813)
## Verified Workflow

### Quick Reference

```bash
# Run after adding the test
just test-group tests/shared/core test_normalization.mojo
```

### Step 1 — Identify the target file

Read the normalization test file to understand its structure and existing test count before adding.

### Step 2 — Choose shape and gamma layout

For 4D layer norm (normalizes over last N dims), gamma must be flat over those dims:

| Input shape | Normalized dims | Gamma shape |
| ------------- | ---------------- | ------------- |
| `[B, C, H, W]` | `[C, H, W]` | `[C*H*W]` |
| `[2, 2, 2, 4]` | `[2, 2, 4]` | `[16]` |

### Step 3 — Use non-uniform `grad_output`

**Critical**: When `grad_output=ones`, layer norm's mathematical identity causes
`sum(grad_output * x_hat) = sum(x_hat) = 0` (by normalization), making the last
backward term vanish identically. This masks bugs in the backward formula.

Use alternating mixed-sign values with small magnitudes (e.g., `[0.03, -0.07, 0.05, ...]`).

### Step 4 — Implement the test function

```mojo
fn test_layer_norm_backward_gradient_input_4d() raises:
    """Test layer_norm_backward gradient w.r.t. input on 4D inputs using numerical validation.

    Shape: [2, 2, 2, 4] — 2 samples, normalized over [2, 2, 4] = 16 elements each.
    Gamma shape: [16] (flattened last 3 dims), matching 4D implementation convention.
    """
    # 4D tensor: (batch=2, channels=2, H=2, W=4)
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    shape.append(2)
    shape.append(4)

    # Input with varying values across all 32 elements
    var x = zeros(shape, DType.float32)
    for i in range(32):
        x._data.bitcast[Float32]()[i] = Float32(i) * 0.1 + 0.05

    # Gamma shape [16], non-uniform values cycling through [1.5, 0.8, 1.2, 2.0]
    var param_shape = List[Int]()
    param_shape.append(16)
    var gamma = ones(param_shape, DType.float32)
    for i in range(16):
        var cycling_values = List[Float32]()
        cycling_values.append(1.5)
        cycling_values.append(0.8)
        cycling_values.append(1.2)
        cycling_values.append(2.0)
        gamma._data.bitcast[Float32]()[i] = cycling_values[i % 4]
    var beta = zeros(param_shape, DType.float32)

    # Non-uniform grad_output: 32 values with alternating mixed signs
    var grad_output = zeros(shape, DType.float32)
    var go_vals = List[Float32]()
    # ... (32 values, alternating positive/negative, small magnitude ~0.01–0.09)
    for i in range(32):
        grad_output._data.bitcast[Float32]()[i] = go_vals[i]

    # Analytical backward pass
    var result = layer_norm_backward(grad_output, x, gamma, epsilon=1e-5)
    var grad_input = result[0]

    # Numerical gradient closure
    fn forward_for_grad_4d(inp: ExTensor) raises -> ExTensor:
        var out = layer_norm(inp, gamma, beta, epsilon=1e-5)
        var weighted = multiply(out, grad_output)
        var result_inner = weighted
        while result_inner.dim() > 0:
            result_inner = reduce_sum(result_inner, axis=0, keepdims=False)
        return result_inner

    var numerical_grad = compute_numerical_gradient(
        forward_for_grad_4d, x, epsilon=1e-4
    )

    assert_gradients_close(
        grad_input, numerical_grad, rtol=1e-2, atol=1e-5,
        message="Layer norm 4D gradient w.r.t. input",
    )
```

### Step 5 — Add call to `main()`

Insert after the existing 2D gradient test call:

```mojo
    test_layer_norm_backward_gradient_input_4d()
    print("✓ test_layer_norm_backward_gradient_input_4d")
```

### Step 6 — Commit and create PR

```bash
git add tests/shared/core/test_normalization.mojo
git commit -m "test(normalization): add numerical gradient test for layer_norm_backward on 4D inputs

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `grad_output=ones` | Uniform all-ones grad_output for simplicity | `sum(grad_output * x_hat) = sum(x_hat) = 0` by normalization identity — last backward term vanishes, masking bugs | Always use non-uniform grad_output for layer norm gradient tests |
| Creating a new file | Adding a 5th test_normalization file | Existing file had room (7→8 fns) | Count existing `fn test_` before deciding to create vs extend |
| Gamma shape `[C, H, W]` = `[2, 2, 4]` | Using full 3D gamma for 4D input | Implementation convention uses flat `[C*H*W]` = `[16]` for 4D inputs | Verify gamma shape convention matches the implementation, not intuition |

## Results & Parameters

### Working Configuration

```
Input shape:    [2, 2, 2, 4]
Gamma shape:    [16]   # flattened last 3 dims
FD epsilon:     1e-4   # central finite differences
Layer norm eps: 1e-5
rtol:           1e-2
atol:           1e-5
```

### File Targeted

```
tests/shared/core/test_normalization.mojo
```

After this addition: 8 functions.

### Imports Required

```mojo
from shared.testing import (
    compute_numerical_gradient,
    assert_gradients_close,
)
from shared.core.extensor import ExTensor, zeros, ones
from shared.core.normalization import layer_norm, layer_norm_backward
from shared.core.arithmetic import multiply
from shared.core.reduction import sum as reduce_sum
```
