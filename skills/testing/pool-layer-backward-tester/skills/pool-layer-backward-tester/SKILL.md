---
name: pool-layer-backward-tester
description: "Implement a pooling backward pass tester following the three-tier gradient checking pattern (shape, analytical, numerical). Use when: adding test_pool_layer_backward to a Mojo layer_testers utility, validating MaxPool/AvgPool backward pass gradients, or filling a gap where conv/batchnorm backward testers exist but pooling backward is absent."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | pool-layer-backward-tester |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | Missing pooling backward tester in layer_testers utility |
| **Resolution** | Three-tier gradient checking tester + imports for backward functions |

## When to Use

- `layer_testers.mojo` has `test_conv_layer_backward` and `test_batchnorm_layer_backward` but no `test_pool_layer_backward`
- MaxPool2d/AvgPool2d backward passes exist in `shared.core.pooling` but no reusable tester validates them
- A gradient checking test for pooling layers needs to cover both analytical correctness and numerical validation
- An audit issue references missing pooling backward coverage in the layer testers utility

## Verified Workflow

### Step 1: Read the existing backward tester pattern

Before writing, read `test_conv_layer_backward` and `test_batchnorm_layer_backward` in `layer_testers.mojo` to
match the exact three-tier structure used throughout the file.

```bash
grep -n "test_conv_layer_backward\|test_batchnorm_layer_backward" shared/testing/layer_testers.mojo
```

### Step 2: Import pooling backward functions

Add `maxpool2d_backward` and `avgpool2d_backward` to the existing pooling import block:

```mojo
from shared.core.pooling import (
    maxpool2d,
    avgpool2d,
    pool_output_shape,
    maxpool2d_backward,
    avgpool2d_backward,
)
```

### Step 3: Implement three-tier tester

The function signature should mirror `test_pooling_layer` (forward tester) but add backward-specific params:

```mojo
@staticmethod
fn test_pool_layer_backward(
    channels: Int,
    input_h: Int,
    input_w: Int,
    pool_size: Int,
    stride: Int,
    dtype: DType,
    pool_type: String = "max",
    padding: Int = 0,
) raises:
```

**Tier 1 — Shape check**: Run forward + backward with `ones_like(output)` grad, assert `grad_input.shape() == input.shape()`.

**Tier 2 — Analytical value check**:

- MaxPool: use a tiny 1×1×2×2 input with values `[1, 4, 2, 3]`. With pool_size=2, stride=2, the max is at index 1.
  Assert `gi[1] > 0.5` and `gi[0,2,3] < 1e-6`.
- AvgPool: use a 1×1×2×2 input of all-ones. Assert each grad element equals `1 / (pool_size * pool_size)` within 1e-5.

**Tier 3 — Numerical gradient check**: Use a non-uniform `grad_output` (pattern `i%4 * 0.25 - 0.3`) to avoid
AvgPool gradient cancellation with symmetric inputs. Define a scalar-output forward closure:

```mojo
fn forward_max(x: ExTensor) raises escaping -> ExTensor:
    var pool_out = maxpool2d(x, pool_size, stride, padding=padding)
    var result = ExTensor([1], x.dtype())
    var s: Float64 = 0.0
    for i in range(pool_out.numel()):
        s += pool_out._get_float64(i) * grad_out_nu._get_float64(i)
    result._set_float64(0, s)
    return result^
```

Then compare `analytical_grad` (from `maxpool2d_backward(grad_out_nu, input_small, ...)`) against
`compute_numerical_gradient(forward_max, input_small, epsilon)` using `assert_gradients_close`.

### Step 4: Epsilon and tolerance selection

```
epsilon = GRADIENT_CHECK_EPSILON_FLOAT32  # 3e-4 for float32 (see issue #2704)
          GRADIENT_CHECK_EPSILON_OTHER    # for other dtypes
tolerance: rtol=1e-3, atol=5e-4          # pool backward is simple routing/averaging
```

Pool backward is element-wise routing (MaxPool) or uniform distribution (AvgPool), so much tighter tolerances
apply compared to conv2d (rtol=1e-1) or linear (rtol=0.10).

### Step 5: Commit with SKIP=mojo-format if needed

If the local mojo binary version differs from the pinned version in pixi.toml, pre-commit will fail on mojo-format:

```bash
SKIP=mojo-format git commit -m "feat(testing): add test_pool_layer_backward to layer_testers.mojo"
```

CI runs mojo format with the correct version.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `ones_like(output)` as grad_output for numerical check | Passed `ones_like(output)` as upstream gradient into the scalar closure | AvgPool with symmetric (seeded random) inputs caused gradient cancellation — numerical grad ≈ 0 everywhere | Use non-uniform grad_output (e.g. `i%4 * 0.25 - 0.3`) to break symmetry and prevent cancellation |
| Using `compute_numerical_gradient` directly on the pool output (vector) | Called `compute_numerical_gradient(forward, input, epsilon)` where `forward` returned the raw pool output | The vector-output path sums all Jacobian elements, which works for some layers but can cancel for AvgPool | Wrap the forward fn to compute a weighted dot product with grad_out_nu and return a scalar ExTensor |
| Adding `maxpool2d_backward` import inline with existing single-line import | `from shared.core.pooling import maxpool2d, avgpool2d, pool_output_shape, maxpool2d_backward, avgpool2d_backward` | No actual failure — but the multi-import form is cleaner | Expand single-line imports to parenthesized form when adding backward functions |

## Results & Parameters

### Working function signature

```mojo
LayerTester.test_pool_layer_backward(
    channels=2,
    input_h=4,
    input_w=4,
    pool_size=2,
    stride=2,
    dtype=DType.float32,
    pool_type="max"  # or "avg"
)
```

### Tolerance rationale

| Layer Type | rtol | atol | Reason |
|------------|------|------|--------|
| Pool backward | 1e-3 | 5e-4 | Simple routing/averaging — minimal accumulation error |
| Conv backward | 1e-1 | 1e-1 | Large kernel accumulates floating-point errors |
| Linear backward | 0.10 | 0.10 | Matmul accumulates errors over in_features |
| Activation backward | 1e-2 | 1e-2 | Element-wise but may have saturation regions |

### Analytical tier: known-value inputs

```mojo
# MaxPool: gradient routes to max position only
var x_known = ExTensor([1, 1, 2, 2], dtype)
x_known._set_float64(0, 1.0)  # not max
x_known._set_float64(1, 4.0)  # max — receives gradient
x_known._set_float64(2, 2.0)
x_known._set_float64(3, 3.0)
var go = ExTensor([1, 1, 1, 1], dtype)
go._set_float64(0, 1.0)
var gi = maxpool2d_backward(go, x_known, 2, 2, 0)
# gi[1] > 0.5, gi[0] ≈ gi[2] ≈ gi[3] ≈ 0

# AvgPool: gradient distributed equally (1/k^2 per position)
var x_avg = ExTensor([1, 1, 2, 2], dtype)  # all-ones
for k in range(4): x_avg._set_float64(k, 1.0)
var gi_avg = avgpool2d_backward(go, x_avg, 2, 2, 0)
# Each gi_avg[k] ≈ 0.25 (1/pool_size^2)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3720, PR #4782 | [notes.md](../references/notes.md) |
