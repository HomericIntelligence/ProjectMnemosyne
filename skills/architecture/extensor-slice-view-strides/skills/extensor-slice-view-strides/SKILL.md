---
name: extensor-slice-view-strides
description: "Add stride-aware slice() view semantics and _nd_index_to_flat_offset to Mojo ExTensor for zero-copy slicing of non-contiguous tensors. Use when: implementing slice() that must work on transposed/strided views, fixing element access bugs in non-contiguous tensors, or adding a reusable view_with_strides primitive."
category: architecture
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | extensor-slice-view-strides |
| **Category** | architecture |
| **Repo** | HomericIntelligence/ProjectOdyssey |
| **Issue** | #3799 |
| **PR** | #4801 |
| **Branch** | `3799-auto-impl` |
| **Follows** | `extensor-view-semantics` (issue #3236, PR #3794) |

## When to Use

- Implementing `slice()` on `ExTensor` that must correctly handle non-contiguous (transposed/strided) source tensors
- Fixing a bug where `__getitem__`, `_get_float32`, `_get_float64`, `_get_int64` return wrong values on transposed views because they assume contiguous layout
- Adding a `view_with_strides(new_shape, new_strides)` primitive as a shared building block for reshape/slice/transpose view creation
- Adding `_nd_index_to_flat_offset(linear_idx)` to convert a C-order flat index to the correct byte offset for non-contiguous tensors
- Writing tests for `slice() + transpose()` composition where the slice source is already a strided view

## Verified Workflow

### Quick Reference

```mojo
# view_with_strides: zero-copy view with arbitrary shape/strides
var v = tensor.view_with_strides(new_shape, new_strides)
# v._is_view == True, v._data == tensor._data (shared)

# _nd_index_to_flat_offset: byte offset for flat index on any layout
var byte_offset = tensor._nd_index_to_flat_offset(linear_idx)
# Correct for contiguous AND non-contiguous (transposed) tensors
```

### 1. Understand the bug

The root issue in non-contiguous tensor element access is that the internal
`_get_float32` / `_get_float64` / `_get_int64` methods all compute:

```mojo
var offset = index * dtype_size  # WRONG for transposed/strided views
```

After `transpose()`, strides are permuted but the raw data pointer still points to
the original contiguous buffer. The flat-index formula must decode the C-order index
into per-dimension coordinates and then apply the non-contiguous strides.

### 2. Add `_nd_index_to_flat_offset`

Place this method after `is_contiguous()`. It converts a C-order flat index to a
byte offset using per-dimension strides:

```mojo
fn _nd_index_to_flat_offset(self, linear_idx: Int) -> Int:
    var dtype_size = self._get_dtype_size()
    var ndim = len(self._shape)
    var remaining = linear_idx
    var element_offset = 0
    for i in range(ndim - 1, -1, -1):
        var coord = remaining % self._shape[i]
        remaining //= self._shape[i]
        element_offset += coord * self._strides[i]
    return element_offset * dtype_size
```

For a contiguous tensor this gives `linear_idx * dtype_size`. For a transposed
tensor it correctly traverses non-unit strides.

### 3. Add `view_with_strides`

Place this method after `_nd_index_to_flat_offset`. It is the shared primitive for
all zero-copy view creation:

```mojo
fn view_with_strides(
    self, new_shape: List[Int], new_strides: List[Int]
) -> ExTensor:
    var result = self.copy()      # increments refcount
    result._is_view = True
    result._shape = List[Int]()
    for i in range(len(new_shape)):
        result._shape.append(new_shape[i])
    result._strides = List[Int]()
    for i in range(len(new_strides)):
        result._strides.append(new_strides[i])
    var n = 1
    for i in range(len(new_shape)):
        n *= new_shape[i]
    result._numel = n
    return result^
```

This does **not** move the data pointer — callers that need a different base (e.g.
`slice()`) adjust `result._data` after calling this.

### 4. Fix internal element access methods

For each of `_get_float32`, `_set_float32`, `_get_float64`, `_set_float64`,
`_get_int64`, `_set_int64`, replace:

```mojo
var dtype_size = self._get_dtype_size()
var offset = index * dtype_size
```

with:

```mojo
var offset: Int
if self.is_contiguous():
    offset = index * self._get_dtype_size()
else:
    offset = self._nd_index_to_flat_offset(index)
```

The `is_contiguous()` fast-path preserves performance for the common case.

### 5. Refactor `slice()` to use `view_with_strides`

Replace the hand-rolled view construction in `slice()` with:

```mojo
# Build new shape (same as self except axis shrinks)
var new_shape = self._shape.copy()   # REQUIRED: explicit copy, not assignment
new_shape[axis] = end - start

# Strides are unchanged — create view with same strides, new shape
var result = self.view_with_strides(new_shape, self._strides)

# Adjust base pointer to start of slice
var offset_bytes = start * self._strides[axis] * self._get_dtype_size()
result._data = self._data + offset_bytes

return result^
```

**Critical**: `var new_shape = self._shape` fails with "cannot be implicitly
copied" — always use `self._shape.copy()`.

### 6. Write tests (ADR-009 split: ≤10 test functions per file)

**`test_extensor_slicing_view_strides.mojo`** — primitives:

- `view_with_strides` sets `_is_view = True`
- `view_with_strides` applies new shape/strides and recomputes numel
- `view_with_strides` shares `_data` pointer with original
- `_nd_index_to_flat_offset` equals `index * dtype_size` for contiguous tensors
- `_nd_index_to_flat_offset` uses permuted strides for transposed tensors
- `__getitem__` on transposed view returns correct values

**`test_extensor_slicing_view.mojo`** — slice() semantics:

- `slice()` returns `_is_view = True`
- Values are correct via `__getitem__`
- Writes to view propagate to original tensor
- `axis=1` slicing works on 2D tensor
- `axis` out-of-range raises `Error`
- `end > dim_size` raises `Error`
- `slice()` on a transposed source returns correct values

### 7. Docstring rule

Mojo enforces that docstrings begin with a capital letter or non-alpha character.
Test functions named after methods (e.g. `test_view_with_strides_is_view`) must
have docstrings like `"""The view_with_strides method..."""` not
`"""view_with_strides..."""`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `var new_shape = self._shape` | Direct assignment to copy shape for `slice()` | Mojo `List[Int]` is not `ImplicitlyCopyable`; compiler error "value of type 'List[Int]' cannot be implicitly copied" | Always use `.copy()` when assigning a `List[Int]` field to a new variable |
| Docstrings starting with method name | `"""view_with_strides returns..."""` | Mojo compiler error: "doc string summary should begin with a capital letter or non-alpha character" | Prefix with `The`, `A`, `An`, or a non-alpha character |
| Updating only `slice()` without fixing accessor methods | Assumed `view_with_strides` alone was sufficient | Transposed-view slices returned wrong values because `_get_float32`/`_get_int64` still used `index * dtype_size` | Non-contiguous view correctness requires fixing all element accessor methods, not just the view-creation entry point |

## Results & Parameters

### Key APIs added

```mojo
# In shared/core/extensor.mojo — ExTensor struct

fn _nd_index_to_flat_offset(self, linear_idx: Int) -> Int
fn view_with_strides(self, new_shape: List[Int], new_strides: List[Int]) -> ExTensor
```

### Test commands

```bash
just test-group "tests/shared/core" "test_extensor_slicing_view_strides.mojo"
just test-group "tests/shared/core" "test_extensor_slicing_view.mojo"
just test-group "tests/shared/core" "test_extensor_slicing*.mojo"
```

### Pre-existing failures (not introduced)

| Test file | Error | Root cause |
|-----------|-------|------------|
| `test_extensor_slicing_part3.mojo` | `Single slice only supported for 1D tensors` | Pre-existing limitation in `__getitem__(*slices)` |
| `test_slicing_part2.mojo` | `'alias' is deprecated, use 'comptime'` | Pre-existing in `shared/data/__init__.mojo` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3799, PR #4801 | [notes.md](../references/notes.md) |
