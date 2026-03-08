---
name: extensor-hash-api-docs
description: "Document trait-implementing special methods in Mojo struct docstrings and package __init__.mojo API listings. Use when: a new dunder method is added to a Mojo struct but not mentioned in docs or the package module listing."
category: documentation
date: 2026-03-07
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| **Category** | documentation |
| **Effort** | Low (docs-only, no logic changes) |
| **Files Changed** | 2 (`extensor.mojo`, `shared/core/__init__.mojo`) |
| **Scope** | Mojo struct docstrings + package `__init__.mojo` |

## When to Use

- A `__hash__`, `__eq__`, `__lt__`, or similar trait-implementing dunder method was added to a Mojo struct but is not mentioned in the module docstring or package listing
- A follow-up issue explicitly asks to add the method to "API documentation" or "public API surface"
- The package `__init__.mojo` module-level `Modules:` table or section comment is missing a trait mention
- A PR review notes that a new method is undocumented

## Verified Workflow

1. **Locate the method** with `Grep` for `__hash__` (or the target method) in the `.mojo` file
2. **Read surrounding context** — check both the method docstring and the struct-level docstring
3. **Update the method docstring** in `extensor.mojo`:
   - Add a sentence explaining the trait being implemented (`Hashable`, `Comparable`, etc.)
   - Add a `Note:` section explaining the algorithm (what data is hashed, any edge cases)
   - Expand the `Example:` block with equality and inequality cases
4. **Update `shared/core/__init__.mojo`** in two places:
   - Module-level `Modules:` table entry for `extensor` — append `(ExTensor, implements Hashable via __hash__)`
   - Section comment above the `from shared.core.extensor import (` block — add a one-liner note
5. **Run pre-commit** (`just precommit`) to verify Mojo format and markdown lint pass
6. **Commit, push, create PR** — pre-commit hooks validate automatically on commit

## Results & Parameters

### Docstring Pattern

```mojo
fn __hash__[H: Hasher](self, mut hasher: H):
    """Compute hash based on shape, dtype, and data.

    ExTensor implements the `Hashable` trait, allowing tensors to be used as
    dictionary keys or in hash-based data structures. Two tensors with identical
    shape, dtype, and element values will produce the same hash.

    Parameters:
        H: The hasher type conforming to the Hasher trait.

    Args:
        hasher: The hasher to write values into.

    Note:
        The hash is computed from the tensor's shape dimensions, dtype ordinal,
        and raw bit patterns of all element values. NaN values with different
        bit representations will hash differently.

    Example:
        ```mojo
        from hashlib import hash
        var x = ones([3], DType.float32)
        var h = hash(x)

        # Tensors with identical shape, dtype, and values hash equally
        var y = ones([3], DType.float32)
        assert hash(x) == hash(y)

        # Tensors with different shapes hash differently
        var z = ones([4], DType.float32)
        # hash(x) != hash(z)  (with overwhelming probability)
        ```
    """
```

### `__init__.mojo` Module Listing Pattern

```mojo
Modules:
    extensor: Core tensor type (ExTensor, implements Hashable via __hash__) and creation functions
```

### `__init__.mojo` Section Comment Pattern

```mojo
# ============================================================================
# Core Tensor Type and Creation Functions
# ============================================================================
# ExTensor implements the Hashable trait (__hash__), allowing tensors to be
# used as dictionary keys or in hash-based data structures via hash(tensor).

from shared.core.extensor import (
    ExTensor,
    ...
)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching for `__hash__` without context | Grepped for `__hash__` alone | Found the method but missed that the docstring `Example` was already present but minimal | Always read `-C 10` context to see the full docstring before editing |
| Trying to add `__hash__` to the import list | Considered adding `__hash__` as an explicit re-export in `__init__.mojo` | Dunder methods are not importable symbols — they are trait implementations on the struct | Document dunders via comments and docstrings, not import lists |
| Reading the full `extensor.mojo` file | Attempted `Read` on the full file | File exceeds 25K token limit, read fails | Use `Grep` with `-C` context for targeted reads; use `offset`+`limit` for specific line ranges |
