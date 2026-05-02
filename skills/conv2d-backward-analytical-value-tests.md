---
name: conv2d-backward-analytical-value-tests
description: "Use when: (1) writing conv2d_backward tests that verify exact gradient values (not just shapes), (2) using all-ones configs for analytically tractable batch accumulation or multi-channel verification, (3) verifying grad_bias=batch*out_H*out_W, grad_weights=batch*1.0, grad_input=out_channels, (4) testing padding>0 border pixel gradient reduction analytically"
category: testing
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [conv2d, backward-pass, analytical-values, mojo, batch-accumulation, multi-channel, padding, border-pixels]
---
## Overview

| Field | Value |
|-------|-------|
| **Topic** | Analytically tractable value tests for conv2d backward pass |
| **Approach** | All-ones configuration with exact expected values derived analytically |
| **Key outputs verified** | `grad_input`, `grad_weights`, `grad_bias` — exact floating-point values |
| **Configurations covered** | Single-channel, multi-channel (in_ch=3, out_ch=8), batched (batch=2), padding=1 |
| **Language** | Mojo |
| **API** | `conv2d_backward(grad_output, x, kernel, stride, padding)` |

## When to Use

1. Need to verify exact gradient values, not just shapes or finite-difference proximity
2. Adding batch>1 backward tests — `grad_bias` and `grad_weights` must accumulate over batch
3. Existing tests only cover single-channel (`in_channels=1, out_channels=1`) backward passes
4. Verifying that border pixels receive fewer gradient contributions than interior pixels (padding>0)
5. Writing analytically verifiable tests without relying on numerical differentiation infrastructure

## Verified Workflow

### Quick Reference

**All-ones formula table (padding=0, spatial=kH=kW, → single output position):**

| Gradient | Formula | Example (in_ch=3, out_ch=8, batch=1) |
|----------|---------|--------------------------------------|
| `grad_weights[oc,ic,kh,kw]` | `batch * 1.0` | `1.0` |
| `grad_input[b,ic,ih,iw]` | `out_channels * 1.0` | `8.0` |
| `grad_bias[oc]` | `batch * out_H * out_W` | `1.0` (out is 1×1) |

**Batched formula (batch=2, spatial=3, kernel=3, → out is 1×1):**

| Gradient | Expected value |
|----------|---------------|
| `grad_bias[oc]` | `2.0` (= batch * 1 * 1) |
| `grad_weights[oc,ic,kh,kw]` | `2.0` (= batch * 1.0) |
| `grad_input[b,ic,ih,iw]` | `8.0` (= out_channels) |

**Padding=1 border pixel formula (all-ones, padding=1, kernel=3, out_ch=C, spatial=N):**

```
grad_input[b,ic,ih,iw] = out_channels × overlap_h(ih) × overlap_w(iw)

h_overlap(0) = h_overlap(N-1) = 2  (border row covered by 2 output rows)
h_overlap(1..N-2) = 3              (interior row covered by 3 output rows)

corner (0,0):        2×2 = 4  → 4 × C
edge non-corner (0,1): 2×3 = 6 → 6 × C
interior (1,1):      3×3 = 9  → 9 × C
```

For C=8, N=5: corner=32.0, edge=48.0, interior=72.0.

### Step 1: Choose analytically tractable setup

Use all-ones input, all-ones kernel, zero bias, `stride=1, padding=0`, and spatial size that yields exactly `out_H = out_W = 1` (i.e., `input_spatial = kernel_spatial`).

```mojo
var batch = 1
var in_channels = 3
var out_channels = 8
var kH = 3; var kW = 3
var stride = 1; var padding = 0
# input shape: (1, 3, 3, 3) → output shape: (1, 8, 1, 1)
```

Single output position makes expected values trivially computable without numerical tools.

### Step 2: Implement multi-channel shapes test

```mojo
fn test_conv2d_backward_multichannel_shapes() raises:
    var batch = 1; var in_channels = 3; var out_channels = 8
    var in_height = 6; var in_width = 6; var kH = 3; var kW = 3
    var stride = 1; var padding = 1  # same-padding preserves spatial dims

    var input_shape = List[Int]()
    input_shape.append(batch); input_shape.append(in_channels)
    input_shape.append(in_height); input_shape.append(in_width)
    var x = ones(input_shape, DType.float32)

    var kernel_shape = List[Int]()
    kernel_shape.append(out_channels); kernel_shape.append(in_channels)
    kernel_shape.append(kH); kernel_shape.append(kW)
    var kernel = ones(kernel_shape, DType.float32)

    var bias_shape = List[Int]()
    bias_shape.append(out_channels)
    var bias = zeros(bias_shape, DType.float32)

    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)

    assert_equal(result.grad_input.shape()[0], batch)
    assert_equal(result.grad_input.shape()[1], in_channels)
    assert_equal(result.grad_weights.shape()[0], out_channels)
    assert_equal(result.grad_weights.shape()[1], in_channels)
    assert_equal(result.grad_bias.shape()[0], out_channels)
```

