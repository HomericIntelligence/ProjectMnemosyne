---
name: mojo-tensor-unit-test-and-gradient-checking
description: "Use when: (1) writing or extending Mojo tensor unit tests (dtype-aware string/repr, BFloat16 NaN canonicalization, UInt bitwise boundary tests, view vs copy semantics in slice tests), (2) re-enabling NOTE-disabled or TODO-stubbed Mojo test files and resolving TODO(#N) markers, (3) writing numerical gradient checks for conv2d, depthwise conv2d, batch norm, layer norm, or pooling backward passes in Mojo, (4) a gradient check reports analytical≈0 vs numerical≈nonzero for a normalization layer (often caused by symmetric weight initialization), (5) adding end-to-end convergence tests as a complement to per-op finite-difference checks, (6) diagnosing symmetric-weight-init dead-symmetry pathology where uniform-fill weights produce algebraically zero gradients to early layers, (7) adding hardware-guarded BF16 precision recommendations to dtype selection functions."
category: testing
date: 2026-07-19
version: "1.2.0"
user-invocable: false
history: mojo-tensor-unit-test-and-gradient-checking.history
tags:
  - mojo
  - tensor
  - unit-test
  - gradient-checking
  - backward-pass
  - finite-differences
  - bfloat16
  - dtype
  - weight-init
  - dead-symmetry
  - conv2d
  - batch-norm
  - layer-norm
---

# Mojo Tensor Unit Test and Gradient Checking

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Category** | testing |
| **Language** | Mojo v0.26.1+ |
| **Objective** | Canonical reference for Mojo tensor unit-test patterns, numerical gradient/backward-pass checking, symmetric-weight-init diagnostics, and BF16 precision selection |
| **Outcome** | Consolidated from 4 skills covering tensor test patterns, gradient checking, dead-symmetry debugging, and BF16 dtype recommendation |
| **Verification** | verified-ci |

## When to Use

Use this skill when working in a Mojo tensor/operator test suite and any of these apply:

1. Writing or extending tensor unit tests: dtype-aware `__str__`/`__repr__`, BFloat16 NaN
   canonicalization, UInt bitwise NOT / overflow boundary tests, view vs copy semantics in slices
2. Re-enabling NOTE-disabled or TODO-stubbed Mojo test files, or resolving `TODO(#N)` markers after
   a blocking issue closes
3. Writing numerical gradient checks for conv2d, depthwise conv2d, batch norm, layer norm, or
   pooling backward passes
4. A gradient check reports `analytical ≈ 0` vs `numerical ≈ nonzero` for a normalization layer
   (often caused by symmetric weight initialization or uniform `grad_output`)
5. Adding end-to-end convergence tests as a complement to per-op finite-difference checks
6. Diagnosing symmetric-weight-init dead-symmetry where uniform-fill weights produce algebraically
   zero gradients to early layers (loss plateaus at `ln(num_classes)`)
7. Adding hardware-guarded BF16 precision recommendations to a dtype-selection function

Do NOT use when:

- Tests are skipped due to an active, unfixed compiler bug — document the blocker instead
- The blocking upstream issue is still open — verify `gh issue view N --json state` first
- The task is a runtime numeric-correctness bug (not a test) — different scope

## Verified Workflow

### Quick Reference

| Task | Key Action |
| ---- | ---------- |
| Activate `__str__`/`__repr__` stubs | Implement `Stringable`/`Representable`; dispatch via `_format_element()` by dtype |
| Dtype-aware int/bool formatting | Use explicit `== DType.xxx` comparisons (not `is_integral()`) |
| BF16 NaN canonicalization | Raw bit manipulation (UInt16 read, `<< 16`, Float32 bitcast); never numeric cast |
| BF16 regression (silent no-op) | Three-part test: read zero-guard, write zero-guard, round-trip; tolerance `1e-2` |
| UInt bitwise NOT / overflow tests | Use typed variables; `~UInt8(0)==255`; `255+1` wraps to 0 |
| View vs copy | `tensor[a:b]` returns a copy; `tensor.slice(a, b)` returns a write-through view |
| Re-enable disabled tests | `Read` file first; identify disable pattern; check blockers; uncomment/fix syntax |
| Normalization gradient check | Never `ones_like(output)`; use `sum(output^2)` loss → `grad_output = 2*output` |
| API choice | `check_gradient(rtol, atol)` for all real tests; `check_gradients(tol)` only meta-tests |
| Convergence test | Run ≥20 SGD steps on persistent params; assert relative loss drop; asymmetric init |
| Dead-symmetry diagnosis | Loss plateau at `ln(C)` + tiny early-layer grads → rerun with asymmetric init first |
| BF16 dtype recommendation | Add `hardware_has_bf16: Bool = True` param; guard Apple Silicon (no BF16) |

