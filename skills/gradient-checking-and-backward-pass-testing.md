---
name: gradient-checking-and-backward-pass-testing
description: "Use when: (1) writing numerical gradient checks for conv2d, depthwise\
  \ conv2d, batch norm, layer norm, or pooling backward passes in Mojo, (2) a gradient\
  \ check reports analytical≈0 vs numerical≈nonzero for a normalization layer, (3)\
  \ migrating from check_gradients() to check_gradient() or choosing tolerances for\
  \ float32 backward tests, (4) extending backward coverage to inference mode, 4D\
  \ inputs, multi-channel configs, or all three gradient fields (grad_input, grad_weights,\
  \ grad_bias), (5) implementing analytically tractable exact-value tests for conv2d\
  \ backward with all-ones configs"
category: testing
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: gradient-checking-and-backward-pass-testing.history
tags:
  - gradient-checking
  - backward-pass
  - batch-norm
  - layer-norm
  - conv2d
  - depthwise-conv2d
  - pooling
  - finite-differences
  - float32-precision
  - mojo
---

# Gradient Checking and Backward Pass Testing

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-05-19 |
| Objective | Numerically correct backward pass tests for all ML layer types in Mojo |
| Outcome | Consolidated patterns from 10 skills covering conv2d, depthwise conv2d, batch norm, layer norm, and pooling |
| Verification | unverified |

## When to Use

- Conv2d, depthwise conv2d, batch norm, layer norm, or pooling backward pass lacks gradient-correctness tests
- Gradient check fails with "analytical ≈ 0 but numerical ≈ 0.009" for a normalization layer
- Choosing between `check_gradient()` and `check_gradients()` APIs
- Adding inference-mode (`training=False`) backward tests for batch norm
- Extending gradient coverage to 4D inputs, multi-channel configs, param gradients (grad_gamma, grad_beta)
- Writing exact-value analytical tests for conv2d backward (no finite differences needed)
- Per-file test count is approaching its limit and a new file must be created

## Verified Workflow

### Quick Reference

**Normalization cancellation fix (BatchNorm, LayerNorm — any zero-mean layer):**

```mojo
# NEVER use ones_like(output) for normalization backward tests!
# PREFERRED: sum(output^2) loss — closed-form derivative
var two = full_like(output, 2.0)
var grad_output = multiply(two, output)  # dL/dY = 2 * output

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var out = batch_norm2d(inp, gamma, beta, running_mean, running_var,
                           training=True, epsilon=1e-5)[0]
    var sq = multiply(out, out)
    var r = sq
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r

# ALTERNATIVE: non-uniform cycling pattern (interim approach)
var grad_output = zeros_like(output)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = Float32(i % 4) * Float32(0.25) - Float32(0.3)
# Pattern: [-0.3, -0.05, 0.2, 0.45, ...], mean ≈ 0.075
```

**check_gradient() vs check_gradients():**

| API | Tolerance model | Use when |
| --- | --- | --- |
| `check_gradient(fwd, bwd, x, grad_out, rtol, atol)` | Combined: `abs(diff) ≤ atol + rtol*magnitude` | All gradient checking tests (correct for large magnitudes) |
| `check_gradients(fwd, bwd, x, eps, tol)` | Pure absolute: `abs(diff) < tol` | ONLY the 2 meta-test files that verify Bool-return semantics |

**Tolerance quick-ref by layer type:**

| Layer | rtol | atol | epsilon |
| --- | --- | --- | --- |
| Conv2D backward | `1e-2` | `1e-2` | `1e-4` or `3e-4` |
| Depthwise Conv2D | `1e-2` | `1e-2` | `3e-4` |
| BatchNorm training | `2e-2` | `1e-4` | `1e-3` |
| BatchNorm inference | `1e-2` | `1e-4` | `1e-3` |
| LayerNorm input | `1e-2` | `1e-5` | `1e-4` |
| LayerNorm gamma/beta | `1e-2` | `1e-4` | `1e-4` |
| MaxPool/AvgPool | `1e-3` | `5e-4` | `3e-4` |

### Step 1: Understand the Cancellation Problem

Normalization layers have a structural property:

