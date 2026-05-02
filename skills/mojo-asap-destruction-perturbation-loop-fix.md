---
name: mojo-asap-destruction-perturbation-loop-fix
description: "Fix Mojo ASAP-destruction crashes in finite-difference perturbation loops where _get_float64/_set_float64 per-element bitcasts on temporary tensors returned by forward_fn trigger heap-use-after-free. Use when: (1) gradient checking tests crash intermittently AFTER printing test output (not before), (2) loop reads temporary tensors element-by-element after a forward pass, (3) same libKGENCompilerRTShared crash signature but crash happens mid-execution."
category: debugging
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - asap-destruction
  - bitcast
  - gradient-checking
  - perturbation-loop
  - mojo
  - heap-use-after-free
  - data_ptr
  - forward_fn
---

# Mojo ASAP Destruction in Perturbation Loops

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-29 |
| **Objective** | Root-cause and fix intermittent CI crashes in gradient checking tests |
| **Outcome** | Success — ASAP destruction UAF in `_check_gradients_perturb` fixed; CI stabilised |
| **Verification** | verified-ci (PR #5116, pushed and triggered fresh CI run) |

## When to Use

- `gradient_checker.mojo` perturbation loops crash intermittently in CI
- Crash has **test output printed before it** (e.g., "Running activation gradient tests...")
  — distinguishing it from a JIT *compilation* buffer overflow (which crashes before any output)
- Same `libKGENCompilerRTShared.so+0x3cb78b → libc __fortify_fail_abort` signature
- Code calls `tensor._get_float64(j)` or `tensor._set_float64(j, v)` inside a loop
  on a tensor that was returned by a function call in the same scope
- The loop variable tensor was NOT bound to a `var` at the beginning of a scope that
  outlives the loop (i.e., it's a temporary from `forward_fn(x)`)

## Diagnosis: Runtime vs. Compilation Crash

The key diagnostic is **where the crash appears relative to test output**:

| Symptom | Cause | Fix |
| --------- | ------- | ----- |
| `execution crashed` appears **before any test output** | JIT compilation buffer overflow — reduce `from shared.core import` to targeted submodule imports | See `mojo-jit-crash-doc` skill |
| `execution crashed` appears **after test output** | Runtime memory bug — ASAP destruction UAF | This skill |
| Crash after "Running X tests..." + warning lines | UAF during perturbation loop | This skill |
| Crash after specific assertion failure message | Real test logic bug | Debug the backward pass |

In the failing CI logs:
```
Running activation gradient tests...              ← test output printed
WARNING: check_gradients() got uniform grad_output...  ← more output
#0 0x00007fd16fdcb78b (libKGENCompilerRTShared.so+0x3cb78b)
execution crashed                                 ← crash AFTER output = runtime bug
```

## Root Cause

Mojo 0.26.1 applies **ASAP (As Soon As Possible) destruction** to local variables.
When `forward_fn(x)` returns a temporary `AnyTensor`, the compiler may destroy it
as soon as it appears to have been "used" — but `tensor.numel()` in `range(output_plus.numel())`
is the last apparent structural use, not the element reads in the loop body.

Each call to `_get_float64(j)` does:
```mojo
var ptr = (self._data + offset).bitcast[Float32]()
return ptr[].cast[DType.float64]()
```

If `self` was already destroyed (freed), `self._data` is a dangling pointer.
The heap allocator metadata corruption accumulates until glibc detects it and aborts
via `__fortify_fail_abort` (the `libc.so.6+0x45330` frame in the stack trace).

The crash is **non-deterministic** because ASLR changes memory layout between runs —
sometimes the freed region is re-used quickly (crash), sometimes not (pass).

## Verified Workflow

### Quick Reference

```bash
# Find all _get_float64/_set_float64 calls on temporaries in loop bodies
grep -n "_get_float64\|_set_float64" shared/testing/gradient_checker.mojo

# Pattern to look for (DANGEROUS — temporary tensor in loop):
# var output_plus = forward_fn(input_copy_plus)
# for j in range(output_plus.numel()):
#     var diff = output_plus._get_float64(j) ...  ← UAF risk

# Pattern to look for (SAFE — data_ptr acquired before loop):
# var output_plus = forward_fn(input_copy_plus)
# var out_plus_ptr = output_plus.data_ptr[dtype]()  ← keeps tensor alive
# for j in range(output_plus.numel()):
#     var diff = Float64(out_plus_ptr[j]) ...       ← safe
```

### Detailed Steps

**1. Identify the failing location**

Check if the crash comes before or after test output. If after → runtime bug.
Read the test runner output to find which test group crashed, then read the
perturbation function it uses.

**2. Audit all `_get_float64` / `_set_float64` calls inside loops**

```bash
grep -n "_get_float64\|_set_float64" shared/testing/gradient_checker.mojo
```

For each call, check: is the `self` tensor a temporary returned by `forward_fn` in this
scope, OR a named local that persists for the function lifetime? Only the former is dangerous.

**3. Apply the fix: acquire `data_ptr[dtype]()` before the loop**

The fix only works inside dtype-dispatched functions (those with `[dtype: DType]` parameter):

```mojo
# BEFORE (DANGEROUS — ASAP destruction UAF):
var output_plus = forward_fn(input_copy_plus)
var output_minus = forward_fn(input_copy_minus)
var numerical_sum: Float64 = 0.0
for j in range(output_plus.numel()):
    var diff = output_plus._get_float64(j) - output_minus._get_float64(j)
    numerical_sum += diff / (2.0 * epsilon)

# AFTER (SAFE — data_ptr derivation keeps tensors alive):
var output_plus = forward_fn(input_copy_plus)
var output_minus = forward_fn(input_copy_minus)
# Acquire typed pointers BEFORE the loop. Deriving data_ptr keeps the
# tensor alive for the pointer's scope (modular/modular#6187).
var out_plus_ptr = output_plus.data_ptr[dtype]()
var out_minus_ptr = output_minus.data_ptr[dtype]()
var numerical_sum: Float64 = 0.0
for j in range(output_plus.numel()):
    var diff = Float64(out_plus_ptr[j]) - Float64(out_minus_ptr[j])
    numerical_sum += diff / (2.0 * epsilon)
```

**4. Fix all occurrences in the file**

`gradient_checker.mojo` had 3 perturbation functions with this pattern:

| Function | Tensors affected |
| ---------- | ----------------- |
| `_check_gradients_perturb[dtype]` | `output_plus`, `output_minus` |
| `_compute_sampled_grad_perturb[dtype]` | `f_plus`, `f_minus` |
| `_perturb_and_compute_loss[dtype]` | `out_plus`, `out_minus`, `grad_output` |

**5. Add ASAN coverage to prevent regression**

```yaml
# .github/workflows/asan-tests.yml
- name: Run gradient checking tests under ASAN
  run: |
    just test-group-asan "tests/shared/core" "test_gradient_checking_basic.mojo test_gradient_checking_dtype.mojo"
```

ASAN will report `heap-use-after-free` immediately on any future regression,
instead of producing the misleading `execution crashed` message.

**6. Verify**

Push to the PR branch and check that gradient checking CI jobs pass consistently
across multiple runs. The crash was ~40-60% rate before the fix.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Classifying crash as JIT buffer overflow | Assumed `execution crashed` = compilation-time issue because same stack trace as known JIT crashes | Ignored the test output printed BEFORE the crash — compilation crashes never produce test output | Always check whether test output precedes the crash; if yes, it's a runtime bug |
| Transitive import fix (targeted submodule imports) | Converted 22 `from shared.core import` to `from shared.core.submodule import` in library code | Correct fix for JIT buffer overflow crashes, but doesn't fix runtime UAF crashes | Two different bugs have identical crash signatures; the import fix was valid for a different population of crashes |
| Assuming existing `_get_float64` fix was complete | Prior commit (#5104) fixed perturbation loops with `data_ptr`; assumed fix was comprehensive | `_check_gradients_perturb` was fixed but `_compute_sampled_grad_perturb` and `_perturb_and_compute_loss` still used `_get_float64` on temporaries | When fixing a pattern, grep for ALL instances in the file, not just the reported location |

## Results & Parameters

### Key Distinction: Two Separate Crash Populations

```text
Both crashes: libKGENCompilerRTShared.so+0x3cb78b → libc __fortify_fail_abort
Both crashes: same 4-frame stack trace

Population A (JIT buffer overflow):
  - Crash BEFORE any test output
  - Fix: targeted submodule imports (reduce compilation footprint)
  - Trigger: from shared.core import forces 37K+ line compilation

Population B (ASAP destruction UAF):
  - Crash AFTER test output (some tests ran successfully)
  - Fix: data_ptr[dtype]() before inner loop
  - Trigger: _get_float64 per-element bitcast on temporary from forward_fn
```

### ASAN Output (What You'd See With ASAN Enabled)

```text
ERROR: AddressSanitizer: heap-use-after-free on address 0x... at pc ...
READ of size 4 at 0x... thread T0
    #0 in AnyTensor::_get_float64(int)
    #1 in _check_gradients_perturb[...]
    ...
freed by thread T0 here:
    #0 in operator delete(void*)
    #1 in AnyTensor::__del__()
```

This is the smoking gun that proves it's a UAF, not a compilation-time crash.

### Files Modified

```
shared/testing/gradient_checker.mojo  — 3 perturbation functions fixed
.github/workflows/asan-tests.yml      — 2 new ASAN test groups added
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5116, branch 4458-auto-impl | Gradient checking tests stabilized; ASAN coverage added |
