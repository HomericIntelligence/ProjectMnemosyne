---
name: conv2d-backward-padding-gradient-tests
description: "Add numerical gradient checks for conv2d_backward with padding > 0 in Mojo. Use when: (1) existing conv backward tests only cover padding=0, (2) need to exercise boundary handling in transposed convolution for grad_input, (3) extending padding coverage to padding=1 and padding=2."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | conv2d-backward-padding-gradient-tests |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | Gradient correctness with padding > 0 (boundary handling) |
| **Resolution** | New test file `test_backward_conv_padding.mojo` with 4 `check_gradient` tests |

## When to Use

- Existing conv2d backward numerical gradient tests only cover `padding=0`
- Need to validate the transposed convolution boundary-handling path for `grad_input` (only triggered when `padding > 0`)
- Adding `padding=1` (same-size output) or `padding=2` (extended output) coverage to a backward test suite
- The existing test files are full (ADR-009 ≤10 limit) and cannot accept more tests
- Want to verify `grad_weights` with padded boundary accumulation paths

## Verified Workflow

### Quick Reference

| padding | Input shape | Output shape | Boundary condition exercised |
|---------|------------|--------------|------------------------------|
| 1 | `(1,1,4,4)` | `(1,1,4,4)` | Every position adjacent to padding |
| 2 | `(1,1,5,5)` | `(1,1,7,7)` | Kernel extends entirely into padding region |

### Step 1: Check existing test files for capacity

ADR-009 caps each test file at ≤10 `fn test_` functions. Before adding to an existing file, count its test functions:

```bash
grep -c "^fn test_" <test-root>/test_backward_conv_pool.mojo
```

If the file is at or over 10, create a new file (e.g., `test_backward_conv_padding.mojo`).

### Step 2: Create the new test file

