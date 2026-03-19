---
name: conv2d-all-gradients-dedicated-file
description: 'Create a dedicated test file to gradient-check all three conv2d backward
  outputs (grad_input, grad_weights, grad_bias) across multiple configurations. Use
  when: conv2d backward grad_weights and grad_bias lack finite-difference validation
  and a new dedicated file is needed.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Problem | `conv2d_backward` tests in existing files only gradient-check `grad_input`; `grad_weights` and `grad_bias` are untested by finite differences |
| Solution | Create `test_gradient_checking_conv2d.mojo` with 9 tests covering all three outputs across three configurations (same-padding, strided, multi-channel) |
| Constraint | ADR-009: ≤10 `fn test_` functions per file; 9 tests fit exactly |
| Result | New file + CI workflow pattern update; PR #4793 created with auto-merge enabled |

## When to Use

1. `conv2d_backward` returns a struct with `grad_input`, `grad_weights`, `grad_bias` but
   only `grad_input` has finite-difference gradient checks
2. A follow-up issue (e.g. issue #3774 following #3233) explicitly requests
   dedicated coverage for all backward outputs
3. Existing gradient-checking files are at or near the ADR-009 10-test limit
4. The project uses `check_gradients(forward_fn, backward_fn, x, epsilon, tolerance)`
   from `shared.testing.gradient_checker`

## Verified Workflow

### Quick Reference

```bash
# Count tests in existing files to decide if new file is needed
grep -c "^fn test_" tests/shared/core/test_gradient_checking_*.mojo

# Verify new file stays under limit
grep -c "^fn test_" tests/shared/core/test_gradient_checking_conv2d.mojo
# Expected: 9

# Add to CI pattern
grep -n "Core Gradient" .github/workflows/comprehensive-tests.yml
```

### Step 1: Audit existing coverage

Check which backward outputs already have gradient checking:

```bash
grep -n "grad_weights\|grad_bias\|grad_input" \
  tests/shared/core/test_gradient_checking_*.mojo \
  tests/shared/core/test_backward_conv_pool.mojo
```

Identify the gap: `grad_weights` and `grad_bias` may only appear in shape/value tests,
not in `check_gradients()` calls.

### Step 2: Check ADR-009 capacity in existing files

```bash
grep -c "^fn test_" tests/shared/core/test_gradient_checking_basic.mojo
grep -c "^fn test_" tests/shared/core/test_gradient_checking_dtype.mojo
```

If adding 9 tests (3 outputs × 3 configs) would exceed 10 in any file,
create a new dedicated file instead.

### Step 3: Design three configurations

Cover three cases that stress different aspects of the backward pass:

| Config | stride | padding | Input shape | Kernel shape | Why |
|--------|--------|---------|-------------|--------------|-----|
| A (same-padding) | 1 | 1 | (1,1,4,4) | (1,1,3,3) | Tests padding boundary behavior |
| B (strided) | 2 | 0 | (1,1,7,7) | (1,1,3,3) | Tests stride-induced gradient sparsity |
| C (multi-channel) | 1 | 1 | (1,2,5,5) | (3,2,3,3) | Tests multi-channel accumulation |

### Step 4: Create the test file

File: `tests/shared/core/test_gradient_checking_conv2d.mojo`

Header pattern (required):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Imports:

```mojo
from shared.core.conv import conv2d, conv2d_backward
from shared.core.extensor import ExTensor, zeros
from shared.testing.gradient_checker import check_gradients
from shared.testing.assertions import assert_true
```

Test structure for each output (repeat for grad_input, grad_weights, grad_bias):

```mojo
fn test_conv2d_<config>_grad_<output>() raises:
    """Test conv2d grad_<output> with <config description>."""
    # Build x, kernel, bias with non-uniform initialization
    for i in range(<size>):
        x._data.bitcast[Float32]()[i] = Float32(i) * 0.1
    for i in range(<size>):
        kernel._data.bitcast[Float32]()[i] = Float32(i) * 0.05 + 0.1

    fn forward(<var>: ExTensor) raises escaping -> ExTensor:
        return conv2d(<x_or_var>, <k_or_var>, <b_or_var>, stride=<s>, padding=<p>)

    fn backward_fn(grad_out: ExTensor, <var>: ExTensor) raises escaping -> ExTensor:
        var result = conv2d_backward(grad_out, <x_or_var>, <k_or_var>, stride=<s>, padding=<p>)
        return result.grad_<output>

    var passed = check_gradients(forward, backward_fn, <var>, epsilon=1e-4, tolerance=1e-2)
    assert_true(passed, "Conv2D <config> grad_<output> check failed")
```

**Key patterns:**

- Use `epsilon=1e-4` (not `1e-5`) for conv2d — consistent with existing tests in this repo
- The variable being perturbed changes per output:
  - `grad_input` → perturb `x` (input tensor)
  - `grad_weights` → perturb `kernel` (kernel tensor)
  - `grad_bias` → perturb `bias` (bias tensor)
- Non-uniform initialization prevents degenerate all-zero gradients
- `raises escaping` required on closures passed to `check_gradients`

### Step 5: Update CI workflow pattern

Add the new file to the `"Core Gradient"` pattern entry in
`.github/workflows/comprehensive-tests.yml`:

```yaml
- name: "Core Gradient"
  path: "tests/shared/core"
  pattern: "... test_gradient_checking_conv2d.mojo ..."
  continue-on-error: true
```

Insert alphabetically among other `test_gradient_checking_*.mojo` entries.

### Step 6: Commit and create PR

```bash
git add tests/shared/core/test_gradient_checking_conv2d.mojo
git add .github/workflows/comprehensive-tests.yml
git commit -m "test(conv2d): Add gradient checking for grad_weights and grad_bias

Creates test_gradient_checking_conv2d.mojo with 9 finite-difference
gradient checks covering all three conv2d backward outputs
(grad_input, grad_weights, grad_bias) across three configurations.

Closes #<issue-number>"

gh pr create --title "test(conv2d): Add gradient checking for grad_weights and grad_bias" \
  --body "Closes #<issue-number>" --label "testing"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add to existing file | Adding all 9 tests to `test_gradient_checking_dtype.mojo` | Would exceed ADR-009 10-test limit (file already had tests) | Count existing tests first; create new file when limit would be breached |
| Use `check_gradient` (no s) | Using `from shared.testing import check_gradient` instead of `check_gradients` | Different API: `check_gradient` requires explicit `grad_output` tensor; `check_gradients` computes it internally | Use `check_gradients` from `shared.testing.gradient_checker` for self-contained tests |
| Run tests locally | `pixi run mojo test tests/shared/core/test_gradient_checking_conv2d.mojo` | GLIBC version mismatch — Mojo requires 2.32+, host may have older | Test via CI/Docker only; see `docs/dev/mojo-glibc-compatibility.md` |

## Results & Parameters

### Test parameters (copy-paste)

```mojo
# Conv2D gradient checking parameters
epsilon=1e-4    # Step size (larger than default 1e-5 for conv stability)
tolerance=1e-2  # 1% relative tolerance (consistent with other conv2d tests)
```

### Configuration table

| Config | Input | Kernel | stride | padding | Tests |
|--------|-------|--------|--------|---------|-------|
| same-padding | (1,1,4,4) | (1,1,3,3) | 1 | 1 | grad_input, grad_weights, grad_bias |
| strided | (1,1,7,7) | (1,1,3,3) | 2 | 0 | grad_input, grad_weights, grad_bias |
| multi-channel | (1,2,5,5) | (3,2,3,3) | 1 | 1 | grad_input, grad_weights, grad_bias |

### CI pattern entry

```yaml
pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo test_gradient_checking_basic.mojo test_gradient_checking_conv2d.mojo test_gradient_checking_dtype.mojo ..."
```
