---
name: gradient-checking-test-setup-fixes
description: 'Fix gradient checking test failures caused by pathological test setup.
  Use when: (1) gradient checks fail with analytical~0 vs numerical~nonzero for normalization
  layers, (2) any gradient check exceeds tolerance due to large-magnitude gradients,
  (3) migrating check_gradients() to check_gradient(). Migration is COMPLETE as of v3.0.0.'
category: testing
date: 2026-04-09
version: 3.0.0
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
  - migration-complete
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Complete migration from `check_gradients()` to `check_gradient()` across all gradient checking tests |
| **Outcome** | All 5 remaining test files migrated (59 calls). 2 meta-test files intentionally keep `check_gradients()`. PR #5210. |
| **Verification** | verified-local (PR #5210 created, CI pending) |
| **History** | [changelog](./gradient-checking-test-setup-fixes.history) |

## When to Use

- CI "Core Gradient" test group fails with gradient checking mismatches
- Batch norm backward gradient check shows analytical~0 vs numerical~0.09 (cancellation gotcha)
- Any gradient check exceeds tolerance when gradient magnitudes are large (>10)
- `check_gradients()` is used anywhere outside the 2 meta-test files (broken tolerance model)
- Accumulated float32 precision error exceeds absolute tolerance in multi-element output sums
- Migrating a test file from `check_gradients()` to `check_gradient()`

## Verified Workflow

### Quick Reference

```bash
# Diagnose: extract failure lines from CI
gh run view <run_id> --log-failed 2>&1 | grep -E "(FAILED|Gradient check FAILED|Analytical:|Numerical:|Tolerance:)"

# Find tests still using check_gradients() — should only be the 2 meta-test files
grep -r "check_gradients" tests/shared/core/test_gradient_check*.mojo
# Expected: only test_gradient_checker_meta.mojo and test_gradient_checker_noncont_tensors.mojo
```

### Migration Status (v3.0.0 -- COMPLETE)

All gradient checking test files now use `check_gradient()` except for 2 intentional exceptions:

| File | Status | Notes |
| --- | --- | --- |
| `test_gradient_checking_batch_norm.mojo` | Migrated (v1.0.0) | Non-uniform grad_output for cancellation fix |
| `test_gradient_checking_conv2d.mojo` | Migrated (v2.0.0) | Relative tolerance for large magnitudes |
| `test_gradient_checking_depthwise_conv2d.mojo` | Migrated (v2.0.0) | Non-uniform inputs + relative tolerance |
| `test_gradient_validation.mojo` | Migrated (v3.0.0) | 59 calls across 5 files |
| `test_gradient_validation_activations.mojo` | Migrated (v3.0.0) | |
| `test_gradient_validation_layers.mojo` | Migrated (v3.0.0) | |
| `test_gradient_checking_basic.mojo` | Migrated (v3.0.0) | |
| `test_gradient_checking_dtype.mojo` | Migrated (v3.0.0) | |
| `test_gradient_checker_meta.mojo` | KEEPS `check_gradients()` | Tests Bool-return semantics (intentional False for wrong gradients) |
| `test_gradient_checker_noncont_tensors.mojo` | KEEPS `check_gradients()` | Tests Bool-return semantics (intentional False for wrong gradients) |

### Detailed Steps

1. **Always use `check_gradient()` (no trailing 's')** for ALL gradient checking tests:

   The critical difference is the tolerance model:

   | API | Tolerance | Formula |
   | --- | --- | --- |
   | `check_gradients()` | Pure absolute | `abs(diff) >= tolerance` (BROKEN for large gradients) |
   | `check_gradient()` | Combined relative+absolute | `abs(diff) > atol + rtol * max_magnitude` (CORRECT) |

   For a gradient of magnitude 32.4 with diff 0.046:
   - `check_gradients(tolerance=0.01)`: 0.046 >= 0.01 -- FAIL
   - `check_gradient(rtol=1e-2, atol=1e-2)`: 0.046 > (0.01 + 0.01*32.4) = 0.334 -- PASS

   **Exception**: `test_gradient_checker_meta.mojo` and `test_gradient_checker_noncont_tensors.mojo`
   MUST keep `check_gradients()` because they test Bool-return semantics -- they verify that the
   checker returns False for intentionally wrong gradients. `check_gradient()` raises on failure
   instead of returning Bool, so it cannot be used for "verify the checker rejects wrong gradients" tests.

2. **The `_ones_grad` helper** -- create grad_output from forward output shape:

   ```mojo
   from shared.testing.gradient_checker import check_gradient
   from shared.core.any_tensor import AnyTensor, zeros, zeros_like

   fn _ones_grad(output: AnyTensor) raises -> AnyTensor:
       """Create all-ones grad_output matching the forward output shape."""
       var grad = zeros_like(output)
       for i in range(output.numel()):
           grad._set_float64(i, 1.0)
       return grad^

   # In each test:
   var output = forward(input)
   var grad_output = _ones_grad(output)
   check_gradient(forward, backward, input, grad_output, rtol=1e-2, atol=1e-2)
   ```

   `check_gradient()` requires an explicit `grad_output` parameter (unlike `check_gradients()`
   which hardcodes ones internally). The `_ones_grad` helper creates it from the forward output.

3. **Tolerance mapping** -- converting old `check_gradients()` calls:

   | Old call | New call | Rationale |
   | --- | --- | --- |
   | `check_gradients(..., tolerance=0.01)` | `check_gradient(..., rtol=1e-2, atol=1e-2)` | Standard: 1% relative + absolute floor |
   | `check_gradients(..., tolerance=0.05)` | `check_gradient(..., rtol=5e-2, atol=1e-4)` | Large values: relative tolerance handles magnitude scaling; tighter absolute floor |
   | `check_gradients(..., tolerance=0.1)` | `check_gradient(..., rtol=1e-1, atol=1e-2)` | Relaxed: tolerance maps directly to rtol |
   | `check_gradients(...)` (default tolerance) | `check_gradient(..., rtol=1e-2, atol=1e-2)` | Default mapping |

   **Rule of thumb**: `tolerance=X` maps to `rtol=X`. Set `atol=1e-2` for normal cases.
   For large-value tests where magnitudes scale up, use `atol=1e-4` to let relative tolerance dominate.

4. **For normalization layers (batch norm, layer norm)** -- use non-uniform grad_output:

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

5. **Always use non-uniform inputs**:

   ```mojo
   var input = zeros(shape, DType.float32)
   for i in range(input.numel()):
       input._data.bitcast[Float32]()[i] = Float32(i) * Float32(0.1)
   ```

6. **Remove stale comments**: If test files contain comments referencing old workarounds for JIT/bitcast crashes, remove them. The root cause (bitcast UAF) has been fixed.

### Decision Tree (v3.0.0)

```text
Writing or migrating a gradient checking test?
├─ Is this a meta-test that checks Bool return of check_gradients()?
│   └─ YES → Keep check_gradients() (test_gradient_checker_meta, test_gradient_checker_noncont_tensors)
└─ NO → Use check_gradient() (no trailing 's') with:
    ├─ Normalization layer? → Non-uniform grad_output (Float32(i%4)*0.25 - 0.3)
    └─ All other layers → _ones_grad(output) helper
    ├─ Old tolerance=X → rtol=X, atol=1e-2 (normal) or atol=1e-4 (large values)
    └─ Always: non-uniform inputs
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Increasing tolerance to hide batch norm mismatch | Raise tolerance from 1e-2 to 1e-1 | Masks the real issue -- doesn't validate the backward pass correctly | Fix the test setup, not the threshold |
| Fixing the batch norm backward formula | Suspected formula bug since analytical=0 but numerical=0.09 | The formula IS correct -- zero is the right answer for uniform grad_output | Verify the math before assuming the implementation is wrong |
| Using epsilon=1e-5 for conv2d | Smaller epsilon for more accurate finite differences | Float32 rounding error gets WORSE with smaller epsilon (~56% precision loss) | Smaller epsilon != more accurate in float32; use 3e-4 |
| Keeping uniform ones() inputs for depthwise conv2d | Assumed uniform inputs would be fine since depthwise conv doesn't normalize | Uniform inputs create degenerate patterns where many gradient contributions cancel | Always use non-uniform inputs for gradient checking |
| v1.0.0: Removing epsilon=1e-4 for conv2d (keeping check_gradients) | Changed from epsilon=1e-4 to default 3e-4, keeping check_gradients() | Diff dropped from 0.134 to 0.046 but STILL failed absolute tolerance of 0.01 | The problem was the tolerance MODEL (absolute vs relative), not the epsilon |
| v1.0.0: Using check_gradients() with non-uniform inputs for depthwise | Added non-uniform inputs but kept check_gradients() | Diff was 0.0103 at magnitude 126.4 -- barely exceeded absolute tolerance 0.01 | Large-magnitude gradients need relative tolerance; absolute tolerance can't scale |
| v3.0.0: Helper `_make_ones_grad(fwd: NumericalForward, x: AnyTensor)` | Tried to create helper taking a NumericalForward trait parameter to compute forward output internally | Mojo `def` functions cannot take trait parameters directly -- NumericalForward is a trait, not a concrete type | Use `_ones_grad(output: AnyTensor)` taking the already-computed forward output instead of trying to abstract over the forward function |

## Results & Parameters

### Tolerance Settings (v3.0.0 -- ALL layers)

```yaml
# Use check_gradient() for everything (except 2 meta-test files)
# Standard mapping:
rtol: 1e-2   # 1% relative tolerance (maps from old tolerance= value)
atol: 1e-2   # absolute floor for near-zero gradients

# Large-value mapping (when old tolerance=0.05):
rtol: 5e-2   # 5% relative tolerance
atol: 1e-4   # tight absolute floor — let relative tolerance dominate

# epsilon: auto-selected by check_gradient() based on dtype
```

### The Key Insight (v1.0.0 -> v2.0.0 -> v3.0.0)

```text
v1.0.0 thought the problem was epsilon (step size for finite differences).
v2.0.0 discovered the problem was the tolerance model itself.
v3.0.0 completed the migration across all test files.

check_gradients() asks: "Is the absolute difference < 0.01?"
  -> For gradient=32.4, diff=0.046: 0.046 >= 0.01 -> FAIL (0.14% error, should pass)

check_gradient() asks: "Is the absolute difference < atol + rtol * magnitude?"
  -> For gradient=32.4, diff=0.046: 0.046 < 0.01 + 0.01*32.4 = 0.334 -> PASS

Only 2 files keep check_gradients(): meta-tests that need Bool return value.
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5107 (2 commits), CI Core Gradient group | [notes.md](./gradient-checking-test-setup-fixes.notes.md) |
| ProjectOdyssey | PR #5210, 5 files / 59 calls migrated | Migration complete across entire test suite |
