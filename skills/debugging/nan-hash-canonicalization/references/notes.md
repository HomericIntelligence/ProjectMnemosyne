# Session Notes: NaN Hash Canonicalization (Issue #3382)

## Session Context

- **Date**: 2026-03-07
- **Repository**: ProjectOdyssey (`HomericIntelligence/ProjectOdyssey`)
- **Branch**: `3382-auto-impl`
- **Issue**: #3382 — Handle NaN hash stability in `__hash__`
- **PR**: #4058
- **Follow-up to**: Issue #3164 / PR #3373 (bitcast-based float hash fix, skill: `mojo-hash-bitcast-floats`)

## Objective

After fixing `ExTensor.__hash__` to use IEEE 754 bitcast (issue #3164), a follow-up issue
noted that different NaN bit patterns (signaling NaN, negative NaN, different NaN payloads)
still produce different hashes, even though they all represent "not-a-number" semantically.

The fix was to detect NaN after bitcast and replace with a single canonical bit pattern
before hashing.

## Files Modified

### `shared/core/extensor.mojo` (modified)

**Location**: `__hash__` method at line ~2867

**Change**: Added 4 lines — three `alias` constants and one `if` check — to the element
hashing loop. The loop already bitcast float64 to UInt64; the new check detects NaN and
substitutes `0x7FF8000000000000` (canonical quiet NaN).

```mojo
# Added aliases
alias CANONICAL_NAN_F64: UInt64 = 0x7FF8000000000000
alias F64_INF_BITS: UInt64 = 0x7FF0000000000000
alias F64_ABS_MASK: UInt64 = 0x7FFFFFFFFFFFFFFF

# Added check inside the loop
if (int_bits & F64_ABS_MASK) > F64_INF_BITS:
    int_bits = CANONICAL_NAN_F64
```

### `tests/shared/core/test_hash.mojo` (new file)

New dedicated test file with 15 test functions:

- Helper functions to inject specific NaN bit patterns via `_data.bitcast[UInt32]()[]`
- Tests for float32, float64, float16 NaN variants
- Tests for mixed NaN+normal tensors
- Tests for shape/dtype sensitivity (regression)
- Tests for integer types (no regression)

## Key Design Decisions

1. **Canonicalize in Float64 space, not per-dtype**: The existing `_get_float64()` helper
   converts all dtypes to Float64 before bitcast. This means all NaN variants (from float16,
   float32, float64, bfloat16) are already in Float64 space when the check runs. No per-dtype
   canonicalization branches needed.

2. **Hash-side only**: No modification to stored tensor data. The `nan_tensor()` function
   continues to store the raw NaN produced by `0.0 / 0.0`. Only the hash computation
   normalizes to a canonical form.

3. **Bitwise NaN detection**: `(bits & 0x7FFFFFFFFFFFFFFF) > 0x7FF0000000000000` is
   self-contained and requires no import. It correctly identifies all NaN variants by
   stripping the sign bit and comparing against infinity.

## Testing Constraints

Local Mojo tests cannot run on this system (requires glibc >= 2.32, system has older version).
Tests verified correct by:

1. Logic review: The NaN detection condition is mathematically correct per IEEE 754 spec
2. Test file follows existing patterns from `test_utility.mojo` and `test_edge_cases.mojo`
3. Pre-commit hooks pass (mojo format, markdownlint, trailing whitespace, etc.)
4. CI will run full test suite in Docker

## Pre-commit Results

```
Mojo Format....................................................Passed
Check for deprecated List[Type](args) syntax...................Passed
Validate Test Coverage.........................................Passed
Check Test Count Badge.........................................Passed
Markdown Lint..................................................Passed
Trim Trailing Whitespace.......................................Passed
Fix End of Files...............................................Passed
Check YAML.....................................................Passed
Check for Large Files..........................................Passed
Fix Mixed Line Endings.........................................Passed
```

The one failing check (`Ruff Check Python` — F811 redefinition in
`tests/scripts/test_migrate_odyssey_skills.py`) is pre-existing and unrelated to this issue.

## NaN Bit Pattern Reference

| Type | Bits (hex) | Description |
|------|-----------|-------------|
| Float32 +qNaN | `0x7FC00000` | Positive quiet NaN (canonical) |
| Float32 -qNaN | `0xFFC00000` | Negative quiet NaN |
| Float32 sNaN | `0x7F800001` | Signaling NaN (MSB mantissa = 0, payload = 1) |
| Float32 ∞ | `0x7F800000` | Positive infinity (boundary: all mantissa bits zero) |
| Float64 +qNaN | `0x7FF8000000000000` | Positive quiet NaN (canonical) |
| Float64 -qNaN | `0xFFF8000000000000` | Negative quiet NaN |
| Float64 sNaN | `0x7FF0000000000001` | Signaling NaN |
| Float64 ∞ | `0x7FF0000000000000` | Positive infinity |
| Float16 +qNaN | `0x7E00` | Positive quiet NaN (canonical) |
| Float16 -qNaN | `0xFE00` | Negative quiet NaN |
| Float16 ∞ | `0x7C00` | Positive infinity |
