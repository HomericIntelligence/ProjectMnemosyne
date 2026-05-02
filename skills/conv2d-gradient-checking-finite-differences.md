---
name: conv2d-gradient-checking-finite-differences
description: "Use when: (1) conv2d_backward tests only validate shapes but not grad_input/grad_weights values numerically, (2) adding finite-difference gradient checks for standard conv2d across padding=0, padding>0, stride, and multi-channel configurations, (3) verifying transposed convolution correctness, (4) extending gradient checking coverage to all three backward outputs (grad_input, grad_weights, grad_bias), (5) keeping per-file test count under 10"
category: testing
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [conv2d, gradient-checking, finite-differences, mojo, backward-pass, numerical-gradients, padding]
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Topic** | Numerical gradient checking for conv2d backward pass (standard conv2d) |
| **Approach** | Finite differences via `check_gradient` / `check_gradients` / `compute_numerical_gradient` |
| **Key outputs verified** | `grad_input`, `grad_weights`, `grad_bias` |
| **Configurations covered** | padding=0, padding=1, padding=2, stride=1, stride=2, multi-channel, batched |
| **Language** | Mojo |

## When to Use

1. `conv2d_backward` tests only verify shapes/bias but not `grad_input` or `grad_weights` numerically
2. Existing gradient-checking files are at their per-file test limit and a new dedicated file is needed
3. Adding coverage for specific conv configurations: same-padding (stride=1, padding=1), strided (stride=2, padding=0), multi-channel (in_channels>1, out_channels>1)
4. Validating boundary handling in transposed convolution for `grad_input` when `padding > 0`
5. Creating a dedicated file for all three backward outputs across multiple configurations

## Verified Workflow

### Quick Reference

```bash
# Count tests in existing files before adding
grep -c "^fn test_" <test-root>/test_gradient_checking_*.mojo
grep -c "^fn test_" <test-root>/test_backward_conv_pool.mojo

# Verify new file stays under per-file test limit
grep -c "^fn test_" <test-root>/test_gradient_checking_conv2d.mojo
# Expected: ≤10

# Add to CI pattern
grep -n "Core Gradient" .github/workflows/comprehensive-tests.yml
```

**Tolerance quick-ref:**

| Parameter | Value | API |
|-----------|-------|-----|
| `rtol` | `1e-2` | `check_gradient(forward, backward, x, grad_output, rtol=1e-2, atol=1e-2)` |
| `atol` | `1e-2` | Same as above |
| `epsilon` | `1e-4` (or `3e-4`) | `check_gradients(..., epsilon=1e-4, tolerance=1e-2)` |
| `tolerance` | `1e-2` | `check_gradients` single-arg form |

### Step 1: Identify the right test file

Two APIs exist — pick the one matching your existing tests:

- **`check_gradient(forward_fn, backward_fn, x, grad_output, rtol, atol)`** — from `shared.testing`; requires explicit `grad_output` tensor
- **`check_gradients(forward_fn, backward_fn, x, epsilon, tolerance)`** — from `shared.testing.gradient_checker`; computes `grad_output` internally
- **`compute_numerical_gradient(forward_fn, x, epsilon)` + `assert_gradients_close(...)`** — explicit two-step approach

Files to target by type:
- `test_backward_conv_pool.mojo` — backward-pass numerical checks (uses `check_gradient`)
- `test_gradient_checking_dtype.mojo` — dtype-specific checks (uses `check_gradients`)
- `test_gradient_checking_conv2d.mojo` — dedicated conv2d file when others are full

### Step 2: Count existing tests

```bash
grep -c "^fn test_" <test-root>/test_gradient_checking_dtype.mojo
```

If adding 3+ tests would breach the ≤10 limit, create a new file. Required header for all files:

```mojo
```

### Step 3: Add grad_input numerical check (padding=0)

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

### Step 4: Add grad_weights numerical check

Pass `kernel` as the variable being perturbed; capture `x` in the closure:

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

