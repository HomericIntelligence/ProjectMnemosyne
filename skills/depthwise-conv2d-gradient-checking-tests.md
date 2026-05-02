---
name: depthwise-conv2d-gradient-checking-tests
description: "Use when: (1) depthwise_conv2d_backward exists but lacks gradient-correctness tests, (2) adding per-channel finite-difference gradient checking for grad_input, grad_weights, and grad_bias, (3) the kernel shape is (channels,1,kH,kW) not (out_ch,in_ch,kH,kW), (4) keeping per-file test count ≤8"
category: testing
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [depthwise-conv2d, gradient-checking, finite-differences, mojo, backward-pass]
---
## Overview

| Field | Value |
|-------|-------|
| **Topic** | Numerical gradient checking for `depthwise_conv2d_backward` |
| **Approach** | Finite differences via `check_gradient()` from `shared.testing` |
| **Key outputs verified** | `grad_input`, `grad_weights`, `grad_bias` |
| **Configurations covered** | stride=1/2, padding=0/1, single-channel, multi-channel |
| **Language** | Mojo |
| **Per-file test limit** | ≤8 `fn test_` per file (stricter than standard conv2d) |

## When to Use

1. `depthwise_conv2d_backward` has shape tests but no finite-difference gradient checks
2. Adding tests for all three gradient fields: `grad_input` (perturb x), `grad_weights` (perturb kernel), `grad_bias` (analytical)
3. Working in a Mojo project with a strict per-file test count (≤8 `fn test_` per file)
4. Tests must cover multiple configurations: stride=1/2, padding=0/1, single-channel, multi-channel
5. CI workflow uses a matrix `pattern` field listing individual `.mojo` test filenames

## Verified Workflow

### Quick Reference

**Critical API differences from regular conv2d:**

| Aspect | Regular Conv2D | Depthwise Conv2D |
|--------|---------------|-----------------|
| Kernel shape | `(out_channels, in_channels, kH, kW)` | `(channels, 1, kH, kW)` |
| Gradient field | `.grad_weights` | `.grad_weights` (NOT `.grad_kernel`) |
| Return type | `GradientTriple` | `GradientTriple` |
| Assertion API | `assert_almost_equal(a, b, tolerance=...)` | Same — takes `tolerance:` NOT `rtol`/`atol` |

```mojo
# Depthwise kernel shape — one filter per input channel:
kernel_shape.append(channels)
kernel_shape.append(1)   # Always 1
kernel_shape.append(kH)
kernel_shape.append(kW)
```

### Step 1: Understand the backward function signature

```bash
grep -n "fn depthwise_conv2d_backward" <project-root>/shared/core/conv.mojo
grep -n "grad_weights\|grad_bias\|grad_input" <project-root>/shared/core/gradient_types.mojo
```

Key details:
- Input shape: `(batch, channels, H, W)`
- Kernel shape: `(channels, 1, kH, kW)` — one filter per input channel
- Returns `GradientTriple` with `.grad_input`, `.grad_weights`, `.grad_bias`

### Step 2: Count existing tests (limit is ≤8 per file)

```bash
grep -c "^fn test_" <test-root>/test_backward_conv_pool.mojo
```

Keep depthwise test files to ≤8 `fn test_` per file (stricter than the ≤10 used for some other files). Create new split files when ≥6 tests exist.

### Step 3: Create part1 — grad_input checks

File: `<test-root>/test_depthwise_conv_grad_check_part1.mojo`

Tests to include (5 total):
- Shape verification for all three gradient fields
- `grad_input` numerical check: stride=1, padding=0 (1,1,4,4 input, 1,1,3,3 kernel)
- `grad_input` numerical check: stride=2
- `grad_input` numerical check: padding=1
- `grad_input` numerical check: 3 channels

### Step 4: check_gradient closure pattern for grad_input

```mojo
fn forward_input(inp: ExTensor) raises -> ExTensor:
    return depthwise_conv2d(inp, kernel, bias, stride=1, padding=0)

fn backward_input(grad_out: ExTensor, inp: ExTensor) raises -> ExTensor:
    var grads = depthwise_conv2d_backward(grad_out, inp, kernel, stride=1, padding=0)
    return grads.grad_input

check_gradient(forward_input, backward_input, x, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 5: check_gradient closure pattern for grad_weights

Perturb `kernel`, hold `x` fixed:

```mojo
fn forward_weights(k: ExTensor) raises -> ExTensor:
    return depthwise_conv2d(x, k, bias, stride=1, padding=0)