```text
x_norm = (x - mean(x)) / std(x)  =>  sum(x_norm) = 0  (always)
```

BatchNorm backward contains a term `sum(grad_output * x_norm)`. When `grad_output = ones`:
- `sum(1 * x_norm) = sum(x_norm) = 0` → analytical gradient is **exactly zero**
- In float32, perturbing `x[i]` by ε=1e-4 produces numerical gradient ≈ 0.009
- Result: "false failure" — 1000× mismatch, but the implementation is correct

**The same identity holds for LayerNorm and any mean-centering normalization layer.**

### Step 2: Choose the Correct grad_output Strategy

**For normalization layers** — use either:

1. `sum(output^2)` loss (preferred — loss function with closed-form derivative):

   ```mojo
   var grad_output = multiply(full_like(output, 2.0), output)
   # forward closure reduces sum(out * out) to scalar
   ```

2. Non-uniform cycling pattern (interim):

   ```mojo
   for i in range(output.numel()):
       grad_output._data.bitcast[Float32]()[i] = Float32(i % 4) * Float32(0.25) - Float32(0.3)
   ```

**For conv2d / depthwise conv2d** — `ones_like(output)` is safe (no zero-mean property).
With `padding > 0`, prefer non-uniform to be safe at boundary positions.

**For pooling** — use non-uniform for the numerical tier (AvgPool with symmetric inputs
can cause gradient cancellation).

**Consistency rule**: The `grad_output` and `forward_for_grad` closure MUST derive from the
same loss function.

### Step 3: Use check_gradient() (Not check_gradients())

```mojo
from shared.testing.gradient_checker import check_gradient

fn _ones_grad(output: AnyTensor) raises -> AnyTensor:
    var grad = zeros_like(output)
    for i in range(output.numel()):
        grad._set_float64(i, 1.0)
    return grad^

var output = forward(input)
var grad_output = _ones_grad(output)
check_gradient(forward, backward, input, grad_output, rtol=1e-2, atol=1e-2)
```

Why `check_gradient()` is required: For a gradient of magnitude 32.4 with diff 0.046:

- `check_gradients(tolerance=0.01)`: 0.046 ≥ 0.01 → **FAIL** (false failure)
- `check_gradient(rtol=1e-2, atol=1e-2)`: 0.046 ≤ 0.01 + 0.01×32.4 = 0.334 → **PASS**

**Tolerance conversion from old check_gradients() calls:**

| Old call | New call |
| --- | --- |
| `check_gradients(..., tolerance=0.01)` | `check_gradient(..., rtol=1e-2, atol=1e-2)` |
| `check_gradients(..., tolerance=0.05)` | `check_gradient(..., rtol=5e-2, atol=1e-4)` |
| `check_gradients(..., tolerance=0.1)` | `check_gradient(..., rtol=1e-1, atol=1e-2)` |

**Exceptions** (must keep `check_gradients()`):
- `test_gradient_checker_meta.mojo` — tests Bool-return semantics
- `test_gradient_checker_noncont_tensors.mojo` — tests Bool-return semantics

### Step 4: Conv2D Gradient Checking

Two gradient checking APIs — pick the one matching existing tests:

```mojo
# API 1: check_gradient (explicit grad_output)
fn forward_input(inp: ExTensor) raises -> ExTensor:
    return conv2d(inp, kernel, bias, stride=1, padding=0)

fn backward_input(grad_out: ExTensor, inp: ExTensor) raises -> ExTensor:
    return conv2d_backward(grad_out, inp, kernel, stride=1, padding=0).grad_input

var output = forward_input(x)
var grad_output = ones_like(output)
check_gradient(forward_input, backward_input, x, grad_output, rtol=1e-2, atol=1e-2)

# API 2: check_gradients (internal grad_output, note 'raises escaping' on closures)
fn forward(x: ExTensor) raises escaping -> ExTensor:
    return conv2d(x, kernel, bias, stride=stride, padding=padding)

fn backward(grad_out: ExTensor, x: ExTensor) raises escaping -> ExTensor:
    return conv2d_backward(grad_out, x, kernel, stride=stride, padding=padding).grad_input

var passed = check_gradients(forward, backward, input, epsilon=1e-4, tolerance=1e-2)
assert_true(passed, "Conv2D gradient check failed")
```

