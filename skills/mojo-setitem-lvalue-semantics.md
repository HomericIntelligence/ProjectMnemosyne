---
name: mojo-setitem-lvalue-semantics
description: "Documents Mojo subscript assignment semantics and ExTensor __setitem__ implementation: obj[i]=val uses __getitem__ lvalue, not __setitem__; adding __setitem__ overloads to structs lacking them; handling GLIBC mismatch causing mojo format pre-commit failures; and test patterns for Float64/Int64/out-of-bounds coverage. Use when: (1) debugging 'cannot implicitly convert' errors on ExTensor/subscript assignments, (2) designing subscript APIs in Mojo structs, (3) encountering 'cannot call function that may raise' after wrapping subscript assignments, (4) CI fails with 'expression must be mutable in assignment' on tensor subscript lines, (5) mojo format pre-commit hook fails locally with GLIBC_2.32+ not found, (6) adding tests for __setitem__ overloads on Mojo tensor types."
category: debugging
date: 2026-03-21
version: "2.0.0"
user-invocable: false
tags: [mojo, type-errors, subscript, setitem, getitem, lvalue, ExTensor, Float32, Float64, Float16, glibc, pre-commit, testing, ci-cd]
---

# Mojo __setitem__ Lvalue Semantics

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-21 |
| **Objective** | Fix 314 type errors after replacing bitcast UAF writes with subscript assignment; add ExTensor __setitem__ and tests |
| **Outcome** | All errors resolved; discovered Mojo `obj[i]=val` uses lvalue, not `__setitem__`; __setitem__ overloads added; test suite extended |
| **Mojo Version** | 0.26.1 |
| **Absorbed** | mojo-setitem-glibc-hook-skip (v1.0.0), mojo-setitem-test-pattern (v1.0.0) on 2026-05-03 |

## When to Use

- Debugging `cannot implicitly convert 'Float64' value to 'Float32'` errors on subscript assignments
- Designing Mojo structs that need to accept multiple types via subscript assignment
- Migrating from direct pointer writes (`bitcast[T]()[i] = val`) to safe assignment APIs
- Encountering `cannot call function that may raise in a context that cannot raise` after wrapping subscript assignments in type constructors
- CI "Core Utilities" fails with `error: expression must be mutable in assignment` at tensor subscript assignment lines
- Tests call `t[index] = value` but `ExTensor.__setitem__` does not exist
- Local `pixi run mojo format` exits with `GLIBC_2.32 not found` / `GLIBC_2.33 not found` / `GLIBC_2.34 not found`
- Pre-commit `mojo-format` hook fails with exit code 1 but no actual formatting errors (just GLIBC crash)
- Implementing `__setitem__` on a struct that already has `_set_float64` / `_set_int64` internal setters
- Adding tests for a new `__setitem__` method on a Mojo tensor/array struct with Float64 and Int64 overloads
- Testing the out-of-bounds error path without the `raises` keyword (which cannot assert the error was actually raised)
- Following TDD for an indexing setter that may live in a separate feature branch not yet merged

## Verified Workflow

### Quick Reference

```text
Problem:  tensor[i] = Float64(x)  -> ERROR: cannot convert Float64 to Float32
Fix 1:    tensor[i] = Float32(x)  -> OK (matches __getitem__ return type)
Fix 2:    tensor.set(i, Float64(x))  -> OK (explicit method call with overloads)
Fix 3:    tensor._set_float64(i, Float64(x))  -> OK (for non-raising contexts)
```

### Step 1: Understand the Semantics

In Mojo, `obj[i] = val` is syntactic sugar for lvalue assignment through `__getitem__`, NOT a call to `__setitem__`. The compiler:

1. Calls `__getitem__(i)` to get an lvalue reference
2. Assigns `val` to that reference
3. Since `__getitem__` returns `Float32`, `val` must be `Float32`

This means `__setitem__` overloads for `Float64`, `Float16`, `Int64`, etc. are **dead code** -- they are never invoked via `obj[i] = val` syntax.

### Step 2: Diagnose CI and Local Failures

```bash
gh run view <run-id> --log | grep -A5 "mutable\|setitem\|GLIBC"
```

Look for:
- `error: expression must be mutable in assignment` → missing `__setitem__`
- `GLIBC_2.3[234] not found` → local mojo format unusable

### Step 3: Find the Insertion Point and Internal Setter Pattern

```bash
grep -n "__getitem__\|_set_float64\|_set_int64" shared/core/extensor.mojo
```

Key facts:
- `_set_float64(self, index: Int, value: Float64)` and `_set_int64(self, index: Int, value: Int64)` take plain `self` (mutate via raw pointer)
- `__setitem__` itself needs `mut self`
- Dispatch pattern: float dtypes (float16/32/64) → `_set_float64`; all others → `_set_int64`