### Step 3: Implement multi-channel values test (padding=0, single spatial output)

```mojo
fn test_conv2d_backward_multichannel_values() raises:
    var batch = 1; var in_channels = 3; var out_channels = 8
    var kH = 3; var kW = 3; var stride = 1; var padding = 0
    # (1,3,3,3) all ones — 3x3 input, 3x3 kernel → (1,8,1,1) output

    var input_shape = List[Int]()
    input_shape.append(batch); input_shape.append(in_channels)
    input_shape.append(3); input_shape.append(3)
    var x = ones(input_shape, DType.float32)

    var kernel_shape = List[Int]()
    kernel_shape.append(out_channels); kernel_shape.append(in_channels)
    kernel_shape.append(kH); kernel_shape.append(kW)
    var kernel = ones(kernel_shape, DType.float32)

    var bias_shape = List[Int]()
    bias_shape.append(out_channels)
    var bias = zeros(bias_shape, DType.float32)

    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)

    # grad_weights[oc,ic,kh,kw] = 1.0 (1 spatial pos, all-ones input)
    var n_weights = out_channels * in_channels * kH * kW
    var grad_weights_data = result.grad_weights._data.bitcast[Float32]()
    for i in range(n_weights):
        assert_almost_equal(grad_weights_data[i], Float32(1.0), tolerance=1e-4)

    # grad_input[b,ic,ih,iw] = out_channels = 8.0
    var n_inputs = batch * in_channels * 3 * 3
    var grad_input_data = result.grad_input._data.bitcast[Float32]()
    for i in range(n_inputs):
        assert_almost_equal(grad_input_data[i], Float32(out_channels), tolerance=1e-4)

    # grad_bias[oc] = 1.0 (1 spatial pos, 1 batch item)
    var grad_bias_data = result.grad_bias._data.bitcast[Float32]()
    for oc in range(out_channels):
        assert_almost_equal(grad_bias_data[oc], Float32(1.0), tolerance=1e-4)
```

### Step 4: Implement batched grad_bias test (batch=2)

```mojo
fn test_conv2d_backward_batched_grad_bias() raises:
    """Verify grad_bias accumulates correctly over batch dimension.
    Config: batch=2, in_channels=3, out_channels=8, spatial=3x3, kernel=3x3
    stride=1, padding=0 -> output shape: (2, 8, 1, 1)
    grad_bias[oc] = batch * out_H * out_W = 2.0
    """
    var batch = 2
    var in_channels = 3; var out_channels = 8
    var kH = 3; var kW = 3
    var stride = 1; var padding = 0

    var input_shape = List[Int]()
    input_shape.append(batch); input_shape.append(in_channels)
    input_shape.append(3); input_shape.append(3)
    var x = ones(input_shape, DType.float32)

    var kernel_shape = List[Int]()
    kernel_shape.append(out_channels); kernel_shape.append(in_channels)
    kernel_shape.append(kH); kernel_shape.append(kW)
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
```

### Step 5: Implement batched grad_weights test (batch=2)

```mojo
fn test_conv2d_backward_batched_grad_weights() raises:
    """Verify grad_weights and grad_input accumulate over batch dimension.
    grad_weights[oc, ic, kh, kw] = 2.0 (sum over batch=2)
    grad_input[b, ic, ih, iw] = 8.0 (out_channels)
    """
    # (same setup as batched_grad_bias, batch=2)

    var grad_weights_data = result.grad_weights._data.bitcast[Float32]()
    var n_weights = out_channels * in_channels * kH * kW
    for i in range(n_weights):
        assert_almost_equal(grad_weights_data[i], Float32(2.0), tolerance=1e-4)

    var grad_input_data = result.grad_input._data.bitcast[Float32]()
    var n_inputs = batch * in_channels * 3 * 3
    for i in range(n_inputs):
        assert_almost_equal(grad_input_data[i], Float32(Float32(out_channels)), tolerance=1e-4)
```

### Step 6: Padding=1 border pixel value test

Derive expected values using the overlap formula:

