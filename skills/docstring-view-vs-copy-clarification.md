---
name: docstring-view-vs-copy-clarification
description: 'Fix docstring inconsistencies where memory semantics are mislabeled
  (view vs copy). Use when: a docstring claims ''view'' but the implementation allocates
  new memory, or sibling methods have conflicting return-type documentation.'
category: documentation
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Objective** | Audit and fix docstrings that claim view/shared-memory semantics but whose implementation actually copies data (or vice versa) |
| **Scope** | Docstring-only — no implementation changes |
| **Language** | Mojo (applicable to any language with view/copy distinction) |
| **Trigger** | Issue flagging `_is_view` flag inconsistency or misleading "returns a view" language |

## When to Use

- A docstring says "returns a view" or "shares memory" but the implementation allocates fresh memory and copies bytes
- A flag like `_is_view` is set to `True` after calling `self.copy()` (or equivalent), making the flag technically correct but the prose confusing
- Sibling methods (e.g., `slice()` vs `__getitem__(Slice)` vs `__getitem__(*slices)`) use inconsistent language for similar concepts
- Code review identifies that callers might misuse a method based on its documented semantics

## Verified Workflow

1. **Read the issue** — get the exact line numbers and method names cited
2. **Read all sibling methods** together to understand the full semantics landscape before writing a single line of documentation
3. **Check the implementation, not just the docstring** — run `grep` for the actual code path (`self.copy()`, `_is_view = True/False`, `Self(shape, dtype)`, etc.)
4. **Classify each method** into one of three buckets:
   - True view: pointer offset into original buffer, `_is_view = True`, no bytes copied
   - Copy with view flag: `self.copy()` + `_is_view = True` (this is the bug pattern)
   - Independent copy: fresh allocation, `_is_view = False`
5. **Update only the docstring** — do not change any implementation logic
6. **Use precise language** in the updated docstring:
   - True view: "zero-copy view", "pointer offset", "`_is_view = True`", "modifying will affect original"
   - Independent copy: "independent copy", "`_is_view = False`", "does not share memory"
   - In Notes: cross-reference the sibling methods so callers know which to use
7. **Run pre-commit** to confirm no formatting issues: `pixi run pre-commit run --files <path>`
8. **Commit, push, open PR** with `Closes #<issue>`

## Results & Parameters

### Classification Table (from Issue #3297)

| Method | Implementation | `_is_view` | Docstring Fix Needed |
| -------- | --------------- | ------------ | ---------------------- |
| `slice()` | `self.copy()` + pointer offset | `True` | Clarify "shallow pointer copy" — **yes** |
| `__getitem__(Slice)` | Fresh `Self(shape, dtype)` + byte copy | `False` | Already said "copy" — **no** |
| `__getitem__(*slices)` | Fresh `Self(shape, dtype)` + byte copy | `False` | Already said "copy" — **no** |

### Key Docstring Patterns

**For a true pointer-offset view:**

```text
Creates a shallow copy of the tensor struct whose `_data` pointer is offset
into the original buffer. No data bytes are copied. The returned tensor has
`_is_view = True`, and modifying its elements will affect the original tensor.

Returns:
    A new ExTensor whose `_data` pointer references the same underlying memory
    as the original, offset to `start` along `axis`. This is a zero-copy view:
    no data bytes are allocated or copied.
```

**For an independent copy:**

```text
Returns:
    A new ExTensor with its own data buffer (a copy of the selected elements).
    The `_is_view` flag is set to False. Does not share memory with original.
```

**Notes cross-reference pattern:**

```text
Notes:
    Unlike `__getitem__(Slice)` and `__getitem__(*slices)`, which both return
    independent copies (`_is_view = False`), this method returns a genuine view
    that shares memory with the original tensor.
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fixing implementation instead of docs | Considered changing `__getitem__(*slices)` to use pointer offset | Multi-dim slices produce non-contiguous data; a simple pointer offset is insufficient without stride metadata | Always check whether the "bug" is in the docs or the code first |
| Updating only one method | Would have fixed `slice()` without updating `__getitem__` overloads | Sibling inconsistency would remain; callers still confused | Read all sibling methods before writing any fix |
| Assuming `self.copy()` = deep copy | Initially worried `self.copy()` copied bytes | Mojo `self.copy()` calls `__copyinit__`, which for pointer-based structs is a shallow copy (pointer copy, not byte copy) | Verify what `copy()` / `__copyinit__` actually does for the specific type |
