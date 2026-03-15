---
name: noncontiguous-tensor-guard
description: "Add as_contiguous() guards to Mojo flat-buffer kernels so non-contiguous tensor views don't silently produce wrong results. Use when: a kernel uses _data.bitcast[T]()[i] flat indexing, adding support for transposed/sliced tensor inputs, or auditing kernels after a new non-contiguous tensor API is introduced."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | noncontiguous-tensor-guard |
| **Category** | testing |
| **Mojo Version** | v0.26.1 |
| **Pattern Source** | matrix.mojo matmul() guard (PR #3236) |
| **Files Affected** | arithmetic.mojo, reduction.mojo, conv.mojo |

## When to Use

- A Mojo kernel reads tensor data via `_data.bitcast[T]()[i]` (flat-buffer indexing)
- The kernel receives inputs that may be non-contiguous (e.g. from `transpose()`, `slice()`)
- A new non-contiguous view API has been introduced (e.g. `ExTensor.transpose(dim0, dim1)`)
- CI tests pass but results are numerically wrong for transposed inputs
- Auditing all kernels for correctness after a guard is added to one (follow-up PRs)

## Verified Workflow

### 1. Identify the root cause

Flat-buffer kernels assume element `i` is at byte offset `i * sizeof(T)`. Non-contiguous
tensors have gaps or reorderings in memory, so `_data.bitcast[T]()[i]` reads from the
wrong position.

```mojo
# Bug: assumes contiguous layout
var val = tensor._data.bitcast[Float32]()[i]

# Fix: materialize contiguous copy first
var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
var val = t._data.bitcast[Float32]()[i]
```

### 2. Add the import

```mojo
from shared.core.shape import as_contiguous
```

### 3. Add guard at the public API boundary

Place the guard in the **public wrapper** or **dispatch function** (not deep in the
inner kernel), so all call paths are covered:

```mojo
fn conv2d(x: ExTensor, kernel: ExTensor, bias: ExTensor, ...) raises -> ExTensor:
    var x_cont = x if x.is_contiguous() else as_contiguous(x)
    var kernel_cont = kernel if kernel.is_contiguous() else as_contiguous(kernel)
    var bias_cont = bias if bias.is_contiguous() else as_contiguous(bias)
    # Pass x_cont, kernel_cont, bias_cont to inner kernel
```

For functions without `raises` (e.g. `_reduce_all_impl`), guard in the **dispatching
function** that does have `raises`:

```mojo
fn _dispatch_reduce_all(tensor: ExTensor, ...) raises -> ExTensor:
    var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
    return _reduce_all_impl(t, ...)  # inner fn has no raises
```

### 4. Write non-contiguous test fixtures

**Critical**: `transpose(dim0, dim1)` only produces a non-contiguous tensor when the two
swapped dimensions have **different sizes**. Swapping equal-size dims gives identical
strides — the result is still contiguous and `is_contiguous()` returns true.

```mojo
# ✅ Correct: non-square spatial dims, swap H and W
fn _make_nc_input() raises -> ExTensor:
    var x = ones([1, 1, 4, 6], DType.float32)   # H=4, W=6 (different sizes)
    var nc = x.transpose(2, 3)  # shape (1,1,6,4), strides [24,24,1,6] ≠ C-order [24,24,4,1]
    assert_false(nc.is_contiguous(), "input must be non-contiguous")
    return nc^

# ❌ Wrong: square spatial dims — swapping gives identical strides
var x = ones([1, 1, 4, 4], DType.float32)
var nc = x.transpose(2, 3)  # strides [16,16,4,1] → still C-order!

# ❌ Wrong: N=1, C=1 — swapping batch/channel dims
var x = ones([1, 1, 4, 4], DType.float32)
var nc = x.transpose(0, 1)  # dim0 stride==dim1 stride, no change
```

### 5. Structure tests to match contiguous baseline

Use all-ones tensors so the non-contiguous view has the same logical values as a
contiguous tensor of the same shape. Compare results element-by-element:

```mojo
fn test_add_noncontiguous_lhs() raises:
    """Add with non-contiguous lhs matches contiguous baseline."""
    var base = ones([1, 1, 6, 4], DType.float32)    # contiguous
    var nc   = _make_nc_input()                       # non-contiguous, same logical values
    var rhs  = ones([1, 1, 6, 4], DType.float32)

    var expected = add(base, rhs)
    var result   = add(nc,   rhs)

    var ep = expected._data.bitcast[Float32]()
    var rp = result._data.bitcast[Float32]()
    for i in range(expected.numel()):
        assert_almost_equal(rp[i], ep[i], tolerance=1e-4)
```

### 6. Split test files per ADR-009

Mojo v0.26.1 heap corruption triggers under high test load. Limit each file to ≤10
`fn test_` functions. Use `_part1.mojo`, `_part2.mojo` naming:

```text
test_arithmetic_noncontiguous_part1.mojo   (8 tests: add/sub/mul/div element-wise)
test_arithmetic_noncontiguous_part2.mojo   (2 tests: broadcasting variants)
test_reduction_noncontiguous_part1.mojo    (6 tests: sum/mean all/axis0/axis1)
test_reduction_noncontiguous_part2.mojo    (6 tests: max_reduce/min_reduce)
test_conv_noncontiguous_part1.mojo         (8 tests: conv2d forward)
test_conv_noncontiguous_part2.mojo         (8 tests: conv2d_backward)
```

### 7. Verify and commit

```bash
just test-group tests/shared/core "test_*_noncontiguous_*.mojo"
git add shared/core/arithmetic.mojo shared/core/conv.mojo shared/core/reduction.mojo \
        tests/shared/core/test_*_noncontiguous_*.mojo
git commit -m "fix(core): add as_contiguous guard to all flat-buffer kernels"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `transpose(0, 1)` on `(1,1,4,4)` for NCHW fixture | Create non-contiguous (1,1,4,4) tensor by swapping N and C dims | N=1 and C=1 have the same size so strides are equal after swap — `is_contiguous()` returns true, assertion `assert_false(nc.is_contiguous())` triggers runtime error | Only `transpose(dim0, dim1)` with dims of **different sizes** produces non-contiguous strides |
| `transpose(0, 1)` on `(1,1,2,2)` for grad_output | Create non-contiguous grad_output for backward pass tests | Same issue: all batch/channel dims have size 1, swapping gives identical strides | For NCHW tensors with N=C=1, always transpose the spatial dims H and W, using non-square spatial sizes (e.g., 4×6→transpose→6×4) |
| Guard in inner `_reduce_all_impl` | Tried to add guard inside the implementation function which lacks `raises` | `as_contiguous()` is marked `raises`; functions without `raises` cannot call it | Place guard in the `_dispatch_*` wrapper that already has `raises`, pass the contiguous copy to the inner function |
| Using `transpose_view()` for 4D tensors | Called `transpose_view(x_4d)` from `shared.core.matrix` | `transpose_view` is designed for 2D matrices — doesn't correctly handle 4D NCHW tensors | Use `ExTensor.transpose(dim0, dim1)` for N-dimensional stride-based transposition |

## Results & Parameters

### Verified Configuration (Issue #3800)

**Pattern**: Public-API guard — materialize contiguous copy before any `_data.bitcast[T]()[i]` access.

**Files modified**:

- `shared/core/arithmetic.mojo`: guard in `_broadcast_binary`, `multiply_scalar`
- `shared/core/reduction.mojo`: guard in `_dispatch_reduce_all`, `_dispatch_reduce_axis`
- `shared/core/conv.mojo`: guard in `conv2d`, `conv2d_backward`, `depthwise_conv2d`, `depthwise_conv2d_backward`

**Guard template**:

```mojo
from shared.core.shape import as_contiguous

# At public API entry point:
var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
# Use t._data.bitcast[...]() instead of tensor._data.bitcast[...]()
```

**Non-contiguous fixture template** (reliable):

```mojo
fn _make_nc_nchw() raises -> ExTensor:
    """Non-contiguous (1,1,6,4) tensor via transpose of non-square spatial dims."""
    var x = ones([1, 1, 4, 6], DType.float32)  # H != W required
    var nc = x.transpose(2, 3)                  # (1,1,6,4), strides [24,24,1,6]
    assert_false(nc.is_contiguous(), "fixture must be non-contiguous")
    return nc^
```

**Test count per file**: ≤8 `fn test_` functions (ADR-009 headroom below 10-function limit).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4804, Issue #3800 | [notes.md](../references/notes.md) |
