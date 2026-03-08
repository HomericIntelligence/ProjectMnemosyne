---
name: mojo-extensor-method-from-issue
description: "Pattern for adding stride-view methods to ExTensor and migrating tests from standalone-function workarounds to method-syntax. Use when: implementing ExTensor methods that replace workarounds, updating tests with stride-mutation hacks, or encountering deprecated List syntax in docstring examples."
category: tooling
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Issue** | #3390 - Implement transpose() to replace stride-mutation workaround |
| **PR** | #4078 |
| **Branch** | `3390-auto-impl` |
| **Files Changed** | `shared/core/extensor.mojo`, `tests/shared/core/test_utility.mojo` |
| **Result** | Success — pre-commit passed, PR created |

## When to Use

- Implementing a new method on `ExTensor` that creates a stride-based view (transpose, permute, etc.)
- Removing standalone function workarounds in favor of proper method-syntax on `ExTensor`
- Tests use `transpose_view(a)` or direct `_strides` mutation and need upgrading to `a.transpose(0, 1)`
- Adding docstring examples to Mojo methods with `List[Int]` construction

## Verified Workflow

### 1. Locate insertion point after `slice()`

```bash
grep -n "fn reshape\|fn slice\|fn __getitem__" shared/core/extensor.mojo
```

Insert new method between `slice()` and `__getitem__` — consistent with existing ordering.

### 2. Implement stride-view method pattern

```mojo
fn transpose(self, dim0: Int, dim1: Int) raises -> ExTensor:
    """Return a non-contiguous view with dim0 and dim1 swapped.
    ...
    """
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

### 3. Write docstring examples with List[Int] literals (NOT deprecated constructor)

**WRONG** (triggers pre-commit check-list-constructor hook):
```mojo
var a = ones(List[Int](3, 4), DType.float32)
```

**CORRECT**:
```mojo
var shape = List[Int]()
shape.append(3)
shape.append(4)
var a = ones(shape, DType.float32)
```

### 4. Update tests — remove standalone function import, use method syntax

In test imports: remove `transpose_view` from `from shared.core import (...)`

In test bodies:
```mojo
# Before (workaround):
var b = transpose_view(a)

# After (proper method):
var b = a.transpose(0, 1)
```

### 5. Commit — pre-commit will catch issues automatically

```bash
git add shared/core/extensor.mojo tests/shared/core/test_utility.mojo
git commit -m "feat(extensor): add ExTensor.transpose(dim0, dim1) ..."
```

If `check-list-constructor` hook fails: fix docstring examples to use `append()` style.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Docstring with `List[Int](3, 4)` constructor | Used shorthand in docstring example: `var a = ones(List[Int](3, 4), DType.float32)` | `check-list-constructor` pre-commit hook scans ALL Mojo source including docstring code blocks and rejects deprecated constructor syntax | Docstring examples are scanned by pre-commit hooks — always use `append()` style even in code block examples |

## Results & Parameters

### Stride-view method correctness

After `a = ones([3, 4], DType.float32)`:
- `a._strides` = `[4, 1]`, `a._shape` = `[3, 4]`
- `b = a.transpose(0, 1)` → `b._strides` = `[1, 4]`, `b._shape` = `[4, 3]`
- `b.is_contiguous()` → `False` (stride[0]=1 ≠ expected 3)
- `c = as_contiguous(b)` → `c.is_contiguous()` → `True`, strides `[3, 1]`

### Key implementation notes

- Use `self.copy()` then set `result._is_view = True` — same pattern as `slice()`
- Return with `result^` (ownership transfer)
- The `transpose_view()` standalone function in `matrix.mojo` handles arbitrary permutations via `Optional[List[Int]]`; the new method handles the common 2-axis case with cleaner syntax
- `transpose_view` remains in `shared.core` exports — it is used by other callers; only remove the import from the specific test file

### Pre-commit hooks that apply to Mojo edits

| Hook | Trigger | Fix |
|------|---------|-----|
| `mojo format` | Bad formatting | Auto-fixed by hook — re-stage |
| `check-list-constructor` | `List[Int](...)` in ANY source line | Use `append()` style everywhere including docstrings |
| `trailing-whitespace` | Trailing spaces | Auto-fixed — re-stage |
| `end-of-file-fixer` | Missing newline | Auto-fixed — re-stage |
