---
name: conv2d-backward-padding-value-tests
description: 'Documents how to write analytically verifiable backward pass tests for
  conv2d with padding>0, verifying border pixel gradient reduction. Use when: adding
  value tests for padded convolutions, verifying gradient correctness affected by
  receptive field overlap, or catching silent correctness bugs in conv2d_backward
  with non-zero padding.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Task** | Add gradient value tests for conv2d_backward with padding=1 |
| **Issue** | #3785 — multi-channel backward tests with padding>0 and value checks |
| **Language** | Mojo (v0.26.1) |
| **File modified** | `tests/shared/core/test_conv_part3.mojo` |
| **PR** | #4799 |
| **Outcome** | All 7 tests pass; border pixel gradient reduction verified |

## When to Use

Apply this skill when:

1. A test validates shape but not values for a padded convolution backward pass
2. The existing values test uses `padding=0` only — need to verify `padding>0`
3. You need to confirm border pixels receive fewer gradient contributions than interior pixels
4. ADR-009 limits you to ≤10 test functions and you must add a targeted value test

## Verified Workflow

### Quick Reference

```
overlap_count(ih, iw) = h_overlap(ih) × w_overlap(iw)

For padding=1, kernel=3, spatial=5:
  h_overlap(0) = h_overlap(4) = 2  (border row covered by 2 output rows)
  h_overlap(1..3) = 3              (interior row covered by 3 output rows)

grad_input[b, ic, ih, iw] = out_channels × overlap_count(ih, iw)
  corner (0,0):        2×2 = 4  → 4 × 8 = 32.0
  edge non-corner (0,1): 2×3 = 6 → 6 × 8 = 48.0
  interior (1,1):      3×3 = 9  → 9 × 8 = 72.0
```

### Step 1 — Derive analytical expected values

For an all-ones config (input, kernel, grad_output all ones):

- `grad_input[b, ic, ih, iw] = out_channels × overlap_count(ih, iw)`
- `overlap_count(ih, iw)` = how many output positions (oh, ow) have (ih, iw) in their receptive field

With `padding=P`, `kernel=K`, `spatial=N` (same-padding so output spatial = N):
- Input row `ih` is covered by output rows `oh ∈ [ih-P, ih+(K-1-P)]` clipped to `[0, N-1]`
- For `padding=1, K=3`: `oh ∈ [ih-1, ih+1]` clipped to `[0, N-1]`
  - Border rows 0 and N-1: covered by 2 output rows
  - Interior rows 1..N-2: covered by 3 output rows

Key invariant to assert: `corner_grad < edge_grad < interior_grad`

### Step 2 — Design the all-ones test configuration

Choose parameters that keep calculation tractable:

```mojo
var batch = 1
var in_channels = 3    # realistic multi-channel
var out_channels = 8   # realistic multi-channel
var in_height = 5      # small enough for manual verification
var in_width = 5
var kH = 3
var kW = 3
var stride = 1
var padding = 1        # same-padding: output = input spatial dims
```

Verify expected output shape: `(1 + 2×1 - 3)/1 + 1 = 5` ✓ same-padding preserved.

### Step 3 — Implement the test function

```mojo
fn test_conv2d_backward_multichannel_padding1_values() raises:
    """Test conv2d_backward computes correct gradient values with padding=1.
    ...
    """
    # Build input, kernel, bias all-ones / all-zeros
    var x = ones(input_shape, DType.float32)
    var kernel = ones(kernel_shape, DType.float32)
    var bias = zeros(bias_shape, DType.float32)

    # Forward then backward
    var output = conv2d(x, kernel, bias, stride, padding)
    var grad_output = ones(output.shape(), DType.float32)
    var result = conv2d_backward(grad_output, x, kernel, stride, padding)
    var grad_input = result.grad_input

    # Verify shape
    assert_equal(grad_input.shape()[0], batch)
    assert_equal(grad_input.shape()[1], in_channels)
    assert_equal(grad_input.shape()[2], in_height)
    assert_equal(grad_input.shape()[3], in_width)

    # Flat index: ic * H*W + ih * W + iw
    var grad_input_data = grad_input._data.bitcast[Float32]()

    # Check all in_channels (symmetry: all-ones kernel)
    for ic in range(in_channels):
        var base = ic * in_height * in_width
        assert_almost_equal(grad_input_data[base + 0], Float32(32.0), tolerance=1e-3)  # corner
        assert_almost_equal(grad_input_data[base + 1], Float32(48.0), tolerance=1e-3)  # edge
        assert_almost_equal(grad_input_data[base + 1*in_width+1], Float32(72.0), tolerance=1e-3)  # interior

    # Directional invariant: border < interior
    assert_true(grad_input_data[0] < grad_input_data[1])
    assert_true(grad_input_data[1] < grad_input_data[1*in_width+1])
```

### Step 4 — Register in `main()` and verify test count

ADR-009 requires ≤10 test functions per file. Count before adding.

```mojo
fn main() raises:
    ...
    test_conv2d_backward_multichannel_padding1_values()
    print("✓ test_conv2d_backward_multichannel_padding1_values")
    ...
```

Run locally to confirm all pass:

```bash
just test-group tests/shared/core "test_conv_part3.mojo"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `padding=2` for smaller overlap counts | Larger padding → more zero-padded region, smaller overlap at borders | Over-complicates analytical derivation; output spatial changes unless carefully sized | Stick to same-padding (padding=1, kernel=3) so output spatial = input spatial |
| Asserting all interior pixels equal | Checked only position (1,1) | Not all "interior" positions have 3×3 overlap — only positions where both h and w are interior | Verify positions individually; `(1,1)` is always safe for a 5×5 grid |
| Using `padding=0` for the new test | Existing test already uses `padding=0` | Duplicate of `test_conv2d_backward_multichannel_values` — adds no coverage | Always verify what the existing tests cover before designing a new one |
| Setting `tolerance=1e-5` | Same as the no-padding values test | Large spatial sums (up to 72.0) accumulate more floating-point error | Use `tolerance=1e-3` for sums over many elements |

## Results & Parameters

### Passing test output

```
Running Conv2D Part 3 tests (backward pass and integration)...
✓ test_conv2d_backward_shapes
✓ test_conv2d_backward_bias_gradient
✓ test_conv2d_no_bias_backward_shapes
✓ test_conv2d_backward_multichannel_shapes
✓ test_conv2d_backward_multichannel_values
✓ test_conv2d_backward_multichannel_padding1_values
✓ test_conv2d_forward_backward_consistency

All Conv2D Part 3 tests passed!
✅ PASSED: tests/shared/core/test_conv_part3.mojo
```

### Key gradient formula

```
For all-ones config, padding=P, kernel K×K, out_channels=C:
  overlap_h(ih) = min(ih+1, K-P, N-ih, P+1)   # simplified for padding=1, K=3
  grad_input[b,ic,ih,iw] = C × overlap_h(ih) × overlap_w(iw)
```

For `padding=1, K=3, C=8, N=5`:

| Position | h_overlap × w_overlap | grad_input |
|----------|-----------------------|------------|
| corner (0,0) | 2 × 2 = 4 | 32.0 |
| edge (0,1) | 2 × 3 = 6 | 48.0 |
| interior (1,1) | 3 × 3 = 9 | 72.0 |
