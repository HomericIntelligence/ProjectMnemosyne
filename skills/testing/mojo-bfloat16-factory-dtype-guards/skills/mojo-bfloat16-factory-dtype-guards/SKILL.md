---
name: mojo-bfloat16-factory-dtype-guards
description: "Add bfloat16 dtype guard tests to Mojo tensor factory functions. Use when: a factory function routes float16/float32/float64 to a float path but is missing bfloat16, causing silent int-truncation of bfloat16 values."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo tensor factory functions (`arange`, `eye`, `linspace`, `randn`) check `dtype == DType.float16 or float32 or float64` to route values to `_set_float64`. Missing `DType.bfloat16` causes silent routing to `_set_int64`, truncating all float values to 0 |
| **Symptom** | bfloat16 tensors created by factory functions have all-zero or integer-truncated values |
| **Root Cause** | Dtype condition list `float16 or float32 or float64` does not include `bfloat16` |
| **Fix** | Add `or dtype == DType.bfloat16` to each condition; write regression tests |
| **Pattern** | Two-test-per-function: one for dtype preservation, one for correct float values |

## When to Use

- A Mojo tensor factory function routes to `_set_float64` for float types but bfloat16
  values are silently wrong (truncated to int)
- Adding tests for a bfloat16 dtype routing bug where the fix has already been applied
- Verifying that `bfloat16` is included in a multi-dtype condition alongside `float16`,
  `float32`, `float64`
- Writing regression tests that would catch re-introduction of the missing dtype condition

## Verified Workflow

### Quick Reference

| Function | Dtype test | Value test |
|----------|-----------|------------|
| `arange` | correct dtype preserved | [0.0, 1.0, 2.0, 3.0] not [0, 0, 0, 0] |
| `eye` | correct dtype preserved | diagonal=1.0, off-diagonal=0.0 |
| `linspace` | correct dtype preserved | [0.0, 1.0, 2.0, 3.0, 4.0] |
| `randn` | correct dtype preserved | ≥40/50 values have \|val\| > 1e-3 |

### Step 1: Locate all dtype-routing conditions in the factory functions

```bash
grep -n "DType.float16\|DType.float32\|DType.float64" shared/core/extensor.mojo \
  | grep -v "bfloat16"
```

Any line that mentions `float16 or float32 or float64` without `bfloat16` is a bug.

### Step 2: Verify the fix is in place

Each condition should look like:

```mojo
if (
    dtype == DType.float16
    or dtype == DType.float32
    or dtype == DType.float64
    or dtype == DType.bfloat16
):
    tensor._set_float64(i, value)
else:
    tensor._set_int64(i, Int(value))
```

### Step 3: Create a dedicated test file per ADR-009

Per ADR-009 (≤10 `fn test_` per file), create a separate file:

```text
tests/shared/core/test_creation_bfloat16.mojo
```

Add the ADR-009 header:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_creation.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Step 4: Write two tests per factory function

**Pattern A — dtype test**: verifies dtype is preserved after creation.

```mojo
fn test_arange_bfloat16_dtype() raises:
    """Test arange() preserves bfloat16 dtype."""
    var t = arange(0.0, 5.0, 1.0, DType.bfloat16)
    assert_dtype(t, DType.bfloat16, "arange bfloat16 should preserve dtype")
    assert_numel(t, 5, "arange(0, 5, 1) bfloat16 should have 5 elements")
```

**Pattern B — value test**: verifies float values are stored, not int-truncated zeros.

```mojo
fn test_arange_bfloat16_values() raises:
    """Test arange() with bfloat16 stores float values (not silently truncated to int)."""
    # bfloat16 has ~2 decimal digits of precision; use integer-valued sequence
    var t = arange(0.0, 4.0, 1.0, DType.bfloat16)
    # If routed to _set_int64, all values would be 0 (Int64 truncation)
    # bfloat16 tolerance: ~1e-2 for small integers
    assert_value_at(t, 0, 0.0, 1e-2, "arange bfloat16 [0] should be 0.0")
    assert_value_at(t, 1, 1.0, 1e-2, "arange bfloat16 [1] should be 1.0")
    assert_value_at(t, 2, 2.0, 1e-2, "arange bfloat16 [2] should be 2.0")
    assert_value_at(t, 3, 3.0, 1e-2, "arange bfloat16 [3] should be 3.0")
```

