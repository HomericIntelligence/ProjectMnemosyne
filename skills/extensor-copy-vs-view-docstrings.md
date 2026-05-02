---
name: extensor-copy-vs-view-docstrings
description: 'Document copy-vs-view memory semantics in tensor class docstrings. Use
  when: a tensor class exposes both view-returning (slice) and copy-returning (__getitem__)
  access patterns without a unified contract at the class level.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: extensor-copy-vs-view-docstrings

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-15 |
| Objective | Add explicit copy-vs-view memory semantics documentation to `ExTensor` in `shared/core/extensor.mojo` |
| Outcome | Success — 4 docstring improvements, pre-commit passed, PR #4823 created |
| Category | documentation |
| Issue | #3902 (follow-up from #3298) |

## When to Use

Use this skill when:

- A tensor or array class exposes `slice()` (view-based) and `__getitem__` (copy-based) with
  no unified memory contract at the class level
- A GitHub issue flags that `_is_view` semantics are implicit rather than explicitly documented
- A code reader cannot tell from the field docstring alone which methods set `_is_view = True`
  vs `False`, or what the consequence is for `__del__`
- An access method overload (e.g. `__getitem__(Int)` returning a scalar) lacks a note
  clarifying that view/copy semantics do not apply to it

## Verified Workflow

### 1. Read the existing class and method docstrings

```bash
grep -n "fn slice\|fn __getitem__\|_is_view" shared/core/extensor.mojo
```

Note which docstrings already cross-reference the view/copy contract and which do not.

### 2. Identify the four documentation gaps

| Location | Gap |
| ---------- | ----- |
| Struct docstring | No "Memory Semantics" summary section |
| `_is_view` field | One-line docstring with no explanation of which methods set it |
| `__getitem__(*slices)` | No cross-reference to `slice()` (inconsistent with `__getitem__(Slice)`) |
| `__getitem__(Int)` | No note clarifying it returns a scalar, not a tensor view/copy |

### 3. Add a Memory Semantics section to the struct docstring

Insert after the `Attributes` block (before `Examples`). Use a table format:

```text
Memory Semantics:
    ExTensor exposes two distinct access patterns with different memory contracts.

    +----------------------------+----------+---------------------+------------------------------+
    | Method                     | Returns  | _is_view            | Memory                       |
    +----------------------------+----------+---------------------+------------------------------+
    | slice(start, end, axis)    | ExTensor | True  (view)        | Shared — zero-copy           |
    | __getitem__(Slice)         | ExTensor | False (copy)        | Independent — data copied    |
    | __getitem__(*slices)       | ExTensor | False (copy)        | Independent — data copied    |
    | __getitem__(Int)           | Float32  | N/A (scalar result) | Scalar value, not a tensor   |
    +----------------------------+----------+---------------------+------------------------------+

    Use `slice()` for memory-efficient batch iteration where the original data must
    remain unmodified. Use `__getitem__` overloads when independent copies are needed.
```

### 4. Expand the `_is_view` field docstring

Replace the one-liner with a paragraph explaining:

- Which methods set it `True` (`slice()`) vs `False` (constructors, `__getitem__`)
- The `__del__` consequence (skip freeing `_data` when True to avoid double-free)

### 5. Add cross-reference to `__getitem__(*slices)` Notes

Append to the existing `Notes:` block:

```text
Unlike `slice()`, which returns a genuine view (`_is_view = True`, shared memory,
zero-copy), this method always allocates independent memory for the result.
Use `slice()` for memory-efficient extraction along a single axis.
```

This makes the Notes consistent with the `__getitem__(Slice)` overload which already
had this cross-reference.

### 6. Add Notes to `__getitem__(Int)`

This overload returns a `Float32` scalar — the view/copy distinction does not apply.
Add a `Notes:` block:

```text
Notes:
    Unlike `slice()` (view, shared memory) and `__getitem__(Slice)` /
    `__getitem__(*slices)` (copy, independent ExTensor), this overload
    extracts a single numeric value and has no memory ownership semantics.
```

### 7. Run pre-commit

```bash
pixi run pre-commit run --files shared/core/extensor.mojo
```

Verify: `Mojo Format ... Passed`, `Trim Trailing Whitespace ... Passed`, `Fix End of Files ... Passed`.

### 8. Commit and create PR

```bash
git add shared/core/extensor.mojo
git commit -m "docs(extensor): clarify copy-vs-view semantics in ExTensor docstrings

Closes #<issue-number>"

git push -u origin <branch-name>
gh pr create --title "docs(extensor): clarify copy-vs-view semantics in ExTensor docstrings" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Checking for existing gaps | Expected `slice()` docstring to be the weak point | `slice()` already had full cross-references to `__getitem__`; the gaps were in `__getitem__(Int)`, `__getitem__(*slices)`, the struct docstring, and the `_is_view` field | Read ALL related docstrings before assuming where the gap is — good docs in one method don't mean sibling methods are consistent |
| Scope assessment | Considered adding a separate `.md` design doc | Issue was documentation-only with no behavioral changes — a separate file would be over-engineering | For docstring-only issues, edit in-place; no need for new files |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| File modified | `shared/core/extensor.mojo` |
| Lines added | +38 (net, documentation only) |
| Pre-commit hooks | All passed (mojo format, trailing whitespace, end-of-file) |
| PR | #4823 |
| Issue | #3902 |
| Branch | `3902-auto-impl` |
| Time to implement | < 10 min (documentation-only task) |

### Key Patterns

**Struct-level memory semantics table** — put it between `Attributes:` and `Examples:` in the
struct docstring. ASCII table format works in Mojo docstrings (no markdown renderer).

**Consistent cross-referencing** — if one overload's `Notes:` points to an alternative, all
sibling overloads should too. Grep for the pattern first (`grep -n "fn __getitem__"`) to
identify which overloads already have it.

**Scalar overloads need explicit N/A** — `__getitem__(Int)` returning a primitive needs a
note stating the view/copy distinction doesn't apply. Without it, readers may wonder whether
the scalar return shares memory.
