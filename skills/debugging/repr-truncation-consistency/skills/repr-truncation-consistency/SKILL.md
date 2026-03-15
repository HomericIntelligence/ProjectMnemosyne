---
name: repr-truncation-consistency
description: "Apply NumPy-style truncation to __repr__ for consistency with __str__. Use when: a class has truncated __str__ but untruncated __repr__, or repr() on large objects causes performance issues."
category: debugging
date: 2026-03-15
user-invocable: false
---

# repr-truncation-consistency

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Issue** | #4038 - Apply `__repr__` truncation for consistency with `__str__` |
| **Objective** | Make `repr()` on large `ExTensor` objects safe by applying the same threshold-based truncation already in `__str__` |
| **Outcome** | ✅ Success — `__repr__` now mirrors `__str__` truncation (threshold=1000, show 3+3 with `...`) |
| **PR** | #4858 |

## When to Use

Use this skill when:

- A class added `__str__` truncation but `__repr__` was missed (common follow-up issue)
- `repr()` on large tensor/array objects produces extremely long strings
- CI or logs are flooding due to untruncated debug output
- Fixing a "follow-up from #XXXX" issue where `__str__` was fixed but `__repr__` was not

## Verified Workflow

### 1. Read the Existing `__str__` Implementation

Before touching `__repr__`, read the `__str__` method to understand the truncation pattern already in use:

```bash
grep -n "fn __str__\|fn __repr__\|TRUNCATE_THRESHOLD\|SHOW_ELEMENTS" <file>
```

Capture the exact constants and logic to replicate faithfully.

### 2. Update `__repr__` with the Same Constants and Branch

Replace the unguarded loop with the threshold check:

```mojo
fn __repr__(self) -> String:
    """Detailed representation for debugging with NumPy-style truncation.

    For tensors with more than 1000 elements, shows only the first 3 and
    last 3 elements with '...' in between to prevent performance issues.
    """
    comptime TRUNCATE_THRESHOLD = 1000
    comptime SHOW_ELEMENTS = 3

    # ... build shape/dtype prefix ...
    result += ", data=["
    if self._numel > TRUNCATE_THRESHOLD:
        for i in range(SHOW_ELEMENTS):
            if i > 0:
                result += ", "
            result += String(self._get_float64(i))
        result += ", ..."
        for i in range(self._numel - SHOW_ELEMENTS, self._numel):
            result += ", " + String(self._get_float64(i))
    else:
        for i in range(self._numel):
            if i > 0:
                result += ", "
            result += String(self._get_float64(i))
    result += "])"
    return result
```

**Key rule**: Use `comptime` constants (not hardcoded literals) so they match `__str__` exactly
and can be updated in one place later.

### 3. Write Tests Mirroring `test_<class>_str.mojo`

Create `test_<class>_repr.mojo` following the same test case structure as the existing `__str__` test
file. Required coverage:

| Test | What It Checks |
|------|----------------|
| Empty tensor (numel=0) | No crash, correct format |
| Single element | Full output, no truncation |
| Small tensor (numel ≤ threshold) | All elements shown, no `...` |
| Exactly at threshold | No truncation (boundary condition) |
| numel = threshold + 1 | Truncation activates |
| Large tensor format | Correct prefix/suffix, last 3 elements present |
| dtype preserved | dtype appears in repr string |
| Shape preserved | shape/numel appear in repr (if `__repr__` includes them) |
| Edge case: 6 elements | No truncation near SHOW_ELEMENTS * 2 |
| Empty int/non-float dtypes | No crashes for non-default dtypes |

### 4. Verify Existing Tests Still Pass

Check that any existing `test_repr_*` tests (e.g., `test_repr_complete`) use tensors with
fewer elements than the threshold so they are unaffected by the change.

```bash
grep -rn "repr\|__repr__" tests/ | grep -v "test_extensor_repr"
```

### 5. Commit and PR

```bash
git add <file.mojo> tests/<category>/test_<class>_repr.mojo
git commit -m "fix(<scope>): apply __repr__ truncation for consistency with __str__

Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using hardcoded `1000` and `3` in `__repr__` | Copied literals from `__str__` directly | Would diverge if constants are updated in `__str__` later | Always use `comptime` named constants, not literals |
| Skipping tests for `__repr__` | Assumed `__str__` tests provided sufficient coverage | `__repr__` has different output format (includes shape/numel) so format assertions differ | Mirror the `__str__` test file but adjust expected strings for `__repr__` format |

## Results & Parameters

```
Truncation threshold: 1000 elements
Elements shown at each end: 3
Format: <prefix>, data=[v0, v1, v2, ..., vN-2, vN-1, vN])
Test cases added: 11
Files modified: 1 source + 1 new test file
```

### Key Invariants

- Tensors with `numel <= 1000`: all elements shown, no `...`
- Tensors with `numel > 1000`: first 3 + `...` + last 3 shown
- Empty tensor (`numel == 0`): `data=[]` with no errors
- The `...` only appears in the `data=[...]` section, not in shape/dtype

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #4858, Issue #4038 | [notes.md](../references/notes.md) |
