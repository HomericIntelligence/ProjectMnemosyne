# Session Notes: mojo-shape-noncontiguous-value-tests

## Session Context

- **Date**: 2026-03-15
- **Issue**: HomericIntelligence/ProjectOdyssey#4086
- **PR**: HomericIntelligence/ProjectOdyssey#4867
- **Follow-up from**: #3391

## Objective

Add value-correctness regression tests for all shape ops in `shape.mojo`
when called on non-contiguous (transposed) tensors. The existing test suite
verified only `is_contiguous()` status and stride shapes, missing element-value
regression that would surface flat-index bugs.

## Steps Taken

1. Read issue #4086 prompt and explored codebase
2. Identified `transpose_view()` in `shared/core/matrix.mojo` as the mechanism
   for creating non-contiguous tensors (copies raw bytes, overwrites strides)
3. Verified `transpose()` returns a contiguous copy (not useful for this test)
4. Calculated expected values for each op manually using stride arithmetic
5. Created `tests/shared/core/test_shape_noncontiguous_values.mojo`
6. Fixed two compile errors: wrong `assert_value_at` arg type, lowercase docstrings
7. Ran tests — all compile and execute; 6/7 ops surface value bugs

## Key Learnings

### transpose_view() vs transpose()

- `transpose()` = produces correctly rearranged **copy** (contiguous, values correct)
- `transpose_view()` = copies raw bytes, **overwrites strides** with permuted values
  → `is_contiguous()` returns `False`, `_get_float64(i)` reads wrong values

### Stride Arithmetic

For input shape `(R, C)` C-order strides `[C, 1]`, after `transpose_view()` to `(C, R)`:
- Strides become `[1, C]`
- Logical `[r, c]` = flat_mem[`r*1 + c*C`] = flat_mem[`r + C*c`]

### assert_value_at Signature

```
fn assert_value_at(tensor, index, expected: Float64, tolerance: Float64, message: String)
```

Passing a String as 3rd positional arg causes a type error. Use 3-arg form or `message=` keyword.

### Mojo Docstring Capitalization

The Mojo compiler enforces that docstring summaries start with a capital letter
or non-alpha character. `"""reshape()...` fails; `"""Verify reshape()...` passes.

### broadcast_to Already Correct

`broadcast_to()` in `shape.mojo` already uses stride-aware indexing internally,
so it passes the non-contiguous value test without any fix needed.

### ADR-009 File Limit

Max 10 `fn test_` per file to avoid heap corruption. 7 tests fit comfortably.

## Files Created

- `tests/shared/core/test_shape_noncontiguous_values.mojo` (in ProjectOdyssey)

## Test Results

```
PASS: broadcast_to() non-contiguous value correctness
FAIL: reshape() FAILED: Expected value 4.0 at index 1, got 1.0
FAIL: flatten() FAILED: Expected value 4.0 at index 1, got 1.0
FAIL: permute() FAILED: Expected value 1.0 at index 1, got 3.0
FAIL: concatenate() FAILED: Expected value 4.0 at index 1, got 1.0
FAIL: tile() FAILED: Expected value 2.0 at index 1, got 1.0
FAIL: repeat() FAILED: Expected value 2.0 at index 1, got 1.0
```

Failures are the intended regression signals — fixes will come in a follow-up PR.
