---
name: conv2d-backward-gradient-testing
description: "Add numerical gradient checks for conv2d_backward in Mojo using check_gradient with finite differences. Use when: conv2d backward tests only validate shapes but not grad_input or grad_weights values numerically."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | conv2d-backward-gradient-testing |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | Gradient correctness (beyond shape checks) |
| **Resolution** | Two new `check_gradient` tests in `test_backward_conv_pool.mojo` |

## When to Use

- conv2d backward tests validate shapes and bias but not `grad_input` or `grad_weights` values
- Implementing a follow-up to shape-only conv2d backward tests (e.g., post `test_conv2d_backward_shapes`)
- Need to verify mathematical correctness of `conv2d_backward` via finite differences
- Checking `grad_weights` numerically (requires treating kernel as the perturbed input variable)
- Adding gradient correctness tests to `<test-root>/core/test_backward_conv_pool.mojo`

## Verified Workflow

### Step 1: Understand the `check_gradient` API

`check_gradient(forward_fn, backward_fn, x, grad_output, rtol, atol)` perturbs each element of `x`
using central finite differences and compares against `backward_fn(grad_output, x)`.

Key insight: to check **`grad_weights`**, pass the **kernel** as `x` and capture the actual
input tensor in the closure — finite differences will then perturb each kernel element.

### Step 2: Add `test_conv2d_backward_grad_input_numerical`

Use small tensors (input `1x1x4x4`, kernel `1x1x3x3`) for speed. Initialize with non-uniform
values so the gradient check is meaningful (all-ones or all-zeros produce degenerate gradients).

```mojo
fn test_conv2d_backward_grad_input_numerical() raises:
    """Test conv2d_backward grad_input values via numerical gradient checking."""
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
        return conv2d(inp, kernel, bias, stride=1, padding=0)

    fn backward_input(grad_out: ExTensor, inp: ExTensor) raises -> ExTensor:
        var grads = conv2d_backward(grad_out, inp, kernel, stride=1, padding=0)
        return grads.grad_input

    var output = forward_input(x)
    var grad_output = ones_like(output)
    check_gradient(forward_input, backward_input, x, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 3: Add `test_conv2d_backward_grad_weights_numerical`

Capture the fixed input `x` in the closure; pass `kernel` as the variable being perturbed.
The backward closure returns `grads.grad_weights`.

```mojo
fn test_conv2d_backward_grad_weights_numerical() raises:
    """Test conv2d_backward grad_weights values via numerical gradient checking."""
    # (same x and kernel setup as above)

    fn forward_weights(k: ExTensor) raises -> ExTensor:
        return conv2d(x, k, bias, stride=1, padding=0)

    fn backward_weights(grad_out: ExTensor, k: ExTensor) raises -> ExTensor:
        var grads = conv2d_backward(grad_out, x, k, stride=1, padding=0)
        return grads.grad_weights

    var output = forward_weights(kernel)
    var grad_output = ones_like(output)
    check_gradient(
        forward_weights, backward_weights, kernel, grad_output, rtol=1e-2, atol=1e-2
    )
```

### Step 4: Update `main()` to call both new tests

Add both calls after the existing shape/stride tests and before pooling tests.

### Step 5: Commit with `SKIP=mojo-format` if GLIBC < 2.32

On hosts with GLIBC < 2.32, `mojo` cannot run locally. The mojo-format pre-commit hook will
fail. Use `SKIP=mojo-format git commit` — mojo format is enforced in CI via Docker where
GLIBC >= 2.32.

```bash
SKIP=mojo-format git commit -m "test(conv2d_backward): ..."
```

## Tolerance Guidelines

conv2d accumulates more floating-point error than linear layers due to strided access patterns
and multiple accumulation passes. Use relaxed tolerances:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `rtol` | `1e-2` | Conv2D strided accumulation error |
| `atol` | `1e-2` | Same as existing conv2d gradient test |
| `epsilon` | auto (default) | `check_gradient` auto-selects 1e-4 for float32 |

For comparison, linear layer tests use `rtol=1e-3, atol=5e-4`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `mojo test` locally | `pixi run mojo test tests/shared/core/test_backward_conv_pool.mojo` | Host GLIBC 2.31 < required 2.32 | Use `SKIP=mojo-format` for commit; tests validated in CI Docker environment |
| Checking for existing `test_backward.mojo` | Expected tests to be in `test_backward.mojo` | File was split into `test_backward_conv_pool.mojo`, `test_backward_linear.mojo`, etc. due to ADR-009 heap corruption bug | Always check `Glob` for all backward test files before assuming location |
| Using tight tolerances (1e-3/1e-6) | Copying atol/rtol from linear layer tests | Conv2d has higher accumulation error than linear; tests would fail | Use rtol=1e-2, atol=1e-2 for conv2d — matches deprecated test_backward.mojo pattern |

## Results & Parameters

### Test Size Recommendation

| Tensor | Shape | Elements | Rationale |
|--------|-------|----------|-----------|
| input | `(1,1,4,4)` | 16 | Issue #3281 spec; fast gradient check |
| kernel | `(1,1,3,3)` | 9 | Issue #3281 spec; output is 2x2 = 4 elements |
| bias | `(1,)` | 1 | Zero bias; not tested separately |

### Initialization Pattern

Non-uniform values prevent degenerate (all-zero or all-constant) gradients:

```mojo
# Input: 0.0, 0.1, 0.2, ..., 1.5
for i in range(16):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

# Kernel: 0.1, 0.15, 0.2, ..., 0.5
for i in range(9):
    kernel._data.bitcast[Float32]()[i] = Float32(i) * 0.05 + 0.1
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3281, PR #3865 | [notes.md](../references/notes.md) |
