# Session Notes: noncontiguous-tensor-guard

## Session Context

- **Date**: 2026-03-15
- **Project**: ProjectOdyssey
- **Issue**: #3800 — "Add is_contiguous() guard to all flat-buffer kernels"
- **PR**: #4804
- **Branch**: `3800-auto-impl`
- **Follow-up to**: #3236 (added `as_contiguous()` guard to `matmul()`)

## Objective

Audit all Mojo kernels that use `_data.bitcast[T]()[i]` flat-buffer arithmetic and
add `as_contiguous()` guards. Non-contiguous view inputs (e.g. from `transpose()`)
silently produce wrong results because flat index `i` assumes element `i` is at byte
offset `i * sizeof(T)`.

## Files Modified

### `shared/core/arithmetic.mojo`

Added guard in `_broadcast_binary` (handles add/sub/mul/div via broadcasting):

```mojo
from shared.core.shape import as_contiguous

# In _broadcast_binary():
var a_cont = a if a.is_contiguous() else as_contiguous(a)
var b_cont = b if b.is_contiguous() else as_contiguous(b)
# Use a_cont._data / b_cont._data / a_cont.shape() / b_cont.shape()
```

Also guarded `multiply_scalar`:

```mojo
var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
```

### `shared/core/reduction.mojo`

Added guard in dispatch functions (inner `_reduce_all_impl` / `_reduce_axis_impl` lack `raises`):

```mojo
fn _dispatch_reduce_all(tensor: ExTensor, ...) raises -> ExTensor:
    var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
    return _reduce_all_impl(t, ...)

fn _dispatch_reduce_axis(tensor: ExTensor, ...) raises -> ExTensor:
    var t = tensor if tensor.is_contiguous() else as_contiguous(tensor)
    return _reduce_axis_impl(t, ...)
```

### `shared/core/conv.mojo`

Guarded all 4 public functions: `conv2d`, `conv2d_backward`, `depthwise_conv2d`,
`depthwise_conv2d_backward`. No guard needed for `depthwise_separable_conv2d*` because
they delegate entirely to the already-guarded functions.

## Test Files Created

All pass locally with `just test-group tests/shared/core "test_*_noncontiguous_*.mojo"`.

| File | Tests | Status |
| ------ | ------- | -------- |
| `test_arithmetic_noncontiguous_part1.mojo` | 10 (add/sub/mul/div + contiguous result check) | ✅ |
| `test_arithmetic_noncontiguous_part2.mojo` | 2 (broadcasting, baseline comparison) | ✅ |
| `test_reduction_noncontiguous_part1.mojo` | 6 (sum/mean all/axis0/axis1) | ✅ |
| `test_reduction_noncontiguous_part2.mojo` | 6 (max_reduce/min_reduce all/axis0/axis1) | ✅ |
| `test_conv_noncontiguous_part1.mojo` | 8 (conv2d forward) | ✅ |
| `test_conv_noncontiguous_part2.mojo` | 8 (conv2d_backward) | ✅ |

## Key Debugging Discoveries

### Non-contiguous fixture failure

**Error**: `Unhandled exception caught during execution: input must be non-contiguous`

**Cause**: Tests used `tensor.transpose(0, 1)` on `(1,1,4,4)` tensors where both
swapped dims have size 1. Swapping dims of equal size gives identical strides — the
result is still C-contiguous.

**Fix**: Use non-square spatial dimensions and transpose the spatial (H, W) dims:

```mojo
# Non-square: H=4, W=6
var x = ones([1, 1, 4, 6], DType.float32)
var nc = x.transpose(2, 3)  # shape (1,1,6,4)
# Strides: [24, 24, 1, 6] ≠ C-order [24, 24, 4, 1] → genuinely non-contiguous
```

### Docstring capitalisation error

Mojo requires docstring summaries to begin with a capital letter or non-alpha character.
Fixed by running Python regex over all test files:

```python
import re
content = re.sub(
    r'("""|\'\'\')([a-z])',
    lambda m: m.group(1) + m.group(2).upper(),
    content
)
```

### `raises` propagation constraint

`as_contiguous()` is marked `raises`. Inner kernel functions without `raises` cannot
call it. Solution: place guard in the public dispatcher (which already has `raises`),
pass the contiguous copy to the inner function.

## Commit

```
fix(core): add as_contiguous guard to all flat-buffer kernels

Closes #3800
```

## Reference Pattern (from matrix.mojo matmul, PR #3236)

```mojo
var a_cont = a if a.is_contiguous() else as_contiguous(a)
var b_cont = b if b.is_contiguous() else as_contiguous(b)
# use a_cont._data.bitcast[...]()
```
