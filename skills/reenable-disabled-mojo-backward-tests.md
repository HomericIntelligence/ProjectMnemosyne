---
name: reenable-disabled-mojo-backward-tests
description: 'Re-enable disabled Mojo backward pass tests by verifying the root cause
  is resolved and writing analytically-verifiable gradient test cases. Use when: backward
  tests are commented out with stale ownership/borrowing notes, or when gradient type
  aliases have been updated.'
category: testing
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Re-enable Disabled Mojo Backward Pass Tests

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-04 |
| Objective | Re-enable Conv2D backward pass tests that were disabled with a stale ownership/borrowing comment |
| Outcome | 4 backward tests added and passing in CI |
| Issue | #3085 — `[Cleanup] Enable disabled Conv2D backward tests` |

## When to Use

- Backward pass tests are commented out with a note like "disabled due to ownership issues in XBackwardResult"
- A `comptime` type alias change (e.g. `Conv2dBackwardResult = GradientTriple`) resolved the underlying issue
- You need to confirm gradient type field names before writing tests
- A cleanup issue asks to "re-enable" tests with a stale disable comment

## Verified Workflow

### 1. Confirm the Root Cause is Already Resolved

Read the source file to verify the backward result type is now an alias for a `Copyable, Movable` type:

```bash
grep -n "comptime.*BackwardResult\|GradientTriple\|GradientPair" shared/core/conv.mojo | head -20
```

Look for lines like:
```mojo
comptime Conv2dBackwardResult = GradientTriple
comptime Conv2dNoBiasBackwardResult = GradientPair
```

If these exist, the ownership issue is resolved — proceed.

### 2. Read Gradient Type Field Names

Check the gradient type source to get exact field names:

```bash
grep -n "var grad_" shared/core/gradient_types.mojo
```

**GradientTriple fields** (used by `conv2d_backward`):
- `.grad_input` — gradient w.r.t. input
- `.grad_weights` — gradient w.r.t. kernel/weights
- `.grad_bias` — gradient w.r.t. bias

**GradientPair fields** (used by `conv2d_no_bias_backward`):
- `.grad_a` — gradient w.r.t. first input (input tensor)
- `.grad_b` — gradient w.r.t. second input (kernel)

### 3. Write Analytically-Verifiable Tests

Write tests whose expected gradient values can be computed by hand:

**Shape test** — simplest, just verify grad shapes match inputs:

```mojo
fn test_conv2d_backward_output_shape() raises:
    # ... create input (1,1,4,4), kernel (1,1,3,3), bias (1,)
    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var grads = conv2d_backward(grad_output, x, kernel, stride, padding)
    assert_equal(grads.grad_input.shape()[2], in_height)
    assert_equal(grads.grad_weights.shape()[2], kH)
    assert_equal(grads.grad_bias.shape()[0], out_channels)
```

**Analytical value test** — use 1x1 kernel = 1.0 for identity gradients:

```mojo
fn test_conv2d_backward_single_sample() raises:
    # Input (1,1,2,2) = [[1,2],[3,4]], kernel (1,1,1,1) = 1.0
    # grad_output = ones (1,1,2,2)
    # Expected:
    #   grad_input = 1.0 everywhere (1x1 kernel=1.0 * grad_out=1.0)
    #   grad_weights = sum(input) = 1+2+3+4 = 10.0
    #   grad_bias = sum(grad_output) = 4.0
    var grads = conv2d_backward(grad_output, x, kernel, stride=1, padding=0)
    assert_almost_equal(grads.grad_weights._data.bitcast[Float32]()[0], 10.0, tolerance=1e-5)
    assert_almost_equal(grads.grad_bias._data.bitcast[Float32]()[0], 4.0, tolerance=1e-5)
```

### 4. Remove Stale Comments and Wire into main()

Replace the commented-out block:

```mojo
# ============================================================================
# Conv2D Backward Pass Tests (DISABLED)
# ============================================================================
# NOTE: Backward tests are currently disabled due to ownership issues in Conv2dBackwardResult.
```

With the real test functions. Then add them to `main()`:

```mojo
test_conv2d_backward_output_shape()
print("✓ test_conv2d_backward_output_shape")

test_conv2d_backward_single_sample()
print("✓ test_conv2d_backward_single_sample")
```

Also remove any stale `TODO(#NNNN)` comments in `main()`.

## Key Patterns

### Field Name Discrepancy: GradientTriple vs GradientPair

`conv2d_backward` → returns `GradientTriple`:
- `.grad_input`, `.grad_weights`, `.grad_bias`

`conv2d_no_bias_backward` → returns `GradientPair`:
- `.grad_a` (input gradient), `.grad_b` (kernel gradient)

**Note**: The field naming is inconsistent between the two types. Always verify by reading `gradient_types.mojo` directly.

### 1x1 Kernel as Analytical Test Case

A 1×1 kernel with value 1.0 acts as an identity transform. For input `X` and `grad_out` all-ones:
- `grad_input[i] = kernel[0] * grad_out[i] = 1.0`
- `grad_weights[0] = sum(X * grad_out) = sum(X)`
- `grad_bias[0] = sum(grad_out) = numel(output)`

This gives exact, hand-computable expected values independent of kernel size.

### Local Mojo Execution May Fail Due to GLIBC

On older Linux hosts (GLIBC < 2.32), `mojo` will fail with:

```text
/lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.32' not found
```

This is a host environment issue, not a code issue. Tests run correctly in CI (Docker with correct GLIBC). Pre-commit hooks that call `mojo format` will also fail but other hooks (markdown, YAML, Python) still pass and validate the code structure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo test` locally | Tried to verify tests pass before committing | GLIBC 2.32+ required but host has older version | Cannot validate Mojo execution locally — rely on CI |
| Running `just pre-commit-all` | Tried to run all pre-commit hooks | `just` not in PATH on this host | Use `pixi run pre-commit run --all-files` instead |
| Assumed `grad_a`/`grad_b` for both types | Assumed GradientTriple and GradientPair share field names | GradientTriple uses `grad_input`/`grad_weights`/`grad_bias`; only GradientPair uses `grad_a`/`grad_b` | Always read `gradient_types.mojo` to confirm field names before writing tests |

## Results & Parameters

Analytically-verifiable test configuration that produces exact expected values:

```mojo
# Input: (1, 1, 2, 2) = [[1.0, 2.0], [3.0, 4.0]]
# Kernel: (1, 1, 1, 1) = [[1.0]]
# grad_output: ones (1, 1, 2, 2)
# stride=1, padding=0

# Expected outputs:
# grad_input = [[1.0, 1.0], [1.0, 1.0]]  (all 1.0 — identity kernel)
# grad_weights[0] = 10.0                  (sum of input = 1+2+3+4)
# grad_bias[0] = 4.0                      (sum of grad_output = 4 elements)
```

CI workflow that runs the tests:
```yaml
# .github/workflows/comprehensive-tests.yml
- name: Run test group
  run: just test-group "tests/shared/core" "test_conv.mojo"
```
