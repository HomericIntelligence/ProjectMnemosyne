---
name: mojo-multichannel-conv2d-backward-tests
description: "Pattern for testing multi-channel Conv2D backward passes in Mojo with analytically tractable gradient verification. Use when: adding backward pass tests for conv layers with multiple input/output channels, verifying grad_input/grad_weights/grad_bias shapes and values."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Language | Mojo |
| Test file | `tests/shared/core/test_conv.mojo` |
| Issue | #3235 (follow-up from #3085) |
| Config tested | `in_channels=3, out_channels=8` |
| API | `conv2d_backward(grad_output, x, kernel, stride, padding)` |

## When to Use

- Adding backward pass tests for Conv2D with `in_channels > 1` or `out_channels > 1`
- Existing tests only cover single-channel (`in_channels=1, out_channels=1`) backward passes
- Need to verify gradient accumulation across input channels and output channels
- Want analytically verifiable gradient values without numerical differentiation

## Verified Workflow

### 1. Identify the backward API

```mojo
var result = conv2d_backward(grad_output, x, kernel, stride, padding)
var grad_input = result.grad_input    # shape: (batch, in_channels, H, W)
var grad_kernel = result.grad_weights # shape: (out_channels, in_channels, kH, kW)
var grad_bias = result.grad_bias      # shape: (out_channels,)
```

Value access via `._data.bitcast[Float32]()[index]`.

### 2. Shape-only test (large spatial, with padding)

Use `in_channels=3, out_channels=8`, `padding=1` to preserve spatial dims:

```mojo
fn test_conv2d_backward_multichannel_shapes() raises:
    var batch = 1; var in_channels = 3; var out_channels = 8
    var in_height = 6; var in_width = 6; var kH = 3; var kW = 3
    var stride = 1; var padding = 1

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

### 3. Values test — analytically tractable config

Use `padding=0`, `3x3 input`, `3x3 kernel` → single spatial output `(1,1)`:

**All-ones setup** makes expected values easy to compute without numerical differentiation:

| Gradient | Expected value | Derivation |
|----------|---------------|------------|
| `grad_weights[oc, ic, kh, kw]` | `1.0` | `sum(grad_out * x) = 1.0 * 1.0` (1 spatial pos) |
| `grad_input[b, ic, ih, iw]` | `8.0` | `sum over 8 oc: grad_out * kernel = 8 * 1.0 * 1.0` |
| `grad_bias[oc]` | `1.0` | `sum(grad_out) = 1.0` (1 spatial pos, 1 batch) |

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

    var n_weights = out_channels * in_channels * kH * kW
    var grad_weights_data = result.grad_weights._data.bitcast[Float32]()
    for i in range(n_weights):
        assert_almost_equal(grad_weights_data[i], Float32(1.0), tolerance=1e-4)

    var n_inputs = batch * in_channels * 3 * 3
    var grad_input_data = result.grad_input._data.bitcast[Float32]()
    for i in range(n_inputs):
        assert_almost_equal(grad_input_data[i], Float32(out_channels), tolerance=1e-4)

    var grad_bias_data = result.grad_bias._data.bitcast[Float32]()
    for oc in range(out_channels):
        assert_almost_equal(grad_bias_data[oc], Float32(1.0), tolerance=1e-4)
```

### 4. Wire into main()

```mojo
test_conv2d_backward_multichannel_shapes()
print("✓ test_conv2d_backward_multichannel_shapes")

test_conv2d_backward_multichannel_values()
print("✓ test_conv2d_backward_multichannel_values")
```

### 5. Pre-commit passes automatically

- Mojo Format hook auto-formats the new functions
- `Validate Test Coverage` hook passes (new `fn test_*` functions are detected)
- No manual formatting step needed

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo test` locally | Executed test directly on host | glibc version too old (requires GLIBC_2.32+, host has older) | CI-only validation is expected on this host; commit and let CI run tests |
| Using `randn` for test inputs | Considered seeded random inputs for variety | seed-not-wired bug from prior learnings makes randn unreliable | Use deterministic special values (ones/zeros) — always analytically verifiable |
| Using list literals for shapes | Attempted `List[Int](1, 3, 6, 6)` | Deprecated syntax flagged by pre-commit hook | Always use `List[Int]()` + `.append()` calls for shape construction |

## Results & Parameters

### Configuration that works

```text
Shape test:  batch=1, in_channels=3, out_channels=8, spatial=6x6, kH=kW=3, stride=1, padding=1
Values test: batch=1, in_channels=3, out_channels=8, spatial=3x3, kH=kW=3, stride=1, padding=0
```

### Key invariant

With all-ones and `padding=0, spatial=kH=kW=3`:
- Output spatial size = `(3-3)/1 + 1 = 1` — single output position makes grad computation trivial
- `grad_weights` = input value at receptive field = 1.0
- `grad_input` = sum over output channels × kernel × grad = out_channels × 1.0 × 1.0

### Value access pattern

```mojo
# Flat index access for gradient verification
var data = tensor._data.bitcast[Float32]()
assert_almost_equal(data[i], expected, tolerance=1e-4)
```
