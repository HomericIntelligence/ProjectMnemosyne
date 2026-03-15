---
name: mojo-silent-noop-int8-dtype-fix
description: "Fix silent no-op writes in Mojo dtype dispatch functions missing integer branches. Use when: a _set_float* function silently discards writes for int8, a dtype chain has no integer branch, or a test documents a known no-op instead of asserting correct truncation."
category: debugging
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo dtype dispatch functions (`_set_float64`, `_set_float32`) silently do nothing for integer dtypes when no matching `elif` branch exists |
| **Root Cause** | `if/elif` chains without an `else` are silent no-ops in Mojo — unmatched dtypes fall through without error |
| **Fix** | Add the missing integer `elif` branch with truncation cast (e.g. `value.cast[DType.int8]()`) |
| **Test Update** | Replace no-op-documenting tests with truncation-assertion tests |
| **Affected files** | `shared/core/extensor.mojo` — `_set_float64` and `_set_float32` |

## When to Use

- A test contains a comment like "silent no-op" or "TODO: add int8 branch" for a setter function
- A dtype round-trip test uses `_set_int64` as a workaround because `_set_float64` doesn't work for that dtype
- A dtype audit (`grep _set_float`) reveals an integer dtype has no branch in float setter functions
- A write to an integer tensor silently has no effect

## Verified Workflow

### Quick Reference

```bash
# 1. Find all setter functions missing integer branches
grep -n "_set_float64\|_set_float32" shared/core/extensor.mojo

# 2. Read the function body (look for the last elif — that's where to add)
# 3. Add the int8 branch immediately after the last float branch
# 4. Mirror the fix to _set_float32
# 5. Replace no-op test with truncation test
# 6. Update main() in the test file
```

### Step 1: Identify the missing branch

Grep for `_set_float` functions and read their `if/elif` chains. A missing
integer dtype means any write for that dtype is silently discarded.

```mojo
# Before: _set_float64 stops at float64 — int8 falls through silently
if self._dtype == DType.float16:
    ...
elif self._dtype == DType.float32:
    ...
elif self._dtype == DType.float64:
    ...
# int8: no branch → silent no-op
```

### Step 2: Add the int8 branch with truncation semantics

Append the missing `elif` immediately after the last float branch. Use
`bitcast[Int8]()` + `value.cast[DType.int8]()` to match the pattern used by
all other branches.

```mojo
# After: add int8 branch with truncation cast
elif self._dtype == DType.int8:
    var ptr = (self._data + offset).bitcast[Int8]()
    ptr[] = value.cast[DType.int8]()
```

Apply the same fix to `_set_float32`:

```mojo
elif self._dtype == DType.int8:
    var ptr = (self._data + offset).bitcast[Int8]()
    ptr[] = value.cast[DType.int8]()
```

### Step 3: Update the docstring

Change "assumes float-compatible dtype" to "truncating to the tensor's dtype"
and add a `Note:` section documenting the int8 truncation.

### Step 4: Replace the no-op test

Delete the test that documents the bug and replace it with a test that
asserts correct truncation behavior:

```mojo
# Before: documents the bug
fn test_int8_set_float64_is_noop() raises:
    var t = zeros([1], DType.int8)
    t._set_float64(0, 1.0)
    assert_almost_equal(t._get_float64(0), 0.0, tolerance=1e-9)  # stays 0

# After: asserts correct truncation
fn test_int8_set_float64_truncates_to_int8() raises:
    var t = zeros([4], DType.int8)
    t._set_float64(0, 42.0)
    t._set_float64(1, -1.0)
    t._set_float64(2, 0.0)
    t._set_float64(3, 127.9)   # truncates to 127 (max int8)
    assert_almost_equal(t._get_float64(0), 42.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(1), -1.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(2), 0.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(3), 127.0, tolerance=1e-9)
```

Add a parallel test for `_set_float32`:

```mojo
fn test_int8_set_float32_truncates_to_int8() raises:
    var t = zeros([4], DType.int8)
    t._set_float32(0, 42.0)
    t._set_float32(1, -1.0)
    t._set_float32(2, 0.0)
    t._set_float32(3, 127.9)
    assert_almost_equal(t._get_float64(0), 42.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(1), -1.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(2), 0.0, tolerance=1e-9)
    assert_almost_equal(t._get_float64(3), 127.0, tolerance=1e-9)
```

### Step 5: Update main() in the test file

Replace the call to the old test name with the new test names and add the
`_set_float32` test call.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Option 2: raise on unsupported dtype | Issue proposed raising an error for int8 instead of truncating | Raises break all existing callers that pass int8 tensors — truncation is the correct semantic (mirrors Python/numpy behavior) | Silent no-ops are worse than errors, but truncation is better than errors when the operation is semantically valid |
| Patching only `_set_float64` | Initially considered only fixing the one function mentioned in the issue title | `_set_float32` had the identical missing branch — fixing only one leaves the other broken | Always grep for sibling functions with the same pattern when fixing a dtype dispatch chain |
| Adding `else: pass` | Considered adding an explicit `else` branch as a no-op documentation | Still silently discards writes — just makes the silence explicit rather than fixing it | Don't document bugs in code; fix them |

## Results & Parameters

**PR**: HomericIntelligence/ProjectOdyssey#4825

**Files changed**:

- `shared/core/extensor.mojo` — added `int8` branch to `_set_float64` (line ~1190) and `_set_float32` (line ~1253)
- `tests/shared/core/test_extensor_dtype_roundtrip.mojo` — replaced noop test with two truncation tests

**Cast pattern** (copy-paste):

```mojo
elif self._dtype == DType.int8:
    var ptr = (self._data + offset).bitcast[Int8]()
    ptr[] = value.cast[DType.int8]()
```

**Test values that cover the int8 range**:

```text
42.0   → 42    (positive integer)
-1.0   → -1    (negative integer)
0.0    → 0     (zero)
127.9  → 127   (truncation at max int8, not rounding)
```
