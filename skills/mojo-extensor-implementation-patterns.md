---
name: mojo-extensor-implementation-patterns
description: "Use when: (1) implementing or fixing utility methods on ExTensor (dunder methods, type conversions, hash, bool, setitem, getitem), (2) fixing silent dtype failures in bfloat16 I/O paths, (3) adding stride-view methods (transpose, permute) to ExTensor, (4) encountering Mojo type errors (Int64 implicit conversion, missing __getitem__ overload), (5) documenting ExTensor view/owner contract or fixing MD060 markdownlint errors"
category: debugging
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---
# Mojo ExTensor Implementation Patterns

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-29 |
| Objective | Consolidate patterns for implementing and fixing ExTensor methods: utility methods, bfloat16 I/O, stride-view methods, type errors, and view/owner contract documentation |
| Outcome | Merged from 7 source skills covering bfloat16 I/O fix, __bool__, method-from-issue (transpose), type errors, utility method implementation, utility methods audit, and view contract documentation |
| Verification | unverified |

## When to Use

- ExTensor bfloat16 tensors return zeros after writes (`_set_float64`/`_get_float64` silent failure)
- Auditing whether all dtypes in `get_test_dtypes()` correctly round-trip through the float64 I/O path
- Adding boolean-context support (`__bool__`) to a Mojo struct with existing `item()`
- Implementing a new method on ExTensor that creates a stride-based view (transpose, permute)
- Tests use standalone function workarounds (e.g., `transpose_view(a)`) and need upgrading to method syntax
- Test fails with `cannot implicitly convert 'Int64' value to 'Float32'`
- Test fails with `no matching method in call to '__getitem__'` for list-indexed assignment
- Adding new `__setitem__` overloads without a matching `__getitem__` overload
- Adding Python/NumPy-compatible dunder methods to a Mojo struct with type-erased storage
- Implementing mutable indexing on a `UnsafePointer[UInt8]` storage type
- Documenting shared-ownership tensor semantics, refcount lifecycle, or view contract
- `markdownlint-cli2` MD060 table-column-style errors in doc files

## Verified Workflow

### Quick Reference

```bash
# Audit what already exists before writing anything
grep -n "fn __setitem__\|fn __int__\|fn __float__\|fn __str__\|fn __repr__\|fn __hash__\|fn contiguous\|fn clone\|fn item\|fn tolist\|fn __len__\|fn diff\|fn is_contiguous\|fn __bool__" shared/core/extensor.mojo

# Locate insertion points
grep -n "fn __int__\|fn __float__\|fn __len__\|fn item\|fn reshape\|fn slice\|fn __getitem__" shared/core/extensor.mojo | head -20

# Check bfloat16 I/O functions
grep -n "_get_dtype_size_static\|_get_float64\|_set_float64" shared/core/extensor.mojo

# Lint documentation
pixi run npx markdownlint-cli2 docs/dev/<file>.md
```

### Part 1: Audit First (Critical Principle)

Before writing a single line, grep for existing implementations. In practice, `clone()`, `item()`, `tolist()`, `__len__`, `diff()`, and `is_contiguous()` were already present when implementing utility methods. Only 7 methods were actually missing.

```bash
grep -n "fn __setitem__\|fn __int__\|fn __float__\|fn __str__\|fn __repr__\|fn __hash__\|fn contiguous\|fn clone\|fn item\|fn tolist\|fn __len__\|fn diff\|fn is_contiguous" shared/core/extensor.mojo
```

The same audit principle applies to free functions — check `shared/tensor/any_tensor.mojo` before implementing NumPy-style wrappers.

### Part 2: Implement Utility Dunder Methods

**`__setitem__` (two overloads)** — place after the last `__getitem__` overload:

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_float64(index, value)