### Step 5: Padding > 0 — use non-uniform grad_output

**Critical**: With `padding > 0`, uniform `grad_output` (e.g., `ones_like`) can produce zero net gradient at boundary positions due to symmetric cancellation. Use non-uniform:

```mojo
var grad_output = zeros_like(output)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = (
        Float32(i % 4) * Float32(0.25) - Float32(0.3)
    )
# Cycles: -0.3, -0.05, 0.2, 0.45 — no position receives zero gradient
```

Tensor shapes for padding tests:

| padding | Input | Kernel | Output | grad_output elements |
|---------|-------|--------|--------|---------------------|
| 1 | `(1,1,4,4)` | `(1,1,3,3)` | `(1,1,4,4)` | 16 |
| 2 | `(1,1,5,5)` | `(1,1,3,3)` | `(1,1,7,7)` | 49 |

### Step 6: check_gradients pattern (all three outputs, multiple configs)

When using `check_gradients` from `shared.testing.gradient_checker`:

```mojo
fn test_conv2d_grad_<variant>() raises:
    """Test Conv2D gradient with <description>."""
    var input = full(input_shape, 0.5, DType.float32)
    var kernel = full(kernel_shape, 0.1, DType.float32)
    var bias = zeros(bias_shape, DType.float32)

    fn forward(x: ExTensor) raises escaping -> ExTensor:
        return conv2d(x, kernel, bias, stride=<S>, padding=<P>)

    fn backward(grad_out: ExTensor, x: ExTensor) raises escaping -> ExTensor:
        var grads = conv2d_backward(grad_out, x, kernel, stride=<S>, padding=<P>)
        return grads.grad_input  # or grad_weights / grad_bias

    var passed = check_gradients(forward, backward, input, epsilon=1e-4, tolerance=1e-2)
    assert_true(passed, "Conv2D <variant> gradient check failed")
```

Three configurations to cover:

| Config | in_ch | out_ch | kernel | stride | padding | input shape |
|--------|-------|--------|--------|--------|---------|-------------|
| same-padding | 1 | 1 | 3x3 | 1 | 1 | (1,1,5,5) |
| strided | 1 | 1 | 3x3 | 2 | 0 | (1,1,7,7) |
| multi-channel | 2 | 3 | 3x3 | 1 | 0 | (1,2,5,5) |

For strided: use input 7x7 so output is (7-3)/2+1 = 3x3 (integer division works out).

Note: `raises escaping` is required on closures passed to `check_gradients`.

### Step 7: Closure-to-grad_output correspondence

When using `compute_numerical_gradient`, the `forward_fn` must produce a scalar. The reduction used determines what `grad_output` to pass to backward:

```mojo
fn forward_for_input(inp: ExTensor) raises -> ExTensor:
    var out = conv2d_no_bias(inp, kernel, stride, padding)
    var reduced = out
    while reduced.dim() > 0:
        reduced = reduce_sum(reduced, axis=0, keepdims=False)
    return reduced

# Using sum reduction → grad_output = ones_like(output)
var grad_output = ones_like(forward_output)
```

### Step 8: Update CI workflow

Add new test files to the `"Core Gradient"` pattern entry:

```yaml
- name: "Core Gradient"
  path: "tests/shared/core"
  pattern: "... test_gradient_checking_conv2d.mojo test_backward_conv_padding.mojo ..."
  continue-on-error: true
```

Insert alphabetically among other `test_gradient_checking_*.mojo` entries.

### Step 9: Commit (GLIBC / SKIP pattern)

On hosts with GLIBC < 2.32, `mojo` cannot run locally. The mojo-format pre-commit hook will fail. Use `SKIP=mojo-format git commit`:

```bash
SKIP=mojo-format git commit -m "test(conv2d_backward): ..."
```

