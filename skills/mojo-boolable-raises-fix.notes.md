# Session Notes: mojo-boolable-raises-fix

## Raw Session Details

**Date**: 2026-03-07
**Issue**: #3393 — Remaining placeholder tests in test_utility.mojo need implementation
**Branch**: 3393-auto-impl
**PR**: #4089

## Problem Discovery

The issue claimed there were `pass` placeholder tests for `__bool__`, `__str__`, `__repr__`, `__hash__`.
On inspection, all four were already implemented with real assertions (a prior PR had done this work).

The actual failing test was `test_bool_requires_single_element` at line 359:

```text
/tests/shared/core/test_utility.mojo:359:23: error: no matching function in initialization
    var val = Bool(t)  # Should raise error for multi-element tensor
              ~~~~^~~
note: candidate not viable: failed to infer parameter 'T',
      argument type 'ExTensor' does not conform to trait 'Boolable'
```

## Root Cause Analysis

`ExTensor` struct declaration:
```mojo
struct ExTensor(
    Copyable,
    Hashable,
    ImplicitlyCopyable,
    Movable,
    Representable,
    Sized,
    Stringable,
):
```

`Boolable` is NOT in the list. The `__bool__` method is:
```mojo
fn __bool__(self) raises -> Bool:
    return self.item() != 0.0
```

Because `__bool__` has `raises`, the struct cannot implement `Boolable` (which requires non-raising).
`Bool(t)` requires `Boolable`, so it fails to compile.

## The Fix

Changed line 359 in `tests/shared/core/test_utility.mojo`:

```mojo
# Before:
var val = Bool(t)  # Should raise error for multi-element tensor

# After:
var val = t.__bool__()  # Should raise error for multi-element tensor
```

`t.__bool__()` calls the method directly, skipping trait dispatch. The `raises` propagates through
the surrounding `try` block exactly as intended.

## Key Insight: `if t:` vs `Bool(t)`

- `if t:` compiles fine even with raising `__bool__` — Mojo propagates raises through `if`
- `Bool(t)` requires `Boolable` trait which mandates non-raising `__bool__`
- `t.__bool__()` works regardless of `raises` — direct method call

## Verification

Pre-commit hooks all passed. CI unable to run locally (GLIBC version mismatch).
PR #4089 created with auto-merge enabled.

## Diagnostic Process

1. Read `.claude-prompt-3393.md` → understood issue context
2. Found `test_utility.mojo` → saw tests were NOT placeholders
3. Checked CI run #22808229965 logs → found exact compile error at line 359
4. Traced `Bool(t)` → `Boolable` → `raises` incompatibility
5. Applied minimal fix: `Bool(t)` → `t.__bool__()`