fn __setitem__(mut self, index: Int, value: Int64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_int64(index, value)
```

**`__int__` and `__float__`** — delegate to `item()`:

```mojo
fn __int__(self) raises -> Int:
    return Int(self.item())

fn __float__(self) raises -> Float64:
    return self.item()
```

**`__bool__`** — place after `__len__`, before `__int__`:

```mojo
fn __bool__(self) raises -> Bool:
    """Return boolean value of single-element tensor (True if non-zero)."""
    return self.item() != 0.0
```

**`__str__` and `__repr__`**:

```mojo
fn __str__(self) -> String:
    var s = String("ExTensor([")
    for i in range(self._numel):
        if i > 0:
            s += ", "
        s += String(self._get_float64(i))
    s += "], dtype="
    s += String(self._dtype)
    s += ")"
    return s
```

**`__hash__`** — use `dtype_to_ordinal()` from `shared.core.dtype_ordinal`:

```mojo
fn __hash__(self) -> UInt:
    from shared.core.dtype_ordinal import dtype_to_ordinal
    var h: UInt = 0
    for i in range(len(self._shape)):
        h = h * 31 + UInt(self._shape[i])
    h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
    for i in range(self._numel):
        var val = self._get_float64(i)
        var int_bits = Int(val * 1000000.0)
        h = h * 31 + UInt(int_bits)
    return h
```

**`contiguous()`** — delegate to `clone()`:

```mojo
fn contiguous(self) raises -> ExTensor:
    return self.clone()
```

**`__getitem__` for `List[Int]` indices** — add immediately after `__getitem__(self, index: Int)`:

```mojo
fn __getitem__(self, indices: List[Int]) raises -> Float32:
    """Get element at multi-dimensional index."""
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
    return self._get_float32(flat_idx)
```

**Free function wrapper pattern** (for `any_tensor.mojo`):

```mojo
fn copy(tensor: AnyTensor) raises -> AnyTensor:
    """Create an independent deep copy of the tensor."""
    return tensor.clone()
```

### Part 3: Activate Placeholder Tests for `__bool__`

```mojo
# Before (placeholder):
fn test_bool_single_element() raises:
    # if t_zero:  # Should be False
    pass  # Placeholder

# After (active tests):
fn test_bool_single_element() raises:
    if t_zero:
        raise Error("Zero tensor should be falsy")
    if not t_nonzero:
        raise Error("Non-zero tensor should be truthy")

# Multi-element error test — call Bool(t) directly, not item(t):
fn test_bool_requires_single_element() raises:
    var t = ones(shape, DType.float32)
    var error_raised = False
    try:
        var val = Bool(t)  # Should raise for multi-element
        _ = val
    except e:
        error_raised = True
        var error_msg = String(e)
        if "single" not in error_msg.lower() and "element" not in error_msg.lower():
            raise Error("Error message should mention single-element requirement")
    if not error_raised:
        raise Error("__bool__ on multi-element tensor should raise error")
```

### Part 4: Fix BFloat16 I/O (Silent Write Failures)

Three functions must all have a matching branch for every supported dtype:

| Function | Missing branch symptom |
| ---------- | ---------------------- |
| `_get_dtype_size_static` | Wrong element offsets → corrupted reads/writes beyond index 0 |
| `_set_float64` | Silent no-op → value stays at zero-initialized memory |
| `_get_float64` | Reads bits via wrong path → garbage or zero result |

```mojo
# Fix _get_dtype_size_static (bfloat16 is 2 bytes, same as float16):
if dtype == DType.float16 or dtype == DType.bfloat16:
    return 2

# Fix _get_float64 (use SIMD[DType.bfloat16, 1] — no BFloat16 scalar alias in Mojo):
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[SIMD[DType.bfloat16, 1]]()
    return ptr[].cast[DType.float64]()

# Fix _set_float64:
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[SIMD[DType.bfloat16, 1]]()
    ptr[] = value.cast[DType.bfloat16]()
```

**Zero-guard test** (detects silent write failures):

```mojo
fn test_bfloat16_set_get_float64_roundtrip() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_float64(0, 1.5)
    var got = t._get_float64(0)
    assert_true(got != 0.0, "bfloat16 _get_float64 returned 0 after _set_float64(1.5)")
    assert_almost_equal(got, 1.5, tolerance=1e-2)
```

**Tolerance reference:**

| DType | Recommended tolerance |
| ------- | ---------------------- |
| float64 | 1e-9 |
| float32 | 1e-6 |
| float16 | 1e-3 |
| bfloat16 | 1e-2 |

Note: `1.5` is exactly representable in all float formats — use it for round-trip tests.

`int8` has no `_set_float64` branch — documented silent no-op. TODO: add int8 support with truncation semantics or raise error.

### Part 5: Add Stride-View Methods (transpose, permute)

Insert new method between `slice()` and `__getitem__` — consistent with existing ordering:

```mojo
fn transpose(self, dim0: Int, dim1: Int) raises -> ExTensor:
    """Return a non-contiguous view with dim0 and dim1 swapped."""
    var ndim = self.dim()
    if ndim < 2:
        raise Error("transpose requires at least 2 dimensions")
    if dim0 < 0 or dim0 >= ndim:
        raise Error("transpose: dim0 out of range")
    if dim1 < 0 or dim1 >= ndim:
        raise Error("transpose: dim1 out of range")

    var result = self.copy()
    result._is_view = True

    var tmp_shape = result._shape[dim0]
    result._shape[dim0] = result._shape[dim1]
    result._shape[dim1] = tmp_shape

    var tmp_stride = result._strides[dim0]
    result._strides[dim0] = result._strides[dim1]
    result._strides[dim1] = tmp_stride

    return result^
```

Update tests to use method syntax:

```mojo
# Before (workaround):
var b = transpose_view(a)

# After (proper method):
var b = a.transpose(0, 1)
```

Also remove `transpose_view` from the specific test file's imports (but keep it in `shared.core` exports — other callers use it).

### Part 6: Fix Mojo Type Errors

**Error A** — `cannot implicitly convert 'Int64' value to 'Float32'`:

```mojo
# WRONG — Float64(Int64_val) is not valid in Mojo v0.26.1
fn __setitem__(mut self, index: Int, value: Int64) raises:
    self.__setitem__(index, Float64(value))  # FAILS

# CORRECT — use .cast[DType.float64]()
fn __setitem__(mut self, index: Int, value: Int64) raises:
    self.__setitem__(index, value.cast[DType.float64]())
```

**Error B** — `no matching method in call to '__getitem__'` for `t[[i,j]] = val`:

Mojo decomposes `t[[i, j]] = val` into a `__getitem__` call followed by assignment. If no `__getitem__(List[Int])` overload exists, Mojo reports the error as a missing `__getitem__` even though a `__setitem__(List[Int], ...)` exists. Fix: add the `__getitem__(List[Int])` overload (see Part 2 above).

**Rule**: Whenever you add a `__setitem__` for a new index type, add a matching `__getitem__` too.

### Part 7: Docstring Examples with List[Int] (NOT Deprecated Constructor)

```mojo
# WRONG — triggers check-list-constructor pre-commit hook (scans ALL Mojo including docstrings):
var a = ones(List[Int](3, 4), DType.float32)

# CORRECT — use append() style even in docstring code blocks:
var shape = List[Int]()
shape.append(3)
shape.append(4)
var a = ones(shape, DType.float32)
```

### Part 8: Document ExTensor View/Owner Contract

Three sections to add in `docs/dev/extensor-view-contract.md`:

1. **Refcount Mechanics** — `__copyinit__`/`__del__` lifecycle. Critical subtlety: `_is_view` is a semantic tag only; both views and value-copies participate equally in reference counting.

2. **`view_with_strides()` — Not Available** — document what was proposed, why it was dropped, redirect callers to existing view-returning operations.

3. **When to Call `as_contiguous()`** — the guard pattern:

```mojo
# CORRECT guard pattern
if a.is_contiguous():
    a_cont = a               # zero-copy shared-ownership
else:
    a_cont = as_contiguous(a)  # allocates C-order copy

# ANTI-PATTERN: wrong guard
if a.is_view():              # Wrong — a view can be contiguous
    a_cont = as_contiguous(a)
```

**Fix MD060 table-column-style linting** — pad all columns to the width of the widest cell:

```markdown
# Before (fails MD060):
| Operation | Location | View? |
|-----------|----------|-------|
| `transpose(dim0, dim1)` | `extensor.mojo` | Yes |

# After (passes MD060):
| Operation               | Location         | View? |
|-------------------------|------------------|-------|
| `transpose(dim0, dim1)` | `extensor.mojo`  | Yes   |
```

Also: `#<issue-number>` at line start is parsed as an ATX heading (MD018). Replace with `issue-<number>` or rephrase.

```bash
# Lint markdown after editing (must show "0 error(s)")
pixi run npx markdownlint-cli2 docs/dev/<file>.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Implementing all operations from scratch | Tried to implement every operation in the issue | Most operations (clone, item, diff, __len__, __setitem__, __str__, __repr__, __int__, __float__) already existed | Always grep for existing implementations before writing new code |
| `Float64(Int64_value)` constructor | Pass `Int64` directly to `Float64()` constructor | Mojo v0.26.1 does not support implicit Scalar[int64] → Scalar[float64] conversion | Always use `.cast[DType.float64]()` for Scalar type conversions in Mojo |
| Rely on `__setitem__(List[Int])` for `t[[i,j]] = val` | Assumed having `__setitem__(List[Int], ...)` was sufficient | Mojo decomposes `t[x] = val` into `__getitem__(x)` + assign — both must exist | Whenever you add `__setitem__` for a new index type, add matching `__getitem__` too |
| `Float64.to_bits()` in `__hash__` | Used `val.to_bits()` to get exact IEEE bits | Method does not exist on `Float64` in Mojo v0.26.1 | Use `Int(val * 1000000.0)` as integer approximation |
| `DType._as_i8()` for hash ordinal | Called `self._dtype._as_i8().cast[DType.uint8]()` | Private/nonexistent method on DType | Use `dtype_to_ordinal()` from `shared.core.dtype_ordinal` |
| `Float32` overload for `__setitem__` | Planned both Float32 and Float64 overloads | Redundant — Float64 covers both cases | Use Float64 + Int64 as the two canonical overloads |
| Using `BFloat16` scalar type for bfloat16 pointer | Looking for `BFloat16` alias similar to `Float16`/`Float32`/`Float64` | Mojo stdlib has no `BFloat16` scalar alias | For bfloat16, use `SIMD[DType.bfloat16, 1]` as the pointer target |
| Storing bfloat16 as uint16 | `dtype_cast.mojo` uses `cast_to_bfloat16` storing as `DType.uint16` | This is a conversion helper, not how native `DType.bfloat16` tensors store data | Native `DType.bfloat16` ExTensors use `SIMD[DType.bfloat16, 1]` memory layout |
| Using `--ours` for extensor.mojo when branch adds new methods | Kept HEAD version thinking it already had everything | HEAD was missing `__hash__[H: Hasher]` — the correct trait impl | Always check what new content the branch adds; don't blindly use `--ours` |
| Adding `Hashable` to struct without `Representable` | Took branch struct declaration that dropped `Representable` | Struct missing `Representable` breaks `__repr__` trait satisfaction | Always merge trait lists from both sides during conflict resolution |
| Placing `__bool__` after `__float__` | Considered grouping bool with numeric conversions | Minor ordering issue | Convention: `__bool__` near `__len__` (both "meta" methods), before numeric conversions |
| Docstring with `List[Int](3, 4)` constructor | Used shorthand in docstring example | `check-list-constructor` pre-commit hook scans ALL Mojo source including docstring code blocks | Docstring examples are scanned by pre-commit hooks — always use `append()` style |
| Committed `#3236` at line start in prose | Wrote "during the #3236 development cycle" | MD018: markdownlint treats `#3236` at line start as a malformed ATX heading | Replace `#<N>` at line start with `issue-<N>` or rephrase |
| Compact table style without padding | `\|Op\|Loc\|` without padding spaces | MD060: linter requires "aligned" style — pipes must align with header row | Pad every column to the width of its widest cell |
| Running tests locally | `pixi run mojo test tests/shared/core/test_utility.mojo` | GLIBC version incompatibility on host OS | Tests only run in Docker/CI; validate correctness by code review and pre-commit hooks |

## Results & Parameters

### Methods Added to ExTensor (Reference)

| Method | Signature | Notes |
| -------- | ----------- | ------- |
| `__setitem__` | `(mut self, index: Int, value: Float64) raises` | bounds-checked |
| `__setitem__` | `(mut self, index: Int, value: Int64) raises` | use `.cast[DType.float64]()` not `Float64(val)` |
| `__getitem__` | `(self, indices: List[Int]) raises -> Float32` | required for `t[[i,j]] = val` syntax |
| `__int__` | `(self) raises -> Int` | delegates to `item()` |
| `__float__` | `(self) raises -> Float64` | delegates to `item()` |
| `__bool__` | `(self) raises -> Bool` | delegates to `item() != 0.0` |
| `__str__` | `(self) -> String` | `ExTensor([...], dtype=...)` |
| `__repr__` | `(self) -> String` | includes shape metadata |
| `__hash__` | `(self) -> UInt` | shape + dtype + data; use `dtype_to_ordinal()` |
| `contiguous` | `(self) raises -> ExTensor` | delegates to `clone()` |
| `transpose` | `(self, dim0: Int, dim1: Int) raises -> ExTensor` | stride-swap view |

### Key Import for Hash

```mojo
from shared.core.dtype_ordinal import dtype_to_ordinal
```

### Scalar Type Conversion Pattern

```mojo
# Correct pattern for Scalar[DType.X] -> Scalar[DType.Y]:
value.cast[DType.target_dtype]()

# NOT:
TargetType(source_value)  # Fails for Scalar types in Mojo v0.26.1
```

### Pre-commit Hooks That Apply to Mojo Edits

| Hook | Trigger | Fix |
| ------ | --------- | ----- |
| `mojo format` | Bad formatting | Auto-fixed by hook — re-stage |
| `check-list-constructor` | `List[Int](...)` in ANY source line | Use `append()` style everywhere including docstrings |
| `trailing-whitespace` | Trailing spaces | Auto-fixed — re-stage |
| `end-of-file-fixer` | Missing newline | Auto-fixed — re-stage |

### Stride-view Correctness Reference

After `a = ones([3, 4], DType.float32)`:
- `a._strides` = `[4, 1]`, `a._shape` = `[3, 4]`
- `b = a.transpose(0, 1)` → `b._strides` = `[1, 4]`, `b._shape` = `[4, 3]`
- `b.is_contiguous()` → `False`
- `c = as_contiguous(b)` → `c.is_contiguous()` → `True`, strides `[3, 1]`

### `__getitem__` / `__setitem__` Symmetry Rule

In Mojo v0.26.1, `t[x] = val` requires BOTH:
- `__getitem__(x)` — for read access
- `__setitem__(x, val)` — for write access

Even if you only intend to write, the absence of `__getitem__` causes a compile error.
