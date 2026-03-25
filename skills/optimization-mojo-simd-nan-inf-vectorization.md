---
name: optimization-mojo-simd-nan-inf-vectorization
description: "SIMD-vectorize NaN/Inf detection functions in Mojo for hot-path performance. Use when: (1) optimizing element-wise tensor scanning functions, (2) implementing SIMD early-exit patterns in Mojo, (3) using vectorize[] with lane reduction for counting."
category: optimization
date: 2025-03-25
version: "1.0.0"
user-invocable: false
tags: [mojo, simd, vectorization, numerical-safety, performance, nan-detection]
---

# SIMD Vectorization of NaN/Inf Detection in Mojo

## Overview

| Field | Value |
|-------|-------|
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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `vectorize[]` for `has_nan` | Used `vectorize[]` closure with a `found` flag | Cannot `return True` from inside `vectorize[]` closure to exit the outer function — the closure is a separate function | Use manual SIMD loop (`while` + `ptr.load`) when early exit is needed |
| `List[Int](2, 8)` constructor | Tried to construct List with positional args | Mojo 0.26.1 `List[Int]` has no multi-arg constructor; must use `append()` or list literals `[2, 8]` | Always use `var s = List[Int](); s.append(n)` pattern or `[n]` list literal syntax |
| Lowercase docstring start | Used `"""has_nan returns...` | Mojo `--Werror` rejects docstrings not starting with capital letter or non-alpha | Always capitalize the first word of docstrings |
| `mojo format` on `comptime` | Ran `mojo format` on files using `comptime` keyword | Formatter crashes with `'_python_symbols' object has no attribute 'comptime_assert_stmt'` | Known Mojo formatter limitation — `comptime` keyword not yet supported by formatter; the `mojo-format-compat.sh` wrapper handles this gracefully |

## Results & Parameters

### Performance Characteristics

| Metric | Scalar (Before) | SIMD (After) | Improvement |
|--------|-----------------|--------------|-------------|
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
|---------|---------|---------|
| ProjectOdyssey | Issue #4910 — SIMD-vectorize numerical safety hot path | [PR #5119](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5119) |