Use this header (required for ADR-009 compliance):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_backward_conv_pool.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Numerical gradient tests for conv2d_backward with padding > 0."""

from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like
from shared.core.conv import conv2d, conv2d_backward
from shared.testing import check_gradient
```

### Step 3: Use non-uniform `grad_output` to avoid boundary cancellation

**Critical insight**: With `padding > 0`, uniform `grad_output` (e.g., `ones_like`) can produce
zero net gradient at boundary positions due to symmetric cancellation across padded zeros.
Use a non-uniform `grad_output` to ensure all gradient paths carry distinct signal:

```mojo
var grad_output = zeros_like(output)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = (
        Float32(i % 4) * Float32(0.25) - Float32(0.3)
    )
```

This pattern (`i % 4 * 0.25 - 0.3`) produces values `-0.3, -0.05, 0.2, 0.45` cycling through
all output positions, ensuring no position receives zero gradient.

### Step 4: Add `grad_input` test for padding=1

```mojo
fn test_conv2d_backward_grad_input_padding1() raises:
    """Numerical gradient check for grad_input with padding=1."""
    var input_shape = List[Int]()
    input_shape.append(1); input_shape.append(1)
    input_shape.append(4); input_shape.append(4)
    var x = zeros(input_shape, DType.float32)
    for i in range(16):
        x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

    var kernel_shape = List[Int]()
    kernel_shape.append(1); kernel_shape.append(1)
    kernel_shape.append(3); kernel_shape.append(3)
    var kernel = zeros(kernel_shape, DType.float32)
    for i in range(9):
        kernel._data.bitcast[Float32]()[i] = Float32(i) * 0.05 + 0.1

    var bias_shape = List[Int]()
    bias_shape.append(1)
    var bias = zeros(bias_shape, DType.float32)

    fn forward_input(inp: ExTensor) raises -> ExTensor:
        return conv2d(inp, kernel, bias, stride=1, padding=1)

    fn backward_input(grad_out: ExTensor, inp: ExTensor) raises -> ExTensor:
        var grads = conv2d_backward(grad_out, inp, kernel, stride=1, padding=1)
        return grads.grad_input

    var output = forward_input(x)
    var grad_output = zeros_like(output)
    for i in range(16):
        grad_output._data.bitcast[Float32]()[i] = (
            Float32(i % 4) * Float32(0.25) - Float32(0.3)
        )
    check_gradient(forward_input, backward_input, x, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 5: Add `grad_weights` test for padding=1

Same setup; pass `kernel` as the variable and capture `x` in the closure:

```mojo
fn test_conv2d_backward_grad_weights_padding1() raises:
    """Numerical gradient check for grad_weights with padding=1."""
    # (same x and kernel setup as above)

    fn forward_weights(k: ExTensor) raises -> ExTensor:
        return conv2d(x, k, bias, stride=1, padding=1)

    fn backward_weights(grad_out: ExTensor, k: ExTensor) raises -> ExTensor:
        var grads = conv2d_backward(grad_out, x, k, stride=1, padding=1)
        return grads.grad_weights

    var output = forward_weights(kernel)
    var grad_output = zeros_like(output)
    for i in range(16):
        grad_output._data.bitcast[Float32]()[i] = (
            Float32(i % 4) * Float32(0.25) - Float32(0.3)
        )
    check_gradient(forward_weights, backward_weights, kernel, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 6: Repeat for padding=2 with larger input

Use `(1,1,5,5)` input → `(1,1,7,7)` output (49 elements). Iterate over 49 elements for `grad_output`:

```mojo
# padding=2 output size: (1,1,7,7) = 49 elements
for i in range(49):
    grad_output._data.bitcast[Float32]()[i] = (
        Float32(i % 4) * Float32(0.25) - Float32(0.3)
    )
```

### Step 7: Call all 4 tests from `main()`

```mojo
fn main() raises:
    print("Running conv2d_backward numerical gradient tests with padding > 0...")
    test_conv2d_backward_grad_input_padding1()
    print("✓ test_conv2d_backward_grad_input_padding1")
    test_conv2d_backward_grad_weights_padding1()
    print("✓ test_conv2d_backward_grad_weights_padding1")
    test_conv2d_backward_grad_input_padding2()
    print("✓ test_conv2d_backward_grad_input_padding2")
    test_conv2d_backward_grad_weights_padding2()
    print("✓ test_conv2d_backward_grad_weights_padding2")
    print("All conv2d_backward padding gradient tests passed!")
```

### Step 8: Run the new test file

```bash
just test-group "tests/shared/core" "test_backward_conv_padding.mojo"
```

Expected output:

```text
Running conv2d_backward numerical gradient tests with padding > 0...
✓ test_conv2d_backward_grad_input_padding1
✓ test_conv2d_backward_grad_weights_padding1
✓ test_conv2d_backward_grad_input_padding2
✓ test_conv2d_backward_grad_weights_padding2
All conv2d_backward padding gradient tests passed!
✅ PASSED: tests/shared/core/test_backward_conv_padding.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding to `test_backward_conv_pool.mojo` | Planned to insert 4 tests into existing file | File already has 11 tests (over ADR-009 ≤10 limit) | Always `grep -c "^fn test_"` existing files before adding; create new file if at/over limit |
| Adding to `test_gradient_checking_dtype.mojo` | Considered adding padding=1 tests there | File already full at 10/10 with note "Budget is FULL" in main() | Read the `main()` docstring — it often documents the capacity status |
| Using `ones_like(output)` as `grad_output` | Copied pattern from padding=0 tests | With padding > 0, symmetric boundary positions get uniform gradient → potential cancellation; non-uniform is safer | Always use non-uniform `grad_output` when testing padded convolutions |

## Results & Parameters

### Tensor Shapes

| padding | Input | Kernel | Output | grad_output elements |
|---------|-------|--------|--------|---------------------|
| 1 | `(1,1,4,4)` | `(1,1,3,3)` | `(1,1,4,4)` | 16 |
| 2 | `(1,1,5,5)` | `(1,1,3,3)` | `(1,1,7,7)` | 49 |

### Tolerance Settings

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `rtol` | `1e-2` | Matches existing conv2d backward tests; padding adds boundary accumulation error |
| `atol` | `1e-2` | Same as existing conv2d backward tests |
| `epsilon` | auto (default) | `check_gradient` auto-selects `1e-4` for float32 |

### Non-Uniform `grad_output` Pattern

```mojo
# Cycles -0.3, -0.05, 0.2, 0.45 across output positions
for i in range(numel):
    grad_output._data.bitcast[Float32]()[i] = (
        Float32(i % 4) * Float32(0.25) - Float32(0.3)
    )
```

### Initialization Pattern

```mojo
# Input: 0.0, 0.1, 0.2, ..., 1.5 (for 16 elements) or 2.4 (for 25 elements)
for i in range(numel):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

# Kernel: 0.1, 0.15, 0.2, ..., 0.5 (for 9 elements)
for i in range(9):
    kernel._data.bitcast[Float32]()[i] = Float32(i) * 0.05 + 0.1
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3817, PR #4809 | [notes.md](../references/notes.md) |
