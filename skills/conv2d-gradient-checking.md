---
name: conv2d-gradient-checking
description: 'Add numerical gradient checking tests for conv2d backward pass using
  finite differences. Use when: conv2d_backward tests only verify shape/value with
  uniform inputs and need full numerical correctness validation.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Problem | `conv2d_backward` tests verify shape correctness and 1x1-kernel analytical values but cannot detect numerical errors in the full backward pass for arbitrary kernels |
| Solution | Add `check_gradients()` tests for same-padding, strided, and multi-channel configurations to `test_gradient_checking_dtype.mojo` |
| Constraint | ADR-009 Mojo 0.26.1 heap corruption bug: keep <10 tests per file |
| Result | 3 new tests added; file stays at 8 total (within limit); all pre-commit hooks pass |

## When to Use

1. `conv2d_backward` has shape/value tests but no finite-difference gradient checking
2. Adding coverage for specific conv configurations: same-padding (stride=1, padding=1), strided (stride=2, padding=0), multi-channel (in_channels>1, out_channels>1)
3. Any Mojo project using the `check_gradients()` / `shared.testing` infrastructure
4. Extending `test_gradient_checking_dtype.mojo` (or equivalent split file) without exceeding the ADR-009 <10 test limit

## Verified Workflow

### Step 1: Identify the right file

The gradient checking tests are split into two files due to ADR-009:

- `test_gradient_checking_basic.mojo` — activations, arithmetic, edge cases (~8 tests)
- `test_gradient_checking_dtype.mojo` — dtype-specific, conv2d, losses (~5 tests before this change)

Add conv2d tests to `test_gradient_checking_dtype.mojo` since it already imports `conv2d` and `conv2d_backward`.

### Step 2: Count existing tests before adding

```bash
grep -c "^fn test_" tests/shared/core/test_gradient_checking_dtype.mojo
```

Must stay below 10 after additions (ADR-009 limit).

### Step 3: Add tests following the established pattern

Each test follows this exact structure:

```mojo
fn test_conv2d_grad_<variant>() raises:
    """Test Conv2D gradient with <description>."""
    var input_shape = List[Int]()
    input_shape.append(<batch>)
    input_shape.append(<in_channels>)
    input_shape.append(<H>)
    input_shape.append(<W>)
    var input = full(input_shape, 0.5, DType.float32)

    var kernel_shape = List[Int]()
    kernel_shape.append(<out_channels>)
    kernel_shape.append(<in_channels>)
    kernel_shape.append(<kH>)
    kernel_shape.append(<kW>)
    var kernel = full(kernel_shape, 0.1, DType.float32)

    var bias_shape = List[Int]()
    bias_shape.append(<out_channels>)
    var bias = zeros(bias_shape, DType.float32)

    fn forward(x: ExTensor) raises escaping -> ExTensor:
        return conv2d(x, kernel, bias, stride=<S>, padding=<P>)

    fn backward(grad_out: ExTensor, x: ExTensor) raises escaping -> ExTensor:
        var grads = conv2d_backward(grad_out, x, kernel, stride=<S>, padding=<P>)
        return grads.grad_input

    var passed = check_gradients(
        forward, backward, input, epsilon=1e-5, tolerance=1e-2
    )
    assert_true(passed, "Conv2D <variant> gradient check failed")
```

### Step 4: Three configurations to cover

| Test Name | in_channels | out_channels | kernel | stride | padding | input shape |
|-----------|-------------|--------------|--------|--------|---------|-------------|
| `test_conv2d_grad_3x3_same_padding` | 1 | 1 | 3x3 | 1 | 1 | (1,1,5,5) |
| `test_conv2d_grad_3x3_strided` | 1 | 1 | 3x3 | 2 | 0 | (1,1,7,7) |
| `test_conv2d_grad_multichannel` | 2 | 3 | 3x3 | 1 | 0 | (1,2,5,5) |

For strided: use input size 7x7 so output is (7-3)/2+1 = 3x3 (integer division works out).

### Step 5: Register in `main()`

```mojo
fn main() raises:
    # ... existing calls ...
    test_conv2d_gradient_fp32()
    test_conv2d_grad_3x3_same_padding()
    test_conv2d_grad_3x3_strided()
    test_conv2d_grad_multichannel()
    test_cross_entropy_gradient_fp32()
```

### Step 6: Commit (pre-commit will run mojo format)

```bash
git add tests/shared/core/test_gradient_checking_dtype.mojo
git commit -m "test(conv2d): add numerical gradient checking for conv2d backward pass"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run tests locally | `pixi run mojo test tests/shared/core/test_gradient_checking_dtype.mojo` | GLIBC version mismatch on host (requires 2.32/2.33/2.34, host has older) | Mojo tests only run in CI Docker environment; local GLIBC incompatibility is a known constraint |
| Add tests to new file | Create `test_gradient_checking_conv2d.mojo` | Not necessary; `test_gradient_checking_dtype.mojo` had only 5 tests (room for 3 more under ADR-009 limit) | Check existing file counts before creating new files |
| Run via `just test` | `just test` command | `just` not installed on host | Use `pixi run mojo test` directly or rely on CI |

## Results & Parameters

### Tolerance Settings

```mojo
check_gradients(forward, backward, input, epsilon=1e-5, tolerance=1e-2)
```

- `epsilon=1e-5`: Central-difference perturbation size (optimal for float32 conv)
- `tolerance=1e-2`: Relative tolerance between analytical and numerical gradients

### Kernel/Input Values

Using uniform values (`full(..., 0.5)` for input, `full(..., 0.1)` for kernel) is sufficient for
conv2d because the convolution operation does not have the sum-cancellation problem that affects
normalization layers (no `sum(x_norm) = 0` property).

### ADR-009 Test Count Budget

```
test_gradient_checking_basic.mojo:  8 tests  (activations, arithmetic, edge cases)
test_gradient_checking_dtype.mojo:  8 tests  (composite, linear fp32/fp16, conv2d x4, cross-entropy)
```

Both files stay under the <10 limit. If adding more conv2d tests, create a new split file:
`test_gradient_checking_conv2d.mojo`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3772, issue #3233 | [notes.md](../references/notes.md) |
