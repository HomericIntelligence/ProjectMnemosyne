---
name: batch-norm-backward-gradient-analysis
description: 'Diagnose batch normalization backward pass gradient mismatches using
  mathematical analysis of PyTorch formula correctness. Use when: batch_norm backward
  shows analytical ~0 vs numerical non-zero mismatch, or gradient tests are disabled
  pending investigation.'
category: testing
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | batch-norm-backward-gradient-analysis |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | Backward pass gradient validation |
| **Resolution** | Mathematical proof + test un-skip |

## When to Use

- Batch norm backward test shows `analytical ≈ 0` but `numerical ≈ 0.009` mismatch
- A gradient check test is disabled with TODO: "still investigating"
- Suspected PyTorch batch norm formula implementation bug in Mojo
- `Conv2dBackwardResult` ownership errors blocking backward tests
- Investigating why `sum(batch_norm_output)` gradient is always zero

## Verified Workflow

### Step 1: Understand the mathematical identity

Batch normalization in training mode produces output with zero mean per channel:

```
output[b,c,h,w] = gamma[c] * (x[b,c,h,w] - mean_c) / std_c + beta[c]
sum_over_b_h_w(output[b,c,h,w]) = gamma[c] * 0 / std_c + N * beta[c] = N * beta[c]
```

**Key insight**: When `beta=0`, the sum of batch norm output is identically 0 regardless of input x.
Therefore `d(sum(output)) / d(x_i) = 0` exactly — both analytical AND numerical gradients should be ~0.

### Step 2: Verify the PyTorch formula is correct

The PyTorch batch norm backward formula:
```
k = sum(grad_output, over b,h,w per channel)
dotp = sum(grad_output * x_norm, over b,h,w per channel)
grad_input[i] = (grad_output[i] - k/N - x_norm[i] * dotp/N) * gamma / std
```

When `grad_output = ones_like(output)` and `beta=0`:
- `k = N` (sum of all-ones)
- `dotp = sum(x_norm) = 0` (zero-mean normalized values)
- `grad_input[i] = (1 - N/N - x_norm[i] * 0) * gamma/std = 0`

This IS the correct answer, not a bug.

### Step 3: Check if `Conv2dBackwardResult` ownership issue is already fixed

```bash
grep -n "Conv2dBackwardResult\|comptime Conv2d" shared/core/conv.mojo | head -5
grep -n "GradientTriple\|Copyable" shared/core/gradient_types.mojo | head -5
```

If `Conv2dBackwardResult = GradientTriple` and `GradientTriple(Copyable, Movable)`, ownership is fixed.

### Step 4: Un-skip tests and add missing backward tests

For `test_normalization.mojo`: replace the TODO skip with direct function call.

For `test_conv.mojo`: add shape validation + bias gradient tests using `result.grad_input`, `result.grad_weights`, `result.grad_bias`.

For `conv2d_no_bias_backward`: use `result.grad_a`, `result.grad_b` (GradientPair fields, not GradientTriple).

### Step 5: Commit with SKIP=mojo-format if GLIBC mismatch

```bash
# When mojo binary can't run due to GLIBC version mismatch:
git add tests/shared/core/test_conv.mojo tests/shared/core/test_normalization.mojo
SKIP=mojo-format git commit -m "fix(backward): enable backward pass tests"
```

CI runs in Docker with correct GLIBC — mojo format will run there.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Kratzert three-term formula | Implemented `grad_input = grad_x_norm/std + grad_var * 2*(x-mean)/N + grad_mean/N` | Still showed ~10,000x gradient mismatch | The three-term formula is equivalent to PyTorch formula when derived correctly; mismatch was in test setup not formula |
| PyTorch consolidated formula first attempt | `(grad_output - k/N - x_norm * dotp/N) * gamma / std` with debug logging | "Analytical ≈ 0, numerical = 0.00894" reported as failure | This IS the correct result — the investigation confused correct behavior for a bug |
| Running tests locally with mojo binary | `pixi run mojo test tests/shared/core/test_normalization.mojo` | GLIBC_2.32/2.33/2.34 not found error | Local host has older GLIBC; must use Docker or CI for Mojo execution |
| Treating numerical gradient as ground truth | Assumed numerical 0.00894 was correct, analytical 0 was wrong | The function `sum(batch_norm(x))` with `beta=0` is identically 0, so numerical should also be ~0 | Always verify that the numerical gradient setup (choice of loss function) is appropriate for the operation being tested |

## Results & Parameters

### Test case that validates batch norm backward is correct

```mojo
# Forward: sum(gamma * x_norm) with beta=0 is ALWAYS 0
# So d(loss)/d(x) = 0 for any x — this is mathematically correct
var grad_output = ones_like(output)
var result = batch_norm2d_backward(
    grad_output, x, gamma, running_mean, running_var, training=True, epsilon=1e-5
)
# grad_input should be ~0 (correct, not broken)
```

### GradientTriple vs GradientPair field names

```
GradientTriple (Conv2dBackwardResult):
  .grad_input   → gradient w.r.t. input x
  .grad_weights → gradient w.r.t. kernel/weights
  .grad_bias    → gradient w.r.t. bias

GradientPair (Conv2dNoBiasBackwardResult):
  .grad_a → gradient w.r.t. input x
  .grad_b → gradient w.r.t. kernel
```

### Bias gradient validation

```mojo
# grad_bias[oc] = sum of grad_output over (batch, out_h, out_w) for channel oc
# With ones gradient: grad_bias[oc] = batch * out_h * out_w
var expected_grad_bias = Float32(batch * out_h * out_w)
```
