---
name: mojo-value-verification-tests
description: 'Add value-correctness assertions to Mojo shape operation tests that
  only verify element counts. Use when: shape tests pass with assert_numel/assert_dim
  but do not check actual output data values.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| Problem | Shape operation tests verify structure (numel, dim) but not correctness of output values |
| Fix | Add `assert_value_at` (per-element) and `assert_all_values` (constant fill) checks |
| Applies To | split, tile, repeat, broadcast_to, permute, and any shape op producing predictable values |
| Helpers | Both helpers are available in `shared.testing.assertions` and re-exported from `tests/shared/conftest` |

## When to Use

1. A test calls `assert_numel` and `assert_dim` but never checks what values are in the tensor
2. Implementing follow-up issue to add value verification to shape operation tests
3. A shape op (tile, repeat, split, broadcast, permute) produces deterministic output from known input
4. You want to distinguish between "result has right shape" and "result has right data"

## Verified Workflow

### Step 1: Identify the expected values from the operation semantics

For each operation, derive expected flat-index values from the input:

| Operation | Input | Expected Output |
| ----------- | ------- | ----------------- |
| `split(a, 3)` where `a=[0..11]` | parts[k] starts at k*4 | `parts[k][j] == k*4 + j` |
| `split_with_indices(a, [3,7])` where `a=[0..9]` | parts are [0..2],[3..6],[7..9] | `parts[0][j]==j`, `parts[1][j]==j+3`, `parts[2][j]==j+7` |
| `tile(a, [3])` where `a=[0,1,2]` | repeats `a` 3 times | `b[rep*3 + j] == j` |
| `tile(ones, [2,3])` | all ones tiled | all values == 1.0 |
| `repeat(a, 2)` where `a=[0,1,2]` | each element repeated | `b[j*2] == b[j*2+1] == j` |
| `repeat(ones, 2, axis=0)` | all ones repeated | all values == 1.0 |
| `broadcast_to(a, [4,3])` where `a=[0,1,2]` | 4 rows of `[0,1,2]` | `b[row*3 + col] == col` |
| `permute(ones, [2,0,1])` | ones tensor permuted | all values == 1.0 |

### Step 2: Choose the right helper

- **`assert_value_at(tensor, index, expected_float64)`** — for per-element sequential checks
- **`assert_all_values(tensor, constant)`** — when all elements should equal one constant value

Both helpers are imported via the conftest re-export and take an optional `message` kwarg.

### Step 3: Add assertions after existing structural checks

```mojo
fn test_tile_1d() raises:
    var a = arange(0.0, 3.0, 1.0, DType.float32)  # [0, 1, 2]
    var reps = List[Int]()
    reps.append(3)
    var b = tile(a, reps)

    # Existing structural checks
    assert_numel(b, 9, "Tiled tensor should have 9 elements")

    # New value checks: [0, 1, 2, 0, 1, 2, 0, 1, 2]
    for rep in range(3):
        for j in range(3):
            assert_value_at(b, rep * 3 + j, Float64(j), message="tile_1d value mismatch")
```

```mojo
fn test_tile_multidim() raises:
    # ... setup ones tensor, tile it ...
    assert_numel(b, 36, "Should have 36 elements")

    # All values remain 1.0 since source is all-ones
    assert_all_values(b, 1.0, message="tile_multidim: all values should be 1.0")
```

### Step 4: For split tests, iterate per-part

```mojo
fn test_split_equal() raises:
    var a = arange(0.0, 12.0, 1.0, DType.float32)
    var parts = split(a, 3)
    # Structural checks...
    for i in range(3):
        assert_numel(parts[i], 4, "Each part should have 4 elements")

    # Value checks: parts[k][j] == k*4 + j
    for j in range(4):
        assert_value_at(parts[0], j, Float64(j),     message="parts[0] value mismatch")
        assert_value_at(parts[1], j, Float64(j + 4), message="parts[1] value mismatch")
        assert_value_at(parts[2], j, Float64(j + 8), message="parts[2] value mismatch")
```

### Step 5: For broadcast_to, use row*cols + col flat indexing

```mojo
fn test_broadcast_to_compatible() raises:
    var a = arange(0.0, 3.0, 1.0, DType.float32)  # (3,)
    var b = broadcast_to(a, [4, 3])                 # (4, 3)
    assert_numel(b, 12, "Should have 12 elements")

    # Each row equals [0, 1, 2]
    for row in range(4):
        for col in range(3):
            assert_value_at(b, row * 3 + col, Float64(col), message="broadcast_to value mismatch")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run tests locally | `pixi run mojo test tests/shared/core/test_shape.mojo` | GLIBC version incompatibility on host (needs Docker) | Verify logical correctness by inspection; CI will run actual tests |
| Use `assert_all_values` for repeat_elements | All elements checked as a constant | repeat_elements produces mixed values [0,0,1,1,2,2] not a constant | Use `assert_value_at` in a loop for non-uniform outputs |
| Checking broadcast by column only | `assert_value_at(b, col, Float64(col))` only checking first row | Only validated row 0; rows 1-3 unchecked | Use nested row/col loop with flat index `row * cols + col` |

## Results & Parameters

### Helper Signatures

```mojo
fn assert_value_at(
    tensor: ExTensor,
    index: Int,           # flat linear index
    expected: Float64,
    tolerance: Float64 = 1e-6,
    message: String = "",
) raises

fn assert_all_values(
    tensor: ExTensor,
    expected: Float64,    # all elements must equal this
    tolerance: Float64 = 1e-6,
    message: String = "",
) raises
```

### Import Path

```mojo
from tests.shared.conftest import (
    assert_value_at,
    assert_all_values,
)
```

Both are re-exported from `shared.testing.assertions`.

### Which Helper to Use

| Scenario | Helper |
| ---------- | -------- |
| Output from `ones` tensor (tile/repeat/permute) | `assert_all_values(b, 1.0)` |
| Output from `arange` tensor (split/tile/repeat_elements) | `assert_value_at` in loop |
| Broadcast of `arange` to 2D | Nested `assert_value_at` with `row * cols + col` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3276 / PR #3845 | [notes.md](../references/notes.md) |
