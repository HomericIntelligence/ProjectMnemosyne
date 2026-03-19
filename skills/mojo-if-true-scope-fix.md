---
name: mojo-if-true-scope-fix
description: 'Replace Mojo ''if True:'' constant condition anti-patterns with named
  helper functions. Use when: Mojo --Werror reports constant condition warnings on
  if True: blocks used for scope-based destructor testing.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo `--Werror` treats `if True:` as a constant condition warning, breaking compilation |
| **Root Cause** | `if True:` was used intentionally to create inner scopes for testing reference counting (destructor triggers on scope exit) |
| **Solution** | Extract `if True:` block bodies into named helper functions — function return acts as scope exit |
| **Mojo Version** | v0.26.1+ |

## When to Use

1. Mojo compiler emits: `error: if statement with constant condition 'if True'`
2. Test files use `if True:` blocks to force scope exit for destructor/refcount testing
3. Migrating memory leak tests to newer Mojo versions with stricter warnings
4. Code review finds `if True:` patterns in `.mojo` files

## Verified Workflow

### Quick Reference

```mojo
# BEFORE (constant condition warning):
fn test_scope_exit_decrements_refcount() raises:
    var tensor1 = zeros([10, 10], DType.float32)
    if True:
        var tensor2 = tensor1
        # tensor2 destroyed here, refcount drops

# AFTER (helper function scope):
fn _copy_and_check_refcount(tensor1: ExTensor) -> Int:
    """Helper: copy tensor in inner scope and return inner refcount."""
    var tensor2 = tensor1
    return tensor1._refcount[]

fn test_scope_exit_decrements_refcount() raises:
    var tensor1 = zeros([10, 10], DType.float32)
    var inner_refcount = _copy_and_check_refcount(tensor1)
    # tensor2 destroyed on helper return, refcount drops
```

### Step 1: Identify all `if True:` instances

```bash
grep -n "if True:" tests/shared/core/test_memory_leaks*.mojo
```

### Step 2: Categorize the scope purpose

Each `if True:` block tests one of these patterns:

- **Copy scope**: Copy a tensor, check refcount, let copy die
- **Modification scope**: Copy tensor, modify shared data, verify original
- **Allocation scope**: Allocate tensor to test deallocation on exit
- **View scope**: Create a view, verify it doesn't free data on destruction

### Step 3: Extract helper functions

Naming convention: prefix with `_` (private), use descriptive verb phrases.

| Pattern | Helper Name | Signature |
|---------|-------------|-----------|
| Copy and check refcount | `_copy_and_check_refcount` | `(tensor: ExTensor) -> Int` |
| Modify through copy | `_modify_through_copy` | `(tensor: ExTensor) raises` |
| Allocate and use | `_alloc_and_use_tensor` | `() raises` |
| Check shared deallocation | `_check_shared_deallocation` | `() raises` |
| Create and drop view | `_create_and_drop_view` | `(original: ExTensor) raises` |
| Check view refcount | `_check_view_refcount` | `(original: ExTensor, initial: Int) raises -> Int` |

### Step 4: Handle nested `if True:` blocks

Nested `if True:` (two levels deep) can chain helper calls:

```mojo
# BEFORE:
if True:
    var tensor1 = ...
    if True:
        var tensor2 = tensor1
        # inner scope
    # outer scope continues

# AFTER:
fn _inner_scope(tensor1: ExTensor) -> Int:
    var tensor2 = tensor1
    return tensor1._refcount[]

fn _outer_scope() raises:
    var tensor1 = ...
    var inner_rc = _inner_scope(tensor1)
    # continues with outer scope
```

### Step 5: Handle single-variable scopes (alternative)

For simple single-variable scopes, `_ = var^` (ownership transfer + drop) works without a helper:

```mojo
# Single-variable scope alternative:
var view = original.reshape(shape)
assert_true(view._is_view, "Should be view")
_ = view^  # Explicitly drop view
```

This was already used in `test_memory_leaks_part2.mojo` before this fix.

### Step 6: Verify no `if True:` remains

```bash
grep -n "if True:" tests/shared/core/test_memory_leaks*.mojo
# Should return no matches
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `with` context manager | Use `with` block for scoping | Not available in Mojo v0.26.1 | Check Mojo version before proposing syntax |
| Scope helper trait | Dedicated trait to create scope | Not supported in Mojo v0.26.1 | Helper functions are the idiomatic Mojo solution |
| `_ = var^` for all cases | Use ownership transfer drop for all scopes | Awkward for multi-variable scopes (can only drop one var) | Reserve for single-variable cases; use helpers for complex scopes |

## Results & Parameters

**PR**: HomericIntelligence/ProjectOdyssey#4890
**Issue**: HomericIntelligence/ProjectOdyssey#4523
**Files fixed**: 3 files (`test_memory_leaks.mojo`, `_part1.mojo`, `_part3.mojo`)
**Instances removed**: 12 `if True:` patterns total
**Helper functions created**: 6 unique helpers (duplicated across files for isolation)

**Key insight**: Mojo function return scope is semantically equivalent to block scope for
ownership/destruction. Variables declared inside a function are destroyed when the function
returns, decrementing refcounts and triggering `__del__` — identical behavior to `if True:`
scope exit.
