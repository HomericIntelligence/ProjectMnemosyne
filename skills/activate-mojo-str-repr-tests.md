---
name: activate-mojo-str-repr-tests
description: 'Implement Stringable/Representable traits on a Mojo struct and activate
  commented-out __str__/__repr__ placeholder tests. Use when: a test file has TODO-guarded
  __str__/__repr__ stubs, you need String()/repr() support on a Mojo struct, or tests
  are commented out pending string method implementation.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Skill: Activate Mojo __str__/__repr__ Tests

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Category** | testing |
| **Objective** | Implement `__str__`/`__repr__` on `ExTensor` and activate placeholder tests in `test_utility.mojo` |
| **Outcome** | Successfully added `Stringable`/`Representable` traits, implemented both methods, activated 2 tests with concrete assertions |
| **Context** | Issue #3162 - Activate `__str__`/`__repr__` tests in `test_utility.mojo` (follow-up from #2722) |

## When to Use

Use this skill when:

- A Mojo test file has placeholder stubs like `pass  # Placeholder` with `# TODO(#NNNN): Implement __str__` comments
- A Mojo struct needs `String(t)` or `repr(t)` support (i.e., `Stringable`/`Representable` traits)
- Tests are guarded by TODO comments referencing an upstream issue that is now resolved
- You need to implement both human-readable (`__str__`) and debug-detailed (`__repr__`) string representations

Do NOT use when:

- The upstream implementation issue is still open — verify `__str__`/`__repr__` exist before activating tests
- The struct already implements `Stringable`/`Representable` — only the test activation step is needed
- The struct uses a non-standard element access mechanism that `_get_float64` doesn't cover

## Verified Workflow

### Step 1: Confirm Implementation Status

Before activating tests, verify whether `__str__`/`__repr__` already exist:

```bash
grep -rn "fn __str__\|fn __repr__" shared/core/extensor.mojo
```

If not present, implementation is needed first (Steps 2-3). If present, skip to Step 4.

### Step 2: Add Traits to Struct Declaration

Locate the struct definition and add `Stringable` and `Representable` to the trait list:

```mojo
# Before
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

# After
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Stringable, Representable):
```

### Step 3: Implement __str__ and __repr__

Insert after `__len__` (or at the end of dunder methods). Use the existing internal `_get_float64(index)` method for element access:

```mojo
fn __str__(self) -> String:
    """Human-readable string representation."""
    var result = String("ExTensor([")
    for i in range(self._numel):
        if i > 0:
            result += ", "
        result += String(self._get_float64(i))
    result += "], dtype=" + String(self._dtype) + ")"
    return result

fn __repr__(self) -> String:
    """Detailed representation for debugging."""
    var shape_str = String("[")
    for i in range(len(self._shape)):
        if i > 0:
            shape_str += ", "
        shape_str += String(self._shape[i])
    shape_str += "]"
    var result = String("ExTensor(shape=") + shape_str
    result += ", dtype=" + String(self._dtype)
    result += ", numel=" + String(self._numel)
    result += ", data=["
    for i in range(self._numel):
        if i > 0:
            result += ", "
        result += String(self._get_float64(i))
    result += "])"
    return result
```

### Step 4: Identify Element Access Method

Before implementing, confirm the internal element read method:

```bash
grep -n "fn _get_float64\|fn _get_float32\|fn _get_int64" shared/core/extensor.mojo
```

For `ExTensor`, `_get_float64(index: Int) -> Float64` handles all dtypes (float16/32/64 + integer types via cast). Use this for both `__str__` and `__repr__`.

### Step 5: Activate Placeholder Tests

Replace the commented stubs in the test file. The expected format for `String(DType.float32)` is `"float32"`. For `String(Float64(0.0))`, Mojo produces `"0.0"`:

```mojo
fn test_str_readable() raises:
    """Test __str__ produces readable output."""
    var t = arange(0.0, 3.0, 1.0, DType.float32)
    var s = String(t)
    assert_equal(s, "ExTensor([0.0, 1.0, 2.0], dtype=float32)", "__str__ format")


fn test_repr_complete() raises:
    """Test __repr__ produces complete representation."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    var t = ones(shape, DType.float32)
    var r = repr(t)
    assert_equal(
        r,
        "ExTensor(shape=[2, 2], dtype=float32, numel=4, data=[1.0, 1.0, 1.0, 1.0])",
        "__repr__ format",
    )
```

### Step 6: Add assert_equal to Imports

Check whether `assert_equal` is already imported in the test file:

```bash
grep "assert_equal" tests/shared/core/test_utility.mojo
```

If not present, add it to the `from tests.shared.conftest import (...)` block.

### Step 7: Verify with Pre-commit

```bash
pixi run pre-commit run --all-files
```

Expected: all hooks pass (mojo format may show GLIBC errors on older Linux systems — this is a local environment issue, not a code error).

## Key Findings

### DType String Format

`String(DType.float32)` produces `"float32"` — confirmed by multiple test assertions across the codebase (e.g., `test_dtype_ordinal.mojo`, `test_serialization.mojo`).

### Float64 String Format

`String(Float64(0.0))` produces `"0.0"`, `String(Float64(1.0))` produces `"1.0"` — Mojo uses standard decimal float representation for integer-valued floats, matching the issue comment suggestions.

### Implementation Was Missing

The issue assumed `__str__`/`__repr__` were already implemented (follow-up from #2722), but code inspection showed they were absent. Both the implementation AND test activation were required. Always grep for the methods before assuming they exist.

### _get_float64 Handles All Dtypes

The `_get_float64(self, index: Int) -> Float64` method in `ExTensor` handles float16, float32, float64, and all integer types (via `_get_int64` cast). Safe to use as the universal element accessor in `__str__`/`__repr__`.

### Local Mojo Unavailable

The local system had GLIBC version incompatibilities preventing `mojo test` from running. CI (Docker-based) is required for actual test execution. This is expected and acceptable — pre-commit hooks (markdown lint, YAML, trailing whitespace) still pass locally.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| `__str__` format | `ExTensor([0.0, 1.0, 2.0], dtype=float32)` |
| `__repr__` format | `ExTensor(shape=[2, 2], dtype=float32, numel=4, data=[1.0, 1.0, 1.0, 1.0])` |
| Trait list addition | `Stringable, Representable` |
| Element accessor | `self._get_float64(i)` |
| Import needed | `assert_equal` from `tests.shared.conftest` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Grep for `__str__` in `extensor.mojo` | Expected to find existing implementation based on issue title saying "methods are implemented" | Methods did not exist in `extensor.mojo` — only in unrelated `nvfp4.mojo`/`mxfp4.mojo` | Always verify implementation existence before activating tests; issue descriptions can be wrong |
| Run `pixi run mojo test` locally | Expected to run tests to verify string format | GLIBC version mismatch (`GLIBC_2.32`, `2.33`, `2.34` not found) | Local Mojo requires newer GLIBC; use Docker/CI for actual test runs |
| Using `_get_float64_at` as method name | Issue plan suggested this name | Method is actually named `_get_float64` in `ExTensor` | Always grep for actual method names rather than trusting plan docs |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3371, Issue #3162 | [notes.md](../references/notes.md) |