### Step 5: Use a wider tolerance for bfloat16

bfloat16 has only ~2-3 decimal digits of precision (vs 6 for float32). Use `1e-2`
instead of `1e-6` for value assertions. For integer-valued sequences (0.0, 1.0, 2.0...),
bfloat16 is exact, so either tolerance works — but `1e-2` is the safe default.

### Step 6: For randn(), use a nonzero-count approach

randn() values come from N(0,1). If routed to `_set_int64`, Box-Muller float values
(0.3, -1.2, etc.) would be truncated to 0. Test this by counting non-zero values:

```mojo
fn test_randn_bfloat16_nonzero() raises:
    var t = randn([50], DType.bfloat16, seed=42)
    var nonzero_count = 0
    for i in range(t.numel()):
        var val = t._get_float64(i)
        if val > 1e-3 or val < -1e-3:
            nonzero_count += 1
    # Most values from N(0,1) have |val| > 1e-3; require ≥40 of 50
    assert_true(
        nonzero_count >= 40,
        "randn bfloat16 should store non-zero floats, not int-truncated zeros",
    )
```

### Step 7: Run the new test file

```bash
just test-group tests/shared/core "test_creation_bfloat16.mojo"
```

Expected output:

```text
Running ExTensor bfloat16 dtype guard tests (issue #3906)...
All bfloat16 dtype guard tests passed!
✅ PASSED: tests/shared/core/test_creation_bfloat16.mojo
```

## Results & Parameters

**Session results** (ProjectOdyssey, 2026-03-15, issue #3906):

- 8 tests in `tests/shared/core/test_creation_bfloat16.mojo`
- ADR-009 limit: ≤10; actual: 8 (20% safety margin)
- All 8 tests passed on first run
- Tolerance used: `1e-2` for bfloat16 value assertions (safe for small integers)
- Seed used for randn: `42` (deterministic; threshold: ≥40/50 nonzero)

**Test count breakdown**:

| Function | Tests | Names |
|----------|-------|-------|
| `arange` | 2 | `test_arange_bfloat16_dtype`, `test_arange_bfloat16_values` |
| `eye` | 2 | `test_eye_bfloat16_dtype`, `test_eye_bfloat16_values` |
| `linspace` | 2 | `test_linspace_bfloat16_dtype`, `test_linspace_bfloat16_values` |
| `randn` | 2 | `test_randn_bfloat16_dtype`, `test_randn_bfloat16_nonzero` |

**Key config**:

- File: `tests/shared/core/test_creation_bfloat16.mojo`
- ADR-009 header: required
- bfloat16 tolerance: `1e-2`
- randn threshold: `≥40` of 50 non-zero values

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4826 / Issue #3906 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding tests to existing part3/part4 files | Append bfloat16 tests directly to `test_creation_part3.mojo` (8 tests) and `test_creation_part4.mojo` (6 tests) | Part3 was at 8 tests — adding would hit ADR-009 limit | Create a new dedicated file per ADR-009 when existing files are near the limit |
| Using `1e-6` tolerance for bfloat16 | Same tolerance as float32 tests | bfloat16 has only ~2 decimal digits of precision; could cause false failures with non-integer values | Use `1e-2` tolerance for bfloat16; `1e-6` is safe only for float32/float64 |
| Asserting exact mean/std for randn bfloat16 | Testing distribution statistics (mean≈0, std≈1) like float32 randn tests | bfloat16 precision makes statistical convergence unreliable for small N | Test structural property (non-zero values) instead of distribution statistics |
