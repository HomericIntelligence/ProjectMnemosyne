---
name: testing-view-copy-semantics-mismatch
description: "Fix CI failures caused by tests assuming __getitem__(Slice) returns a view when it actually returns a copy. Use when: (1) test asserts _is_view but gets False, (2) __setitem__ write-through test fails because the 'view' is actually a copy, (3) slice() vs __getitem__(Slice) semantics diverge, (4) CI fix introduces new failures from implicit type conversion."
category: testing
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - view
  - copy
  - slice
  - semantics
  - mojo
  - tensor
  - ci-fix
  - type-conversion
---

# View vs Copy Semantics Mismatch in Tensor Tests

Fix CI failures caused by tests that assume `__getitem__(Slice)` returns a view when it
returns a copy, and by missing `.as_any()` type conversions.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Fix CI failures introduced by our own PR during iterative bug fixing |
| **Outcome** | Success -- 2 of 3 failures fixed, 1 identified as pre-existing upstream Mojo bug |
| **Repository** | ProjectOdyssey |
| **PR** | #5097 (round 2 fixes) |

## When to Use

- A test asserts `_is_view == True` but fails because `__getitem__(Slice)` returns a copy
- A `__setitem__` write-through test fails (writes to "view" don't affect the original)
- CI reports `value passed to 'input' cannot be converted from 'Tensor' to 'AnyTensor'`
- Fixing one test introduces a new failure because the return type changed
- You need to distinguish between `slice()` (view) and `__getitem__` (copy) semantics

## Verified Workflow

### Quick Reference

```bash
# Check if a method returns view or copy:
grep -A5 "fn __getitem__.*Slice" shared/tensor/any_tensor.mojo
# Look for: "_is_view = False" (copy) vs "_is_view = True" (view)

# Check if forward() expects AnyTensor or Tensor[dtype]:
grep "fn forward.*self.*input" shared/core/layers/conv2d.mojo
# If AnyTensor: call with tensor.as_any()
# If Tensor[dtype]: call directly

# Quick fix for view semantics:
# WRONG: var view = tensor[2:8]        # Returns COPY (_is_view=False)
# RIGHT: var view = tensor.slice(2, 8)  # Returns VIEW (_is_view=True)
```

### Detailed Steps

#### Pattern 1: View vs Copy Semantics

Two AnyTensor methods look similar but have different semantics:

| Method | Returns | `_is_view` | Memory | Use When |
|--------|---------|------------|--------|----------|
| `tensor[a:b]` (`__getitem__(Slice)`) | Copy | `False` | New allocation | Read-only slicing, safe to mutate independently |
| `tensor.slice(a, b)` | View | `True` | Shared with parent | Write-through to original, zero-copy batching |

If a test needs write-through semantics (modifying the slice affects the original),
it MUST use `slice()`, not `__getitem__`:

```mojo
# WRONG: __getitem__ returns a copy — writes don't affect original
var view = original[2:8]
view[0] = Float32(99.0)  # Only modifies the copy!

# RIGHT: slice() returns a view — writes affect original
var view = original.slice(2, 8)
view[0] = Float32(99.0)  # Modifies original[2]!
```

For multi-dimensional view slicing, chain `slice()` calls:

```mojo
# 2D view: rows 1-3, columns 1-3
var view = tensor.slice(1, 3, axis=0).slice(1, 3, axis=1)
```

#### Pattern 2: Tensor to AnyTensor Conversion

When a function expects `AnyTensor` but you have `Tensor[dtype]`, add `.as_any()`:

```mojo
# WRONG: Tensor[DType.float32] cannot convert to AnyTensor
var output = layer.forward(input)

# RIGHT: Explicit conversion
var output = layer.forward(input.as_any())
```

Watch out for cascading type changes: if `output` was previously `Tensor[dtype]`
and is now `AnyTensor`, downstream code using `Tensor`-specific methods may break.

#### Pattern 3: Iterative CI Fix Workflow

When fixing CI failures, expect that your fix may introduce new failures:

1. Push fix
2. Wait for CI
3. Read ALL failures (not just the first one)
4. Classify: caused by our change vs pre-existing
5. Fix what we caused, document what's pre-existing
6. Push and repeat

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fixed tuple destructuring in test_typed_conv2d | Changed `var (a,b,c) = fn()` to subscript access | Introduced new error: `forward(input)` now fails because Tensor can't convert to AnyTensor | When fixing one error in a function, check ALL other calls in that function for type compatibility |
| Assumed `__getitem__(Slice)` returns view | Test at line 40 asserted `_is_view == True` on `original[2:8]` | `__getitem__(Slice)` explicitly returns a copy per its docstring | Always read the method's docstring before assuming its semantics |
| Expected `__del__` view fix to prevent all training_loop crashes | Added `_is_view` guard in `__del__` to prevent bad-free | CI still crashed because without ASAN, prior heap corruption from bitcast UAF (Day 53 pattern) causes the same crash symptoms | A fix that works with ASAN may not fix crashes without ASAN if there are multiple bugs |
| Explore agent claimed line 75 was a bitcast WRITE | Agent reported `training_loop.mojo:75` as the UAF trigger | Line 75 is `Float64(tensor._data.bitcast[Float32]()[0])` -- a READ, not a write | Always verify sub-agent findings by reading the actual code |

## Results & Parameters

### CI Failure Classification Template

When CI fails after your fix, classify each failure:

```bash
# Get all unique failures
gh run view <RUN_ID> --log-failed 2>&1 | grep "❌ FAILED" | sort -u

# For each failure, get 5 lines of context:
gh run view <RUN_ID> --log-failed 2>&1 | grep -B5 "FAILED.*<test_file>"
```

| Classification | Pattern | Action |
|---------------|---------|--------|
| **Our fix broke it** | Error on line we changed or in function we modified | Fix it |
| **Our fix exposed it** | Pre-existing bug now reachable due to our changes | Fix if trivial, else document and defer |
| **Pre-existing, unrelated** | Error in file we didn't touch | Not our problem |

### View Semantics Quick Reference

```mojo
# AnyTensor methods and their semantics:
tensor[i]           # __getitem__(Int) -> Float32 (element access)
tensor[a:b]         # __getitem__(Slice) -> AnyTensor COPY
tensor[a:b, c:d]    # __getitem__(*slices) -> AnyTensor COPY
tensor.slice(a, b)  # slice() -> AnyTensor VIEW (shares memory)
tensor.clone()      # clone() -> AnyTensor COPY (deep copy)
tensor.transpose()  # transpose() -> AnyTensor VIEW (stride-based)
```

### Confirmed CI Fix Results

| Fix | Before | After |
|-----|--------|-------|
| `test_typed_conv2d`: add `.as_any()` | `cannot convert Tensor to AnyTensor` | Passes |
| `test_setitem_view_part1/2`: use `slice()` | `Sliced tensor should be a view` | Passes |
| Container image tar cache | `504 Gateway Time-out` on every job | `Cache hit` + `Cache restored successfully` (682 MB) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5097 round 2 | Iterative CI fix after initial PR introduced new failures |
