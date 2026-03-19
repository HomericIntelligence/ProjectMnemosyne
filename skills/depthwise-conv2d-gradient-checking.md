---
name: depthwise-conv2d-gradient-checking
description: 'Add numerical gradient checking tests for depthwise_conv2d_backward
  using finite differences. Use when: depthwise_conv2d_backward exists but lacks gradient-correctness
  tests, or when adding per-channel (grad_input/grad_weights/grad_bias) coverage split
  across ADR-009-compliant files.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Problem | `depthwise_conv2d_backward` existed in `shared/core/conv.mojo` with no gradient-correctness tests — only shape verification in downstream tests |
| Solution | Split two new test files (part1: grad_input checks, part2: grad_weights/grad_bias checks) using `check_gradient()` from `shared.testing` |
| Constraint | ADR-009: Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so`) requires ≤8 `fn test_` per file |
| Result | 9 tests across 2 files; all gradient fields verified numerically; CI "Core Gradient" matrix updated |

## When to Use

1. `depthwise_conv2d_backward` (or any backward pass) has shape tests but no finite-difference gradient checks
2. Adding tests for all three gradient fields: `grad_input` (perturb x), `grad_weights` (perturb kernel), `grad_bias` (analytical)
3. Working in a Mojo project with the ADR-009 heap-corruption constraint (≤8 `fn test_` per file)
4. Tests must cover multiple configurations: stride=1/2, padding=0/1, single-channel, multi-channel
5. CI workflow uses a matrix `pattern` field listing individual `.mojo` test filenames

## Verified Workflow

### Step 1: Understand the backward function signature

```bash
grep -n "fn depthwise_conv2d_backward" shared/core/conv.mojo
```

Key details for depthwise conv:

- Input shape: `(batch, channels, H, W)`
- Kernel shape: `(channels, 1, kH, kW)` — one filter per input channel (NOT out_channels × in_channels)
- Returns `GradientTriple` with `.grad_input`, `.grad_weights`, `.grad_bias`

Verify the return type:

```bash
grep -n "return\|GradientTriple\|DepthwiseConv" shared/core/conv.mojo | tail -20
```

### Step 2: Confirm field names from gradient_types.mojo

```bash
grep -n "grad_weights\|grad_bias\|grad_input" shared/core/gradient_types.mojo
```

`GradientTriple` uses `.grad_input`, `.grad_weights`, `.grad_bias` (not `.grad_kernel`).

### Step 3: Count existing tests in target files

```bash
grep -c "^fn test_" tests/shared/core/test_backward_conv_pool.mojo
```

ADR-009 limit: ≤8 `fn test_` per file. Create new split files rather than adding to existing ones.

### Step 4: Create part1 (grad_input checks)

File: `tests/shared/core/test_depthwise_conv_grad_check_part1.mojo`

Required ADR-009 header:

```mojo
# ADR-009: This file is intentionally limited to ≤8 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_depthwise_conv_grad_check.
# See docs/adr/ADR-009-heap-corruption-workaround.md
```

Tests to include (5 total):

- Shape verification for all three gradient fields
- `grad_input` numerical check: stride=1, padding=0 (1,1,4,4 input, 1,1,3,3 kernel)
- `grad_input` numerical check: stride=2
- `grad_input` numerical check: padding=1
- `grad_input` numerical check: 3 channels

### Step 5: Create part2 (grad_weights + grad_bias checks)

File: `tests/shared/core/test_depthwise_conv_grad_check_part2.mojo`

Tests to include (4 total):

- `grad_weights` numerical check: perturb kernel, hold x fixed
- `grad_bias` analytical check: 1×1 spatial output → `grad_bias[c] = grad_output[0,c,0,0]`
- `grad_weights` multichannel: 2 channels, 2×2 kernel
- Full pipeline: forward + backward, verify all three fields non-zero

### Step 6: Non-uniform input pattern (avoids pathological cancellation)

```mojo
# Non-uniform input
for i in range(16):
    x._data.bitcast[Float32]()[i] = Float32(i) * 0.1

# Non-uniform grad_output — avoids sum-to-zero cancellation (KB pattern)
for i in range(output.numel()):
    grad_output._data.bitcast[Float32]()[i] = Float32(i % 4) * 0.25 - 0.3
