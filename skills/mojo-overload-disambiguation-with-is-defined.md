---
name: mojo-overload-disambiguation-with-is-defined
description: 'Pattern for adding auto-detecting 1-arg overloads in Mojo 0.26.1 without
  ambiguity. Use when: (1) adding a convenience overload that auto-detects a parameter
  via compile-time is_defined[], (2) hitting ''ambiguous call'' errors with two overloads
  sharing leading parameters with defaults, (3) detecting Apple Silicon or platform
  traits at compile time.'
category: training
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
| ---------- | ------- |
| **Mojo version** | 0.26.1 |
| **Problem** | `is_apple_silicon()` does not exist in `sys.info`; overloads with same leading params + defaults cause "ambiguous call" |
| **Solution** | Use `is_defined["APPLE"]()` from `sys` for compile-time platform detection; remove defaults from the explicit N-arg overload |
| **Pattern** | 1-arg auto-detect overload calls N-arg explicit overload with detected value injected |
| **Testability** | Guard function takes `is_apple: Bool` as parameter so CI can simulate Apple Silicon without target hardware |

## When to Use

- You want to add a convenience overload (e.g. `fn foo(x: T)`) that auto-detects a hardware capability
- Both the new 1-arg overload and the existing N-arg overload have matching leading parameters with defaults, causing Mojo to emit "ambiguous call"
- You need compile-time Apple Silicon detection in Mojo 0.26.1 (`sys.info.is_apple_silicon` does NOT exist)
- You need a testable guard that CI can invoke with a simulated `is_apple=True` without needing real Apple hardware

## Verified Workflow

### Quick Reference

```mojo
# ❌ Does NOT exist in Mojo 0.26.1
from sys.info import is_apple_silicon  # Error: module 'info' does not contain 'is_apple_silicon'

# ✅ Correct compile-time platform detection
from sys import is_defined
fn detect_hardware_bf16_support() -> Bool:
    return not is_defined["APPLE"]()
```

### Step 1 — Use `is_defined["APPLE"]()` for Apple Silicon detection

```mojo
from sys import is_defined

fn detect_hardware_bf16_support() -> Bool:
    """Returns False on Apple Silicon, True elsewhere."""
    return not is_defined["APPLE"]()
```

`is_defined` is available from `sys` (not `sys.info`) and evaluates at compile time.

### Step 2 — Resolve overload ambiguity by removing defaults from the explicit overload

When adding a 1-arg auto-detecting overload alongside a 3-arg explicit one, Mojo cannot
resolve `fn foo(x: T)` if both match via defaults. Fix: **remove defaults** from the
N-arg explicit overload.

```mojo
# ❌ AMBIGUOUS — both match fn recommend_precision_dtype(2000.0)
fn recommend_precision_dtype(model_size_mb: Float64) -> DType: ...
fn recommend_precision_dtype(model_size_mb: Float64, hardware_has_fp16: Bool = True, hardware_has_bf16: Bool = True) -> DType: ...

# ✅ UNAMBIGUOUS — 1-arg only matches first; 3-arg requires all 3 args
fn recommend_precision_dtype(model_size_mb: Float64) -> DType:
    return recommend_precision_dtype(model_size_mb, True, detect_hardware_bf16_support())

fn recommend_precision_dtype(model_size_mb: Float64, hardware_has_fp16: Bool, hardware_has_bf16: Bool) -> DType:
    ...
```

Callers using keyword args (`hardware_has_fp16=True, hardware_has_bf16=False`) still work
because keyword args unambiguously select the 3-arg overload.

### Step 3 — Testable guard with injected Bool

For functions that raise on Apple Silicon, use the injected-bool pattern so CI can test
the guard without running on Apple hardware:

```mojo
fn _check_bf16_platform_support(is_apple: Bool) raises:
    """Testable guard — inject is_apple=True to simulate Apple Silicon in CI."""
    if is_apple:
        raise Error(
            "BF16 (bfloat16) is not supported on Apple Silicon (M1/M2/M3). "
            "Use PrecisionConfig.fp16() instead on Apple hardware."
        )

@staticmethod
fn bf16(initial_scale: Float32 = 65536.0) raises -> PrecisionConfig:
    _check_bf16_platform_support(is_defined["APPLE"]())
    return PrecisionConfig(mode=PrecisionMode.BF16, ...)
```

In tests:
```mojo
# Simulate Apple Silicon without Apple hardware
_check_bf16_platform_support(True)   # raises — test this
_check_bf16_platform_support(False)  # no-op — test this
```

### Step 4 — Update call sites that relied on defaults

After removing defaults from the explicit overload, any call with fewer than N args must
either use the auto-detecting overload or be updated to pass all args explicitly:

```mojo
# Before (had defaults — worked with 2 args)
recommend_precision_dtype(50.0, hardware_has_fp16=True)  # ❌ now ambiguous

# After — pass all 3 args explicitly
recommend_precision_dtype(50.0, hardware_has_fp16=True, hardware_has_bf16=True)
# Or use the 1-arg auto-detecting overload
recommend_precision_dtype(50.0)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `from sys.info import is_apple_silicon` | Used `is_apple_silicon()` from `sys.info` as documented in newer Mojo versions | Error: "module 'info' does not contain 'is_apple_silicon'" — function does not exist in Mojo 0.26.1 | Use `is_defined["APPLE"]()` from `sys` instead |
| `from sys import os_is_macos` | Tried `os_is_macos()` from `sys` module | Error: "package 'sys' does not contain 'os_is_macos'" | Not in 0.26.1 stdlib; `is_defined` is the only compile-time option |
| 1-arg overload alongside 3-arg with defaults | `fn foo(x)` + `fn foo(x, y=True, z=True)` — 1-arg call matched both | Mojo emits "ambiguous call" — does not prefer more-specific overload | Remove defaults from the explicit N-arg overload to make overloads unambiguous |
| 2-arg overload (`model_size_mb` + `hardware_has_fp16`) | Added middle overload alongside the 3-arg | Same ambiguity problem: 2-arg call matched 2-arg overload AND 3-arg with one default | The only safe shape is 1-arg auto-detect + N-arg fully-explicit (no defaults) |

## Results & Parameters

### Environment

```text
Mojo version: 0.26.1.0 (156d3ac6)
Platform: Linux x86 (WSL2)
Target CI: Ubuntu, GLIBC 2.35
```

### Compile-time constants available via `is_defined` (Mojo 0.26.1)

```mojo
from sys import is_defined

is_defined["APPLE"]()     # True on macOS/Apple Silicon targets
is_defined["__arm64__"]() # True on ARM64 targets
is_defined["__aarch64__"]() # True on AArch64 targets
# All returned False on Linux x86 CI (expected)
```

### Final working pattern (copy-paste)

```mojo
from sys import is_defined

fn detect_hardware_bf16_support() -> Bool:
    return not is_defined["APPLE"]()

fn recommend_precision_dtype(model_size_mb: Float64) -> DType:
    """1-arg overload — auto-detects BF16 support."""
    return recommend_precision_dtype(
        model_size_mb,
        hardware_has_fp16=True,
        hardware_has_bf16=detect_hardware_bf16_support(),
    )

fn recommend_precision_dtype(
    model_size_mb: Float64,
    hardware_has_fp16: Bool,   # No default — required for disambiguation
    hardware_has_bf16: Bool,   # No default — required for disambiguation
) -> DType:
    """N-arg explicit overload."""
    if not hardware_has_fp16:
        return DType.float32
    if model_size_mb < 100.0:
        return DType.float32
    elif model_size_mb < 1000.0:
        return DType.float16
    else:
        return DType.bfloat16 if hardware_has_bf16 else DType.float16
```