**Tolerance quick-ref by layer type:**

| Layer | rtol | atol | epsilon |
| --- | --- | --- | --- |
| Conv2D backward | `1e-2` | `1e-2` | `1e-4` or `3e-4` |
| Depthwise Conv2D | `1e-2` | `1e-2` | `3e-4` |
| BatchNorm training | `2e-2` | `1e-4` | `1e-3` |
| BatchNorm inference | `1e-2` | `1e-4` | `1e-3` |
| LayerNorm input | `1e-2` | `1e-5` | `1e-4` |
| LayerNorm gamma/beta | `1e-2` | `1e-4` | `1e-4` |
| MaxPool/AvgPool | `1e-3` | `5e-4` | `3e-4` |

**Dtype tolerance (round-trip):** bfloat16 `1e-2` (7 mantissa bits) · float16 `1e-3` (10 bits) ·
float32 `1e-6` (23 bits).

---

### Detailed Steps

#### A. Tensor Unit-Test Patterns

**A1 — Dtype-aware str/repr.** When `__str__` renders int32 as `"1.0"` or bool as `"0.0"`, add a
`_format_element` helper that dispatches by dtype with explicit comparisons (the codebase uses
runtime enum comparisons everywhere — do NOT use `dtype.is_integral()`):

```mojo
fn _format_element(self, i: Int) -> String:
    if self._dtype == DType.bool:
        return "True" if self._get_int64(i) != 0 else "False"
    elif (self._dtype == DType.int8 or self._dtype == DType.int16
          or self._dtype == DType.int32 or self._dtype == DType.int64
          or self._dtype == DType.uint8 or self._dtype == DType.uint16
          or self._dtype == DType.uint32 or self._dtype == DType.uint64):
        return String(self._get_int64(i))
    else:
        return String(self._get_float64(i))
```

Expected outputs: `ExTensor([0, 1, 2], dtype=int32)`, `ExTensor([False, True, False], dtype=bool)`.

**A2 — BFloat16 NaN canonicalization.** A numeric cast (`Float64(Float32(BFloat16))`) silently
canonicalizes NaN mantissa bits, breaking hash consistency. Use raw bit manipulation — BF16 bits
map directly to the upper 16 bits of Float32:

```mojo
elif self._dtype == DType.bfloat16:
    var raw_ptr = (self._data + offset).bitcast[UInt16]()
    var f32_bits: UInt32 = UInt32(raw_ptr[]) << 16
    return Float64(UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[])
```

Inject raw NaN bits via `t._data.bitcast[UInt16]()[0] = raw_bits` (the typed setter re-canonicalizes).
NaN patterns: `0x7FC0` (canonical positive quiet NaN), `0xFFC0` (negative quiet NaN). Note `0x7F80`
is +Inf and `0xFF80` is -Inf — mantissa zero, NOT NaN. All three NaN-hash tests must assert equal
hashes (canonical, negative, cross-variant).

**A3 — BFloat16 silent-no-op regression.** Audit dtype-dispatched functions for a missing bfloat16
branch. Three-part test using exactly-representable values (0.5, 1.0, 1.5, 2.0, -1.0): a read
zero-guard, a write zero-guard, and a round-trip, all with `tolerance=1e-2`. Unsafe (not exact in
bfloat16): 0.1, 0.3, 1.3, 2.7, 3.9.

**A4 — UInt boundary tests.** Use typed variables, not literal expressions, so arithmetic stays in
the type. Bitwise NOT: `~UInt8(0)==255`, `~UInt8(255)==0`, `~UInt8(0b10101010)==85`, `~~val==val`.
Overflow/wrap: `UInt8(255)+1 → 0`, `UInt8(0)-1 → 255`, `UInt8(16)*16 → 0`. Extend the existing
`test_unsigned.mojo` for overflow; create a standalone file only for bitwise NOT.

**A5 — View vs copy.** `tensor[a:b]` returns a copy (`_is_view == False`); `tensor.slice(a, b)`
returns a write-through view (`_is_view == True`). Use `.slice()` when a test mutates and expects
the original to change. When a function expects `AnyTensor` but you hold `Tensor[dtype]`, add
`.as_any()` and check ALL call sites for cascading type changes.