Mojo format is enforced in CI via Docker where GLIBC >= 2.32.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `mojo test` locally | `pixi run mojo test <test-path>` | GLIBC version mismatch (requires 2.32+, host has 2.31) | Use `SKIP=mojo-format` for commit; tests validated in CI Docker environment |
| Using tight tolerances (1e-3/1e-6) | Copying atol/rtol from linear layer tests | Conv2d has higher accumulation error than linear; tests fail | Use rtol=1e-2, atol=1e-2 for conv2d — matches deprecated test_backward.mojo pattern |
| Using `ones_like(output)` with padding>0 | Copied pattern from padding=0 tests | Symmetric boundary positions get uniform gradient → potential cancellation; non-uniform is safer | Always use non-uniform `grad_output` (`i % 4 * 0.25 - 0.3`) when testing padded convolutions |
| Add tests to new file prematurely | Creating `test_gradient_checking_conv2d.mojo` before checking existing capacity | Existing file had only 5 tests — 3 more would fit | Check `grep -c "^fn test_"` before creating new files |
| Using `check_gradient` (no s) | `from shared.testing import check_gradient` | Different API: `check_gradient` requires explicit `grad_output`; `check_gradients` computes internally | Match the API to the test file — check existing imports |
| Using `just test` locally | `just test` command | `just` not installed on the host | Use `pixi run mojo test` directly or rely on CI |
| Checking for existing `test_backward.mojo` | Expected tests in single file | File was split into `test_backward_conv_pool.mojo`, `test_backward_linear.mojo`, etc. | Always `Glob` for all backward test files before assuming location |

## Results & Parameters

### Recommended test tensor shapes

| Tensor | Shape | Elements | Rationale |
|--------|-------|----------|-----------|
| input (padding=0) | `(1,1,4,4)` | 16 | Fast gradient check, non-trivial output |
| kernel | `(1,1,3,3)` | 9 | Standard 3x3, output is 2x2 = 4 elements |
| input (padding=1) | `(1,1,4,4)` | 16 | Same-size output (4x4) |
| input (padding=2) | `(1,1,5,5)` | 25 | Extended output (7x7) |

### Initialization pattern (non-uniform to prevent degenerate gradients)

```mojo
# Input: 0.0, 0.1, 0.2, ..., 1.5
for i in range(16):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

# Kernel: 0.1, 0.15, 0.2, ..., 0.5
for i in range(9):
    kernel._data.bitcast[Float32]()[i] = Float32(i) * 0.05 + 0.1
```

Uniform values (`full(..., 0.5)` input, `full(..., 0.1)` kernel) are sufficient for non-padded tests since conv2d does not have the sum-cancellation problem of normalization layers.

### Per-file test count budget

```
test_gradient_checking_basic.mojo:  ≤10 tests  (activations, arithmetic, edge cases)
test_gradient_checking_dtype.mojo:  ≤10 tests  (composite, linear fp32/fp16, conv2d x4, cross-entropy)
test_gradient_checking_conv2d.mojo: ≤10 tests  (all 3 outputs × 3 configs = 9 tests)
test_backward_conv_padding.mojo:    ≤10 tests  (padding=1 + padding=2 × 2 outputs = 4 tests)
```

### Tolerance comparison

| Layer type | rtol | atol | epsilon |
|------------|------|------|---------|
| Linear | 1e-3 | 5e-4 | 1e-4 |
| Conv2D | 1e-2 | 1e-2 | 1e-4 or 3e-4 |

Conv2D uses relaxed tolerances due to strided access patterns and multiple accumulation passes.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3281, PR #3865 (grad_input/weights, padding=0) | [notes.md](../references/notes.md) |
| ProjectOdyssey | PR #3772, issue #3233 (3 configs via check_gradients) | [notes.md](../references/notes.md) |
| ProjectOdyssey | PR #4793, issue #3774 (all 3 outputs × 3 configs) | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3817, PR #4809 (padding=1 + padding=2) | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3785, PR #4799 (padding>0 value tests, border pixel formula) | [notes.md](../references/notes.md) |
