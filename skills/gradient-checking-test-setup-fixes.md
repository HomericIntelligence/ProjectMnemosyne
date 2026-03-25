---
name: gradient-checking-test-setup-fixes
description: 'Fix gradient checking test failures caused by pathological test setup
  (uniform inputs, wrong epsilon, degenerate cases). Use when: (1) gradient checking
  tests fail with analytical~0 vs numerical~nonzero for normalization layers, (2)
  multi-channel conv2d gradient checks exceed tolerance due to accumulated float32
  precision, (3) depthwise conv2d tests fail with uniform inputs.'
category: testing
date: 2026-03-25
version: 1.0.0
user-invocable: false
tags:
  - gradient-checking
  - batch-norm
  - conv2d
  - depthwise-conv2d
  - float32-precision
  - test-setup
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Root-cause and fix 3 gradient checking test failures on main branch (batch norm, conv2d multi-channel, depthwise conv2d) |
| **Outcome** | All 3 failures identified as test setup issues (not backward pass bugs). Fixed via non-uniform inputs/grad_output, correct epsilon, and explicit tolerances. PR #5107. |

## When to Use

- CI "Core Gradient" test group fails with gradient checking mismatches
- Batch norm backward gradient check shows analytical~0 vs numerical~0.09 (cancellation gotcha)
- Conv2d multi-channel gradient check exceeds tolerance with large-magnitude gradients (~44.5)
- Depthwise conv2d gradient check fails with uniform (ones) inputs
- Any normalization layer gradient check uses `check_gradients()` (which hardcodes `ones_like` grad_output)
- Accumulated float32 precision error exceeds absolute tolerance in multi-element output sums

## Verified Workflow

### Quick Reference

```bash
# Diagnose: extract failure lines from CI
gh run view <run_id> --log-failed 2>&1 | grep -E "(FAILED|❌|Gradient check FAILED|Analytical:|Numerical:|Tolerance:)"

# Check if check_gradients() is using uniform grad_output (always does)
grep "check_gradients" tests/shared/core/test_gradient_checking_*.mojo

# Check if tests use uniform inputs
grep "ones(" tests/shared/core/test_gradient_checking_*.mojo
```

### Detailed Steps

1. **Identify the failure pattern** from CI logs:

   | Pattern | Root Cause | Fix |
   |---------|-----------|-----|
   | Analytical: ~0, Numerical: ~0.09 | Batch norm cancellation with uniform grad_output | Use `check_gradient()` with non-uniform grad_output |
   | Max diff 0.134, values ~44.5, tolerance 0.01 | Float32 precision error with epsilon=1e-4 | Use default epsilon=3e-4 |
   | Kernel gradient check failed with ones() inputs | Degenerate gradient patterns from uniform input | Use non-uniform inputs |

2. **For batch norm tests** — switch from `check_gradients()` to `check_gradient()`:

   `check_gradients()` (line 95 in gradient_checker.mojo) hardcodes `grad_output = ones_like(output)`.
   `check_gradient()` (line 727) accepts a custom `grad_output` parameter.

   ```mojo
   # BEFORE: uses check_gradients() which hardcodes ones grad_output
   var passed = check_gradients(forward, backward, input)

   # AFTER: use check_gradient() with non-uniform grad_output
   var output = forward(input)
   var grad_output = _make_non_uniform_grad_output(output)
   check_gradient(forward, backward, input, grad_output, rtol=1e-2, atol=1e-2)
   ```

   Non-uniform grad_output pattern (proven, from team KB):

   ```mojo
   fn _make_non_uniform_grad_output(output: AnyTensor) raises -> AnyTensor:
       var grad_output = zeros(output.shape(), output._dtype)
       for i in range(output.numel()):
           var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
           grad_output._data.bitcast[Float32]()[i] = val
       return grad_output^
   ```

   Also use non-uniform input (not all `ones`):

   ```mojo
   fn _make_non_uniform_input(shape: List[Int]) raises -> AnyTensor:
       var input = zeros(shape, DType.float32)
       for i in range(input.numel()):
           input._data.bitcast[Float32]()[i] = Float32(i) * Float32(0.1) + Float32(0.1)
       return input^
   ```