```

Do NOT use `ones_like(output)` as `grad_output` — it can cause sum-to-zero cancellation
in symmetric kernels.

### Step 7: check_gradient() closure pattern for grad_input

```mojo
fn forward_input(inp: ExTensor) raises -> ExTensor:
    return depthwise_conv2d(inp, kernel, bias, stride=1, padding=0)

fn backward_input(grad_out: ExTensor, inp: ExTensor) raises -> ExTensor:
    var grads = depthwise_conv2d_backward(grad_out, inp, kernel, stride=1, padding=0)
    return grads.grad_input

check_gradient(forward_input, backward_input, x, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 8: check_gradient() closure pattern for grad_weights

Perturb `kernel`, hold `x` fixed:

```mojo
fn forward_weights(k: ExTensor) raises -> ExTensor:
    return depthwise_conv2d(x, k, bias, stride=1, padding=0)

fn backward_weights(grad_out: ExTensor, k: ExTensor) raises -> ExTensor:
    var grads = depthwise_conv2d_backward(grad_out, x, k, stride=1, padding=0)
    return grads.grad_weights

check_gradient(forward_weights, backward_weights, kernel, grad_output, rtol=1e-2, atol=1e-2)
```

### Step 9: grad_bias analytical test

When output is 1×1 per channel (kernel_size = input_size, stride=1, padding=0):
`grad_bias[c] = grad_output[0, c, 0, 0]`

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

### Step 10: Update CI workflow

Add new files to the `"Core Gradient"` matrix entry `pattern` field:

```yaml
- name: "Core Gradient"
  path: "tests/shared/core"
  pattern: "... test_depthwise_conv_grad_check_part1.mojo test_depthwise_conv_grad_check_part2.mojo"
  continue-on-error: true
```

### Step 11: Verify ADR-009 compliance

```bash
grep -c "^fn test_" tests/shared/core/test_depthwise_conv_grad_check_part1.mojo
grep -c "^fn test_" tests/shared/core/test_depthwise_conv_grad_check_part2.mojo
# Both must output ≤8
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `grad_kernel` field name | Assumed `depthwise_conv2d_backward` returns `GradientPair` with `.grad_kernel` | Actual return is `GradientTriple` with `.grad_weights` (confirmed from docstring and `gradient_types.mojo`) | Always verify field names from `gradient_types.mojo`, not just the function docstring |
| Using `ones_like(output)` as `grad_output` | Uniform gradient for initial test | Causes sum-to-zero cancellation in symmetric kernel configurations — numerical and analytical gradients both become ~0, masking errors | Use `Float32(i % 4) * 0.25 - 0.3` non-uniform pattern from team KB |
| Adding tests to existing test_backward_conv_pool.mojo | Would have kept tests in one file | File already at or near ADR-009 limit; adding more risks heap corruption in CI | Always check `grep -c "^fn test_"` before adding; create new split files when ≥6 tests exist |
| Using `rtol=1e-3, atol=1e-5` (tighter tolerances) | Tighter than the team KB default for float32 conv | Float32 finite differences have O(1e-4) error; tighter tolerances cause false failures | Use `rtol=1e-2, atol=1e-2` for float32 conv gradient checks |

## Results & Parameters

**Tolerances for float32 depthwise conv gradient checks:**

```mojo
check_gradient(forward_fn, backward_fn, x, grad_output, rtol=1e-2, atol=1e-2)
```

**Kernel shape for depthwise conv (NOT like regular conv2d):**

```mojo
# Regular conv2d: (out_channels, in_channels, kH, kW)
# Depthwise conv: (channels, 1, kH, kW)
kernel_shape.append(channels)
kernel_shape.append(1)   # Always 1 — one filter per input channel
kernel_shape.append(kH)
kernel_shape.append(kW)
```

**Test counts per file (ADR-009 compliant):**

- Part 1: 5 tests (shape + 4× grad_input across stride/padding/multichannel)
- Part 2: 4 tests (grad_weights single, grad_bias analytical, grad_weights multichannel, full pipeline)

**CI pattern update location:** `.github/workflows/comprehensive-tests.yml`, `"Core Gradient"` matrix entry, `pattern` field (append to existing space-separated list).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4794, issue #3775 | [notes.md](../references/notes.md) |
