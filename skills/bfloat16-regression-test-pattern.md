---
name: bfloat16-regression-test-pattern
description: 'Pattern for writing bfloat16 regression tests in Mojo that catch silent-failure
  bugs (missing dtype branches). Use when: (1) adding bfloat16 support to dtype-dispatched
  functions, (2) auditing existing dtype handlers, (3) writing regression tests after
  fixing a silent-write or silent-read bug.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Dtype-dispatched functions (e.g. `_get_float32`, `_set_float32`) often have `if/elif` chains for float16/float32/float64 but omit bfloat16, causing silent failures — writes are no-ops and reads return garbage via the integer fallback path. |
| **Solution** | Three-part regression test: zero-guard, round-trip, and multi-element verification. The zero-guard is the most important — it exactly mirrors the failure mode. |
| **Language** | Mojo 0.26.1 |
| **Test File Pattern** | `tests/shared/core/test_extensor_getset_<fn>.mojo` |
| **Tolerance** | `1e-2` for bfloat16 (7-bit mantissa, ~2 decimal digits precision) |

## When to Use

- After auditing a dtype-dispatched function (grep for `if self._dtype == DType.float16` chains)
- When fixing a "bfloat16 silent no-op" or "bfloat16 reads garbage" bug
- When a PR adds a bfloat16 branch but tests only cover float16/float32/float64
- When reviewing follow-up issues from a prior bfloat16 fix (e.g. issue #3910 follow-up from #3301)

## Verified Workflow

### Quick Reference

```mojo
# 1. Zero-guard test (read path)
fn test_get_<fn>_bfloat16() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_float64(0, 1.5)  # use float64 path (already fixed) to seed
    var got = t._get_<fn>(0)
    assert_true(
        Float64(got) != 0.0,
        "bfloat16 _get_<fn> returned 0 — bfloat16 branch missing",
    )
    assert_almost_equal(Float64(got), 1.5, tolerance=1e-2)

# 2. Zero-guard test (write path)
fn test_set_<fn>_bfloat16() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_<fn>(0, <FloatType>(1.5))
    var got = t._get_float64(0)  # use float64 path (already fixed) to read back
    assert_true(
        got != 0.0,
        "bfloat16 _set_<fn> silently wrote zero — bfloat16 branch missing",
    )
    assert_almost_equal(got, 1.5, tolerance=1e-2)

# 3. Round-trip test (both read and write path together)
fn test_get_<fn>_bfloat16_roundtrip() raises:
    var t = zeros([4], DType.bfloat16)
    t._set_<fn>(0, <FloatType>(1.0))
    t._set_<fn>(1, <FloatType>(2.0))
    t._set_<fn>(2, <FloatType>(0.5))
    t._set_<fn>(3, <FloatType>(-1.0))
    assert_almost_equal(Float64(t._get_<fn>(0)), 1.0, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_<fn>(1)), 2.0, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_<fn>(2)), 0.5, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_<fn>(3)), -1.0, tolerance=1e-2)
```

### Step 1: Audit the function under test

```bash
grep -n "elif self._dtype == DType" shared/core/extensor.mojo | grep -A1 "float64"
```

Look for chains that have float16/float32/float64 but not bfloat16. The pattern:

```mojo
# BROKEN — missing bfloat16
if self._dtype == DType.float16:
    ...
elif self._dtype == DType.float32:
    ...
elif self._dtype == DType.float64:
    ...
else:
    return Float32(self._get_int64(index))  # bfloat16 hits this → garbage
```

### Step 2: Apply the fix

```mojo
# FIXED — with bfloat16 branch
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[BFloat16]()
    return ptr[].cast[DType.float32]()  # for _get_float32
    # OR for _set_float32:
    # ptr[] = value.cast[DType.bfloat16]()
```

### Step 3: Write the three regression tests

Use exactly-representable values to avoid precision ambiguity: `1.0`, `1.5`, `2.0`, `0.5`, `-1.0`.
These are all exactly representable in bfloat16 (power-of-2 fractions).

Avoid values like `1.3`, `2.7` — they are not exactly representable and will fail even with a
correct implementation at `1e-2` tolerance.

### Step 4: Register in `main()`

```mojo
print("Running _get_<fn> bfloat16 tests (regression for #<issue>)...")
test_get_<fn>_bfloat16()
test_get_<fn>_bfloat16_roundtrip()

print("Running _set_<fn> bfloat16 tests (regression for #<issue>)...")
test_set_<fn>_bfloat16()
```

### Step 5: ADR-009 heap corruption constraint

Mojo 0.26.1 has a heap corruption bug after ~15 cumulative tests in a single file.
If the target test file already has ≥12 tests, split to a new file:

```
tests/shared/core/test_extensor_getset_<fn>.mojo  # ≥12 tests → split
tests/shared/core/test_extensor_getset_<fn>_bf16.mojo  # new file for bfloat16 tests
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `1.5` in round-trip via `_set_float32` | Called `t._set_float32(0, Float32(1.5))` then `_get_float32` on bfloat16 | 1.5 IS exactly representable in bfloat16 (= 1 + 1/2), this actually works | Verify representability before assuming a value is "safe" |
| Using `2.7` for bfloat16 test | Test value `2.7` used in float32 tests copy-pasted to bfloat16 | 2.7 is not exactly representable in bfloat16; test would fail even with correct code | Use only power-of-2 fractions for bfloat16: 0.5, 1.0, 1.5, 2.0, -1.0 |
| Reading back via `_get_int64` to verify | Used the int64 fallback to confirm writes | The int64 path reinterprets bfloat16 bits as integers — misread. Confirmed fix actually works | Always use the float64 cross-check path (`_get_float64`) to verify bfloat16 writes |
| Checking if fix was needed | Grepped for "bfloat16" in extensor.mojo lines 1188–1246 | Found the fix was already applied in a prior commit; only the tests were missing | Always check both the implementation AND the tests. A fixed function can still lack regression coverage. |

## Results & Parameters

### Session outcome

- **Issue**: #3910 — audit `_set_float32`/`_get_float32` for missing bfloat16 branch
- **Finding**: Code fix was already present (`3c1b07fa`). Tests were missing.
- **PR**: #4827 — added 3 regression tests to `test_extensor_getset_float32.mojo`

### Bfloat16 tolerance rationale

```text
bfloat16: 1 sign bit, 8 exponent bits, 7 mantissa bits
→ ~2 decimal digits of precision
→ tolerance = 1e-2

float16:  1 sign bit, 5 exponent bits, 10 mantissa bits
→ ~3 decimal digits of precision
→ tolerance = 1e-3

float32:  1 sign bit, 8 exponent bits, 23 mantissa bits
→ ~7 decimal digits of precision
→ tolerance = 1e-6
```

### Exactly-representable bfloat16 test values

```text
Safe (power-of-2 fractions):   0.0, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0, -1.5, -2.0
Unsafe (not exact in bfloat16): 0.1, 0.3, 1.3, 2.7, 3.9
```
