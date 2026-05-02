---
name: optimization-simd-gradient-clipping-vectorization
description: "SIMD-vectorize gradient clipping functions (norm, scale, clamp) in Mojo for 4-8x speedup. Use when: (1) replacing scalar _get_float64/_set_float64 loops with SIMD, (2) implementing vectorized L2 norm accumulation, (3) SIMD in-place tensor scaling or clamping."
category: optimization
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [mojo, simd, vectorization, gradient-clipping, training, performance, norm-computation]
---

# SIMD Vectorization of Gradient Clipping in Mojo

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Replace scalar `_get_float64`/`_set_float64` element-by-element loops in gradient clipping with SIMD-vectorized operations for 4-8x throughput improvement |
| **Outcome** | Successful — 4 functions vectorized via 6 SIMD helpers, 13 tests pass (9 existing + 4 new edge-case), zero regressions |
| **Verification** | verified-local |

## When to Use

- Replacing scalar `_get_float64(j)` / `_set_float64(j, val)` loops with SIMD in AnyTensor operations
- Implementing SIMD L2 norm computation (squared sum with `reduce_add()` + Float64 accumulation)
- SIMD in-place tensor scaling (multiply all elements by a constant)
- SIMD in-place tensor clamping (min/max value clipping)
- Optimizing training loop hot paths that touch every gradient element per step
- Converting a function that dispatches on `_dtype` field to SIMD-specific code paths

## Verified Workflow

### Quick Reference

```mojo
from algorithm import vectorize
from sys.info import simd_width_of

# Pattern 1: SIMD norm accumulation (Float64 accumulator for numerical stability)
@always_inline
fn _norm_sq_simd_f32(tensor: AnyTensor) -> Float64:
    comptime simd_width = simd_width_of[DType.float32]()
    var size = tensor._numel
    var ptr = tensor._data.bitcast[Float32]()
    var acc = Float64(0.0)

    @parameter
    fn vectorized_norm[width: Int](idx: Int) unified {mut}:
        var vec = ptr.load[width=width](idx)
        var sq = vec * vec
        acc += sq.reduce_add().cast[DType.float64]()

    vectorize[simd_width](size, vectorized_norm)
    return acc

# Pattern 2: SIMD in-place scaling
@always_inline
fn _scale_simd_f32(tensor: AnyTensor, scale: Float32):
    comptime simd_width = simd_width_of[DType.float32]()
    var size = tensor._numel
    var ptr = tensor._data.bitcast[Float32]()

    @parameter
    fn vectorized_scale[width: Int](idx: Int) unified {mut}:
        var vec = ptr.load[width=width](idx)
        var scale_vec = SIMD[DType.float32, width](scale)
        ptr.store[width=width](idx, vec * scale_vec)

    vectorize[simd_width](size, vectorized_scale)

# Pattern 3: SIMD in-place clamping
@always_inline
fn _clamp_simd_f32(tensor: AnyTensor, min_val: Float32, max_val: Float32):
    comptime simd_width = simd_width_of[DType.float32]()
    var size = tensor._numel
    var ptr = tensor._data.bitcast[Float32]()

    @parameter
    fn vectorized_clamp[width: Int](idx: Int) unified {mut}:
        var vec = ptr.load[width=width](idx)
        var min_vec = SIMD[DType.float32, width](min_val)
        var max_vec = SIMD[DType.float32, width](max_val)
        ptr.store[width=width](idx, max(min_vec, min(max_vec, vec)))

    vectorize[simd_width](size, vectorized_clamp)
```

### Detailed Steps

1. **Add imports**: `from algorithm import vectorize` and `from sys.info import simd_width_of`

2. **Create dtype-specific SIMD helpers** (private, `@always_inline`): Write separate `_f32` and `_f64` variants. This avoids runtime dtype branching inside the inner loop and allows the compiler to specialize fully.

3. **Bitcast the data pointer once**: `tensor._data.bitcast[Float32]()` — converts `UnsafePointer[UInt8]` to typed pointer outside the loop. This eliminates per-element offset calculation and dtype dispatch that `_get_float64` performs.

4. **Use `vectorize[simd_width](size, closure)`**: The `vectorize` builtin handles tail elements automatically — no manual remainder loop needed (unlike manual `while` loops).

