---
name: optimization-mojo-simd-nan-inf-vectorization
description: "SIMD-vectorize NaN/Inf detection and gradient clipping functions in Mojo for hot-path performance. Use when: (1) optimizing element-wise tensor scanning functions, (2) implementing SIMD early-exit patterns in Mojo, (3) using vectorize[] with lane reduction for counting, (4) replacing scalar _get_float64/_set_float64 loops with SIMD, (5) implementing vectorized L2 norm accumulation with Float64 accumulator, (6) SIMD in-place tensor scaling or clamping."
category: optimization
date: 2025-03-25
version: "1.1.0"
user-invocable: false
tags: [mojo, simd, vectorization, numerical-safety, performance, nan-detection, gradient-clipping, training, norm-computation]
absorbed: [optimization-simd-gradient-clipping-vectorization]
---

# SIMD Vectorization of NaN/Inf Detection in Mojo

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2025-03-25 |
| **Objective** | Replace scalar element-by-element loops in hot-path NaN/Inf detection functions with SIMD-vectorized implementations for ~4-16x throughput improvement |
| **Outcome** | Successful — all 4 functions vectorized, 9 new SIMD edge-case tests pass, zero regressions |

## When to Use

- Optimizing element-wise tensor scanning functions (has_nan, has_inf, count_nan, count_inf)
- Implementing SIMD early-exit patterns in Mojo (boolean detection with `reduce_or()`)
- Using `vectorize[]` with lane reduction for parallel counting (`cast[DType.uint8]().reduce_add()`)
- Working with `isnan()`/`isinf()` on SIMD vectors in Mojo 0.26.1+
- Handling scalar tail elements when tensor size is not divisible by SIMD width

## Verified Workflow

### Quick Reference

```mojo
from sys import simd_width_of
from algorithm import vectorize
from math import isnan, isinf

# Pattern 1: Manual SIMD loop with early exit (for boolean detection)
fn _has_nan_core[dtype: DType](tensor: Tensor[dtype]) -> Bool:
    var size = tensor.numel()
    var ptr = tensor._data
    comptime simd_w = simd_width_of[dtype]()

    var i = 0
    while i + simd_w <= size:
        var vec = ptr.load[width=simd_w](i)
        if isnan(vec).reduce_or():
            return True
        i += simd_w

    # Scalar tail
    while i < size:
        if isnan(ptr[i]):
            return True
        i += 1
    return False

# Pattern 2: vectorize[] with lane reduction (for counting)
fn _count_nan_core[dtype: DType](tensor: Tensor[dtype]) -> Int:
    var size = tensor.numel()
    var count = 0
    var ptr = tensor._data
    comptime simd_w = simd_width_of[dtype]()

    @parameter
    fn _count[width: Int](idx: Int) unified {mut}:
        var vec = ptr.load[width=width](idx)
        count += Int(isnan(vec).cast[DType.uint8]().reduce_add())

    vectorize[simd_w](size, _count)
    return count
```

### Detailed Steps

1. **Choose the right pattern based on function semantics**:
   - Boolean detection (has_nan/has_inf): Use **manual SIMD loop** — `vectorize[]` closures cannot `return` from the outer function, so early exit requires a manual `while` loop
   - Counting (count_nan/count_inf): Use **`vectorize[]`** — no early exit needed, and `vectorize[]` handles tail elements automatically

2. **Add required imports**: `from sys import simd_width_of`, `from algorithm import vectorize`

3. **Get SIMD width at compile time**: `comptime simd_w = simd_width_of[dtype]()` — this gives 8 for float32, 4 for float64 on AVX-256 (16 for float32 on AVX-512)

4. **SIMD load and check**: `ptr.load[width=simd_w](i)` loads a SIMD vector; `isnan(vec)` returns `SIMD[DType.bool, width]`

5. **Reduce SIMD results**:
   - For boolean: `isnan(vec).reduce_or()` — True if any lane is NaN
   - For counting: `isnan(vec).cast[DType.uint8]().reduce_add()` — sum of True lanes (True=1, False=0)

