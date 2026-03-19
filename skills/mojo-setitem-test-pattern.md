---
name: mojo-setitem-test-pattern
description: 'Skill: mojo-setitem-test-pattern. Use when: adding tests for __setitem__
  on Mojo tensor types, covering Float64/Int64 overloads and out-of-bounds error handling.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Mojo __setitem__ Test Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Issue** | #3165 — Add `__setitem__` tests to `test_utility.mojo` |
| **Objective** | Add three tests for the new `__setitem__` method on `ExTensor`: valid index (Float64), integer dtype (Int64 overload), and out-of-bounds error |
| **Outcome** | ✅ Success — three test functions added, `main()` updated, PR #3385 created with auto-merge enabled |

## When to Use

Use this skill when:

- Adding tests for a new `__setitem__` method on a Mojo tensor/array struct
- The implementation has two overloads: one accepting `Float64` and one accepting `Int64`
- You need to test the out-of-bounds error path without the `raises` keyword (which cannot assert the error was actually raised)
- Following TDD for an indexing setter that may live in a separate feature branch not yet merged

## Verified Workflow

### 1. Locate the __setitem__ implementation

Check if `__setitem__` exists in the current branch or a sibling worktree:

```bash
grep -n "__setitem__" <package>/extensor.mojo
# If not found, check sibling worktrees:
git worktree list
grep -n "__setitem__" <worktree-path>/<package>/extensor.mojo
```

The implementation is the source of truth for:
- Exact error message (e.g. `"Index out of bounds"`)
- Overload signatures (`Float64` and `Int64`)
- Bounds-check behavior (`index < 0 or index >= self._numel`)

### 2. Write the three test functions

Insert after the `__len__` section and before `__bool__` in the test file:

```mojo
# ============================================================================
# Test __setitem__
# ============================================================================


fn test_setitem_valid_index() raises:
    """Test setting value at valid flat index, verified with __getitem__."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.float32)
    t[1] = 9.5
    assert_value_at(t, 1, 9.5, 1e-6, "__setitem__ should set value at index 1")
    # Other elements unchanged
    assert_value_at(t, 0, 0.0, 1e-6, "Element 0 should remain 0.0")
    assert_value_at(t, 2, 0.0, 1e-6, "Element 2 should remain 0.0")


fn test_setitem_integer_dtype() raises:
    """Test setting integer value via Int64 overload on int32 tensor."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.int32)
    t[2] = Int64(7)
    assert_value_at(t, 2, 7.0, 1e-6, "__setitem__ Int64 should set integer value")
    assert_value_at(t, 0, 0.0, 1e-6, "Element 0 should remain 0")


fn test_setitem_out_of_bounds() raises:
    """Test that __setitem__ raises error for out-of-bounds index."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.float32)

    var raised = False
    try:
        t[5] = 1.0
    except:
        raised = True

    if not raised:
        raise Error("__setitem__ should raise error for out-of-bounds index")
```

### 3. Update main() to call the new tests

Add a `# __setitem__` block between `__len__` and `__bool__`:

```mojo
    # __setitem__
    print("  Testing __setitem__...")
    test_setitem_valid_index()
    test_setitem_integer_dtype()
    test_setitem_out_of_bounds()
```

### 4. Verify patterns match the existing file

- Use `assert_value_at` (already imported) for round-trip get-after-set verification
- Use `try/except` + manual `raised` flag (matches `test_item_requires_single_element` pattern)
- Do NOT use the bare `raises` keyword for error tests — it cannot assert the error was raised
- Use `DType.int32` with `Int64(value)` to exercise the integer overload

### 5. Commit and create PR

```bash
git add tests/shared/core/test_utility.mojo
git commit -m "test(utility): add __setitem__ tests to test_utility.mojo

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "test(utility): add __setitem__ tests" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Verifying tests compile locally | Ran `pixi run mojo build tests/shared/core/test_utility.mojo` | GLIBC version mismatch on this host (requires GLIBC_2.32+, host has older version) | Mojo cannot run locally; CI is the verification gate for compilation |
| Checking `__setitem__` in current branch | `grep -n "__setitem__" shared/core/extensor.mojo` returned no matches | `__setitem__` lives in the issue-2722 worktree, not yet merged to main | Always check sibling worktrees when a follow-up issue references a parent issue |

## Results & Parameters

### Test Functions Added

| Test | DType | Overload | Assertion Method |
|------|-------|----------|-----------------|
| `test_setitem_valid_index` | `float32` | `Float64` (implicit) | `assert_value_at` round-trip |
| `test_setitem_integer_dtype` | `int32` | `Int64` explicit | `assert_value_at` with `7.0` |
| `test_setitem_out_of_bounds` | `float32` | `Float64` (implicit) | `try/except` + manual flag |

### Key Parameters

- Tensor size: 3 elements (minimal, avoids timeout)
- Out-of-bounds index: 5 (clearly > 2, the last valid index)
- Float value used: `9.5` (exact in FP32, avoids precision issues)
- Integer value used: `Int64(7)` (small, fits all integer dtypes)
- Tolerance for `assert_value_at`: `1e-6`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3165, PR #3385 | [notes.md](../references/notes.md) |
