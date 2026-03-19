---
name: mojo-boolable-raises-fix
description: 'Fix Mojo test compile errors from Bool(t) on structs whose __bool__
  has raises, preventing Boolable trait conformance. Use when: CI fails with ''does
  not conform to trait Boolable'', __bool__ is defined with raises, or you need to
  test raising __bool__ without Boolable.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Boolable Raises Fix

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Category** | testing |
| **Objective** | Fix CI compile error where `Bool(t)` was called on an `ExTensor` whose `__bool__` has a `raises` signature |
| **Outcome** | One-line fix: `Bool(t)` → `t.__bool__()`. CI passes, test intent preserved. |
| **Context** | Issue #3393 — placeholder tests in `test_utility.mojo`; CI error on `test_bool_requires_single_element` |

## When to Use

Use this skill when:

- CI fails with: `argument type 'X' does not conform to trait 'Boolable'` or `no matching function in initialization` for `Bool(t)`
- A test uses `Bool(t)` to verify that `__bool__` raises for an invalid input
- The struct's `__bool__` is declared as `fn __bool__(self) raises -> Bool` (i.e., can raise)
- The struct does NOT declare `Boolable` in its trait list (because `Boolable` requires non-raising `__bool__`)

Do NOT use when:
- `__bool__` is non-raising — just add `Boolable` to the struct's trait list
- The test is checking return value, not raise behavior

## Verified Workflow

### Step 1 — Identify the compile error

Read CI log. Look for:

```text
error: no matching function in initialization
note: candidate not viable: failed to infer parameter 'T',
      argument type 'ExTensor' does not conform to trait 'Boolable'
```

The line number points to `Bool(t)` in the test.

### Step 2 — Understand why

`Bool(t)` in Mojo dispatches through the `Boolable` trait, which requires a **non-raising** `__bool__`:

```mojo
# This prevents Boolable conformance:
fn __bool__(self) raises -> Bool: ...

# This would allow Boolable conformance:
fn __bool__(self) -> Bool: ...
```

If `__bool__` must be able to raise (e.g., to error on multi-element tensors), the struct cannot implement `Boolable`, so `Bool(t)` fails to compile.

### Step 3 — Apply the fix

Replace `Bool(t)` with `t.__bool__()` in the test:

```mojo
# Before (compile error):
var val = Bool(t)  # Should raise error for multi-element tensor

# After (works correctly):
var val = t.__bool__()  # Should raise error for multi-element tensor
```

This calls the method directly, bypassing trait dispatch. The `raises` propagates through the `try` block as expected.

### Step 4 — Verify the if-syntax still works

The `if t:` syntax (implicit bool conversion) works even with `raises` in Mojo — the `if` statement propagates raising methods. Only `Bool(t)` requires `Boolable`.

```mojo
# This still compiles fine with raising __bool__:
if t_zero:
    raise Error("Zero tensor should be falsy")
```

### Step 5 — Commit and push

```bash
git add tests/shared/core/test_utility.mojo
git commit -m "fix(test_utility): use __bool__() directly to test raises behavior"
git push -u origin <branch>
gh pr create ...
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Add `Boolable` to struct trait list | Tried conforming to `Boolable` to allow `Bool(t)` | `Boolable` requires non-raising `__bool__`; struct's `__bool__` has `raises` so it cannot conform | `Boolable` and raising `__bool__` are mutually exclusive in Mojo |
| Change `__bool__` to non-raising | Remove `raises` from `__bool__` so `Boolable` is satisfied | Would break the multi-element error test — `__bool__` needs to raise for that case | Can't drop `raises` without changing test semantics |

## Results & Parameters

### One-Line Fix

```mojo
# In test_bool_requires_single_element():
var val = t.__bool__()  # replaces Bool(t)
```

### Key Mojo Trait Rules

| Syntax | Requires | Works with `raises __bool__`? |
|--------|----------|-------------------------------|
| `Bool(t)` | `Boolable` trait (non-raising) | ❌ No |
| `t.__bool__()` | Just the method | ✅ Yes |
| `if t:` | Non-raising `__bool__` OR `raises __bool__` | ✅ Yes |

### Error Signature to Watch For

```text
error: no matching function in initialization
note: failed to infer parameter 'T',
      argument type 'X' does not conform to trait 'Boolable'
```

This always means: the type's `__bool__` has `raises`, but `Bool()` constructor requires `Boolable`.