6. **Handle scalar tail** (manual loop only): After the SIMD loop, process remaining `size % simd_w` elements with a scalar loop

7. **Integer type guard**: Use `@parameter if` to return False/0 for integer dtypes at compile time (integers cannot have NaN/Inf)

## Gradient Clipping SIMD Patterns

This section covers SIMD vectorization of gradient clipping hot paths — replacing
scalar `_get_float64`/`_set_float64` element-by-element loops for 4-8x throughput improvement.

**6 SIMD helper functions** serve **4 gradient clipping functions**:

| Helper | Operation | Used By |
| -------- | ----------- | --------- |
| `_norm_sq_simd_f32/f64` | Squared L2 norm (sum of squares) | `compute_gradient_norm_list`, `clip_gradients_per_param` |
| `_scale_simd_f32/f64` | In-place multiply by scalar | `clip_gradients_by_global_norm`, `clip_gradients_per_param` |
| `_clamp_simd_f32/f64` | In-place min/max clamping | `clip_gradients_by_value_list` |

### Quick Reference

```mojo
from algorithm import vectorize
from sys.info import simd_width_of

# Pattern: SIMD L2 norm accumulation (Float64 accumulator for numerical stability)
@always_inline
fn _norm_sq_simd_f32(tensor: AnyTensor) -> Float64:
    comptime simd_width = simd_width_of[DType.float32]()
    var size = tensor._numel
    var ptr = tensor._data.bitcast[Float32]()   # AnyTensor bitcast pattern
    var acc = Float64(0.0)

    @parameter
    fn vectorized_norm[width: Int](idx: Int) unified {mut}:
        var vec = ptr.load[width=width](idx)
        var sq = vec * vec
        acc += sq.reduce_add().cast[DType.float64]()  # widen to Float64

    vectorize[simd_width](size, vectorized_norm)
    return acc

# Pattern: SIMD in-place scaling
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

# Pattern: SIMD in-place clamping (min/max value clipping)
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

### AnyTensor Data Access Pattern

`AnyTensor._data` is `UnsafePointer[UInt8]`. Bitcast once outside the loop:

```mojo
var ptr = tensor._data.bitcast[Float32]()
```

This eliminates the per-element dtype dispatch, offset calculation, and Float64 conversion
that `_get_float64(j)` / `_set_float64(j, val)` perform on every call.

### Dtype Dispatch in Public Functions

```mojo
# Public function dispatches to SIMD helpers based on _dtype field
if grad._dtype == DType.float32:
    return _norm_sq_simd_f32(grad)
elif grad._dtype == DType.float64:
    return _norm_sq_simd_f64(grad)
else:
    # Scalar fallback for exotic dtypes
    ...
