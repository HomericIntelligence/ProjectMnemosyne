# Session Notes: mojo-hash-bitcast-floats

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3164 - Fix `__hash__` to use bitcast for exact float bit representation
- **Branch**: `3164-auto-impl`
- **PR**: #3373
- **Date**: 2026-03-05

## Original Bug

`ExTensor.__hash__` in `shared/core/extensor.mojo` used:

```mojo
h = h * 31 + UInt(Int(val * 1000000.0))
```

Problems:
- `1e15 * 1e6 = 1e21` overflows `Int` (max ~9.2e18 for Int64)
- `1e-7 * 1e6 = 0.1` truncates to `0`, same as `2e-7 * 1e6 = 0.2`

## Fix Applied

```mojo
var val = self._get_float64(i)
var local_val = val  # local copy required before UnsafePointer.address_of
var int_bits = (UnsafePointer.address_of(local_val)).bitcast[UInt64][]
h = h * 31 + UInt(int_bits)
```

## Files Modified

- `shared/core/extensor.mojo`: Added `__hash__` method with bitcast
- `tests/shared/core/test_utility.mojo`: 4 real hash tests replacing placeholder

## Notes

- The `local_val` intermediate is required — cannot pass a function return value
  directly to `UnsafePointer.address_of` as it has no stable address
- `_get_float64(i)` returns `Float64` regardless of tensor dtype (float16/32/64/int*)
  so we always bitcast as `UInt64` (8 bytes = 64 bits)
- Shape and dtype are also hashed to distinguish tensors with same data but
  different shapes or precisions
- Local mojo compiler (GLIBC too old) could not run tests — CI will validate