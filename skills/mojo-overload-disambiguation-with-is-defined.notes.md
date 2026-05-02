# Session Notes — Mojo Overload Disambiguation with is_defined

## Session Date

2026-03-15

## Issue

GitHub Issue #3711 — Add runtime Apple Silicon detection to `recommend_precision_dtype`

PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4778

## Objective

Add `detect_hardware_bf16_support() -> Bool` to `shared/training/dtype_utils.mojo` so
`recommend_precision_dtype` could auto-detect BF16 support without callers passing
`hardware_has_bf16=False` manually on Apple Silicon. Also add `_check_bf16_platform_support`
to `precision_config.mojo` so `PrecisionConfig.bf16()` raises an actionable error on Apple
Silicon instead of silently returning a broken config.

## Key Discoveries

### 1. `is_apple_silicon()` does not exist in Mojo 0.26.1

The issue description mentioned `sys.info.is_apple_silicon()` but this function is not in
the Mojo 0.26.1 standard library. The compiler returned:

```
error: module 'info' does not contain 'is_apple_silicon'
```

Other attempted functions (`os_is_linux`, `os_is_macos`, `os_name`, `arch_name`) also do not
exist in 0.26.1. The only working compile-time platform detection is `is_defined["APPLE"]()`
from the `sys` package (not `sys.info`).

### 2. Overload ambiguity with default parameters

Adding a 1-arg overload alongside a 3-arg overload that has defaults causes "ambiguous call":

```
error: ambiguous call to 'recommend_precision_dtype'
  candidate declared here: fn recommend_precision_dtype(model_size_mb: Float64) -> DType
  candidate declared here: fn recommend_precision_dtype(model_size_mb: Float64, hardware_has_fp16: Bool = True, hardware_has_bf16: Bool = True) -> DType
```

Mojo does not prefer "more specific" overloads — it treats any ambiguity as an error.
Fix: remove defaults from the explicit N-arg overload. Callers using keyword args still work
because keyword args uniquely identify the N-arg overload.

### 3. Testable guard pattern

To test Apple Silicon behaviour in Linux CI (without Apple hardware), the guard function
accepts `is_apple: Bool` as a parameter instead of calling `is_defined["APPLE"]()` internally.
This allows CI tests to call `_check_bf16_platform_support(True)` to verify the raise path.

## Files Modified

- `shared/training/dtype_utils.mojo` — added `detect_hardware_bf16_support()`, 1-arg overload
- `shared/training/precision_config.mojo` — added `_check_bf16_platform_support()`, updated `bf16()`
- `tests/shared/training/test_dtype_utils.mojo` — 2 new tests

## Test Results

All tests passed on Linux x86 CI (WSL2):

```
✓ detect_hardware_bf16_support returns True on CI hardware
✓ Auto-detecting recommend_precision_dtype works correctly on CI
✓ _check_bf16_platform_support raises on simulated Apple Silicon
✓ _check_bf16_platform_support does not raise on non-Apple Silicon
✓ PrecisionConfig.bf16() succeeds on non-Apple Silicon
✓ Error message has correct content
```