**A6 — Re-enabling disabled tests.** Always `Read` the file before assuming structure. Identify the
disable pattern (stub `main()` printing "SKIPPED", `NOTE: temporarily disabled`, commented-out
`pass # Placeholder`, etc.), verify the blocker is closed (`gh issue view N --json state`), then
uncomment/implement. Common Mojo syntax fixes: `shape.append(4)` not `shape[0]=4`; list literals
`[1,2,3]` not `List[Int](1,2,3)`; DataLoader requires 2D input `[n_samples, feature_dim]`.

**A7 — Value-correctness gap after `as_contiguous()`.** When an existing test only verifies
`is_contiguous()` and `_strides` after `as_contiguous()`, it never checks that the values were
actually reordered. Build the tensor with `arange + reshape + transpose` (predictable values),
derive the expected layout from the transpose stride mapping, and append per-element
`assert_almost_equal` calls after the stride assertions. For `(rows=3, cols=4)` transposed to
`(4, 3)`, the contiguous result follows `c[j,i] = i*cols + j`:

```mojo
# Original (3,4) row-major: a[i,j] = i*4 + j (values 0..11)
# After transpose to (4,3): t[j,i] = a[i,j]; row 0 = col 0 of original: 0, 4, 8
assert_almost_equal(c._get_float64(0), 0.0, 1e-6, "c[0,0] should be 0")
assert_almost_equal(c._get_float64(1), 4.0, 1e-6, "c[0,1] should be 4")
assert_almost_equal(c._get_float64(2), 8.0, 1e-6, "c[0,2] should be 8")
assert_almost_equal(c._get_float64(3), 1.0, 1e-6, "c[1,0] should be 1")
```

Rule: assert values on the contiguous result `c`, NOT on the non-contiguous view `t` —
`_get_float64(i)` reads flat memory ignoring strides, so on `t` it returns the pre-transpose
layout and gives false positives.

#### B. Gradient / Backward-Pass Finite-Difference Checking

**B1 — The normalization cancellation problem.** For any mean-centering normalization layer,
`sum(x_norm) = 0` by construction. BatchNorm/LayerNorm backward contains `sum(grad_output * x_norm)`;
with `grad_output = ones`, this is `sum(x_norm) = 0`, so the analytical gradient is exactly zero
while float32 finite differences pick up ≈0.009 noise — a 1000× false failure. **Never use
`ones_like(output)` for a zero-mean normalization layer.** Use a `sum(output^2)` loss with a
closed-form derivative:

```mojo
var grad_output = multiply(full_like(output, 2.0), output)  # dL/dY = 2*output

fn forward_for_grad(inp: ExTensor) raises -> ExTensor:
    var out = batch_norm2d(inp, gamma, beta, running_mean, running_var, training=True, epsilon=1e-5)[0]
    var r = multiply(out, out)
    while r.dim() > 0:
        r = reduce_sum(r, axis=0, keepdims=False)
    return r
```

The `grad_output` and the `forward_for_grad` closure MUST derive from the same loss. For
conv2d/depthwise, `ones_like(output)` is safe (with `padding>0`, prefer non-uniform). For pooling,
use a non-uniform pattern for the numerical tier (AvgPool with symmetric inputs cancels).

**B2 — Use `check_gradient()`, not `check_gradients()`.** For a gradient magnitude 32.4 with diff
0.046: `check_gradients(tolerance=0.01)` fails (0.046 ≥ 0.01) but
`check_gradient(rtol=1e-2, atol=1e-2)` passes (0.046 ≤ 0.01 + 0.01×32.4 = 0.334). The combined model
`abs(diff) ≤ atol + rtol*magnitude` is correct for large magnitudes. Migration:
`tolerance=0.01 → rtol=1e-2, atol=1e-2`. Keep `check_gradients()` ONLY in the two meta-test files
that verify Bool-return semantics (`test_gradient_checker_meta.mojo`,
`test_gradient_checker_noncont_tensors.mojo`).

**B3 — Analytically-exact conv2d backward.** For all-ones input/kernel, zero bias, single output
position (`input_spatial == kernel_spatial`): `grad_weights = batch×1.0`,
`grad_input = out_channels×1.0`, `grad_bias = batch×out_H×out_W`. Padding=1 border (kernel=3,
out_ch=C): corner `2×2×C`, edge `2×3×C`, interior `3×3×C` (e.g. C=8: 32, 48, 72). Depthwise differs:
kernel shape is `(channels, 1, kH, kW)` and the gradient field is `.grad_weights` (NOT
`.grad_kernel`); per-file limit is ≤8 tests vs ≤10 for regular conv.

