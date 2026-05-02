---
name: mojo-shape-noncontiguous-value-tests
description: 'TDD regression pattern for verifying element-value correctness of shape
  ops on Mojo tensors. Use when: (1) adding value-correctness tests for shape ops
  (reshape, flatten, permute, concatenate, tile, repeat, broadcast_to) on non-contiguous
  inputs, surfacing flat-index bugs where _get_float64(i) ignores _strides; (2) shape
  tests use assert_numel/assert_dim only and need actual value assertions added; (3)
  code review flags tests that pass even if operations produce wrong output.'
category: testing
date: 2026-03-15
version: 2.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-shape-noncontiguous-value-tests |
| **Category** | testing |
| **Language** | Mojo |
| **Issue** | #4086 (follow-up from #3391) |
| **PR** | #4867 |

Captures the pattern for writing element-value regression tests for Mojo shape
operations (`reshape`, `flatten`, `permute`, `concatenate`, `tile`, `repeat`,
`broadcast_to`) when called on non-contiguous (transposed/strided) tensors.

The key insight: existing tests only verified `is_contiguous()` and stride
shapes after `as_contiguous()`, missing element-value regression. Shape ops
that use `_get_float64(i)` (flat index) instead of stride-based indexing
silently return wrong values when the input has non-C-order strides.

## When to Use

- Adding tests for any shape op that reads source elements by flat index
- Writing a regression test before fixing a flat-index bug (TDD-first)
- Verifying a non-contiguous tensor (transposed via `transpose_view()`) is
  correctly read by a shape transformation operation
- Covering a new shape op added to `shape.mojo` for non-contiguous correctness
- Shape tests use `assert_numel` and `assert_dim` only — element counts and dimensions are
  checked but the actual stored values are never verified
- Code review flags tests that pass even if operations produce wrong output — the operation
  could silently corrupt values and tests would still pass
- Newly-enabled tests are stubs — the tests were written to unblock CI but lack content assertions
- Follow-up issues reference "verify actual element values"

**Trigger phrases (contiguous value assertion):**

- "only asserts element counts (assert_numel) and dimensions (assert_dim)"
- "verify actual element values"
- "test_tile_1d verifies 9 elements but not that the values are [0,1,2,0,1,2,0,1,2]"
- "add assert_value_at() calls to verify correctness"

## Verified Workflow

### Setup Pattern

Use `transpose_view()` to create non-contiguous tensors — it copies raw bytes
and overwrites strides with permuted (non-C-order) values, so
`is_contiguous()` returns `False`:

```mojo
# Standard (4,3) non-contiguous tensor
fn make_noncontiguous_4x3() raises -> ExTensor:
    var flat = arange(0.0, 12.0, 1.0, DType.float32)
    var shape: List[Int] = [3, 4]
    var t2d = flat.reshape(shape)
    return transpose_view(t2d)  # shape (4,3), strides [1,4]
```

For `(3,4)` C-order strides are `[4,1]`. After `transpose_view()` to `(4,3)`:
strides become `[1,4]`. Logical element `[r,c] = flat_mem[r + 4c]`.

Row-major traversal of logical `(4,3)`: `[0,4,8, 1,5,9, 2,6,10, 3,7,11]`

For `(3,2)` C-order strides are `[2,1]`. After `transpose_view()` to `(2,3)`:
strides become `[1,2]`. Logical element `[r,c] = flat_mem[r + 2c]`.

Row-major of logical `(2,3)`: `[0,2,4, 1,3,5]`

### Test Structure

Each test follows three steps:

1. Create non-contiguous input with `transpose_view()`
2. Call the shape operation under test
3. Assert every element value matches stride-correct expected output

```mojo
fn test_reshape_noncontiguous_values() raises:
    """Verify reshape() on non-contiguous (4,3) input produces correct flat 1D values.

    Expected: row-major read of logical (4,3) = [0,4,8, 1,5,9, 2,6,10, 3,7,11]
    """
    var t_nc = make_noncontiguous_4x3()
    var new_shape: List[Int] = [12]
    var result = reshape(t_nc, new_shape)

    assert_dim(result, 1, "reshape: result should be 1D")
    assert_numel(result, 12, "reshape: result should have 12 elements")

    var expected: List[Float64] = [0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]
    for i in range(12):
        assert_value_at(result, i, expected[i])
```

