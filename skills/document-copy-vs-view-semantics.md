---
name: document-copy-vs-view-semantics
description: 'Document copy vs view semantics for slicing operations, updating docstrings
  and fixing misleading test names. Use when: NOTE markers exist, test names contradict
  assertions, or ''Returns: view'' contradicts copy implementation.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | document-copy-vs-view-semantics |
| **Category** | documentation |
| **Complexity** | Low |
| **Files touched** | Implementation `.mojo`, test `.mojo` |
| **PR type** | docs-only (no functional change) |

## When to Use

Trigger on any of these conditions:

1. A cleanup issue references `NOTE: Current implementation creates copies, not views` in tests or source
2. A test function name says `test_slice_is_view` but the test body asserts `not _is_view` (name contradicts assertion)
3. A `Returns:` docstring says "view" but implementation sets `_is_view = False`
4. A `Returns:` docstring says "copy" but implementation offsets a shared data pointer
5. Multiple slicing methods exist with inconsistent semantics that are undocumented

## Verified Workflow

### 1. Read the issue and locate NOTE markers

```bash
gh issue view <number> --comments
```

Grep for `NOTE` in test and source files:

```
pattern: NOTE
glob: *.mojo
```

### 2. Read all three relevant methods in one pass

For ExTensor, there are three slicing entry points with different semantics:

| Method | Semantics | Reason |
| -------- | ----------- | -------- |
| `slice(start, end, axis)` | **View** — pointer offset + refcount | Efficient batch extraction |
| `__getitem__(Slice)` | **Copy** — always allocates new buffer | Strided copy avoids lifetime complexity |
| `__getitem__(*slices)` | **View** — pointer offset per dim | Multi-dim analogue of `slice()` |

### 3. Update `slice()` docstring

- Fix: `Returns:` "shares memory with original" (not "new tensor containing the slice")
- Add `Notes:` section explaining: true view, pointer offset, refcount, use for training loops

### 4. Update `__getitem__(Slice)` docstring

- Fix: `Returns:` "copy" not "view"
- Add `Notes:` explaining copy-by-design rationale: strided data, YAGNI, avoids lifetime management
- Point users to `slice()` for view semantics

### 5. Update `__getitem__(*slices)` docstring

- Fix: `Returns:` "shares memory" (view semantics)
- Add `Notes:` explaining per-dimension offset, NumPy analogy

### 6. Fix test names and docstrings

- Rename `test_slice_is_view` → `test_slice_creates_copy` (the old name was the **opposite** of what the test asserts)
- Remove `NOTE:` prefix from both test docstrings; replace with clear "by design" language
- Update the call site in `main()` to use the new function name

### 7. Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass (mojo format is a no-op for docstring-only changes; markdown lint checks `.md` files).

### 8. Commit, push, open PR with auto-merge

```bash
git add <impl-file> <test-file>
git commit -m "docs(extensor): document slicing copy vs view semantics"
git push -u origin <branch>
gh pr create --title "docs(extensor): document slicing copy vs view semantics" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Changing `test_slice_is_view` without updating `main()` | Renamed function but forgot the call site in `main()` | Would have caused a compile error | Always grep for all call sites when renaming a function |
| Treating all three slice methods as having the same semantics | Assumed `__getitem__(Slice)` was also a view | The 1D `__getitem__(Slice)` always copies (strided), while `slice()` and `__getitem__(*slices)` are views | Read the implementation before writing docstrings |
| Using `just pre-commit-all` | Ran `just pre-commit-all` to validate | `just` was not on PATH in this environment | Fall back to `pixi run pre-commit run --all-files` |

## Results & Parameters

### Copy-paste docstring pattern for a copy-returning slice method

```mojo
fn __getitem__(self, slice: Slice) raises -> Self:
    """Get slice of 1D tensor [start:end] or [start:end:step].

    Args:
        slice: Slice object specifying start, end, and optional step.

    Returns:
        New tensor containing a **copy** of the sliced data. The result
        does not share memory with the original tensor.

    Raises:
        Error: If tensor is not 1D or indices are invalid.

    Notes:
        This method always returns a copy (`_is_view = False`), regardless
        of the step value. This is by design: materializing a strided copy
        keeps the implementation simple and avoids lifetime management
        complexity. For memory-efficient batch extraction over the first
        axis, use `slice()` instead, which returns a true view.
    """
```

### Copy-paste docstring pattern for a view-returning slice method

```mojo
fn slice(self, start: Int, end: Int, axis: Int = 0) raises -> ExTensor:
    """Extract a slice along the specified axis.

    ...

    Returns:
        A new tensor view that shares memory with the original tensor.
        Modifying the view will affect the original tensor.

    Notes:
        This method returns a **true view** (shared memory). The data pointer
        is offset into the original buffer and the reference count is
        incremented to keep the buffer alive. This is the recommended method
        for batch extraction in training loops where memory efficiency matters.
    """
```

### Misleading test name anti-pattern to avoid

```mojo
# BAD: name says "is_view" but asserts copy (not _is_view)
fn test_slice_is_view() raises:
    assert_true(not sliced._is_view)  # contradiction!

# GOOD: name matches assertion
fn test_slice_creates_copy() raises:
    assert_true(not sliced._is_view)
```
