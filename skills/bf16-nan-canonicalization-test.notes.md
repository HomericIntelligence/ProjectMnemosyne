# Session Notes: BF16 NaN Canonicalization

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #4060
- **PR**: #4862
- **Branch**: `4060-auto-impl`

## Objective

Extend NaN canonicalization testing to BFloat16 dtype in the `ExTensor.__hash__` implementation.
The existing fix for `__hash__` used `_get_float64()` to canonicalize NaN via Float64 space,
but the BF16 path went through `Float64(Float32(BFloat16))` — a two-step numeric cast that
could silently destroy unusual NaN bit patterns before the `isnan()` bitwise check.

## Investigation Steps

1. Read `shared/core/extensor.mojo` to understand `_get_float64` implementation
2. Found BF16 used `Float64(Float32(ptr[]))` — numeric cast path
3. Identified risk: CPU numeric cast may canonicalize NaN mantissa bits
4. Verified BF16 bit layout: upper 16 bits of Float32, same sign+exponent format
5. Designed fix: read UInt16 raw bits, shift left 16, bitcast to Float32

## Key Discovery: 0xFF80 is NOT a NaN

Initial plan used `0xFF80` as "negative NaN" test case. During implementation discovered:

- BF16 bit pattern: `[sign:1][exp:8][mantissa:7]`
- `0xFF80` = `1111 1111 1000 0000` → sign=1, exp=0xFF (all ones), mantissa=0
- mantissa=0 → **Infinity**, not NaN
- Correct negative quiet NaN: `0xFFC0` = `1111 1111 1100 0000` (mantissa bit 6 set)

This caused initial test design to fail. Fixed by using `0xFFC0` for negative NaN.

## Implementation Approach

### Fix in extensor.mojo

Replaced two-line numeric cast with six-line raw bit manipulation:

```mojo
# Old (wrong):
var ptr = (self._data + offset).bitcast[BFloat16]()
return Float64(Float32(ptr[]))

# New (correct):
var raw_ptr = (self._data + offset).bitcast[UInt16]()
var raw: UInt16 = raw_ptr[]
var f32_bits: UInt32 = UInt32(raw) << 16
var f32_val = UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[]
return Float64(f32_val)
```

### Test Helper

Normal tensor setters go through `_set_float64` which uses the same numeric cast, so
we can't use them to inject raw NaN patterns. Must write directly via pointer cast:

```mojo
fn make_bf16_nan_tensor(raw_bits: UInt16) -> ExTensor:
    var t = ExTensor(Shape(1), DType.bfloat16)
    var raw_ptr = t._data.bitcast[UInt16]()
    raw_ptr[0] = raw_bits
    return t
```

## Test Results

All 3 new tests passed. Pre-existing 13 failures are unrelated to this change.

## Related Issues

- Closes #4060
- Follow-up from #3382 (original NaN canonicalization fix for float16/float32/float64)