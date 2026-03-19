---
name: mojo-tensor-multidim-setitem
description: 'Add multi-dimensional mutable indexing to Mojo ExTensor via List[Int]
  __setitem__ overload. Use when: (1) adding multi-dim write access to a flat-storage
  tensor, (2) converting per-dimension indices to a flat offset via strides, (3) mirroring
  an existing multi-dim __getitem__ with a matching __setitem__.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Mojo Tensor Multi-Dimensional __setitem__

Pattern for adding a `List[Int]` multi-dimensional `__setitem__` overload to a Mojo tensor
struct that stores data in a flat buffer with row-major strides.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-07 | Add `t[[1, 2]] = 5.0` syntax to ExTensor | Implemented via stride-based flat-index delegation, all pre-commit hooks pass |

## When to Use

- Adding multi-dim mutable indexing (`t[[i, j]] = val`) to any Mojo tensor/array struct
- Struct stores elements in a flat `UnsafePointer` buffer with a `_strides: List[Int]` field
- Existing flat `__setitem__(Int, value)` overloads are already present to delegate to
- Want parity with an existing multi-dim `__getitem__` or `*slices: Slice` pattern

## Verified Workflow

1. **Locate existing flat `__setitem__`** — find the overloads that accept `(Int, Float64)`,
   `(Int, Int64)`, `(Int, Float32)`. These already handle bounds checking and dtype dispatch.

2. **Add the overload after the last flat `__setitem__`**, before `__getitem__(Slice)`:

   ```mojo
   fn __setitem__(mut self, indices: List[Int], value: Float64) raises:
       """Set element at multi-dimensional index."""
       if len(indices) != len(self._shape):
           raise Error(
               "Number of indices ("
               + String(len(indices))
               + ") must match tensor rank ("
               + String(len(self._shape))
               + ")"
           )
       var flat_idx = 0
       for i in range(len(indices)):
           if indices[i] < 0 or indices[i] >= self._shape[i]:
               raise Error("Index out of bounds at dimension " + String(i))
           flat_idx += indices[i] * self._strides[i]
       self[flat_idx] = value
   ```

3. **Delegate to `self[flat_idx] = value`** — this calls the flat `(Int, Float64)` overload,
   which already handles all dtype variants (float16/32/64, int types).

4. **Write tests** covering:
   - 2D and 3D tensors (verify stride arithmetic: `[1,2]` on `[3,4]` → flat 6)
   - Float and int dtypes
   - Rank mismatch error (wrong number of indices)
   - Per-dimension out-of-bounds error
   - Negative index error
   - Round-trip: write via multi-dim, read back via flat `__getitem__`
   - Isolation: writing one element doesn't corrupt neighbors

5. **Run pre-commit** — `pixi run pre-commit run --files <changed files>` must pass
   `mojo format`, trailing whitespace, end-of-file-fixer, and check-added-large-files.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3275, PR #3836 | [notes.md](../references/notes.md) |

## Results & Parameters

**Key design decisions**:

- Accept only `Float64` value in the multi-dim overload — the flat `(Int, Float64)` overload
  already dispatches to `_set_float64` or `_set_int64` based on dtype.
- Validate rank before per-dim bounds — cleaner error message for common mistake.
- Use `String(i)` for error messages with dimension index — Mojo requires explicit conversion.
- Place the new overload between the last flat `__setitem__` and the first `__getitem__(Slice)`.

**Test file placement**: `tests/shared/core/test_extensor_setitem.mojo`

**Stride formula** (row-major): `flat_idx = sum(indices[i] * _strides[i] for i in dims)`

Example for `shape=[3,4]`, `strides=[4,1]`, `indices=[1,2]`:
`flat_idx = 1*4 + 2*1 = 6`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Accepting `Float32` value in multi-dim overload | Added separate `(List[Int], Float32)` overload | Redundant — flat `(Int, Float64)` already handles Float32 via dtype dispatch | Delegate to the existing flat overload; only one multi-dim overload needed |
| Trying to run `mojo` locally | `pixi run mojo -I . tests/...` | GLIBC version incompatibility on Debian Buster (requires GLIBC 2.32+, host has 2.31) | Mojo can only run in CI/Docker; verify via pre-commit + code review instead |
| Looking for existing `List[Int]` `__getitem__` to mirror | Expected a `__getitem__(indices: List[Int])` to exist | Not present — multi-dim reads use `*slices: Slice` pattern | Read the actual overloads before assuming symmetry; `__setitem__` can be added independently |
