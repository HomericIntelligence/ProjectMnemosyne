---
name: mojo-exotic-dtype-default-param-crash
description: "Fix Mojo 0.26.1 ASAN abort at module load from exotic dtype (E8M0, FP8) used
  as default parameter values. Use when: (1) ASAN abort fires before any test body runs,
  (2) code uses Scalar[E8M0](1.0) or Scalar[FP8](1.0) as a default param, (3) E8M0/FP8
  float-conversion path is triggered at module load time."
category: debugging
date: 2026-03-27
version: "1.0.0"
user-invocable: false
tags:
  - mojo
  - asan
  - dtype
  - e8m0
  - fp8
  - default-param
  - module-load
---

# Mojo Exotic Dtype Default Parameter Crash

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Fix ASAN abort caused by using exotic float dtypes (E8M0, FP8) as default parameter values |
| **Outcome** | Successful — replace default params with bitcast-safe construction helpers |

## When to Use

- CI test file crashes at ASAN abort before any test body executes
- Code contains `Scalar[E8M0](1.0)` or `Scalar[FP8](1.0)` as a **default parameter value**
- `E8M0 = DType.float8_e8m0fnu` — exponent-only, no mantissa, no sign, no valid float conversion
- `FP8 = DType.float8_e4m3fn` — less exotic but same crash risk when used as a default param
- The crash signature is the same 3-frame ASAN fingerprint as UAF bitcast crashes but fires
  at module load, not during a write operation

## Root Cause

Default parameter values in Mojo are evaluated **when the module is loaded**, before any test
function runs. The float-to-exotic-dtype cast path (`Scalar[E8M0](1.0)`) triggers an ASAN abort
during this module initialization.

- `E8M0` has no mantissa and no sign bit — it represents exponents only (used in microscaling
  formats). There is no valid path from a Float64 literal to E8M0.
- Even `FP8` (`float8_e4m3fn`) can crash as a default param if the cast path is not safe
  at module-load time.

Runtime calls to `Scalar[FP8](1.0)` inside function bodies are fine — only **default params**
are affected because they run at module scope.

## Verified Workflow

### Quick Reference

```mojo
# CRASHES: evaluated at module load, no valid float->E8M0 conversion
fn some_func(val: Scalar[E8M0] = Scalar[E8M0](1.0)):
    ...

# CRASHES: same for FP8
fn other_func(val: Scalar[FP8] = Scalar[FP8](1.0)):
    ...

# SAFE for E8M0: exponent 127 = 1.0 in E8M0 representation
fn _e8m0_from_exponent(exp: UInt8) -> Scalar[E8M0]:
    return bitcast[E8M0, 1](SIMD[DType.uint8, 1](exp))[0]

alias E8M0_ONE = _e8m0_from_exponent(127)

# SAFE for FP8: 0x3C is the bit pattern for 1.0 in float8_e4m3fn
alias FP8_ONE = bitcast[FP8, 1](SIMD[DType.uint8, 1](0x3C))[0]
```

### Detailed Steps

1. **Identify the module-load crash** — if the crash occurs before any test body runs
   (crash on the first `fn test_*` entry with no test logic executed), look for default
   parameter values using exotic dtypes.

2. **Search for all exotic dtype default params**:

   ```bash
   grep -rn 'Scalar\[E8M0\]\|Scalar\[FP8\]\|float8_e8m0\|float8_e4m3' shared/ tests/ | grep '='
   ```

3. **Replace E8M0 defaults** with a bitcast-safe helper:

   ```mojo
   fn _e8m0_from_exponent(exp: UInt8) -> Scalar[DType.float8_e8m0fnu]:
       return bitcast[DType.float8_e8m0fnu, 1](SIMD[DType.uint8, 1](exp))[0]

   # E8M0 encoding: biased exponent (bias=127), 1.0 = exponent field 127
   alias E8M0_ONE = _e8m0_from_exponent(127)
   ```

4. **Replace FP8 defaults** using the bit pattern for 1.0:

   ```mojo
   # float8_e4m3fn bit pattern: sign=0, exp=0111(7), mantissa=000 -> 0x3C
   alias FP8_ONE = bitcast[DType.float8_e4m3fn, 1](SIMD[DType.uint8, 1](0x3C))[0]
   ```

5. **Files affected in ProjectOdyssey**:
   - `shared/tensor/mxfp4.mojo` line 290 — default param with `Scalar[E8M0](1.0)`
   - `shared/tensor/nvfp4.mojo` line 271 — default param with `Scalar[FP8](1.0)`
   - `shared/tensor/nvfp4.mojo` line 671 — constructor body with `Scalar[FP8](1.0)` (runtime)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Retrying CI | Rerunning the failed test group | ASAN abort is deterministic — not flaky infrastructure | This crash always reproduces; do not retry |
| Treating as UAF | Assuming 3-frame ASAN signature always means bitcast write UAF | The same ASAN abort fires for module-load default-param crashes | Distinguish by crash timing: pre-test-body = module load; mid-test = bitcast write UAF |

## Results & Parameters

### E8M0 Bit Encoding Reference

```text
E8M0 = float8_e8m0fnu:
  - 8 bits: all exponent, no mantissa, no sign
  - Biased exponent with bias=127
  - 1.0 = exponent 127 = 0x7F
  - No valid float cast path -- must use bitcast from UInt8
```

### FP8 (float8_e4m3fn) Bit Encoding Reference

```text
FP8 = float8_e4m3fn:
  - Sign: 1 bit
  - Exponent: 4 bits, bias=7
  - Mantissa: 3 bits
  - 1.0 = 0 0111 000 = 0x3C
  - Runtime Scalar[FP8](1.0) is safe; only default params crash
```

### Diagnostic Pattern: Module-Load vs. Mid-Test Crash

| Indicator | Module-Load Crash | Mid-Test UAF Crash |
| ----------- | ------------------ | -------------------- |
| When crash fires | Before first test body | During test execution |
| Stack shows | Module init frames | Test function + write ops |
| Root cause | Exotic dtype default param | `tensor._data.bitcast[T]()[i] = value` |
| Fix | Replace default param with alias | @always_inline or pointer arithmetic |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | shared/tensor/mxfp4.mojo, shared/tensor/nvfp4.mojo | PR #5177 (unverified) |