### Step 4: Add `__setitem__` Overloads After `__getitem__(self, index: Int)`

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
    """Set element at flat index."""
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")

    if (
        self._dtype == DType.float16
        or self._dtype == DType.float32
        or self._dtype == DType.float64
    ):
        self._set_float64(index, value)
    else:
        self._set_int64(index, Int64(value))

fn __setitem__(mut self, index: Int, value: Int64) raises:
    """Set element at flat index using an integer value."""
    self.__setitem__(index, Float64(value))
```

### Step 5: Choose the Right Fix Pattern (Type Mismatch Sites)

| Context | Pattern | Example |
| --------- | --------- | --------- |
| RHS is same type as `__getitem__` return | Direct assignment | `result[i] = Float32(expr)` |
| RHS is different type, in `raises` context | `set()` method | `result.set(i, Float64(expr))` |
| Inside `@parameter fn` / `parallelize[]` closure | Direct pointer write | `result._set_float64(i, Float64(expr))` |
| Accumulating with mixed types | Cast before arithmetic | `Float64(tensor[i]) + float64_val` |

### Step 6: Implement the `set()` Method

Add overloaded `set()` methods that delegate to `__setitem__`:

```mojo
@always_inline
fn set(mut self, index: Int, value: Float64) raises:
    self.__setitem__(index, value)

@always_inline
fn set(mut self, index: Int, value: Float32) raises:
    self.__setitem__(index, Float64(value))

@always_inline
fn set(mut self, index: Int, value: Float16) raises:
    self.__setitem__(index, Float64(Float32(value)))

@always_inline
fn set(mut self, index: Int, value: Int) raises:
    self.__setitem__(index, Float64(value))
# ... more overloads for Int64, Int32, Int16, Int8, UInt8, etc.
```

### Step 7: Handle Non-Raising Contexts

`parallelize[]` closures use `@parameter fn` which cannot raise. In these contexts:

```mojo
# ERROR: .set() raises, can't use in @parameter fn
@parameter
fn parallel_work(b: Int) capturing:
    output.set(idx, val)  # Cannot call function that may raise

# FIX: Use internal non-raising method
@parameter
fn parallel_work(b: Int) capturing:
    output._set_float64(idx, Float64(val))  # Does not raise
```

### Step 8: Fix Mixed-Type Arithmetic

When `__getitem__` returns Float32 but you need Float64 arithmetic:

```mojo
# ERROR: Float32 + Float64 -> __add__ type mismatch
grad_beta.set(f, grad_beta[f] + grad_out)  # grad_beta[f] is Float32, grad_out is Float64

# FIX: Cast __getitem__ result to match
grad_beta.set(f, Float64(grad_beta[f]) + grad_out)
```

### Step 9: Commit with SKIP=mojo-format (GLIBC Mismatch)

Since mojo requires GLIBC 2.32+ and the dev host doesn't have it, the local pre-commit hook always exits 1.
Per CLAUDE.md policy, `SKIP=hook-id` is valid for broken hooks — document the reason in the commit:

```bash
SKIP=mojo-format git commit -m "fix(core): add ExTensor __setitem__ overloads

SKIP=mojo-format: mojo binary requires GLIBC 2.32+ unavailable on this host.
CI Docker container will run mojo format in the correct environment.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### Step 10: Write Tests for __setitem__

Locate the `__setitem__` implementation (may be in a sibling worktree):

```bash
grep -n "__setitem__" <package>/extensor.mojo
# If not found, check sibling worktrees:
git worktree list
grep -n "__setitem__" <worktree-path>/<package>/extensor.mojo
```

Insert three test functions after the `__len__` section and before `__bool__` in the test file:

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

Update `main()` to call the new tests (add `# __setitem__` block between `__len__` and `__bool__`):

```mojo
    # __setitem__
    print("  Testing __setitem__...")
    test_setitem_valid_index()
    test_setitem_integer_dtype()
    test_setitem_out_of_bounds()
```