**B4 — Pooling three-tier.** Tier 1 shape (`grad_input.shape() == input.shape()`); Tier 2
analytical (MaxPool: only the max position receives gradient; AvgPool: each element `1/pool_size^2`);
Tier 3 numerical with a non-uniform `grad_output`, wrapping the forward to return a scalar
weighted-dot-product ExTensor (the vector-output path sums Jacobian elements and can cancel).

**B5 — Per-file test budget.** CI heap corruption risk grows with file size — keep ≤10 tests
(≤8 depthwise) per file. Check `grep -c "^fn test_" <file>.mojo` before adding; split alphabetically
into a new file and register it in the CI `pattern` list.

#### C. End-to-End Convergence Tests (complement to FD checks)

Per-op FD checks validate *gradient values*, not *training dynamics*. A substrate with correct
per-op gradients can still fail to train if the data pipeline corrupts inputs, the optimizer skips
parameters silently, or writeback is broken. **Add at least one end-to-end convergence test per
autograd substrate.** Three-tier pattern, each running N steps on persistent params asserting a
relative loss drop:

| Tier | Architecture | Steps | Pass criterion | Catches |
|------|--------------|-------|----------------|---------|
| 1 | Tiny MLP (linear → CE) | 20 | loss drops ≥90% | Tape recording, backward dispatch, optimizer step, writeback |
| 2 | Conv stack (conv→relu→flatten→linear→CE) | 30 | loss drops ≥70% | Multi-layer gradient propagation; chained cancellation |
| 3 | Production shape (LeNet) | 50 | loss drops ≥30% | Exact production op stack at realistic shape |

Critical: asymmetric weight init AND asymmetric inputs are mandatory for tiers 2+ (see D); the
loss-drop threshold must be relative (scale-invariant); also assert ≥1 trainable parameter changed
by some `min_abs_delta` to catch silent optimizer no-ops; persist parameter state by reassigning
`parameters[i].data` after each `optimizer.step()`.

#### D. Symmetric-Weight-Init Dead-Symmetry Diagnostic

**Symptom:** convergence test or training run plateaus at chance loss (`ln(num_classes)`), and
gradients to early (conv/embedding) layers come back at fp32 cancellation noise magnitude (~1e-8)
while later (FC) layers have normal-magnitude (~1e-1) gradients.

**The math** — for `y = Wx + b` with W uniformly initialized to constant `c`: every output
`y[i] = c*sum(x) + b[i]` differs only by bias → softmax near-uniform →
`dL/d_logits = softmax - target` sums to exactly 0 across classes → `dL/dx = (sum dL/dy)*c = 0`
algebraically (every W column identical). Upstream layers see near-zero `grad_input`. The
single-linear-layer case does NOT manifest (its own grad is `dL/dy ⊗ x`, still nonzero); the
pathology only appears in multi-layer stacks.

**Don't immediately blame the substrate.** Rerun with asymmetric per-element ramp init first; if
grads then look healthy, the original failure was the pathology, not a backward bug:

```mojo
def _make_asymmetric(shape: List[Int], base: Float64, slope: Float64) raises -> AnyTensor:
    var t = zeros(shape, DType.float32)
    var n = 1
    for d in shape: n *= d
    for i in range(n):
        t._set_float64(i, base + Float64(i) * slope)
    return t^
```

Rule: `slope = base / n` (n = input-dim size) keeps per-element variation comparable to real random
init; `slope=0.0` is uniform — same pathology. Uniform *bias* is harmless (no symmetry to break
across its axis); only uniform *weight matrices/kernels* trigger it. Inputs must also be asymmetric
so conv kernels have spatial signal. If grads still look wrong after asymmetric init, build a
manual-vs-autograd direct comparison — L2 diff should be exactly 0.0 if the substrate is correct.
A test plateau (symmetric init) and a production plateau (real upstream data bug) can share the same
fingerprint; verify each independently.

#### E. Hardware-Guarded BF16 Precision Recommendation

When a `recommend_precision_dtype`-style function leaves the large-model branch returning FP16, add
a `hardware_has_bf16: Bool = True` parameter (default True is safe — most x86/CUDA hardware supports
BF16; Apple Silicon does NOT and must pass `False`):

