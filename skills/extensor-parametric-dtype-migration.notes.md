# Session Notes: ExTensor Parametric DType Migration

## Timeline

1. PR #4996 replaced bitcast UAF writes with `tensor[i] = Float64(val)` -- caused 314 type errors
2. Discovered Mojo `obj[i]=val` uses `__getitem__` lvalue, not `__setitem__`
3. Added `__setitem__` overloads -- dead code, never called
4. Added `set()` method with overloads -- worked but Float64 round-trip lost precision
5. Refactored `set()` to use `_set_float32`/`_set_float64`/`_set_int64` directly
6. Extracted `_resolve_index` helper for DRY bounds-check + stride logic
7. Researched SIMD behavior -- strict same-type assignment via `Scalar[dtype]`
8. Prototyped parametric `MyTensor[dtype: DType]` -- works perfectly
9. Filed GitHub epic #4998 for the full parametric migration

## Key Discovery: Mojo Subscript Assignment

```mojo
# This does NOT call __setitem__:
tensor[i] = Float64(1.0)
# It calls __getitem__(i) -> Float32 lvalue, then assigns Float64 to Float32 -> ERROR

# SIMD works because __getitem__ returns Scalar[Self.dtype]:
var s = SIMD[DType.float32, 4](0.0)
s[0] = 3.14  # FloatLiteral -> Scalar[float32] -> works
```

## Precision Loss Bug

```
set(i, Float64(Float32(3.14159)))
  -> __setitem__(i, Float64(3.14159...))
  -> _set_float64(i, Float64(3.14159...))
  -> value.cast[float32]()
  -> 3.141590118408203  (NOT 3.14159)
```

Fix: `set()` now calls `_set_float32` directly for Float32 values.

## Files Modified (19 files total)

Source: extensor, activation, attention, conv, dropout, layers/dropout, dtype_cast, normalization, pooling
Autograd: tape_types
Data: _datasets_core
Training: accuracy, confusion_matrix
Tests: test_backward_linear, test_backward_losses, test_backward_conv_pool, test_shape_part3, test_setitem_view, test_extensor_setitem
Docs: heap corruption workaround ADR (fixed broken blog link)

## Sub-Agent Strategy

- Round 1: 8 agents for Float64->Float32 conversion (60% success)
- Round 2: 4 agents for remaining errors with .set() (90% success)
- Round 3: 4 agents for test files (100% success)
- Manual: parallelize closures, arithmetic mismatches, precision fix
