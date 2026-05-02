# Session Notes: Mojo __setitem__ Lvalue Semantics

## Context

PR #4996 replaced `tensor._data.bitcast[T]()[i] = val` (bitcast UAF writes) with
`tensor[i] = Float64(val)` (using `__setitem__`). CI reported 314+ type errors because
Mojo's `obj[i] = val` does not dispatch to `__setitem__`.

## Discovery Process

1. Initial plan assumed adding `__setitem__` overloads would fix the errors
2. Added 9 overloads (Float16, Int, Int8/16/32, UInt8/16/32/64) -- all dead code
3. Created minimal test to confirm: `v[1] = Float64(2.0)` fails even with matching `__setitem__`
4. Root cause: Mojo treats `obj[i]` as an lvalue via `__getitem__` (returns Float32)
5. Solution: `set()` method with explicit overloads + `_set_float64` for non-raising contexts

## Minimal Reproduction

```mojo
struct MyVec:
    var data: UnsafePointer[Float32]
    fn __getitem__(self, i: Int) -> Float32: return self.data[i]
    fn __setitem__(mut self, i: Int, val: Float64): self.data[i] = Float32(val)

fn main():
    var v = MyVec(...)
    v[0] = Float64(1.0)  # ERROR: cannot implicitly convert Float64 to Float32
    # __setitem__ is NEVER called -- Mojo uses __getitem__ lvalue
```

## Three Fix Patterns

1. **Float32 cast** -- `result[i] = Float32(expr)` -- works in raising contexts
2. **set() method** -- `result.set(i, expr)` -- works for any type, raises
3. **_set_float64()** -- `result._set_float64(i, Float64(expr))` -- for parallelize closures

## Parallelization Strategy

- Round 1: 8 agents for initial Float64->Float32 conversion (fixed ~60%)
- Round 2: 4 agents for remaining errors using .set() pattern (fixed ~35%)
- Manual fixes: parallelize closures, arithmetic type mismatches (~5%)

## Files Modified

- `shared/core/extensor.mojo` -- Added `set()` overloads, fixed constructors
- `shared/core/activation.mojo` -- 74 lines changed
- `shared/core/attention.mojo` -- 34 lines changed
- `shared/core/conv.mojo` -- 22 lines changed
- `shared/core/dropout.mojo` -- 26 lines changed
- `shared/core/dtype_cast.mojo` -- 18 lines changed
- `shared/core/layers/dropout.mojo` -- 24 lines changed
- `shared/core/normalization.mojo` -- 187 lines changed (largest, most complex)
- `shared/core/pooling.mojo` -- 12 lines changed
- `docs/adr/` heap corruption workaround ADR -- Fixed broken blog link
