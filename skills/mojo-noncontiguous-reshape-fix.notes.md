# Session Notes: mojo-noncontiguous-reshape-fix

## Session Date: 2026-03-15

## Issue

GitHub issue #4084: `reshape()` in `shared/core/shape.mojo` called `_get_float64(i)` on the
source tensor without checking contiguity, producing wrong element order for non-contiguous
(transposed, sliced) tensors.

## Root Cause

`_get_float64(i)` computes `offset = i * dtype_size` — a flat byte offset. This is only
correct when `_strides` matches C-order (row-major). After a transpose, strides no longer
follow C-order, so flat indexing reads elements in the wrong order.

## Fix

Added `is_contiguous()` branch in `reshape()`:
- **Contiguous**: existing flat `_get_float64(i)` loop (unchanged)
- **Non-contiguous**: stride-based byte copy loop — converts flat output index `i` to
  multi-dim coords, computes `src_elem_offset = sum(coord[d] * strides[d])`, then copies
  `dtype_size` raw bytes from `src_ptr[src_elem_offset * dtype_size]` to `dst_ptr[i * dtype_size]`

The pattern was already implemented in `as_contiguous()` in the same file.

## Test Design

Plan suggested strides `(1,3)` on shape `(3,4)` expecting `[0,4,8,...]`.
Actual computation gave `[0,3,6,9,...]`.

Correct approach: simulate `transpose()` by setting shape `(4,3)` and strides `(1,4)`.
Verified manually:
- stride formula: `row*1 + col*4` on data `[0..11]`
- coords (0,0)→0, (0,1)→4, (0,2)→8, (1,0)→1, ... → `[0,4,8,1,5,9,2,6,10,3,7,11]`

## Mojo 0.26.1 Gotchas

- No variadic `List` constructor: `List[Float64](0,4,8,...)` fails
- Use literal syntax: `var x: List[Float64] = [0, 4, 8, ...]`
- `mojo test` subcommand does not exist in 0.26.1; use `mojo build ... && ./binary`
- `_get_float64_at_byte_offset()` does not exist — use `_data` pointer directly

## PR

- Branch: `4084-auto-impl`
- PR: #4866
- Closes: #4084