3. **For conv2d tests** — remove explicit `epsilon=1e-4`:

   The `GRADIENT_CHECK_EPSILON_FLOAT32 = 3e-4` constant exists for a reason (issue #2704).
   With epsilon=1e-4 and multi-channel output (75 elements at magnitude ~44.5), accumulated
   float32 error is 0.134 which exceeds the 0.01 tolerance.

   ```mojo
   # BEFORE: explicit epsilon=1e-4 causes precision issues
   var passed = check_gradients(forward, backward_fn, x, epsilon=1e-4, tolerance=1e-2)

   # AFTER: use default epsilon=3e-4
   var passed = check_gradients(forward, backward_fn, x, tolerance=1e-2)
   ```

4. **For depthwise conv2d tests** — use non-uniform inputs:

   ```mojo
   # BEFORE: uniform inputs
   var input = ones(shape, DType.float32)
   var kernel = ones(kernel_shape, DType.float32)

   # AFTER: non-uniform inputs
   var input = zeros(shape, DType.float32)
   for i in range(input.numel()):
       input._data.bitcast[Float32]()[i] = Float32(i) * Float32(0.1)

   var kernel = zeros(kernel_shape, DType.float32)
   for i in range(kernel.numel()):
       kernel._data.bitcast[Float32]()[i] = Float32(i) * Float32(0.05) + Float32(0.1)
   ```

5. **Import the right function**:

   ```mojo
   # For custom grad_output: use check_gradient (no 's')
   from shared.testing.gradient_checker import check_gradient

   # For default ones grad_output: use check_gradients (with 's')
   from shared.testing.gradient_checker import check_gradients
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Increasing tolerance to hide batch norm mismatch | Raise tolerance from 1e-2 to 1e-1 | Masks the real issue — doesn't validate the backward pass correctly | Fix the test setup (non-uniform grad_output) instead of loosening tolerance |
| Fixing the batch norm backward formula | Suspected formula bug since analytical=0 but numerical=0.09 | The formula IS correct — zero is the mathematically right answer for uniform grad_output | Always verify the math before assuming the implementation is wrong |
| Using epsilon=1e-5 for conv2d | Smaller epsilon for more accurate finite differences | Float32 rounding error gets WORSE with smaller epsilon (~56% precision loss at 1e-5) | Smaller epsilon != more accurate in float32; use 3e-4 (sqrt of machine epsilon) |
| Keeping uniform ones() inputs for depthwise conv2d | Assumed uniform inputs would be fine since depthwise conv doesn't normalize | Uniform inputs create degenerate patterns where many gradient contributions cancel | Always use non-uniform inputs for gradient checking — avoid symmetry artifacts |

## Results & Parameters

### Tolerance Settings by Layer Type

```yaml
# Batch norm (with non-uniform grad_output)
rtol: 1e-2
atol: 1e-2

# Conv2d (any configuration)
epsilon: 3e-4  # default GRADIENT_CHECK_EPSILON_FLOAT32
tolerance: 1e-2

# Depthwise conv2d
epsilon: 3e-4  # default
tolerance: 1e-2
```

### Key API Difference

```text
check_gradients(forward, backward, input, epsilon, tolerance) -> Bool
  - Hardcodes grad_output = ones_like(output)
  - Returns True/False
  - Use for: activations, arithmetic, non-normalization layers

check_gradient(forward, backward, x, grad_output, epsilon, rtol, atol) -> None
  - Accepts custom grad_output
  - Raises on failure (no return value)
  - Use for: normalization layers (batch norm, layer norm, group norm)
```

### Decision Tree

```text
Is the layer a normalization layer (batch norm, layer norm, group norm)?
├─ YES → Use check_gradient() with non-uniform grad_output
│        Pattern: Float32(i % 4) * 0.25 - 0.3
│
└─ NO → Use check_gradients() with default epsilon=3e-4
         ├─ Multi-channel output (>25 elements)? → Keep tolerance ≥ 1e-2
         └─ Use non-uniform inputs (Float32(i) * 0.1)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5107, CI Core Gradient group | [notes.md](./gradient-checking-test-setup-fixes.notes.md) |
