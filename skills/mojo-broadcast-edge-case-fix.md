---
name: mojo-broadcast-edge-case-fix
description: 'Fix and test broadcast_to edge cases in Mojo tensor libraries. Use when:
  broadcast_to incorrectly accepts incompatible target shapes, adding 0-d scalar/identity/multi-axis
  tests, or validating ndim-reduction rejection.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Skill Name** | mojo-broadcast-edge-case-fix |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | Shape operation correctness + edge-case test coverage |
| **Resolution** | Add explicit ndim guard before are_shapes_broadcastable; add 6 edge-case tests |

## When to Use

- `broadcast_to(tensor_2d, target_0d)` succeeds when it should raise (vacuous loop bug)
- Need to add edge-case tests required by the Python Array API Standard for `broadcast_to`
- A `broadcast_to` implementation only tests the "compatible shape" happy path
- `are_shapes_broadcastable(shape, [])` returns `True` because the loop body never executes
- Broadcasting a `(3, 4)` tensor to a 1-D target `[4]` silently succeeds (ndim reduction bug)

## Verified Workflow

### Step 1: Identify the vacuous loop bug

`are_shapes_broadcastable` iterates `range(max(ndim1, ndim2))`.
When `target_shape` is empty (`[]`), `max_ndim = ndim1`, but the per-iteration check
computes `dim2_idx = ndim2 - 1 - i = -1 - i < 0`, which triggers the `else 1` branch —
making every dimension comparison `dim1 vs 1`, which always passes if `dim1` is anything.

The function returns `True` vacuously — **the fix must be in the caller**, not the helper.

### Step 2: Add the ndim guard in broadcast_to

```mojo
var shape = tensor.shape()

# Cannot reduce number of dimensions (target must have >= dims than source)
if len(target_shape) < len(shape):
    raise Error("broadcast_to: cannot broadcast to fewer dimensions")

# Check if broadcast is valid
if not are_shapes_broadcastable(shape, target_shape):
    raise Error("broadcast_to: shapes are not broadcast-compatible")
```

Place the guard **before** calling `are_shapes_broadcastable`. This covers both:
- 0-d target (empty `target_shape`) with non-scalar source
- Any `len(target_shape) < len(shape)` reduction

### Step 3: Add 6 edge-case tests

All test functions follow the existing pattern in `test_shape.mojo`:

```mojo
fn test_broadcast_to_0d_scalar() raises:
    """Test broadcasting a 0-d scalar tensor to any shape."""
    var shape_0d = List[Int]()
    var a = full(shape_0d, 5.0, DType.float32)  # 0-d scalar, value=5.0
    var target_shape = List[Int]()
    target_shape.append(3)
    target_shape.append(4)
    var b = broadcast_to(a, target_shape)

    assert_dim(b, 2, "Broadcasted 0-d tensor should be 2D")
    assert_numel(b, 12, "Broadcasted 0-d tensor should have 12 elements")
    assert_all_values(b, 5.0, 1e-6, "All values should be 5.0")


fn test_broadcast_to_identity() raises:
    """Test broadcasting a tensor to its own shape (identity broadcast)."""
    var shape = List[Int]()
    shape.append(3)
    shape.append(4)
    var a = arange(0.0, 12.0, 1.0, DType.float32)
    var reshaped = reshape(a, shape)
    var b = broadcast_to(reshaped, shape)

    assert_dim(b, 2, "Identity broadcast should preserve ndim")
    assert_numel(b, 12, "Identity broadcast should preserve numel")
    for i in range(12):
        assert_value_at(b, i, Float64(i), 1e-6, "Identity broadcast should preserve values")


fn test_broadcast_to_multi_axis() raises:
    """Test multi-axis broadcasting: (3,) -> (2, 4, 3)."""
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var target_shape = List[Int]()
    target_shape.append(2)
    target_shape.append(4)
    target_shape.append(3)
    var b = broadcast_to(a, target_shape)

    assert_dim(b, 3, "Broadcasted tensor should be 3D")
    assert_numel(b, 24, "Should have 24 elements (2*4*3)")
    for i in range(24):
        assert_value_at(b, i, Float64(i % 3), 1e-6, "Values should repeat row pattern")


fn test_broadcast_to_leading_dims() raises:
    """Test broadcasting with added leading dimensions: (1, 3) -> (5, 3)."""
    var shape = List[Int]()
    shape.append(1)
    shape.append(3)
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var a_2d = reshape(a, shape)
    var target_shape = List[Int]()
    target_shape.append(5)
    target_shape.append(3)
    var b = broadcast_to(a_2d, target_shape)

    assert_dim(b, 2, "Should be 2D")
    assert_numel(b, 15, "Should have 15 elements (5*3)")
    for row in range(5):
        for col in range(3):
            assert_value_at(b, row * 3 + col, Float64(col), 1e-6, "Values should repeat per row")


fn test_broadcast_to_middle_dim_expand() raises:
    """Test broadcasting middle dimension: (1, 3, 1) -> (5, 3, 7)."""
    var shape = List[Int]()
    shape.append(1)
    shape.append(3)
    shape.append(1)
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var a_3d = reshape(a, shape)
    var target_shape = List[Int]()
    target_shape.append(5)
    target_shape.append(3)
    target_shape.append(7)
    var b = broadcast_to(a_3d, target_shape)

    assert_dim(b, 3, "Should be 3D")
    assert_numel(b, 105, "Should have 105 elements (5*3*7)")
    for i in range(5):
        for j in range(3):
            for k in range(7):
                assert_value_at(b, i * 21 + j * 7 + k, Float64(j), 1e-6,
                    "Value should equal middle dim index")


fn test_broadcast_to_reduce_ndim_raises() raises:
    """Test that broadcasting to fewer dimensions raises an error."""
    var shape = List[Int]()
    shape.append(3)
    shape.append(4)
    var a = ones(shape, DType.float32)
    var target_shape = List[Int]()
    target_shape.append(4)  # Only 1D — cannot reduce from 2D

    var error_raised = False
    try:
        var b = broadcast_to(a, target_shape)
        _ = b
    except e:
        error_raised = True
        if "broadcast" not in String(e).lower():
            raise Error("Error message should mention broadcast")

    if not error_raised:
        raise Error("broadcast_to with fewer dimensions should raise error")
```

