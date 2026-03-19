---
name: mojo-assert-close-float-tests
description: 'Documents patterns for comprehensive assert_close_float tests in Mojo.
  Use when: adding float tolerance tests, covering NaN/infinity edge cases, verifying
  atol/rtol boundary behavior.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Objective | Write comprehensive tests for `assert_close_float` covering all tolerance and edge-case scenarios |
| Outcome | 9 test functions added covering atol/rtol boundaries, NaN, infinity; compiled and verified passing |

| Property | Value |
|----------|-------|
| Language | Mojo 0.26.1 |
| Test target | `assert_close_float(a: Float64, b: Float64, rtol: Float64 = 1e-5, atol: Float64 = 1e-8)` |
| Tolerance formula | `\|a - b\| <= atol + rtol * \|b\|` |
| NaN pattern | `Float64(0.0) / Float64(0.0)` |
| Infinity pattern | `Float64(1.0) / Float64(0.0)` |
| Failure test pattern | try/except + assert_true(failed) |

## When to Use

- Adding tests for floating-point comparison/assertion functions in Mojo
- Covering edge cases: NaN equality, infinity mismatch, tolerance boundaries
- Implementing issue follow-ups where imports exist but tests are minimal or missing
- Verifying that a tolerance function rejects values outside atol/rtol bounds

## Verified Workflow

### Step 1: Read the function signature before writing tests

Check whether the function takes `Float64` or `Float32`. Mismatched types cause silent implicit
conversion that masks type errors. Verify the full signature including default tolerance values.

### Step 2: Derive test values from the tolerance formula

`assert_close_float` uses: `|a - b| <= atol + rtol * |b|`

Default values: `atol = 1e-8`, `rtol = 1e-5`

Design boundary values from this formula — e.g. for within-atol test use `diff = 5e-9 < 1e-8`.

### Step 3: Implement NaN and infinity using arithmetic (no literals in Mojo)

```mojo
var nan = Float64(0.0) / Float64(0.0)
var inf = Float64(1.0) / Float64(0.0)
var neg_inf = Float64(-1.0) / Float64(0.0)
```

### Step 4: Use try/except + flag pattern for failure tests

```mojo
fn test_assert_close_float_fails_one_nan() raises:
    var nan = Float64(0.0) / Float64(0.0)
    var failed = False
    try:
        assert_close_float(1.0, nan)
    except:
        failed = True
    assert_true(failed, "assert_close_float should raise for NaN mismatch")
```

### Step 5: Cover all 9 case categories

| Test Case | Description |
|-----------|-------------|
| Basic pass | Values within default tolerance |
| Basic fail | Values far apart (exceeds both atol and rtol) |
| Within atol | `diff < atol` (e.g. diff=5e-9, atol=1e-8) |
| Within rtol | `diff < rtol * \|b\|` but diff > atol |
| Exceeds both | diff > atol + rtol * \|b\| |
| Custom atol pass | Large atol allows larger diff |
| Custom atol fail | Small atol rejects small diff |
| Both NaN | NaN == NaN should pass |
| One NaN | NaN != finite should fail |
| Same +inf | inf == inf should pass |
| Opposite infinities | +inf != -inf should fail |

### Step 6: Compile and run to verify before committing

```bash
pixi run mojo build tests/shared/testing/test_assertions_float.mojo -o /tmp/test_float
/tmp/test_float
```

### Step 7: Watch ADR-009 test count limit

Mojo 0.26.1 has a heap corruption bug after approximately 15 cumulative test function calls in
one file. Add a comment near the test count if approaching the limit:

```mojo
# NOTE: ADR-009 heap corruption limit is ~15 tests per file.
# Currently at 19 tests — split file if adding more.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Used Float32 in existing tests | Passed `Float32(1.0)` to function expecting `Float64` | Implicit conversion worked but was semantically wrong and masked type mismatch | Always check actual function signature before writing tests |
| Assumed Python/pytest conventions | Issue prompt mentioned pytest and Python test patterns | Project is Mojo, not Python — pattern is `fn test_x() raises` not `def test_x()` | Verify language from actual codebase files, not issue template wording |

## Results & Parameters

### Full test coverage pattern for assert_close_float

```mojo
fn test_assert_close_float_passes() raises:
    assert_close_float(1.0, 1.0001, rtol=1e-2, atol=1e-3)

fn test_assert_close_float_passes_within_atol() raises:
    # diff = 5e-9 < atol=1e-8
    assert_close_float(1.0, 1.0 + 5e-9)

fn test_assert_close_float_passes_within_rtol() raises:
    # diff = 5e-6, threshold = 1e-8 + 1e-5 * 1.0 = ~1e-5
    assert_close_float(1.0, 1.0 + 5e-6)

fn test_assert_close_float_fails_exceeds_tolerance() raises:
    var failed = False
    try:
        assert_close_float(1.0, 2.0)
    except:
        failed = True
    assert_true(failed, "assert_close_float should raise when values differ by 1.0")

fn test_assert_close_float_passes_custom_atol() raises:
    # diff = 0.01, custom atol=0.1 is large enough
    assert_close_float(1.0, 1.01, atol=0.1)

fn test_assert_close_float_fails_custom_atol() raises:
    var failed = False
    try:
        # diff = 0.01 exceeds atol=1e-4 and rtol=1e-5 * 1.0
        assert_close_float(1.0, 1.01, atol=1e-4, rtol=1e-5)
    except:
        failed = True
    assert_true(failed, "assert_close_float should raise with tight atol")

fn test_assert_close_float_passes_both_nan() raises:
    var nan = Float64(0.0) / Float64(0.0)
    assert_close_float(nan, nan)  # Both NaN: considered equal

fn test_assert_close_float_fails_one_nan() raises:
    var nan = Float64(0.0) / Float64(0.0)
    var failed = False
    try:
        assert_close_float(1.0, nan)
    except:
        failed = True
    assert_true(failed, "assert_close_float should raise for NaN mismatch")

fn test_assert_close_float_passes_same_inf() raises:
    var inf = Float64(1.0) / Float64(0.0)
    assert_close_float(inf, inf)

fn test_assert_close_float_fails_inf_mismatch() raises:
    var inf = Float64(1.0) / Float64(0.0)
    var neg_inf = Float64(-1.0) / Float64(0.0)
    var failed = False
    try:
        assert_close_float(inf, neg_inf)
    except:
        failed = True
    assert_true(failed, "assert_close_float should raise for opposite infinities")
```

### Function signature reference

```mojo
fn assert_close_float(
    a: Float64,
    b: Float64,
    rtol: Float64 = 1e-5,
    atol: Float64 = 1e-8,
    message: String = "",
) raises
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4096 / PR #4870 | [notes.md](../references/notes.md) |