```

### Detailed Steps

1. **Add imports**: `from algorithm import vectorize` and `from sys.info import simd_width_of`
2. **Create dtype-specific SIMD helpers** (private, `@always_inline`): Write separate `_f32` and `_f64` variants to avoid runtime dtype branching inside the inner loop.
3. **Bitcast the data pointer once**: `tensor._data.bitcast[Float32]()` outside the loop.
4. **Use `vectorize[simd_width](size, closure)`**: Handles tail elements automatically — no manual remainder loop needed.
5. **Inside closure, use `unified {mut}`**: Allows closure to capture and mutate outer-scope accumulator variables.
6. **For norm accumulation, keep Float64 accumulator**: Use `.reduce_add().cast[DType.float64]()` to prevent catastrophic cancellation on large tensors.
7. **Dispatch on `_dtype` in the public function**: With scalar fallback for exotic dtypes.
8. **Test with non-SIMD-aligned sizes**: Sizes 1, 7, 13, 33 (not multiples of SIMD width 8 or 16).

### Gradient Clipping Performance Characteristics

| Metric | Scalar (Before) | SIMD (After) | Improvement |
| -------- | ----------------- | -------------- | ------------- |
| Iterations per 10M float32 (norm) | ~10,000,000 | ~1,250,000 (width=8) | ~8x fewer iterations |
| Iterations per 10M float32 (scale) | ~10,000,000 | ~1,250,000 | ~8x fewer iterations |
| Memory accesses per training step | 20M+ scalar reads/writes | 2.5M SIMD loads/stores | ~8x reduction |

### Critical Pattern: `_get_float64` vs SIMD Bitcast

The scalar accessor `_get_float64(j)` does per-element: function call + offset calculation + dtype branch + Float64 conversion. For Float32 tensors this is 3 unnecessary operations per element.

SIMD `bitcast[Float32]()` + `load[width]` eliminates all three: one bitcast outside the loop, typed loads inside, native Float32 arithmetic with explicit Float64 widening only where needed (accumulator).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `vectorize[]` for `has_nan` | Used `vectorize[]` closure with a `found` flag | Cannot `return True` from inside `vectorize[]` closure to exit the outer function — the closure is a separate function | Use manual SIMD loop (`while` + `ptr.load`) when early exit is needed |
| `List[Int](2, 8)` constructor | Tried to construct List with positional args | Mojo 0.26.1 `List[Int]` has no multi-arg constructor; must use `append()` or list literals `[2, 8]` | Always use `var s = List[Int](); s.append(n)` pattern or `[n]` list literal syntax |
| Lowercase docstring start | Used `"""has_nan returns...` | Mojo `--Werror` rejects docstrings not starting with capital letter or non-alpha | Always capitalize the first word of docstrings |
| `mojo format` on `comptime` | Ran `mojo format` on files using `comptime` keyword | Formatter crashes with `'_python_symbols' object has no attribute 'comptime_assert_stmt'` | Known Mojo formatter limitation — `comptime` keyword not yet supported by formatter; the `mojo-format-compat.sh` wrapper handles this gracefully |
| Direct approach (gradient clipping) | SIMD helpers + vectorize pattern for gradient clipping | Succeeded on first attempt | Following established codebase patterns (activation_simd.mojo, matmul.mojo) eliminates trial-and-error — read reference code first |
| Consider vectorizing `compute_gradient_statistics` | Considered SIMD for the statistics function (norm + min/max/mean + NaN/Inf detection) | Decided against — mixed concerns (NaN/Inf checking requires per-element branches) and it's a monitoring function called infrequently | Not every function benefits from SIMD; prioritize hot-path functions called every training step |

## Results & Parameters

### Performance Characteristics

| Metric | Scalar (Before) | SIMD (After) | Improvement |
| -------- | ----------------- | -------------- | ------------- |
| Iterations per 1M float32 | ~1,000,000 | ~125,000 (width=8) | ~8x fewer iterations |
| Early exit (NaN at idx 0) | 1 iteration | 1 SIMD load | Same |
| Worst case (no NaN) | N iterations | N/simd_w + tail | ~8-16x faster |

### Key SIMD Operations Reference

```mojo
# Load SIMD vector from pointer
var vec = ptr.load[width=simd_w](offset)

# Check for NaN/Inf (returns SIMD[DType.bool, width])
var nan_mask = isnan(vec)
var inf_mask = isinf(vec)

# Boolean reduction (any lane True?)
if nan_mask.reduce_or(): ...

# Count True lanes
var count = Int(nan_mask.cast[DType.uint8]().reduce_add())

# Get compile-time SIMD width for dtype
comptime simd_w = simd_width_of[dtype]()
# float32 → 8 (AVX-256), float64 → 4 (AVX-256)
```

### Test Edge Cases to Cover

- Tensor smaller than SIMD width (pure scalar tail path)
- NaN/Inf at first element (early exit on first SIMD chunk)
- NaN/Inf at last element in tail region
- NaN/Inf at exact SIMD boundary
- Large tensors (1024+ elements)
- Multiple dtypes (float32, float64)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4910 — SIMD-vectorize numerical safety hot path | [PR #5119](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5119) |
| ProjectOdyssey | Issue #4911 — SIMD-vectorize gradient clipping | [PR #5120](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5120) — 4 functions vectorized via 6 SIMD helpers, 13 tests pass |