fn backward_weights(grad_out: ExTensor, k: ExTensor) raises -> ExTensor:
    var grads = depthwise_conv2d_backward(grad_out, x, k, stride=1, padding=0)
    return grads.grad_weights

check_gradient(forward_weights, backward_weights, kernel, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 6: Non-uniform grad_output (avoids sum-to-zero cancellation)

```mojo
# Non-uniform input
for i in range(16):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

# Non-uniform grad_output — avoids sum-to-zero cancellation in symmetric kernels
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = Float32(i % 4) * 0.25 - 0.3
```

Do NOT use `ones_like(output)` as `grad_output` — it can cause sum-to-zero cancellation in symmetric kernels.

### Step 7: Create part2 — grad_weights + grad_bias checks

File: `<test-root>/test_depthwise_conv_grad_check_part2.mojo`

Tests to include (4 total):
- `grad_weights` numerical check: perturb kernel, hold x fixed (single-channel)
- `grad_bias` analytical check: 1×1 spatial output → `grad_bias[c] = grad_output[0, c, 0, 0]`
- `grad_weights` multichannel: 2 channels, 2×2 kernel
- Full pipeline: forward + backward, verify all three fields non-zero

### Step 8: grad_bias analytical test

When output is 1×1 per channel (kernel_size = input_size, stride=1, padding=0):

```mojo
# stride=1, padding=0, kernel=3x3, input=3x3 → output is 1x1 per channel
var output = depthwise_conv2d(x, kernel, bias, stride=1, padding=0)

var grad_output = zeros_like(output)
grad_output._data.bitcast[Float32]()[0] = Float32(0.5)   # channel 0
grad_output._data.bitcast[Float32]()[1] = Float32(-0.3)  # channel 1

var grads = depthwise_conv2d_backward(grad_output, x, kernel, stride=1, padding=0)

assert_almost_equal(grads.grad_bias._data.bitcast[Float32]()[0], Float32(0.5), tolerance=1e-5)
assert_almost_equal(grads.grad_bias._data.bitcast[Float32]()[1], Float32(-0.3), tolerance=1e-5)
```

### Step 9: Update CI workflow

```yaml
- name: "Core Gradient"
  path: "tests/shared/core"
  pattern: "... test_depthwise_conv_grad_check_part1.mojo test_depthwise_conv_grad_check_part2.mojo"
  continue-on-error: true
```

### Step 10: Verify per-file test count

```bash
grep -c "^fn test_" <test-root>/test_depthwise_conv_grad_check_part1.mojo
grep -c "^fn test_" <test-root>/test_depthwise_conv_grad_check_part2.mojo
# Both must output ≤8
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `.grad_kernel` field name | Assumed `depthwise_conv2d_backward` returns `GradientPair` with `.grad_kernel` | Actual return is `GradientTriple` with `.grad_weights` (confirmed from `gradient_types.mojo`) | Always verify field names from `gradient_types.mojo`, not just the function docstring |
| Using `ones_like(output)` as `grad_output` | Uniform gradient for initial test | Causes sum-to-zero cancellation in symmetric kernel configurations — numerical and analytical gradients both become ~0 | Use `Float32(i % 4) * 0.25 - 0.3` non-uniform pattern |
| Adding tests to `test_backward_conv_pool.mojo` | Kept tests in one file | File already at or near the per-file test limit; adding more risks heap corruption in CI | Always check `grep -c "^fn test_"` before adding; create new split files when ≥6 tests exist |
| Using `rtol=1e-3, atol=1e-5` (tighter tolerances) | Copied from linear layer tests | Float32 finite differences have O(1e-4) error; tighter tolerances cause false failures | Use `rtol=1e-2, atol=1e-2` for float32 conv gradient checks |
| Using `assert_almost_equal(a, b, rtol=..., atol=...)` | Passed `rtol`/`atol` keyword args | `assert_almost_equal` takes `tolerance: Float32`, not rtol/atol | Always check the actual Mojo function signature — differs from PyTorch/numpy |

## Results & Parameters

**Tolerances for float32 depthwise conv gradient checks:**

```mojo
check_gradient(forward_fn, backward_fn, x, grad_output, rtol=1e-2, atol=1e-2)
```

**Test counts per file:**

- Part 1: 5 tests (shape + 4× grad_input across stride/padding/multichannel)
- Part 2: 4 tests (grad_weights single, grad_bias analytical, grad_weights multichannel, full pipeline)

**CI pattern update location:** `.github/workflows/comprehensive-tests.yml`, `"Core Gradient"` matrix entry, `pattern` field (append to existing space-separated list).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4794, issue #3775 | [notes.md](../references/notes.md) |
