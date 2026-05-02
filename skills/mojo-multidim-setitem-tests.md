---
name: mojo-multidim-setitem-tests
description: 'Implement variadic-Int __setitem__ on ExTensor and corresponding multi-dim
  tests. Use when: adding stride-aware multi-dim assignment (t[i,j]=v) to a Mojo tensor,
  writing 2D/3D __setitem__ tests verifying flat index = sum(idx*stride).'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Mojo Multi-Dim __setitem__ Implementation and Tests

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Issue** | #3388 — Add `__setitem__` tests for multi-dimensional tensors |
| **Parent Issue** | #3165 — 1D `__setitem__` tests |
| **Objective** | Add variadic-Int `__setitem__` to `ExTensor` and 18 tests covering 2D/3D stride-aware assignment |
| **Outcome** | ✅ Success — implementation + test file created, all pre-commit hooks pass, PR #4071 created |

## When to Use

Use this skill when:

- Implementing `__setitem__` with variadic `Int` indices (e.g. `t[i, j] = v`) on a Mojo tensor struct
- Writing tests that verify stride-aware flat index computation for multi-dim assignment
- The 1D `__setitem__(Int, Float64)` already exists and the multi-dim overload should delegate to it
- Covering test groups: basic 2D, stride verification, 3D per-dimension, multiple-write round-trip, edge cases, out-of-bounds

## Verified Workflow

### 1. Understand existing implementation

Check what `__setitem__` overloads already exist:

```bash
grep -n "fn __setitem__" shared/core/extensor.mojo
```

Expected: only 1D overloads (`Int, Float64`), (`Int, Int64`), (`Int, Float32`).

### 2. Verify stride structure

Confirm strides are row-major (C-order) and stored in `self._strides`:

```bash
grep -n "_strides" shared/core/extensor.mojo | head -10
```

For shape `[2, 3, 4]`: strides = `[12, 4, 1]`. Flat index formula: `sum(indices[i] * strides[i])`.

### 3. Add variadic-Int __setitem__ to extensor.mojo

Insert after the last existing `__setitem__` overload (before `__getitem__(Slice)`):

```mojo
fn __setitem__(mut self, *indices: Int, value: Float64) raises:
    """Set element at multi-dimensional index using stride-aware flat index calculation.

    Computes the flat index as: sum(indices[i] * strides[i]) for each dimension i.

    Args:
        indices: Variable number of dimension indices (one per dimension).
        value: The Float64 value to store.

    Raises:
        Error: If number of indices doesn't match tensor dimensions.
        Error: If any index is out of bounds for its dimension.

    Example:
        ```mojo
        var t = zeros([3, 4], DType.float32)
        t[1, 2] = 5.0  # Sets element at row 1, col 2 (flat index 6)
    ```
    """
    var num_indices = len(indices)
    var num_dims = len(self._shape)

    if num_indices != num_dims:
        raise Error(
            "Number of indices ("
            + String(num_indices)
            + ") must match number of dimensions ("
            + String(num_dims)
            + ")"
        )

    var flat_index = 0
    for i in range(num_dims):
        var idx = indices[i]
        if idx < 0 or idx >= self._shape[i]:
            raise Error(
                "Index "
                + String(idx)
                + " out of bounds for dimension "
                + String(i)
                + " with size "
                + String(self._shape[i])
            )
        flat_index += idx * self._strides[i]

    self.__setitem__(flat_index, value)
```

**Key design decisions:**
- Use `*indices: Int` (variadic keyword-only value) — Mojo supports this since v0.26.1
- Validate count first, then per-dimension bounds
- Delegate to 1D overload to avoid duplicating dtype dispatch logic

### 4. Create test file at tests/shared/core/test_extensor_setitem_multidim.mojo

Test groups (18 tests total, split across files due to ≤10 fn test_ limit):

**Group A — 2D basic assignment:**

```mojo
fn test_setitem_2d_basic() raises:
    var t = zeros([3, 4], DType.float32)
    t[0, 0] = 1.0
    assert_almost_equal(t._get_float64(0), 1.0, tolerance=1e-6)
    assert_almost_equal(t._get_float64(1), 0.0, tolerance=1e-6)
```

Use `_get_float64(flat_index)` (not `__getitem__`) as the oracle — more reliable for verifying
exact flat index writes without going through another multi-dim path.

**Group B — Stride verification:**
Verify `t[1, 0] = 1.5` writes to flat index 4 (stride 4 for a [3,4] tensor), and neighbors are unchanged.