### Required Imports

```mojo
from shared.core import (
    ExTensor,
    arange,
    reshape,
    flatten,
    concatenate,
    permute,
    broadcast_to,
    tile,
    repeat,
    transpose_view,
)
from tests.shared.conftest import (
    assert_value_at,
    assert_dim,
    assert_numel,
)
```

### Assertion Helper Signatures

```mojo
# assert_value_at: checks single element at flat index
fn assert_value_at(
    tensor: ExTensor,
    index: Int,
    expected: Float64,
    tolerance: Float64 = TOLERANCE_DEFAULT,
    message: String = "",
) raises

# assert_all_values: checks all elements equal a constant
fn assert_all_values(
    tensor: ExTensor,
    expected: Float64,
    tolerance: Float64 = TOLERANCE_DEFAULT,
    message: String = "",
) raises
```

**Critical**: Passing a `String` as the 3rd positional arg to `assert_value_at` causes a type error
(3rd param is `tolerance: Float64`). Use keyword `message=` or pass only 3 args.

### Expected Values Per Op

For non-contiguous `(4,3)` with strides `[1,4]` (logical `[r,c] = r + 4c`):

| Op | Input | Expected Flat Output |
| ---- | ------- | ---------------------- |
| `reshape([12])` | `(4,3)` nc | `[0,4,8, 1,5,9, 2,6,10, 3,7,11]` |
| `flatten()` | `(4,3)` nc | `[0,4,8, 1,5,9, 2,6,10, 3,7,11]` |
| `permute([1,0])` | `(4,3)` nc | `[0,1,2,3, 4,5,6,7, 8,9,10,11]` (original arange) |
| `concatenate([t,t], 0)` | `(4,3)` nc | 24 elements: two copies of reshape output |
| `broadcast_to([3,4])` | `(3,1)` nc | `[0,0,0,0, 1,1,1,1, 2,2,2,2]` |
| `tile([1,2])` | `(2,3)` nc | `[0,2,4,0,2,4, 1,3,5,1,3,5]` |
| `repeat(2, 0)` | `(2,3)` nc | `[0,2,4,0,2,4, 1,3,5,1,3,5]` |

### Test File Limit

Limit each file to ≤10 `fn test_` functions. With 7 tests this file fits in one
file. If adding more ops, split to `_part2.mojo`.

### Mojo Docstring Rule

Docstring summaries must begin with a capital letter or non-alpha character.

```mojo
# ❌ WRONG - Mojo compiler error
fn test_foo() raises:
    """reshape() on non-contiguous input..."""

# ✅ CORRECT
fn test_foo() raises:
    """Verify reshape() on non-contiguous input..."""
```

## For Contiguous Tensors: Adding Value Assertions

Use this subsection when adding value assertions to existing contiguous shape tests (e.g., `test_shape.mojo`).

### Categorize each test by input type

| Input type | Assertion strategy |
| ------------ | -------------------- |
| `arange(0..N)` input | Loop `assert_value_at(b, i, Float64(i))` for all N elements |
| `ones(shape)` input | `assert_all_values(b, 1.0)` |
| `full(shape, V)` fill | `assert_all_values(b, V)` or spot-check boundary indices |
| Mix of `ones` + `full(2.0)` | Range loop for first block (1.0), range loop for second block (2.0) |

### Add assertions after existing shape checks

```mojo
# BEFORE — shape only
assert_dim(b, 2, "Reshaped tensor should be 2D")
assert_numel(b, 12, "Reshaped tensor should have same number of elements")

# AFTER — shape + values
assert_dim(b, 2, "Reshaped tensor should be 2D")
assert_numel(b, 12, "Reshaped tensor should have same number of elements")
for i in range(12):
    assert_value_at(b, i, Float64(i), message="reshape value at index " + String(i))
```

### Concatenate/stack require split-range assertions

