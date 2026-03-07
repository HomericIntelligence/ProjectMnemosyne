---
name: conv2d-numerical-gradient-check
description: "Add numerical gradient checks for conv2d_backward grad_input and grad_weights using finite differences. Use when: (1) a conv backward pass lacks numerical validation, (2) verifying transposed convolution gradient correctness, (3) extending existing conv backward tests with gradient checking."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | conv2d-numerical-gradient-check |
| **Category** | testing |
| **Issue** | #3248 |
| **Parent** | #2724 |
| **Files Changed** | `tests/shared/core/test_conv.mojo` |

## When to Use

- A conv2d backward test only validates shapes or bias gradient, not grad_input/grad_weights
- You need to validate transposed convolution paths (highest-risk backward pass operations)
- You want to follow the pattern from `test_batch_norm2d_backward_gradient_input`
- A new backward implementation needs numerical verification

## Verified Workflow

### Step 1: Read existing test file and normalization reference

```bash
# Read the existing conv test file to understand structure
# Read test_normalization.mojo lines 320-380 for the exact pattern to follow
```

### Step 2: Add imports to the test file

```mojo
from shared.core.extensor import ExTensor, zeros, ones, full, ones_like
from shared.testing import (
    compute_numerical_gradient,
    assert_gradients_close,
)
from shared.core.reduction import sum as reduce_sum
```

### Step 3: Add grad_input check function

```mojo
fn test_conv2d_backward_gradient_input() raises:
    var stride = 1
    var padding = 0

    # Small input: (1, 1, 4, 4) — keeps runtime short
    var input_shape = List[Int]()
    input_shape.append(1)
    input_shape.append(1)
    input_shape.append(4)
    input_shape.append(4)
    var x = zeros(input_shape, DType.float32)
    var x_data = x._data.bitcast[Float32]()
    for i in range(16):
        x_data[i] = Float32(i) * Float32(0.1)

    # Kernel: (1, 1, 3, 3)
    var kernel_shape = List[Int]()
    kernel_shape.append(1)
    kernel_shape.append(1)
    kernel_shape.append(3)
    kernel_shape.append(3)
    var kernel = zeros(kernel_shape, DType.float32)
    var k_data = kernel._data.bitcast[Float32]()
    for i in range(9):
        k_data[i] = Float32(i + 1) * Float32(0.5)

    var output = conv2d_no_bias(x, kernel, stride, padding)

    # ones_like grad_output corresponds to sum reduction in the closure
    var grad_output = ones_like(output)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)
    var analytical_grad = result.grad_input

    fn forward_for_input(inp: ExTensor) raises -> ExTensor:
        var out = conv2d_no_bias(inp, kernel, stride, padding)
        var reduced = out
        while reduced.dim() > 0:
            reduced = reduce_sum(reduced, axis=0, keepdims=False)
        return reduced

    var numerical_grad = compute_numerical_gradient(
        forward_for_input, x, epsilon=3e-4
    )

    assert_gradients_close(
        analytical_grad,
        numerical_grad,
        rtol=1e-2,
        atol=1e-4,
        message="conv2d_backward gradient w.r.t. input",
    )
```

### Step 4: Add grad_weights check function (same pattern, perturb kernel)

The kernel test is identical but:
- `forward_for_kernel` captures `x` and takes `k` as argument
- `analytical_grad = result.grad_weights` instead of `result.grad_input`
- Calls `compute_numerical_gradient(forward_for_kernel, kernel, epsilon=3e-4)`

### Step 5: Call both from main()

```mojo
test_conv2d_backward_gradient_input()
print("✓ test_conv2d_backward_gradient_input")

test_conv2d_backward_gradient_kernel()
print("✓ test_conv2d_backward_gradient_kernel")
```

## Results & Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Input shape | (1, 1, 4, 4) | Small enough for fast test, large enough for meaningful gradients |
| Kernel shape | (1, 1, 3, 3) | Standard 3x3 conv, exercises full transposed conv path |
| stride | 1 | Simple case, no stride complications |
| padding | 0 | No-padding case tests grad_input boundary handling |
| epsilon | 3e-4 | Project standard for float32 (from issue #2704) |
| rtol | 1e-2 (1%) | Loose enough for float32 conv, per issue plan |
| atol | 1e-4 | Absolute floor to handle near-zero gradients |
| Input values | `Float32(i) * 0.1` | FP-representable, avoids rounding issues |
| Kernel values | `Float32(i+1) * 0.5` | Non-zero, FP-representable, distinct per element |

## Critical Insight: Closure-to-grad_output Correspondence

The `forward_fn` passed to `compute_numerical_gradient` **must produce a scalar** by reducing
the output. The reduction used determines what `grad_output` to pass to the backward function.

**When using `sum` reduction → use `ones_like(output)` as `grad_output`.**

This is because:
- `loss = sum(conv_output)` → `dL/d_output = ones`
- `grad_input = conv_backward(ones_like(output), x, kernel, ...)`

The numerical gradient then estimates `d(sum(output))/d(input)`, which matches exactly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running mojo locally | `pixi run mojo run tests/shared/core/test_conv.mojo` | GLIBC version mismatch (requires 2.32+, host has 2.31) | Mojo must run in Docker; rely on CI for test validation |
| Using `just` commands | `just test-mojo` | `just` not installed on the host system | Use Docker or CI; `just` is a container-level tool |
| Pulling GHCR image | `docker pull ghcr.io/...` | No GHCR images cached locally, containers not running | Must start Docker environment with `just docker-up` before local testing |