```mojo
fn test_conv2d_backward_multichannel_padding1_values() raises:
    """Test conv2d_backward computes correct gradient values with padding=1.
    For all-ones, padding=1, kernel=3, out_channels=8, spatial=5:
      corner (0,0):      2×2 = 4 → 4×8 = 32.0
      edge (0,1):        2×3 = 6 → 6×8 = 48.0
      interior (1,1):    3×3 = 9 → 9×8 = 72.0
    """
    var batch = 1; var in_channels = 3; var out_channels = 8
    var in_height = 5; var in_width = 5
    var kH = 3; var kW = 3; var stride = 1; var padding = 1

    var x = ones(input_shape, DType.float32)
    var kernel = ones(kernel_shape, DType.float32)
    var bias = zeros(bias_shape, DType.float32)

    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)
    var grad_input = result.grad_input

    # Verify shape preserved (same-padding)
    assert_equal(grad_input.shape()[2], in_height)
    assert_equal(grad_input.shape()[3], in_width)

    var grad_input_data = grad_input._data.bitcast[Float32]()

    # Check all in_channels (symmetry: all-ones kernel)
    for ic in range(in_channels):
        var base = ic * in_height * in_width
        assert_almost_equal(grad_input_data[base + 0], Float32(32.0), tolerance=1e-3)           # corner (0,0)
        assert_almost_equal(grad_input_data[base + 1], Float32(48.0), tolerance=1e-3)           # edge (0,1)
        assert_almost_equal(grad_input_data[base + 1*in_width+1], Float32(72.0), tolerance=1e-3) # interior (1,1)

    # Directional invariant: border < interior
    assert_true(grad_input_data[0] < grad_input_data[1])
    assert_true(grad_input_data[1] < grad_input_data[1*in_width+1])
```

### Step 7: Value access pattern

```mojo
# Flat index access for gradient verification
var data = tensor._data.bitcast[Float32]()
assert_almost_equal(data[i], expected, tolerance=1e-4)
```

Note: `assert_almost_equal` takes `tolerance: Float32`, NOT `rtol`/`atol`.

### Step 8: grad_output shape — pass output.shape() directly

```mojo
var grad_output = ones(output.shape(), DType.float32)
```

Do NOT hardcode the grad_output shape — use the computed output shape.

### Step 9: Create a dedicated file for batch tests

```mojo
"""Tests for conv2d backward pass with batch>1 and/or multi-channel verification."""
```

Create a new file (e.g., `test_backward_conv_pool_batch.mojo`) to keep batch tests organized separately.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `rtol`/`atol` in assert_almost_equal | Passed `rtol=1e-2, atol=1e-2` as keyword args | `assert_almost_equal` takes `tolerance: Float32`, not `rtol`/`atol` | Always check the actual Mojo function signature — differs from PyTorch/numpy |
| Adding tests to existing file | Considered adding to `test_backward_conv_pool.mojo` | File already had many tests; creating a dedicated file keeps concerns separated | Create a dedicated `_batch.mojo` file for batch-specific tests |
| Using `randn` for test inputs | Considered seeded random inputs for variety | Seed-not-wired bug from prior learnings makes randn unreliable | Use deterministic all-ones/all-zeros — always analytically verifiable |
| Using list literals for shapes | `List[Int](1, 3, 6, 6)` | Deprecated syntax flagged by pre-commit hook | Always use `List[Int]()` + `.append()` calls for shape construction |
| Using `padding=2` for smaller overlap | Larger padding → more zero-padded region | Over-complicates analytical derivation; output spatial changes unless carefully sized | Stick to same-padding (padding=1, kernel=3) so output spatial = input spatial |
| Setting `tolerance=1e-5` for padded test | Same as the no-padding values test | Large spatial sums (up to 72.0) accumulate more floating-point error | Use `tolerance=1e-3` for sums over many elements |

## Results & Parameters

### Working configurations

```
Multi-channel shapes test: batch=1, in_channels=3, out_channels=8, spatial=6x6, kH=kW=3, stride=1, padding=1
Multi-channel values test: batch=1, in_channels=3, out_channels=8, spatial=3x3, kH=kW=3, stride=1, padding=0
Batched test:              batch=2, in_channels=3, out_channels=8, spatial=3x3, kH=kW=3, stride=1, padding=0
Padding=1 value test:      batch=1, in_channels=3, out_channels=8, spatial=5x5, kH=kW=3, stride=1, padding=1
```

### Tolerance by test type

| Test type | tolerance | Reason |
|-----------|-----------|--------|
| All-ones, 1×1 output (padding=0) | `1e-4` | Small sums, no accumulation error |
| All-ones, padding=1, large sums | `1e-3` | Sums up to 72.0 need slightly looser tolerance |

### Key invariants (sanity check)

```
With all-ones, padding=0, input_spatial=kernel_spatial:
- Output spatial = 1 (single output position)
- grad_weights = input value = 1.0
- grad_input = sum over output channels × kernel × grad = out_channels × 1.0
- grad_bias = sum over spatial × batch = 1.0 (single pos, single batch)

With batch>1, same config:
- grad_bias multiplies by batch
- grad_weights multiplies by batch
- grad_input unchanged (per-sample, not summed over batch)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3235, PR (multi-channel shapes+values) | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3783, PR #4797 (batched grad_bias + grad_weights) | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3785, PR #4799 (padding=1 border pixel formula) | [notes.md](../references/notes.md) |