```mojo
fn recommend_precision_dtype(
    model_size_mb: Float64,
    hardware_has_fp16: Bool = True,
    hardware_has_bf16: Bool = True,
) -> DType:
    ...
    else:  # large model (>= 1000 MB): BF16 for wider exponent range
        if hardware_has_bf16:
            return DType.bfloat16
        else:
            return DType.float16
```

Update the docstring Args/Recommendations table and add three tests: large+BF16→bfloat16,
large+no-BF16→float16 (Apple guard), large+no-FP16→float32.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Grep for `__str__` before implementing | Expected existing impl per issue description | Methods absent — only in unrelated `nvfp4.mojo` | Verify implementation existence before activating tests; issue descriptions can be wrong |
| Run `pixi run mojo test` locally | Verify tests on host | GLIBC 2.31 vs required 2.32+ | Mojo tests only run in CI Docker; use `SKIP=mojo-format` for the format hook locally |
| `uuid` module for unique tmp path | `from uuid import uuid4` | No `uuid` module in Mojo v0.26.1 | Use `perf_counter_ns()` for a unique `/tmp` suffix |
| Numeric cast for BF16 in `_get_float64` | `Float64(Float32(BFloat16))` | CPU cast canonicalizes NaN bits, breaks hash consistency | Use raw bit manipulation (UInt16 read, `<<16`, Float32 bitcast) |
| Test `0xFF80` as negative BF16 NaN | Treated as negative NaN | `0xFF80` is -Inf (mantissa=0) | BF16 NaN needs exp=0xFF AND mantissa≠0; negative quiet NaN is `0xFFC0` |
| `dtype.is_integral()` for int dtype check | Called `.is_integral()` | Codebase never uses this pattern | Use explicit `== DType.xxx` comparisons to match existing style |
| Assumed `__getitem__(Slice)` returns view | Asserted `_is_view == True` on `tensor[2:8]` | `__getitem__(Slice)` returns a copy | Use `tensor.slice(a, b)` for write-through views |
| Asserted values on non-contiguous view `t` after transpose | Read `t._get_float64(i)` before `as_contiguous()` | `_get_float64(i)` reads flat memory ignoring strides — returns pre-transpose layout | Assert values on the contiguous result `c`, NOT the non-contiguous view `t` |
| Creating new file instead of extending | Created `test_uint_overflow.mojo` | `test_unsigned.mojo` already had the structure | Extend existing test files; don't duplicate |
| `ones_like(output)` for normalization grad | Uniform upstream grad for BN/LN backward | `sum(x_norm)=0`; analytical grad exactly zero; numerical ≈0.009 noise | Never use uniform grad_output for a zero-mean normalization layer |
| Increase atol to hide mismatch | Raised tolerance 1e-5→1e-2 | Masks the real issue without validating correctness | Fix the test setup, not the threshold |
| `check_gradients()` with conv2d (mag 32.4) | Only changed epsilon 1e-4→3e-4 | Diff 0.046 still failed absolute tol 0.01 | The problem is the tolerance model (absolute vs relative); use `check_gradient()` |
| `.grad_kernel` field for depthwise backward | Assumed field named `.grad_kernel` | Return type is `GradientTriple` with `.grad_weights` | Verify field names from `gradient_types.mojo`, not docstrings |
| Adding tests to a file at capacity | Kept adding to one file | At per-file limit; CI heap corruption risk | Check `grep -c "^fn test_"`; split into a new file at ≥6-8 tests |
| Uniform weight init in convergence tests | All weights = 0.05 | Dead-symmetry: identical outputs, uniform softmax, algebraically-zero early grads | Use asymmetric ramp init (`base + i*slope`) for multi-layer tiers |
| Blamed conv2d backward for ln(C) plateau | Saw chance-loss plateau + 1e-8 conv grads | Symmetric init produces the SAME fingerprint as a real substrate bug | Rerun with asymmetric init AND do manual-vs-autograd L2 compare to disambiguate |
| `_make_asymmetric(shape, 0.05, 0.0)` | Wanted "almost uniform" init | `slope=0.0` IS uniform — same pathology | Slope must be measurably nonzero; `slope = base/n` |
| Trusting FD checks as sufficient | Per-op tests passed while training hit 2.76% (chance) | FD validates gradient values, not training dynamics; missed upstream batch-copy bug | Pair every per-op check with ≥1 end-to-end convergence test |
| Trusting an optimizer's step-1 state unit test | `test_adopt_step1_bounded`/`test_adan_prev_grad_seeded` passed after the fix, so re-ran a multi-hour campaign — full run STILL underfit ~40pts vs PyTorch | A passing per-step state test does not prove full-run convergence; the residual cause was separate (baseline adam/momentum bypassed the parity-tested library op via a hand-rolled `_adam_update`) | ALWAYS sanity-run ONE real cell with the fixed binary before a long campaign; add a PyTorch-parity **reference column** and localize by arm — if plain/momentum match the reference but adam doesn't, the bug is the adaptive-optimizer dispatch, not the backward |
| Run tests via `just test-group` | Used `just` runner | `just` not in PATH in worktree | Use `pixi run mojo test <file>` directly |