### Step 11: Commit and Create PR for Tests

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
| --------- | ---------------- | --------------- | ---------------- |
| Add `__setitem__` overloads | Added 9 new `__setitem__` overloads for Float16, Int, Int8, etc. | Mojo never dispatches `obj[i] = val` to `__setitem__` -- these are dead code | `__setitem__` in Mojo is not called via subscript assignment syntax |
| Wrap all RHS in `Float32()` | Changed `result[i] = Float64(x)` to `result[i] = Float32(x)` everywhere | Introduced "cannot call function that may raise" errors in `@parameter fn` closures | `Float32()` constructor raises; can't use in non-raising contexts like `parallelize[]` |
| Delegate to sub-agents (round 1) | Launched 8 parallel agents to fix all files | Agents only fixed ~60% of errors; missed Float16 paths and arithmetic mismatches | Sub-agents need explicit error line numbers and all error categories enumerated |
| Use `.set()` in `parallelize[]` | Replaced direct writes with `.set()` in parallel computation functions | `.set()` raises but `@parameter fn` closures cannot raise | Need separate non-raising internal method (`_set_float64`) for parallel contexts |
| Run `pixi run mojo format` locally | Called mojo format on changed files | `GLIBC_2.32 not found` — mojo binary requires newer glibc than system provides | Mojo toolchain only works inside the project's Docker container on older Linux hosts |
| Find mojo in system PATH | `which mojo` and `find /usr /opt` | Only found the pixi env binary, same GLIBC issue | There is no alternative mojo installation; CI Docker is the only viable environment |
| Inspect formatter output manually | Compared test file against passing commits | Could not determine exact formatter changes without running it | Mojo formatter changes are subtle; the only reliable approach is to run it in CI |
| Use `--no-verify` | Considered bypassing hooks entirely | CLAUDE.md explicitly prohibits `--no-verify`; `SKIP=hook-id` is the correct alternative | Always use `SKIP=specific-hook-id` instead of blanket `--no-verify` |
| Verifying tests compile locally | Ran `pixi run mojo build tests/shared/core/test_utility.mojo` | GLIBC version mismatch on this host (requires GLIBC_2.32+, host has older version) | Mojo cannot run locally; CI is the verification gate for compilation |
| Checking `__setitem__` in current branch | `grep -n "__setitem__" shared/core/extensor.mojo` returned no matches | `__setitem__` lives in the issue-2722 worktree, not yet merged to main | Always check sibling worktrees when a follow-up issue references a parent issue |

## Results & Parameters

### Error Distribution (Lvalue Semantics Migration)

```text
267 errors: cannot implicitly convert 'Float64' to 'Float32'
 24 errors: cannot implicitly convert 'Float16' to 'Float32'
 16 errors: invalid call to '__add__' (Float64/Float32 mismatch)
  6 errors: cannot implicitly convert 'Int64' to 'Float32'
  1 error:  cannot call function that may raise
```

### Fix Pattern Distribution

```text
~200 sites: result[i] = Float32(expr)        -- simple same-type cast
 ~40 sites: result.set(i, expr)              -- explicit method for non-Float32 values
  ~8 sites: result._set_float64(i, expr)     -- for parallelize[] closures
  ~8 sites: Float64(tensor[i]) + expr        -- arithmetic type promotion
  ~5 sites: self._set_float64/int64()        -- internal constructors
```

### Files Affected (Lvalue Semantics Migration)

```text
shared/core/extensor.mojo       -- Added set() overloads, fixed constructors
shared/core/activation.mojo     -- 74 lines changed
shared/core/attention.mojo      -- 34 lines changed
shared/core/conv.mojo           -- 22 lines changed
shared/core/dropout.mojo        -- 26 lines changed
shared/core/dtype_cast.mojo     -- 18 lines changed
shared/core/layers/dropout.mojo -- 24 lines changed
shared/core/normalization.mojo  -- 187 lines changed (largest, most complex)
shared/core/pooling.mojo        -- 12 lines changed
```

### GLIBC Hook Skip — Successful Configuration

```bash
# Commit bypassing only the broken mojo-format hook
SKIP=mojo-format git commit -m "fix(core): ..."
# All other hooks (trailing-whitespace, end-of-file, check-yaml, etc.) still run
```

### Test Assertions Quick Reference (ProjectOdyssey)

```mojo
# Float64 overload
t[1] = 9.5
assert_value_at(t, 1, 9.5, 1e-6, "message")

# Int64 overload
t[2] = Int64(7)
assert_value_at(t, 2, 7.0, 1e-6, "message")

# Out-of-bounds raises
try:
    t[5] = 1.0
except:
    raised = True
```

### ExTensor.__setitem__ Dispatch Table

| Dtype group | Internal setter called |
| ------------- | ---------------------- |
| `DType.float16`, `DType.float32`, `DType.float64` | `_set_float64(index, value)` |
| `DType.int8`, `DType.int16`, `DType.int32`, `DType.int64`, `DType.bool`, etc. | `_set_int64(index, Int64(value))` |

### Test Functions Added

| Test | DType | Overload | Assertion Method |
| ------ | ------- | ---------- | ----------------- |
| `test_setitem_valid_index` | `float32` | `Float64` (implicit) | `assert_value_at` round-trip |
| `test_setitem_integer_dtype` | `int32` | `Int64` explicit | `assert_value_at` with `7.0` |
| `test_setitem_out_of_bounds` | `float32` | `Float64` (implicit) | `try/except` + manual flag |

### Key Test Parameters

- Tensor size: 3 elements (minimal, avoids timeout)
- Out-of-bounds index: 5 (clearly > 2, the last valid index)
- Float value used: `9.5` (exact in FP32, avoids precision issues)
- Integer value used: `Int64(7)` (small, fits all integer dtypes)
- Tolerance for `assert_value_at`: `1e-6`

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #4996 follow-up fix | Fixed 314 type errors across 9 files after bitcast UAF migration |
| ProjectOdyssey | Issue #3165, PR #3385 | Added __setitem__ overloads and three test functions to test_utility.mojo |
