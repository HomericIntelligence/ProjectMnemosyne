---
name: bf16-precision-recommendation
description: 'Add hardware-guarded BF16 support to dtype recommendation functions.
  Use when: enabling BF16 for large Mojo ML models, adding Apple Silicon hardware
  guard for BF16, or extending precision recommendation with hardware capability parameters.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# BF16 Precision Recommendation with Hardware Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Objective** | Enable BF16 in `recommend_precision_dtype()` for large models (>= 1000 MB) with Apple Silicon guard |
| **Outcome** | Implemented `hardware_has_bf16` parameter, large models return `DType.bfloat16` by default, fall back to FP16 on Apple Silicon |
| **Root Cause** | Original function returned `DType.float16` for both medium and large models — large model branch was unimplemented |
| **Key Learning** | Add `hardware_has_bf16: Bool = True` parameter alongside existing `hardware_has_fp16`; BF16 is not supported on Apple Silicon so the guard is critical |

## When to Use

- Adding BF16 support to a Mojo `recommend_precision_dtype`-style function
- Implementing hardware capability guards (Apple Silicon, legacy GPU) for BF16
- Extending dtype recommendation APIs with new hardware parameters while preserving backward compatibility
- Updating corresponding Mojo tests when a function's return value changes for a model size tier

## Verified Workflow

### Step 1: Identify the Unimplemented Branch

The function had a `model_size_mb >= 1000.0` branch that still returned `DType.float16`. Confirmed by reading the source:

```mojo
else:
    # Large model - FP16 strongly recommended
    return DType.float16  # <-- never used BF16
```

### Step 2: Add `hardware_has_bf16` Parameter

Add with default `True` so existing callers are unaffected (BF16 supported on most non-Apple hardware):

```mojo
fn recommend_precision_dtype(
    model_size_mb: Float64,
    hardware_has_fp16: Bool = True,
    hardware_has_bf16: Bool = True,
) -> DType:
```

### Step 3: Implement Large Model Branch

```mojo
else:
    # Large model - BF16 strongly recommended for wider exponent range
    if hardware_has_bf16:
        return DType.bfloat16
    else:
        return DType.float16
```

### Step 4: Update Docstring

- Add `hardware_has_bf16` to `Args:` section with Apple Silicon note
- Update Recommendations table: "Large models (>1GB): BF16 strongly recommended (FP16 if no BF16 hardware)"

### Step 5: Update Tests

Three test cases for the large-model tier:

```mojo
# Large model with BF16 hardware - should recommend BF16
var large_dtype = recommend_precision_dtype(2000.0, hardware_has_fp16=True)
assert_equal(large_dtype, DType.bfloat16, "Large models should use BF16")

# Apple Silicon guard: large model without BF16 - fall back to FP16
var large_no_bf16_dtype = recommend_precision_dtype(
    2000.0, hardware_has_fp16=True, hardware_has_bf16=False
)
assert_equal(large_no_bf16_dtype, DType.float16, "Large models without BF16 hardware should use FP16")

# No FP16 or BF16 hardware: fall back to FP32
var no_hw_dtype = recommend_precision_dtype(
    2000.0, hardware_has_fp16=False, hardware_has_bf16=False
)
assert_equal(no_hw_dtype, DType.float32, "Without FP16 hardware should use FP32")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run tests locally via `pixi run mojo test` | Executed test file directly | GLIBC version mismatch — system GLIBC 2.31, Mojo requires 2.32+ | Tests must run in Docker/CI; local Mojo execution fails on this machine due to GLIBC constraints |
| Run `just test-group` | Used `just` command runner | `just` not in PATH in the worktree shell | Use `pixi run mojo test <file>` directly, not `just` wrapper, or verify `just` is installed |

## Results & Parameters

### Final Signature

```mojo
fn recommend_precision_dtype(
    model_size_mb: Float64,
    hardware_has_fp16: Bool = True,
    hardware_has_bf16: Bool = True,
) -> DType
```

### Return Value by Configuration

| model_size_mb | hardware_has_fp16 | hardware_has_bf16 | Returns |
|---------------|-------------------|-------------------|---------|
| < 100 | any | any | `DType.float32` |
| 100-999 | True | any | `DType.float16` |
| 100-999 | False | any | `DType.float32` |
| >= 1000 | True | True | `DType.bfloat16` |
| >= 1000 | True | False (Apple Silicon) | `DType.float16` |
| >= 1000 | False | any | `DType.float32` |

### Pre-commit Result

All hooks passed: `Mojo Format`, `Check for deprecated List[Type](args) syntax`,
`Validate Test Coverage`, `Trim Trailing Whitespace`, `Fix End of Files`, `Fix Mixed Line Endings`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3710 / Issue #3202 | [notes.md](../references/notes.md) |
