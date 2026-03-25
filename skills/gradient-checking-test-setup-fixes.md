---
name: gradient-checking-test-setup-fixes
description: 'Fix gradient checking test failures caused by pathological test setup.
  Use when: (1) gradient checks fail with analytical~0 vs numerical~nonzero for normalization
  layers, (2) any gradient check exceeds tolerance due to large-magnitude gradients,
  (3) tests use check_gradients() instead of check_gradient().'
category: testing
date: 2026-03-25
version: 2.0.0
user-invocable: false
verification: verified-local
history: gradient-checking-test-setup-fixes.history
tags:
  - gradient-checking
  - batch-norm
  - conv2d
  - depthwise-conv2d
  - float32-precision
  - test-setup
  - tolerance
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Root-cause and fix 3 gradient checking test failures on main (batch norm, conv2d, depthwise conv2d) |
| **Outcome** | Batch norm fixed in v1.0.0. Conv2d/depthwise required v2.0.0 — switching to `check_gradient()` for relative tolerance. PR #5107. |
| **Verification** | verified-local (batch norm confirmed passing in CI; conv2d/depthwise CI pending) |
| **History** | [changelog](./gradient-checking-test-setup-fixes.history) |

## When to Use

- CI "Core Gradient" test group fails with gradient checking mismatches
- Batch norm backward gradient check shows analytical~0 vs numerical~0.09 (cancellation gotcha)
- Any gradient check exceeds tolerance when gradient magnitudes are large (>10)
- `check_gradients()` is used anywhere — it has a fundamentally broken tolerance model
- Accumulated float32 precision error exceeds absolute tolerance in multi-element output sums

## Verified Workflow

### Quick Reference

```bash
# Diagnose: extract failure lines from CI
gh run view <run_id> --log-failed 2>&1 | grep -E "(FAILED|Gradient check FAILED|Analytical:|Numerical:|Tolerance:)"

# Find tests still using check_gradients() (should be migrated to check_gradient())
grep -r "check_gradients" tests/shared/core/test_gradient_checking_*.mojo
```

### Detailed Steps

1. **Always use `check_gradient()` (no trailing 's')** for ALL gradient checking tests:

   The critical difference is the tolerance model:

   | API | Tolerance | Formula |
   | --- | --- | --- |
   | `check_gradients()` | Pure absolute | `abs(diff) >= tolerance` (BROKEN for large gradients) |
   | `check_gradient()` | Combined relative+absolute | `abs(diff) > atol + rtol * max_magnitude` (CORRECT) |

   For a gradient of magnitude 32.4 with diff 0.046:
   - `check_gradients(tolerance=0.01)`: 0.046 >= 0.01 → FAIL
   - `check_gradient(rtol=1e-2, atol=1e-2)`: 0.046 > (0.01 + 0.01*32.4) = 0.334 → PASS

2. **For ALL tests** — use this pattern:

   ```mojo
   from shared.testing.gradient_checker import check_gradient
   from shared.tensor.any_tensor import AnyTensor, zeros, zeros_like

   fn _make_ones_grad_output(output: AnyTensor) raises -> AnyTensor:
       var grad_output = zeros_like(output)
       for i in range(output.numel()):
           grad_output._set_float64(i, 1.0)
       return grad_output^

   # In each test:
   var output = forward(input)
   var grad_output = _make_ones_grad_output(output)
   check_gradient(forward, backward, input, grad_output, rtol=1e-2, atol=1e-2)
   ```

3. **For normalization layers (batch norm, layer norm)** — use non-uniform grad_output:

   ```mojo
   fn _make_non_uniform_grad_output(output: AnyTensor) raises -> AnyTensor:
       var grad_output = zeros(output.shape(), output._dtype)
       for i in range(output.numel()):
           var val = Float32(i % 4) * Float32(0.25) - Float32(0.3)
           grad_output._data.bitcast[Float32]()[i] = val
       return grad_output^
   ```

   Uniform grad_output (ones) causes pathological cancellation: `sum(x_norm) = 0` makes
   analytical gradient exactly 0, while numerical gradient picks up float32 noise ~0.094.

4. **Always use non-uniform inputs**:

   ```mojo
   var input = zeros(shape, DType.float32)
   for i in range(input.numel()):
       input._data.bitcast[Float32]()[i] = Float32(i) * Float32(0.1)
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Increasing tolerance to hide batch norm mismatch | Raise tolerance from 1e-2 to 1e-1 | Masks the real issue — doesn't validate the backward pass correctly | Fix the test setup, not the threshold |
| Fixing the batch norm backward formula | Suspected formula bug since analytical=0 but numerical=0.09 | The formula IS correct — zero is the right answer for uniform grad_output | Verify the math before assuming the implementation is wrong |
| Using epsilon=1e-5 for conv2d | Smaller epsilon for more accurate finite differences | Float32 rounding error gets WORSE with smaller epsilon (~56% precision loss) | Smaller epsilon != more accurate in float32; use 3e-4 |
| Keeping uniform ones() inputs for depthwise conv2d | Assumed uniform inputs would be fine since depthwise conv doesn't normalize | Uniform inputs create degenerate patterns where many gradient contributions cancel | Always use non-uniform inputs for gradient checking |
| v1.0.0: Removing epsilon=1e-4 for conv2d (keeping check_gradients) | Changed from epsilon=1e-4 to default 3e-4, keeping check_gradients() | Diff dropped from 0.134 to 0.046 but STILL failed absolute tolerance of 0.01 | The problem was the tolerance MODEL (absolute vs relative), not the epsilon |
| v1.0.0: Using check_gradients() with non-uniform inputs for depthwise | Added non-uniform inputs but kept check_gradients() | Diff was 0.0103 at magnitude 126.4 — barely exceeded absolute tolerance 0.01 | Large-magnitude gradients need relative tolerance; absolute tolerance can't scale |

## Results & Parameters

### Tolerance Settings (v2.0.0 — ALL layers)

```yaml
# Use check_gradient() for everything
rtol: 1e-2   # 1% relative tolerance
atol: 1e-2   # absolute floor for near-zero gradients
# epsilon: auto-selected by check_gradient() based on dtype
```

### The Key Insight (v1.0.0 → v2.0.0)

```text
v1.0.0 thought the problem was epsilon (step size for finite differences).
v2.0.0 discovered the problem was the tolerance model itself.

check_gradients() asks: "Is the absolute difference < 0.01?"
  → For gradient=32.4, diff=0.046: 0.046 >= 0.01 → FAIL (0.14% error, should pass)

check_gradient() asks: "Is the absolute difference < atol + rtol * magnitude?"
  → For gradient=32.4, diff=0.046: 0.046 < 0.01 + 0.01*32.4 = 0.334 → PASS
```

### Decision Tree (v2.0.0 — UPDATED from v1.0.0)

```text
Writing a gradient checking test?
└─ Use check_gradient() (no trailing 's') with:
    ├─ Normalization layer? → Non-uniform grad_output (Float32(i%4)*0.25 - 0.3)
    └─ All other layers → ones grad_output via _make_ones_grad_output()
    Always: rtol=1e-2, atol=1e-2, non-uniform inputs
```

**v1.0.0 decision tree was WRONG** — it recommended `check_gradients()` for non-normalization
layers. This fails for any test where gradient magnitudes exceed ~1.0.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5107 (2 commits), CI Core Gradient group | [notes.md](./gradient-checking-test-setup-fixes.notes.md) |