**With padding > 0** — use non-uniform `grad_output`:

```mojo
var grad_output = zeros_like(output)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = Float32(i % 4) * Float32(0.25) - Float32(0.3)
```

**Per-file test count budget:**

```
test_gradient_checking_basic.mojo:  ≤10 tests
test_gradient_checking_dtype.mojo:  ≤10 tests
test_gradient_checking_conv2d.mojo: ≤10 tests (all 3 outputs × 3 configs = 9 tests)
test_backward_conv_padding.mojo:    ≤10 tests
```

Check before adding: `grep -c "^fn test_" <file>.mojo`

**Recommended test configurations for conv2d:**

| Config | in\_ch | out\_ch | kernel | stride | padding | input shape |
| --- | --- | --- | --- | --- | --- | --- |
| same-padding | 1 | 1 | 3×3 | 1 | 1 | `(1,1,5,5)` |
| strided | 1 | 1 | 3×3 | 2 | 0 | `(1,1,7,7)` |
| multi-channel | 2 | 3 | 3×3 | 1 | 0 | `(1,2,5,5)` |

### Step 5: Analytically Exact Conv2D Backward Tests

For all-ones input, all-ones kernel, zero bias, single output position (`input_spatial = kernel_spatial`):

| Gradient | Formula | Example (in\_ch=3, out\_ch=8, batch=1) |
| --- | --- | --- |
| `grad_weights[oc,ic,kh,kw]` | `batch × 1.0` | `1.0` |
| `grad_input[b,ic,ih,iw]` | `out_channels × 1.0` | `8.0` |
| `grad_bias[oc]` | `batch × out_H × out_W` | `1.0` (single output pos) |

Batched (batch=2): `grad_bias` and `grad_weights` multiply by batch; `grad_input` unchanged.

Padding=1 border pixel formula (all-ones, kernel=3, out\_ch=C, spatial=N):

```text
grad_input[b,ic,ih,iw] = out_channels × overlap_h(ih) × overlap_w(iw)

corner   (0, 0):   2×2 = 4  →  4×C
edge  (0, 1):      2×3 = 6  →  6×C
interior (1, 1):   3×3 = 9  →  9×C

Example (C=8, N=5): corner=32.0, edge=48.0, interior=72.0
```

### Step 6: Depthwise Conv2D Specifics

**Critical API differences from regular conv2d:**

| Aspect | Regular Conv2D | Depthwise Conv2D |
| --- | --- | --- |
| Kernel shape | `(out_channels, in_channels, kH, kW)` | `(channels, 1, kH, kW)` |
| Gradient field | `.grad_weights` | `.grad_weights` (NOT `.grad_kernel`) |
| Per-file limit | ≤10 tests | ≤8 tests (stricter) |

```mojo
# Depthwise kernel shape
kernel_shape.append(channels)
kernel_shape.append(1)  # Always 1
kernel_shape.append(kH)
kernel_shape.append(kW)
```

**grad_bias analytical test** (1×1 output per channel):

```mojo
var grad_output = zeros_like(output)
grad_output._data.bitcast[Float32]()[0] = Float32(0.5)   # channel 0
grad_output._data.bitcast[Float32]()[1] = Float32(-0.3)  # channel 1
var grads = depthwise_conv2d_backward(grad_output, x, kernel, stride=1, padding=0)
assert_almost_equal(grads.grad_bias._data.bitcast[Float32]()[0], Float32(0.5), tolerance=1e-5)
```

### Step 7: BatchNorm Gradient Testing

**Training mode (sum(output^2) loss approach):**

```mojo
var result = batch_norm2d(x, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
var output = result[0]
var grad_output = multiply(full_like(output, 2.0), output)

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var res = batch_norm2d(inp, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)
    var out = res[0]
    var sq = multiply(out, out)
    var r = sq
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r

var numerical = compute_numerical_gradient(forward_for_grad, x, epsilon=1e-3)
assert_gradients_close(grad_input, numerical, rtol=2e-2, atol=1e-4, message="...")
```

