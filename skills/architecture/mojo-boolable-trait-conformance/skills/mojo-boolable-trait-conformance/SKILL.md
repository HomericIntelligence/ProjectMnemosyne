---
name: mojo-boolable-trait-conformance
description: "Split a raising __bool__ into a non-raising Boolable-conformant __bool__ plus bool_strict(). Use when: a struct has fn __bool__(self) raises -> Bool preventing Boolable trait conformance, you want Bool(t) syntax to work without try/except, or you need NumPy-style silent False for multi-element containers alongside PyTorch-style strict raising."
category: architecture
date: 2026-03-15
user-invocable: false
---

# Skill: Mojo Boolable Trait Conformance via `__bool__` / `bool_strict()` Split

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Objective** | Add `Boolable` trait conformance to `ExTensor` by splitting the raising `__bool__` into a non-raising version and a new `bool_strict()` method |
| **Outcome** | `Bool(t)` syntax enabled; NumPy-style multi-element False behavior added; existing raising semantics preserved via `bool_strict()`; PR #4869 created |
| **PRs** | [#4869](https://github.com/HomericIntelligence/ProjectOdyssey/pull/4869) |
| **Issue** | [#4091](https://github.com/HomericIntelligence/ProjectOdyssey/issues/4091) |

## Overview

When a Mojo struct defines `fn __bool__(self) raises -> Bool`, it **cannot** conform to the
`Boolable` trait because `Boolable` requires a non-raising signature. This is a common
stumbling block when adding Python/NumPy/PyTorch compatibility to Mojo ML structs.

The fix is a two-method split:

- **`fn __bool__(self) -> Bool`**: Non-raising, adds `Boolable` to trait list, returns `False`
  for multi-element tensors (NumPy behavior). Enables `Bool(t)` and `if t:` syntax everywhere.
- **`fn bool_strict(self) raises -> Bool`**: Raising variant for PyTorch-style strict behavior
  where multi-element boolean conversion is an error.

The key insight is choosing the **NumPy semantics** for the non-raising path: multi-element
tensors return `False` silently rather than raising. This is the least surprising behavior
for users of the `Boolable` trait.

## When to Use

1. A struct has `fn __bool__(self) raises -> Bool` and you want `Boolable` trait conformance
2. You want `Bool(t)` syntax without wrapping every call in `try/except`
3. You need to support both "lenient" (NumPy) and "strict" (PyTorch) boolean conversion
4. CI/code review feedback mentions "`__bool__` with `raises` prevents Boolable conformance"
5. Tests use `t.__bool__()` directly because `Bool(t)` wasn't yet available (workaround #4089
   pattern)

## Verified Workflow

### Quick Reference

| Step | Action | Key Point |
|------|--------|-----------|
| 1 | Add `Boolable` to struct trait list | Before `Copyable`, alphabetical order |
| 2 | Replace raising `__bool__` | Non-raising, `_numel != 1` check returns `False` |
| 3 | Add `bool_strict()` method | Delegates to `item()` just like old `__bool__` |
| 4 | Update tests calling `t.__bool__()` | Change to `t.bool_strict()` for raising tests |
| 5 | Add `test_bool_multi_element_non_raising` | Verify `Bool(multi_tensor)` returns `False` |

### Step 1: Add `Boolable` to the struct trait list

```mojo
struct ExTensor(
    Boolable,       # ADD THIS — alphabetical position
    Copyable,
    Hashable,
    ImplicitlyCopyable,
    Movable,
    Representable,
    Sized,
    Stringable,
):
```

### Step 2: Replace the raising `__bool__` with a non-raising version

**Before**:

```mojo
fn __bool__(self) raises -> Bool:
    """..."""
    return self.item() != 0.0
```

**After**:

```mojo
fn __bool__(self) -> Bool:
    """Return the boolean value of a tensor (Boolable trait conformance).

    Follows NumPy behavior: returns False for multi-element tensors,
    and the actual boolean value for single-element tensors. This
    non-raising signature is required for Boolable trait conformance,
    enabling `Bool(t)` syntax and use in boolean contexts.

    For strict PyTorch-style behavior that raises on multi-element
    tensors, use `bool_strict()` instead.

    Returns:
        True if the single element is non-zero, False for zero or
        multi-element tensors.
    """
    if self._numel != 1:
        return False
    return self._get_float64(0) != 0.0
```

**Important**: Do NOT delegate to `self.item()` in `__bool__` — `item()` raises for
multi-element tensors. Access the underlying value directly or guard with the `_numel` check.

### Step 3: Add `bool_strict()` for raising behavior

```mojo
fn bool_strict(self) raises -> Bool:
    """Return the boolean value of a single-element tensor (strict variant).

    Follows PyTorch convention: raises for multi-element tensors.
    Use this when you want an error for accidental multi-element
    boolean conversion, rather than the NumPy-style silent False.

    Returns:
        True if the single element is non-zero, False otherwise.

    Raises:
        Error: If tensor has more than one element.
    """
    return self.item() != 0.0
```

`bool_strict()` can safely delegate to `item()` since it's allowed to raise.

### Step 4: Update existing tests that call `t.__bool__()`

Tests that expected `__bool__()` to raise must now call `bool_strict()`:

```mojo
# BEFORE (old raising __bool__)
var val = t.__bool__()  # Should raise error for multi-element tensor

# AFTER (new API)
var val = t.bool_strict()  # Should raise error for multi-element tensor
```

Also update the test docstring and error message to reference `bool_strict()`.

### Step 5: Add a test for non-raising multi-element behavior

```mojo
fn test_bool_multi_element_non_raising() raises:
    """Test that __bool__ returns False (not raises) for multi-element tensor."""
    var shape = List[Int]()
    shape.append(5)
    var t = ones(shape, DType.float32)

    # __bool__ must not raise — Boolable conformance requires non-raising
    var result = Bool(t)
    if result:
        raise Error("Bool(multi-element tensor) should return False")

    # Also verify zero multi-element tensor
    var t_zero = zeros(shape, DType.float32)
    if Bool(t_zero):
        raise Error("Bool(zero multi-element tensor) should return False")
```

Register this test in the runner alongside the existing `__bool__` tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Delegating `__bool__` to `item()` | `fn __bool__(self) -> Bool { return self.item() != 0.0 }` | `item()` raises for multi-element tensors; non-raising `__bool__` cannot call a raising function without try/except | Access `_numel` and the underlying buffer directly in `__bool__`; delegate to `item()` only in `bool_strict()` |
| Using `Bool(t)` in old test | Tried calling `Bool(t)` in the raising test before implementing non-raising `__bool__` | `Bool(t)` would not raise once `__bool__` was non-raising | After the split, the raising test must call `bool_strict()` explicitly |

## Results & Parameters

**Files modified**: 3

| File | Change |
|------|--------|
| `shared/core/extensor.mojo` | Added `Boolable` to trait list, replaced `__bool__`, added `bool_strict()` (+37/-7 lines net) |
| `tests/shared/core/test_utility.mojo` | Updated raising test to use `bool_strict()`, added `test_bool_multi_element_non_raising` |
| `tests/shared/core/test_utility_part3.mojo` | Updated raising test to use `bool_strict()` |

**Minimal implementation** (copy-paste ready):

```mojo
fn __bool__(self) -> Bool:
    if self._numel != 1:
        return False
    return self._get_float64(0) != 0.0

fn bool_strict(self) raises -> Bool:
    return self.item() != 0.0
```

**Trait list addition**:

```mojo
struct MyStruct(
    Boolable,   # new
    Copyable,
    ...
):
```

## Relationship to Prior Work

This skill is a follow-up to `mojo-extensor-bool-method` (issue #3255, PR #3825), which
added the original raising `__bool__`. The Boolable conformance split is a natural
second step once the basic implementation is in place and trait ergonomics become important.

| Skill | What It Covers |
|-------|----------------|
| `mojo-extensor-bool-method` | Adding `fn __bool__(self) raises -> Bool` for the first time |
| `mojo-boolable-trait-conformance` (this skill) | Splitting to non-raising + `bool_strict()` to add `Boolable` to trait list |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4091, PR #4869 | Follow-up from #3393; workaround in #4089 used `t.__bool__()` directly because `Bool(t)` wasn't available |