5. **Inside the closure, use `unified {mut}`**: This allows the closure to capture and mutate outer-scope variables (like accumulators). The closure signature is `fn[width: Int](idx: Int) unified {mut}`.

6. **For norm accumulation, keep Float64 accumulator**: Use `.reduce_add().cast[DType.float64]()` to widen Float32 partial sums to Float64 before accumulation. This prevents catastrophic cancellation on large tensors.

7. **Dispatch on `_dtype` in the public function**: Check `grad._dtype == DType.float32` / `DType.float64` and call the appropriate SIMD helper, with a scalar fallback for exotic dtypes.

8. **Test with non-SIMD-aligned sizes**: Always test with tensor sizes 1, 7, 13, 33 (not multiples of SIMD width 8 or 16) to verify `vectorize` handles tail correctly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct approach | SIMD helpers + vectorize pattern | Succeeded on first attempt | Following established codebase patterns (activation_simd.mojo, matmul.mojo) eliminates trial-and-error — read reference code first |
| Consider vectorizing `compute_gradient_statistics` | Considered SIMD for the statistics function (norm + min/max/mean + NaN/Inf detection) | Decided against — mixed concerns (NaN/Inf checking requires per-element branches) and it's a monitoring function called infrequently | Not every function benefits from SIMD; prioritize hot-path functions called every training step |

## Results & Parameters

### SIMD Helper Function Summary

| Helper | Operation | Used By |
| -------- | ----------- | --------- |
| `_norm_sq_simd_f32/f64` | Squared L2 norm (sum of squares) | `compute_gradient_norm_list`, `clip_gradients_per_param` |
| `_scale_simd_f32/f64` | In-place multiply by scalar | `clip_gradients_by_global_norm`, `clip_gradients_per_param` |
| `_clamp_simd_f32/f64` | In-place min/max clamping | `clip_gradients_by_value_list` |

### Key SIMD Operations Reference

```mojo
# Bitcast raw pointer to typed pointer (done once, outside loop)
var ptr = tensor._data.bitcast[Float32]()

# Get compile-time SIMD width
comptime simd_width = simd_width_of[DType.float32]()

# Load SIMD vector
var vec = ptr.load[width=width](idx)

# Store SIMD vector
ptr.store[width=width](idx, result_vec)

# Horizontal sum (reduce all lanes to scalar)
var sum = vec.reduce_add()  # Returns Scalar[dtype]

# Widen to Float64 for accumulation
var f64_sum = vec.reduce_add().cast[DType.float64]()

# Broadcast scalar to SIMD vector
var scale_vec = SIMD[DType.float32, width](scalar_value)

# SIMD min/max for clamping
var clamped = max(min_vec, min(max_vec, vec))
```

### Critical Pattern: `_get_float64` vs SIMD Bitcast

The scalar accessor `_get_float64(j)` does per-element: function call + offset calculation + dtype branch + Float64 conversion. For Float32 tensors this is 3 unnecessary operations per element.

SIMD `bitcast[Float32]()` + `load[width]` eliminates all three: one bitcast outside the loop, typed loads inside, native Float32 arithmetic with explicit Float64 widening only where needed (accumulator).

### Performance Characteristics

| Metric | Scalar (Before) | SIMD (After) | Improvement |
| -------- | ----------------- | -------------- | ------------- |
| Iterations per 10M float32 (norm) | ~10,000,000 | ~1,250,000 (width=8) | ~8x fewer iterations |
| Iterations per 10M float32 (scale) | ~10,000,000 | ~1,250,000 | ~8x fewer iterations |
| Memory accesses per training step | 20M+ scalar reads/writes | 2.5M SIMD loads/stores | ~8x reduction |

### Test Edge Cases to Cover

- Tensor size 1 (pure scalar tail, smaller than any SIMD width)
- Tensor sizes 7, 13, 33 (not multiples of common SIMD widths 8/16)
- Large tensors (10,000+ elements) for meaningful SIMD exercise
- Mixed positive/negative values for clamp correctness
- Zero gradients (edge case for norm division)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4911 — SIMD-vectorize gradient clipping | [PR #5120](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5120) |
