---
name: mojo-conv2d-batched-backward-tests
description: "Pattern for verifying Conv2D backward-pass gradient accumulation over the batch dimension in Mojo. Use when: adding batch>1 backward tests for conv layers, verifying grad_bias = batch * out_H * out_W, verifying grad_weights accumulates over multiple batch items."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Language | Mojo |
| Test file | `tests/shared/core/test_backward_conv_pool_batch.mojo` |
| Issue | #3783 (follow-up from #3235) |
| Config tested | `batch=2, in_channels=3, out_channels=8` |
| API | `conv2d_backward(grad_output, x, kernel, stride, padding)` |
| Pattern | Analytically tractable all-ones setup |

## When to Use

- Existing backward tests only cover `batch=1` and you need `batch>1` coverage
- Verifying `grad_bias[oc]` accumulates over all batch items: `= batch * out_H * out_W`
- Verifying `grad_weights[oc, ic, kh, kw]` accumulates over all batch items: `= batch * 1.0`
- Extending `mojo-multichannel-conv2d-backward-tests` (batch=1) to batched inputs
- Writing a new split file per ADR-009 (≤10 `fn test_` functions per file)

## Verified Workflow

### 1. Choose an analytically tractable setup

Use all-ones input, all-ones kernel, zero bias, `stride=1, padding=0`, and a spatial
size that yields exactly `out_H = out_W = 1` (e.g., `input_spatial = kernel_spatial = 3`).

This makes expected values trivially computable:

- `grad_bias[oc]` = sum over `(batch, oh, ow)` of `grad_output[b, oc, oh, ow]`
  = `batch * out_H * out_W * 1.0`
- `grad_weights[oc, ic, kh, kw]` = sum over `(batch, oh, ow)` of `grad_output * x`
  = `batch * 1.0`
- `grad_input[b, ic, ih, iw]` = sum over `oc` of `kernel * grad_output`
  = `out_channels * 1.0`

### 2. Split into a new file (ADR-009)

Create a new file (e.g., `test_backward_conv_pool_batch.mojo`) rather than adding to
an existing file, to stay under the ≤10 `fn test_` limit per ADR-009.

### 3. File skeleton

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
"""Tests for conv2d backward pass with batch>1."""

from tests.shared.conftest import assert_almost_equal, assert_equal
from shared.core.extensor import ExTensor, zeros, ones
from shared.core.conv import conv2d, conv2d_backward


fn test_conv2d_backward_batched_grad_bias() raises:
    """Verify grad_bias accumulates correctly over batch dimension.

    Config: batch=2, in_channels=3, out_channels=8, spatial=3x3, kernel=3x3
    stride=1, padding=0 -> output shape: (2, 8, 1, 1)
    grad_bias[oc] = batch * out_H * out_W = 2.0
    """
    var batch = 2
    var in_channels = 3
    var out_channels = 8
    var kH = 3
    var kW = 3
    var stride = 1
    var padding = 0

    var input_shape = List[Int]()
    input_shape.append(batch)
    input_shape.append(in_channels)
    input_shape.append(3)
    input_shape.append(3)
    var x = ones(input_shape, DType.float32)

    var kernel_shape = List[Int]()
    kernel_shape.append(out_channels)
    kernel_shape.append(in_channels)
    kernel_shape.append(kH)
    kernel_shape.append(kW)
    var kernel = ones(kernel_shape, DType.float32)

    var bias_shape = List[Int]()
    bias_shape.append(out_channels)
    var bias = zeros(bias_shape, DType.float32)

    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)
    var grad_bias = result.grad_bias

    var grad_bias_data = grad_bias._data.bitcast[Float32]()
    for oc in range(out_channels):
        assert_almost_equal(
            grad_bias_data[oc],
            Float32(2.0),  # batch * out_H * out_W
            tolerance=1e-4,
        )


fn test_conv2d_backward_batched_grad_weights() raises:
    """Verify grad_weights and grad_input accumulate over batch dimension.

    grad_weights[oc, ic, kh, kw] = 2.0 (sum over batch=2)
    grad_input[b, ic, ih, iw] = 8.0 (out_channels)
    """
    # ... same setup, then:
    var grad_weights_data = grad_weights._data.bitcast[Float32]()
    for i in range(n_weights):
        assert_almost_equal(grad_weights_data[i], Float32(2.0), tolerance=1e-4)

    var grad_input_data = grad_input._data.bitcast[Float32]()
    for i in range(n_inputs):
        assert_almost_equal(grad_input_data[i], Float32(Float32(out_channels)), tolerance=1e-4)


fn main() raises:
    test_conv2d_backward_batched_grad_bias()
    test_conv2d_backward_batched_grad_weights()
```

### 4. Access raw tensor data

The `_data.bitcast[Float32]()` pattern is how values are checked in these tests:

```mojo
var grad_bias_data = result.grad_bias._data.bitcast[Float32]()
for i in range(num_elements):
    assert_almost_equal(grad_bias_data[i], Float32(expected), tolerance=1e-4)
```

### 5. Use `ones(shape(), DType.float32)` for grad_output

```mojo
var grad_output = ones(output.shape(), DType.float32)
```

This passes the output's computed shape directly. Do NOT hardcode the shape.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `rtol`/`atol` in assert_almost_equal | Passed `rtol=1e-2, atol=1e-2` as keyword args | `assert_almost_equal` takes `tolerance: Float32`, not `rtol`/`atol` | Always check the actual function signature — the Mojo API differs from PyTorch/numpy |
| Adding tests to existing file | Considered adding to `test_backward_conv_pool.mojo` | Would push the file over the ADR-009 ≤10 fn limit | Create a new `_batch.mojo` split file instead |
| Using `Float32(out_channels)` in assertion | Compared `grad_input_data[i]` against `Float32(out_channels)` where `out_channels` is `Int` | Compiles fine — Int-to-Float32 cast is implicit | Fine to use directly; no explicit cast needed |

## Results & Parameters

**Working configuration**:

| Parameter | Value |
|-----------|-------|
| `batch` | 2 |
| `in_channels` | 3 |
| `out_channels` | 8 |
| `spatial` | 3×3 (input) × 3×3 (kernel) → 1×1 output |
| `stride` | 1 |
| `padding` | 0 |
| `tolerance` | 1e-4 |
| `grad_bias expected` | `batch * out_H * out_W = 2.0` |
| `grad_weights expected` | `batch * 1.0 = 2.0` |
| `grad_input expected` | `out_channels = 8.0` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3783, PR #4797 | [notes.md](../references/notes.md) |