**Inference mode (training=False):**

```mojo
# Non-trivial running stats
var running_mean = zeros(param_shape, DType.float32)
running_mean._data.bitcast[Float32]()[0] = 0.3
var running_var = ones(param_shape, DType.float32)
running_var._data.bitcast[Float32]()[0] = 0.5

fn forward_for_gamma_infer(g: ExTensor) raises -> ExTensor:
    var res = batch_norm2d(x, g, beta, running_mean, running_var, training=False, epsilon=1e-5)
    var out = res[0]
    var weighted = multiply(out, grad_output)
    var r = weighted
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r

var num_gamma = compute_numerical_gradient(forward_for_gamma_infer, gamma, epsilon=1e-3)
assert_gradients_close(grad_gamma_analytical, num_gamma, rtol=1e-2, atol=1e-4, message="...")
```

### Step 8: LayerNorm Parameter Gradient Checks

`layer_norm_backward(grad_output, x, gamma, epsilon)` returns `(grad_input, grad_gamma, grad_beta)`.

```mojo
# grad_gamma test — perturb gamma, hold x and grad_output fixed
fn forward_for_gamma(g: ExTensor) raises -> ExTensor:
    var out = layer_norm(x, g, beta, epsilon=1e-5)
    var weighted = multiply(out, grad_output)
    var r = weighted
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r

var num_gamma = compute_numerical_gradient(forward_for_gamma, gamma, epsilon=1e-4)
var grad_gamma_analytical = layer_norm_backward(grad_output, x, gamma, epsilon=1e-5)[1]
assert_gradients_close(grad_gamma_analytical, num_gamma, rtol=1e-2, atol=1e-4, ...)

# grad_beta test — perturb beta (use non-zero beta to document additive shift path)
fn forward_for_beta(b: ExTensor) raises -> ExTensor:
    var out = layer_norm(x, gamma, b, epsilon=1e-5)
    var weighted = multiply(out, grad_output)
    var r = weighted
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r
```

**Gamma shape for 4D inputs** — flattened over last 3 dims:

| Input shape | Gamma shape |
| --- | --- |
| `[B, C, H, W]` | `[C*H*W]` |
| `[2, 2, 2, 4]` | `[16]` |

### Step 9: Pooling Backward (Three-Tier Pattern)

**Tier 1 — Shape:** `grad_input.shape() == input.shape()`

**Tier 2 — Analytical values:**

```mojo
# MaxPool: max position receives gradient, others get 0
var x_known = ExTensor([1, 1, 2, 2], dtype)
x_known._set_float64(1, 4.0)  # max — receives gradient
var go = ExTensor([1, 1, 1, 1], dtype)
go._set_float64(0, 1.0)
var gi = maxpool2d_backward(go, x_known, 2, 2, 0)
# gi[1] > 0.5, gi[0] ≈ gi[2] ≈ gi[3] ≈ 0

# AvgPool: each element = 1 / (pool_size^2)
var gi_avg = avgpool2d_backward(go, x_all_ones, 2, 2, 0)
# Each gi_avg[k] ≈ 0.25
```

**Tier 3 — Numerical check (non-uniform grad_output required for AvgPool):**

```mojo
fn forward_max(x: ExTensor) raises escaping -> ExTensor:
    var pool_out = maxpool2d(x, pool_size, stride, padding=padding)
    var result = ExTensor([1], x.dtype())
    var s: Float64 = 0.0
    for i in range(pool_out.numel()):
        s += pool_out._get_float64(i) * grad_out_nu._get_float64(i)
    result._set_float64(0, s)
    return result^

var analytical = maxpool2d_backward(grad_out_nu, input_small, pool_size, stride, padding)
var numerical = compute_numerical_gradient(forward_max, input_small, epsilon)
assert_gradients_close(analytical, numerical, rtol=1e-3, atol=5e-4, ...)
```

### Step 10: Commit Pattern (GLIBC Mismatch)

On hosts with GLIBC < 2.32, the mojo-format pre-commit hook will fail:

```bash
SKIP=mojo-format git commit -m "test(<layer>): add gradient checking tests"
# CI runs mojo format in Docker with correct GLIBC
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| `grad_output = ones_like(output)` for normalization | Uniform upstream gradient for batch norm \| layer norm backward | `sum(x_norm) = 0` by construction; analytical grad is exactly zero; numerical picks up float32 noise ≈ 0.009 | Never use uniform grad_output for any zero-mean normalization layer |
| Increase atol to hide mismatch | Raised tolerance from 1e-5 to 1e-2 for the failing normalization test | Masks the real issue without validating backward correctness | Fix the test setup, not the threshold |
| Modify backward formula | Changed grad_input formula to produce non-zero output for uniform grad | The formula IS correct; zero result for uniform grad is mathematically right | Don't change correct code to pass a badly designed test |
| `epsilon=1e-6` for numerical gradient | Smaller perturbation for more accurate finite differences | Worsens float32 rounding; analytical vs numerical gap grows | Smaller epsilon increases numerical error in float32; use 3e-4 or 1e-3 |
| `check_gradients()` with conv2d (magnitude 32.4) | Old API kept; only epsilon changed from 1e-4 to 3e-4 | Diff dropped from 0.134 to 0.046 but still failed absolute tolerance 0.01 | The problem was the tolerance model (absolute vs relative), not epsilon |
| `check_gradients()` with non-uniform inputs for depthwise conv2d | Added non-uniform inputs but kept old API | Diff was 0.0103 at magnitude 126.4 — barely exceeded absolute tolerance 0.01 | Large-magnitude gradients need relative tolerance; `check_gradient()` is required |
| Tight tolerances (1e-3\|1e-6) copied from linear layer tests | Used linear layer rtol/atol for conv2d tests | Conv2d accumulates more FP error via strided access + multiple passes | Use rtol=1e-2, atol=1e-2 for conv2d; pool tolerances can be tighter (1e-3\|5e-4) |
| `.grad_kernel` field for depthwise backward | Assumed depthwise returns a field named `.grad_kernel` | Actual return type is `GradientTriple` with `.grad_weights` | Always verify field names from `gradient_types.mojo`, not docstrings |
| `rtol`/`atol` keyword args in `assert_almost_equal` | Passed `rtol=1e-2, atol=1e-2` | `assert_almost_equal` takes `tolerance: Float32`, not rtol/atol | Check the actual Mojo function signature — differs from PyTorch/numpy |
| Adding tests to an existing file at capacity | Kept adding to `test_backward_conv_pool.mojo` | File at per-file test limit; CI heap corruption risk | Check `grep -c "^fn test_"` before adding; create new split file when ≥6-8 tests exist |
| `ones_like(output)` for pooling numerical tier | Passed uniform grad for AvgPool numerical check | AvgPool with symmetric inputs causes gradient cancellation — numerical grad ≈ 0 everywhere | Use non-uniform grad_output for pooling numerical tier |
| `compute_numerical_gradient` on vector pool output | Called function where forward returned raw pool output | Vector-output path sums all Jacobian elements — can cancel for AvgPool | Wrap forward function to compute weighted dot product and return scalar ExTensor |
| Non-uniform alternating pattern as final norm solution | Used `grad_output[i] = (i%4)*0.25 - 0.3` as long-term fix | Works but is ad-hoc, not derived from a loss function | Use `sum(output^2)` loss with `grad_output = 2 * output` for principled verification |
| Single `epsilon=1e-4` for float32 inference mode | Same epsilon as training mode tests | Fixed running stats amplify perturbation sensitivity | Use `epsilon=1e-3` for inference mode batch norm |
| `full_like` not imported | Used `full_like` without adding to extensor import | Mojo compilation error: `full_like` undefined | Add `full_like` to extensor import before using it |
| `_make_ones_grad(fwd: NumericalForward, x)` helper | Helper takes NumericalForward trait parameter to compute forward internally | Mojo `def` functions cannot take trait parameters directly | Use `_ones_grad(output: AnyTensor)` taking the already-computed output |
| Skipping non-uniform pattern for small inputs | Assumed small tensors ([2,4,4,4]) avoid cancellation | Cancellation is structural (math), not statistical — size doesn't matter | The zero-sum property is inherent to batch norm math, not input size |
| `List[Int](1, 3, 6, 6)` literal syntax for shapes | Used list literal constructor | Deprecated syntax flagged by pre-commit hook | Always use `List[Int]()` + `.append()` calls for shape construction |
| Reusing conv2d forward closure directly for batch norm | `fn forward(x): return batch_norm2d(x, ...)[0]` returning full tensor | `compute_numerical_gradient` sums all output elements — equivalent to ones upstream (same cancellation) | The closure must compute the scalar loss explicitly |
| Gamma shape `[C, H, W]` for 4D layer norm | Used 3D gamma for 4D input | Implementation uses flat `[C*H*W]` for 4D inputs | Verify gamma shape convention matches the implementation |
| Create a new standalone testing doc | Draft new `normalization-testing-guide.md` | Duplication; belongs in the existing shared guide | Extend the existing doc; don't create parallel documentation |

## Results & Parameters

### Required Imports

```mojo
from shared.testing import (
    compute_numerical_gradient,
    assert_gradients_close,
)
from shared.testing.gradient_checker import check_gradient
from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like, full_like
from shared.core.normalization import (
    batch_norm2d, batch_norm2d_backward,
    layer_norm, layer_norm_backward,
)
from shared.core.conv import conv2d, conv2d_backward, depthwise_conv2d, depthwise_conv2d_backward
from shared.core.pooling import maxpool2d, avgpool2d, maxpool2d_backward, avgpool2d_backward
from shared.core.arithmetic import multiply
from shared.core.reduction import sum as reduce_sum
```

### Gradient Return Types

```text
GradientTriple (Conv2dBackwardResult, DepthwiseConv2dBackwardResult):
  .grad_input   → gradient w.r.t. input x
  .grad_weights → gradient w.r.t. kernel/weights (NOT .grad_kernel for depthwise)
  .grad_bias    → gradient w.r.t. bias