```mojo
# Concatenate axis=0: a=ones(2x3), b=full(3x3, 2.0) → c is 5x3 (15 elements)
# First 6 elements from a, last 9 from b
for i in range(6):
    assert_value_at(c, i, 1.0, message="concat first half at " + String(i))
for i in range(6, 15):
    assert_value_at(c, i, 2.0, message="concat second half at " + String(i))
```

### For axis=1 concatenation, spot-check at row boundaries

```mojo
# Concatenate axis=1: a=ones(3x2), b=full(3x4, 2.0) → c is 3x6
# Row 0: cols 0-1 from a (1.0), cols 2-5 from b (2.0)
assert_value_at(c, 0, 1.0, message="row0 col0 should be 1.0")
assert_value_at(c, 1, 1.0, message="row0 col1 should be 1.0")
assert_value_at(c, 2, 2.0, message="row0 col2 should be 2.0")
assert_value_at(c, 5, 2.0, message="row0 col5 should be 2.0")
```

### Do NOT add value assertions to tests for unimplemented operations

Tests for `tile`, `repeat`, `broadcast_to`, `permute`, and dtype-only checks are left
without value assertions if the operations are not yet implemented — adding assertions
there would produce opaque failures.

### Running the Tests

```bash
just test-group "tests/shared/core" "test_shape_noncontiguous_values.mojo"
```

Expected output when flat-index bugs are present (tests run, values fail):

```text
PASS: broadcast_to() non-contiguous value correctness
FAIL: reshape() FAILED: Expected value 4.0 at index 1, got 1.0 (diff: 3.0)
FAIL: flatten() FAILED: Expected value 4.0 at index 1, got 1.0 (diff: 3.0)
...
```

`broadcast_to` passes because it already uses stride-aware indexing internally.
The other failures are the intended regression signals.

## Results & Parameters

**Test file location**: `tests/shared/core/test_shape_noncontiguous_values.mojo`

**PR**: HomericIntelligence/ProjectOdyssey#4867

**Bugs surfaced**: 6 of 7 ops had flat-index bugs (`reshape`, `flatten`,
`permute`, `concatenate`, `tile`, `repeat`). `broadcast_to` already correct.

**Key config**:

```mojo
# Tolerance for assert_value_at
TOLERANCE_DEFAULT = 1e-6  # from shared/testing/assertions.mojo

# Non-contiguous tensor creation
var flat = arange(0.0, 12.0, 1.0, DType.float32)  # [0..11]
var t2d = flat.reshape([3, 4])
var t_nc = transpose_view(t2d)  # (4,3), strides [1,4]
```

**Contiguous value assertion results** (Issue #3242, PR #3793):

| Parameter | Value |
| ----------- | ------- |
| File changed | `tests/shared/core/test_shape.mojo` |
| Lines added | 31 insertions |
| Test functions with new assertions | 14 |
| Assertion helpers used | `assert_value_at`, `assert_all_values` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pass message as 3rd positional arg to `assert_value_at` | `assert_value_at(result, i, expected[i], "message")` | 3rd param is `tolerance: Float64`, not `String` — type error | Always check assertion function signatures; use `message=` keyword or 3-arg form |
| Start docstring with lowercase function name | `"""reshape() on ...` | Mojo compiler requires docstring to start with capital letter or non-alpha | Capitalize first word: `"""Verify reshape()...` or `"""Test reshape()...` |
| Use `assert_shape` helper | Called `assert_shape(result, expected_shape)` | `assert_shape` takes `(tensor, shape_list)` but validation errors arose | Use explicit shape checks with `result.shape()[0] != N` instead for clarity |
| Running `pixi run mojo test` locally | Executed mojo test command directly | `GLIBC_2.32/2.33/2.34` not found — host system too old | Mojo tests must run in Docker/CI; local environment is incompatible due to glibc version mismatch |
| Adding value assertions to `test_tile_1d` | Attempted `assert_value_at` for tile output on contiguous tests | Operation not yet implemented — would cause opaque CI failures | Only add value assertions for operations known to be implemented |
