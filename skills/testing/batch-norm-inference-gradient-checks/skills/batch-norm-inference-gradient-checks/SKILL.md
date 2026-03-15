---
name: batch-norm-inference-gradient-checks
description: "Add numerical gradient validation tests for batch_norm2d_backward in inference mode (training=False), covering grad_gamma and grad_beta via finite differences. Use when: gradient checks only cover training=True, inference code path uses running_mean/running_var, or issue asks to extend coverage to inference mode."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Language** | Mojo |
| **Test file** | `tests/shared/core/test_normalization_part3.mojo` |
| **Function under test** | `batch_norm2d_backward` with `training=False` |
| **Validation method** | Central finite differences (`compute_numerical_gradient`) |
| **Tolerances** | `rtol=1e-2`, `atol=1e-4`, `epsilon=1e-3` |
| **ADR constraint** | ≤10 `fn test_` per file (ADR-009 heap corruption workaround) |

## When to Use

- Existing gradient checks only cover `training=True` for `batch_norm2d_backward`
- Inference code path (`training=False`) uses `running_mean`/`running_var` instead of batch statistics
- Issue requests numerical validation of `grad_gamma` and `grad_beta` in inference mode
- Mirroring training-mode gradient tests to inference mode

## Verified Workflow

### Quick Reference

```mojo
# Inference mode backward gradient check pattern
var result_bwd = batch_norm2d_backward(
    grad_output, x, gamma,
    running_mean, running_var,
    training=False, epsilon=1e-5,
)
var grad_gamma_analytical = result_bwd[1]

fn forward_for_gamma_infer(g: ExTensor) raises -> ExTensor:
    var res = batch_norm2d(
        x, g, beta, running_mean, running_var, training=False, epsilon=1e-5
    )
    var out = res[0]
    var weighted = multiply(out, grad_output)
    var result = weighted
    while result.dim() > 0:
        result = reduce_sum(result, axis=0, keepdims=False)
    return result

var numerical_grad_gamma = compute_numerical_gradient(
    forward_for_gamma_infer, gamma, epsilon=1e-3
)

assert_gradients_close(
    grad_gamma_analytical, numerical_grad_gamma,
    rtol=1e-2, atol=1e-4,
    message="Batch norm gradient w.r.t. gamma (inference mode)",
)
```

### Step-by-Step

1. **Identify the test file** — check ADR-009 test count limit (≤10 `fn test_` per file).
   Count existing tests: `grep -c "^fn test_" <file>`. If at limit, use a different part file.

2. **Check the function signature** — `batch_norm2d_backward` requires positional
   `running_mean` and `running_var` (no defaults). Existing tests in the same file
   may use keyword-only calls without these; those are broken/will fail to compile.
   Always match the full signature from the source.

3. **Set up non-trivial running stats** — use values that differ from training-mode defaults
   (e.g. `running_mean = [0.3, 0.7]`, `running_var = [0.5, 1.5]`) to exercise the inference
   code path, not just identity normalization.

4. **Use non-uniform `grad_output`** — sequential values like `Float32(i + 1) * 0.1`
   prevent algebraic cancellation where sums collapse to zero, masking bugs.

5. **Compute forward pass first** — call `batch_norm2d(..., training=False)` with the same
   `running_mean`/`running_var` to get the output shape for `zeros_like`.

6. **Mirror the backward call** — pass all positional args:
   `batch_norm2d_backward(grad_output, x, gamma, running_mean, running_var, training=False, epsilon=1e-5)`

7. **Write the numerical gradient closure** — perturb the parameter being tested (`gamma` or
   `beta`), compute weighted sum of forward output, reduce to scalar.

8. **Call `compute_numerical_gradient`** with `epsilon=1e-3` (larger than training tests
   `1e-4` due to float32 precision with running stats).

9. **Call `assert_gradients_close`** with `rtol=1e-2`, `atol=1e-4`.

10. **Add test calls to `main()`** and verify count stays ≤10.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reuse existing part3 pattern without running stats | Called `batch_norm2d_backward(grad_output, x, gamma, epsilon=1e-5, training=False)` matching other part3 tests | Signature requires positional `running_mean`/`running_var` — no defaults exist | Always grep the actual function signature; existing tests in same file may be broken |
| Using `grad_output = ones(...)` | Uniform gradient for non-uniform channel data | `sum(grad_output * x_hat) ≈ 0` collapses terms in backward formula, masking bugs | Non-uniform `grad_output` is critical for correctness of numerical validation |
| Single `epsilon=1e-4` for float32 inference | Same epsilon as training mode tests | Running stat normalization amplifies perturbation sensitivity; needed `1e-3` | Float32 + fixed running stats = larger finite-diff errors; use `epsilon=1e-3` |

## Results & Parameters

### Confirmed Working Configuration

```mojo
# Running stats that exercise inference path (not zero-mean, unit-var)
var running_mean = zeros(param_shape, DType.float32)
running_mean._data.bitcast[Float32]()[0] = 0.3
running_mean._data.bitcast[Float32]()[1] = 0.7

var running_var = ones(param_shape, DType.float32)
running_var._data.bitcast[Float32]()[0] = 0.5
running_var._data.bitcast[Float32]()[1] = 1.5

# grad_output: sequential values, not uniform
for i in range(16):
    grad_output._data.bitcast[Float32]()[i] = Float32(i + 1) * 0.1

# Tolerances
assert_gradients_close(..., rtol=1e-2, atol=1e-4, ...)
compute_numerical_gradient(..., epsilon=1e-3)
```

### ADR-009 Test Count

After adding 2 new tests (`grad_gamma_inference`, `grad_beta_inference`) to part3:

```
$ grep -c "^fn test_" tests/shared/core/test_normalization_part3.mojo
9
```

9 ≤ 10 — compliant.

### Imports Required

```mojo
from shared.testing import (
    compute_numerical_gradient,
    assert_gradients_close,
)
from shared.core.extensor import ExTensor, zeros, ones, zeros_like
from shared.core.normalization import batch_norm2d, batch_norm2d_backward
from shared.core.arithmetic import multiply
from shared.core.reduction import sum as reduce_sum
```