GradientPair (Conv2dNoBiasBackwardResult):
  .grad_a → gradient w.r.t. input x
  .grad_b → gradient w.r.t. kernel

layer_norm_backward / batch_norm2d_backward return tuples:
  result[0] → grad_input
  result[1] → grad_gamma
  result[2] → grad_beta
```

### Migration Decision Tree

```text
Writing or migrating a gradient checking test?
├─ Is this a meta-test that checks Bool return of check_gradients()?
│   └─ YES → Keep check_gradients() (test_gradient_checker_meta, test_gradient_checker_noncont_tensors)
└─ NO → Use check_gradient() with:
    ├─ Normalization layer? → Non-uniform or sum(output^2) grad_output
    └─ All other layers → _ones_grad(output) helper
    ├─ Old tolerance=X → rtol=X, atol=1e-2 (normal) or atol=1e-4 (large values)
    └─ Always: non-uniform inputs (Float32(i) * 0.1)
```

### CI Workflow Update

```yaml
- name: "Core Gradient"
  path: "tests/shared/core"
  pattern: "... test_gradient_checking_conv2d.mojo test_backward_conv_padding.mojo
    test_depthwise_conv_grad_check_part1.mojo test_depthwise_conv_grad_check_part2.mojo ..."
  continue-on-error: true
```

Insert new test files alphabetically in the `pattern` field.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | BatchNorm backward gradient tests (PRs #3816, #4780) | Sum-of-squares loss pattern for normalization |
| ProjectOdyssey | Conv2d gradient checking (PRs #3865, #3772, #4793, #4809) | All 3 outputs × 3 configs |
| ProjectOdyssey | Depthwise conv2d gradient checking (PR #4794, issue #3775) | Part1+Part2 split files |
| ProjectOdyssey | check\_gradient migration — PR #5107, PR #5210 (59 calls across 5 files) | Migration complete |
| ProjectOdyssey | LayerNorm param gradients (PR #4806, issue #3810) | grad\_gamma and grad\_beta |
| ProjectOdyssey | Pool backward tester (PR #4782, issue #3720) | Three-tier pattern |
| ProjectOdyssey | Conv2d analytical value tests (PRs #4797, #4799, issue #3235) | Batch+padding formulas |
