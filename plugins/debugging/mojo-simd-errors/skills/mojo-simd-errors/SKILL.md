---
name: mojo-simd-errors
description: "Debug SIMD vectorization errors in Mojo tensor operations"
category: debugging
source: ProjectOdyssey
date: 2025-12-28
---

# Mojo SIMD Errors

Debug and fix common SIMD vectorization errors in Mojo code.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-28 |
| Objective | Fix SIMD comparison and conditional selection errors |
| Outcome | Success |

## When to Use

- SIMD comparison operators (`>`, `<`, `==`) fail to compile
- Conditional selection with boolean masks doesn't work
- Vectorized tensor operations produce unexpected results
- Migrating from older Mojo syntax to v0.25.7+

## Verified Workflow

1. **Use method syntax for comparisons**:

   ```mojo
   # Correct: Use .gt() method
   var mask = simd_val.gt(0.0)

   # Wrong: Operator syntax may fail
   # var mask = simd_val > 0.0
   ```

2. **Use .select() for conditional assignment**:

   ```mojo
   # Correct: mask.select(true_val, false_val)
   var result = mask.select(positive_val, zero_val)

   # Wrong: Ternary or if-else
   # var result = mask ? positive_val : zero_val
   ```

3. **Handle boolean mask type correctly**:

   ```mojo
   # mask is SIMD[DType.bool, width], not Bool
   var mask: SIMD[DType.bool, 4] = simd_val.gt(0.0)
   ```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| `simd > 0.0` operator | Operator not defined for SIMD types | Use `.gt()` method |
| `if mask: ...` | Can't branch on SIMD bool | Use `.select()` for vectorized |
| Bitwise AND for masks | Type mismatch with DType.bool | Cast or use `.select()` |
| Python-style ternary | Mojo has different syntax | Use `.select()` method |

## Results & Parameters

```mojo
# ReLU activation with SIMD
fn relu_simd[width: Int](x: SIMD[DType.float32, width]) -> SIMD[DType.float32, width]:
    var zero = SIMD[DType.float32, width](0.0)
    var mask = x.gt(zero)
    return mask.select(x, zero)

# Clamp with SIMD
fn clamp_simd[width: Int](
    x: SIMD[DType.float32, width],
    min_val: Float32,
    max_val: Float32
) -> SIMD[DType.float32, width]:
    var min_simd = SIMD[DType.float32, width](min_val)
    var max_simd = SIMD[DType.float32, width](max_val)
    var above_min = x.gt(min_simd).select(x, min_simd)
    return above_min.lt(max_simd).select(above_min, max_simd)
```

## References

- Mojo SIMD documentation: https://docs.modular.com/mojo/stdlib/builtin/simd
- Related: optimization/mojo-simd-patterns
- Source: ProjectOdyssey PR #2567
