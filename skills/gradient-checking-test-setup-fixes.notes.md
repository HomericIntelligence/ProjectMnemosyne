# Session Notes: Gradient Checking Test Setup Fixes

## Date: 2026-03-25

## Context

CI "Comprehensive Tests" workflow failing on main branch. Isolated to "Core Gradient" test group: 3 of 15 tests failing.

## CI Run Details

- Run ID: 23560373888
- Branch: main
- Commit: d8995ccbc (docs: add notes for investigation)

## Failing Tests (from CI logs)

### 1. test_gradient_checking_batch_norm.mojo

```
Gradient check FAILED:
  Max difference: 0.09416291862726212
  At index: 0
  Analytical: 0.0
  Numerical: 0.09416291862726212
  Tolerance: 0.01
Unhandled exception: batch_norm gradient check failed for batch_size=1
```

Root cause: `check_gradients()` at line 153-157 of gradient_checker.mojo sets `grad_output = ones_like(output)`. For batch norm with beta=0, this triggers the identity `sum(x_norm) = 0`, making the PyTorch backward formula produce exactly 0.

### 2. test_gradient_checking_conv2d.mojo

```
Gradient check FAILED:
  Max difference: 0.13441085815429688
  At index: 43
  Analytical: 44.54999923706055
  Numerical: 44.684410095214844
  Tolerance: 0.01
Unhandled exception: Conv2D multi-channel grad_input check failed
```

Root cause: Test passes `epsilon=1e-4` explicitly, overriding the default `3e-4`. With 75 output elements (3 channels x 5x5) at magnitude ~44.5, accumulated float32 error exceeds 0.01.

Relative error: 0.134/44.68 = 0.3% — well within reason for float32.

### 3. test_gradient_checking_depthwise_conv2d.mojo

```
Unhandled exception: depthwise_conv2d kernel gradient check failed
```

Root cause: All inputs are `ones()` (uniform), creating degenerate gradient patterns.

## Skills Registry Matches

Four existing skills matched this problem:
- `batch-norm-gradient-test-fix.md` — exact fix pattern
- `batch-norm-backward-gradient-analysis.md` — mathematical proof
- `conv2d-gradient-checking.md` — tolerance settings
- `depthwise-conv2d-gradient-checking.md` — non-uniform input patterns

## Key Files Modified

- `tests/shared/core/test_gradient_checking_batch_norm.mojo` — full rewrite
- `tests/shared/core/test_gradient_checking_conv2d.mojo` — remove epsilon=1e-4
- `tests/shared/core/test_gradient_checking_depthwise_conv2d.mojo` — non-uniform inputs

## Key Insight

The two gradient checking functions have a critical API difference:
- `check_gradients()` — hardcodes `grad_output = ones_like(output)` (line 153-157)
- `check_gradient()` — accepts custom `grad_output` parameter (line 727)

For normalization layers, `check_gradients()` will ALWAYS create degenerate test conditions.

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/5107
