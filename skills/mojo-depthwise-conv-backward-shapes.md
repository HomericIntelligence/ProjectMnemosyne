---
name: mojo-depthwise-conv-backward-shapes
description: 'Pattern for adding shape-verification tests for depthwise conv backward
  passes in Mojo. Use when: adding backward tests for depthwise conv variants, verifying
  DepthwiseConv2dNoBiasGradient shapes, mirroring existing conv_no_bias_backward shape
  tests.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
| ---------- | ------- |
| **Skill name** | mojo-depthwise-conv-backward-shapes |
| **Category** | testing |
| **Mojo version** | 0.26.1 |
| **File** | `tests/shared/core/test_conv.mojo` |
| **Related issue** | #3787 (follow-up from #3234) |

## When to Use

- Adding a backward-pass shape test for `depthwise_conv2d_no_bias_backward` to mirror `test_conv2d_no_bias_backward_shapes()`
- Verifying that `DepthwiseConv2dNoBiasGradient` fields `grad_input` and `grad_weights` have the correct shapes
- Extending test coverage for depthwise convolution variants when a regular conv variant already has a test

## Verified Workflow

### Quick Reference

```mojo
fn test_depthwise_conv2d_no_bias_backward_shapes() raises:
    """Test that depthwise_conv2d_no_bias_backward returns correct gradient shapes."""
    var batch = 1
    var channels = 3
    var in_height = 5
    var in_width = 5
    var kH = 3
    var kW = 3
    var stride = 1
    var padding = 0

    var input_shape = List[Int]()
    input_shape.append(batch)
    input_shape.append(channels)
    input_shape.append(in_height)
    input_shape.append(in_width)
    var x = ones(input_shape, DType.float32)

    # Depthwise kernel shape: (channels, 1, kH, kW)
    var kernel_shape = List[Int]()
    kernel_shape.append(channels)
    kernel_shape.append(1)
    kernel_shape.append(kH)
    kernel_shape.append(kW)
    var kernel = ones(kernel_shape, DType.float32)

    var output = depthwise_conv2d_no_bias(x, kernel, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)

    var result = depthwise_conv2d_no_bias_backward(
        grad_output, x, kernel, stride, padding
    )
    var grad_input = result.grad_input
    var grad_weights = result.grad_weights

    # grad_input should match input shape
    assert_equal(grad_input.shape()[0], batch)
    assert_equal(grad_input.shape()[1], channels)
    assert_equal(grad_input.shape()[2], in_height)
    assert_equal(grad_input.shape()[3], in_width)

    # grad_weights should match depthwise kernel shape: (channels, 1, kH, kW)
    assert_equal(grad_weights.shape()[0], channels)
    assert_equal(grad_weights.shape()[1], 1)
    assert_equal(grad_weights.shape()[2], kH)
    assert_equal(grad_weights.shape()[3], kW)
```

### Step 1: Identify the existing analog

Find the existing regular conv variant test (e.g., `test_conv2d_no_bias_backward_shapes()`) and
note the line range. The depthwise test should be inserted immediately after it, before the next
multichannel test.

### Step 2: Extend the import block

Add the depthwise functions to the existing `from shared.core.conv import (...)` block:

```mojo
from shared.core.conv import (
    conv2d,
    conv2d_no_bias,
    conv2d_backward,
    conv2d_no_bias_backward,
    depthwise_conv2d_no_bias,          # add
    depthwise_conv2d_no_bias_backward, # add
)
```

### Step 3: Key shape difference from regular conv

Regular conv kernel: `(out_channels, in_channels, kH, kW)`

Depthwise conv kernel: `(channels, 1, kH, kW)` — second dim is always `1`

The `grad_weights` assertion must check `shape()[1] == 1`, not `shape()[1] == in_channels`.

### Step 4: Wire into `main()`

Insert immediately after the existing `test_conv2d_no_bias_backward_shapes()` call:

```mojo
    test_depthwise_conv2d_no_bias_backward_shapes()
    print("✓ test_depthwise_conv2d_no_bias_backward_shapes")
```

### Step 5: Run and verify

```bash
just test-group "tests/shared/core" "test_conv.mojo"
```

Look for `✓ test_depthwise_conv2d_no_bias_backward_shapes` in the output.

Note: A pre-existing failure in `test_conv2d_backward_gradient_input_with_stride` (stride=2
gradient mismatch) is unrelated to this change.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `in_channels` for kernel depth | Set `kernel_shape.append(in_channels)` at dim 1 | Depthwise kernels always have depth=1, not `in_channels` | Always use `1` for the second kernel dimension in depthwise conv; assert `shape()[1] == 1` |
| Using `grad_kernel` field name | Accessed `result.grad_kernel` as in regular conv test | `DepthwiseConv2dNoBiasGradient` uses `grad_weights`, not `grad_kernel` | Check the return type's actual field names before writing assertions |

## Results & Parameters

**Test configuration that passed:**

```text
batch=1, channels=3, in_height=5, in_width=5, kH=3, kW=3, stride=1, padding=0
Expected grad_input:   (1, 3, 5, 5)
Expected grad_weights: (3, 1, 3, 3)
```

**CI result:** All new assertions pass. Pre-existing unrelated failure in stride=2 gradient test
does not affect this change.

**PR:** HomericIntelligence/ProjectOdyssey#4798