## Results & Parameters

### Required Imports

```mojo
from shared.testing import compute_numerical_gradient, assert_gradients_close
from shared.testing.gradient_checker import check_gradient
from shared.core.extensor import ExTensor, zeros, ones, zeros_like, ones_like, full_like
from shared.core.normalization import (
    batch_norm2d, batch_norm2d_backward, layer_norm, layer_norm_backward,
)
from shared.core.conv import conv2d, conv2d_backward, depthwise_conv2d, depthwise_conv2d_backward
from shared.core.pooling import maxpool2d, avgpool2d, maxpool2d_backward, avgpool2d_backward
from shared.core.arithmetic import multiply
from shared.core.reduction import sum as reduce_sum
```

### Gradient Return Types

```text
GradientTriple (Conv2d / DepthwiseConv2d backward, with bias):
  .grad_input   → gradient w.r.t. input x
  .grad_weights → gradient w.r.t. kernel/weights (NOT .grad_kernel for depthwise)
  .grad_bias    → gradient w.r.t. bias
GradientPair (a.k.a. Conv2dNoBiasBackwardResult — no-bias conv backward path):
  .grad_a → gradient w.r.t. input
  .grad_b → gradient w.r.t. kernel
layer_norm_backward / batch_norm2d_backward return tuples:
  result[0] → grad_input, result[1] → grad_gamma, result[2] → grad_beta
```

### BF16 Recommendation — return value by configuration

| model_size_mb | hardware_has_fp16 | hardware_has_bf16 | Returns |
| --- | --- | --- | --- |
| < 100 | any | any | `DType.float32` |
| 100-999 | True | any | `DType.float16` |
| 100-999 | False | any | `DType.float32` |
| >= 1000 | True | True | `DType.bfloat16` |
| >= 1000 | True | False (Apple Silicon) | `DType.float16` |
| >= 1000 | False | any | `DType.float32` |

### Convergence Test Helpers

```mojo
def _assert_loss_decreased(name: String, losses: List[Float32], min_relative_drop: Float64) raises:
    var first = Float64(losses[0]); var last = Float64(losses[len(losses) - 1])
    if (first - last) / first < min_relative_drop:
        raise Error(name + ": loss drop below required " + String(min_relative_drop))

def _assert_parameter_changed(name: String, before: Float64, after: Float64, min_abs_delta: Float64) raises:
    var delta = before - after if before > after else after - before
    if delta < min_abs_delta:
        raise Error(name + ": parameter unchanged")
```

### Commit on GLIBC-old hosts

```bash
SKIP=mojo-format git commit -m "test(<layer>): add gradient checking tests"
# CI runs mojo format in Docker with correct GLIBC
```

Mojo binary requires GLIBC 2.32+. On older hosts, tests run only in CI; pre-commit hooks still
validate formatting locally.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Tensor test patterns (issues #3162, #3376, #3293, #3292, #4060, #3910, #3842, PRs #5097, #3013, #3077, #4127, #3082, #3081) | str/repr, BF16 NaN, UInt, view/copy, re-enablement |
| ProjectOdyssey | Gradient checking (BN PRs #3816, #4780; conv2d PRs #3865, #3772, #4793, #4809; depthwise PR #4794; migration PRs #5107, #5210; LayerNorm PR #4806; pooling PR #4782; analytical PRs #4797, #4799) | Per-op FD + check_gradient migration |
| ProjectOdyssey | Convergence + dead-symmetry (PR #5466) | 3-tier convergence; `_make_asymmetric`; Tier 1 1.39→0.022, Tier 2 1.41→0.099, Tier 3 7.16e7→2.23 |
| ProjectOdyssey | BF16 precision recommendation (PR #3710, issue #3202) | `hardware_has_bf16` param with Apple Silicon guard |