### Step 4: Register tests in main()

```mojo
# broadcast_to() tests
print("  Testing broadcast_to()...")
test_broadcast_to_compatible()
test_broadcast_to_incompatible()
test_broadcast_to_0d_scalar()
test_broadcast_to_identity()
test_broadcast_to_multi_axis()
test_broadcast_to_leading_dims()
test_broadcast_to_middle_dim_expand()
test_broadcast_to_reduce_ndim_raises()
```

### Step 5: Commit (pre-commit passes without SKIP)

All hooks pass without `SKIP=` because the fix is pure Mojo source (no format violation).
The GLIBC mismatch on the host is irrelevant — mojo format runs fine, tests run in CI.

```bash
git add shared/core/shape.mojo tests/shared/core/test_shape.mojo
git commit -m "fix(shape): add dimension guard and edge-case tests for broadcast_to"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fix in are_shapes_broadcastable | Add early-return for empty target_shape inside the helper | Would require changing helper signature/behavior used by other callers | Fix belongs in the caller (broadcast_to), not the shared helper |
| Using SKIP=mojo-format | Considered skipping pre-commit due to GLIBC | Not needed — mojo format pre-commit hook runs the binary locally but succeeded | Only use SKIP when a hook is genuinely broken; try without first |
| full(shape_0d, Float32(5.0), ...) | Passed Float32 as fill_value to full() | full() signature takes Float64, causing type mismatch at compile time | Use literal 5.0 (Float64) or check function signature before writing tests |

## Results & Parameters

### Imports needed in test file

```mojo
from shared.core import (
    ExTensor, zeros, ones, full, arange, reshape, broadcast_to,
)
from tests.shared.conftest import (
    assert_dim, assert_numel, assert_value_at, assert_all_values,
)
```

### ExTensor 0-d tensor behavior

- `ExTensor([], dtype)` has `_numel = 1` (product of empty list = 1)
- `full([], 5.0, DType.float32)` creates a single-element 0-d scalar tensor
- `broadcast_to(scalar_0d, [M, N])` materializes M*N copies of the scalar value

### Value pattern for multi-axis broadcast

When broadcasting shape `(K,)` → `(A, B, K)`:
- Flat index `i` maps to value `i % K`
- This holds for any number of leading broadcast dimensions

### Middle dim expansion pattern

When broadcasting `(1, K, 1)` → `(A, K, B)`:
- Flat index `i * (K*B) + j * B + k` has value `j` (the middle dim index)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3279, PR #3857 | [notes.md](../references/notes.md) |