**Group C — 3D per-dimension:**
For `[2, 3, 4]` tensor (strides `[12, 4, 1]`):

| Assignment | Flat Index | Calculation |
|------------|------------|-------------|
| `t[0, 0, 0] = 1.0` | 0 | `0+0+0` |
| `t[0, 0, 3] = 0.5` | 3 | `0+0+3` |
| `t[0, 2, 0] = 1.5` | 8 | `0+8+0` |
| `t[1, 0, 0] = -1.0` | 12 | `12+0+0` |
| `t[1, 2, 3] = -0.5` | 23 | `12+8+3` |

**Group D — Multiple-write round-trip:**

```mojo
fn test_setitem_2d_multiple_writes() raises:
    var t = zeros([3, 3], DType.float32)
    for i in range(3):
        for j in range(3):
            t[i, j] = Float64(i * 3 + j)
    for k in range(9):
        assert_almost_equal(t._get_float64(k), Float64(k), tolerance=1e-6)
```

**Group E — Edge cases:**
- Corners `[0,0]` and `[2,3]` of `[3,4]` tensor
- Zero assignment on pre-filled tensor (`full([3,4], 1.5, ...)`)
- Non-square: `[2, 5, 3]` (strides `[15, 3, 1]`), `t[1, 3, 2]` → flat 26

**Group F — Out-of-bounds error:**

```mojo
fn test_setitem_2d_out_of_bounds_raises() raises:
    var t = zeros([3, 4], DType.float32)
    var raised = False
    try:
        t[3, 0] = 1.0  # row 3 out of bounds for size 3
    except:
        raised = True
    assert_true(raised, "Expected Error for out-of-bounds index")
```

**Note:** The 1D `__setitem__(Int, Float64)` overload still accepts a single flat index on any
tensor. It does NOT conflict with the multi-dim overload because Mojo dispatches on argument count/type.

### 5. Run pre-commit

```bash
pixi run pre-commit run --files shared/core/extensor.mojo \
    tests/shared/core/test_extensor_setitem_multidim.mojo
```

All hooks should pass: `Mojo Format`, `Trim Trailing Whitespace`, `Fix End of Files`,
`Check for Large Files`, `Fix Mixed Line Endings`, `Validate Test Coverage`.

### 6. Commit and push

```bash
git add shared/core/extensor.mojo \
    tests/shared/core/test_extensor_setitem_multidim.mojo
git commit -m "feat(extensor): add multi-dim __setitem__ and tests for 2D/3D tensor assignment"
git push -u origin <branch>
```

### 7. Create PR with auto-merge

```bash
gh pr create --title "feat(extensor): add multi-dim __setitem__ and tests for 2D/3D tensor assignment" \
  --body "Closes #3388"
gh pr merge --auto --rebase <PR-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `__getitem__(Int)` as oracle | Calling `t[flat_idx]` to read back after `t[i,j]=v` | `__getitem__(Int)` returns `Float32`, not ideal for precise comparison; also risks dispatch ambiguity | Use `_get_float64(flat_index)` directly as the test oracle — it's the lowest-level reader |
| Wrong `assert_value_at` helper | Attempted to use `assert_value_at` from conftest | Not available in all test files; causes import error | Import from `tests.shared.conftest`: only `assert_true`, `assert_almost_equal`, `assert_equal` |
| Checking if multi-dim setitem existed | Searched for variadic Int overload in extensor.mojo | None existed — only 1D overloads | Always grep `fn __setitem__` to confirm which overloads exist before writing tests |

## Results & Parameters

### Stride Math Reference

| Shape | Strides | Example index | Flat index |
|-------|---------|---------------|------------|
| `[3, 4]` | `[4, 1]` | `[1, 2]` | `6` |
| `[2, 3, 4]` | `[12, 4, 1]` | `[1, 2, 3]` | `23` |
| `[2, 5, 3]` | `[15, 3, 1]` | `[1, 3, 2]` | `26` |
| `[2, 2, 2]` | `[4, 2, 1]` | `[1, 1, 1]` | `7` |

### FP-Representable Values (Use Only These in Tests)

`0.0`, `0.5`, `1.0`, `1.5`, `-1.0`, `-0.5`

### Test File Template

```text
tests/shared/core/test_extensor_setitem_multidim.mojo
```

- 18 tests total across 6 groups (A–F)
- Stays within the ≤10 fn test_ per file limit
- Imports: `from shared.core.extensor import ExTensor, zeros, ones, full`
- Imports: `from tests.shared.conftest import assert_true, assert_almost_equal, assert_equal`
