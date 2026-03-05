---
name: port-feature-branch-impl
description: "Port an implementation from a stale feature branch worktree when the upstream PR was never merged to main. Use when: a test or follow-up issue references functionality that exists only in a worktree branch, not in main."
category: testing
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Trigger** | Follow-up issue assumes a prior implementation is in main, but grep finds nothing |
| **Outcome** | Port the implementation directly, unblock the test, close the follow-up |
| **Risk** | Low — copying known-working code from an existing worktree |
| **Time** | ~10 minutes |

## When to Use

- A test file has `# TODO(#NNN): Implement X` comments blocking a test
- The follow-up issue says "now that X is implemented, activate the test"
- `grep` for the function/method in `main` returns no results
- The original implementation PR is still open or was abandoned on a feature branch
- A worktree for the original issue still exists at `.worktrees/issue-NNN/`

## Verified Workflow

### 1. Confirm the gap

```bash
grep -rn "fn __hash__" shared/core/extensor.mojo   # returns nothing
```

### 2. Locate the implementation in the worktree

```bash
grep -rn "__hash__" /path/to/.worktrees/ | grep "shared/core/extensor.mojo"
# => .worktrees/issue-2722/shared/core/extensor.mojo:2767:    fn __hash__(self) -> UInt:
```

### 3. Read the implementation

Read lines 2767–2793 of `.worktrees/issue-2722/shared/core/extensor.mojo`.

Check for any local imports inside the function body (e.g., `from shared.core.dtype_ordinal import ...`)
and verify those modules exist in the current branch:

```bash
ls shared/core/dtype_ordinal.mojo   # must exist
```

### 4. Port the implementation

Insert the function into the current `extensor.mojo` at the same logical location
(after the last `__dunder__` method, before the utility section).

Use `Edit` tool — do NOT copy-paste via bash.

### 5. Activate the blocked test

Replace commented-out test body with real assertions. Remove the `pass  # Placeholder` line.

### 6. Add the companion test from the issue plan

The issue plan (read via `gh issue view NNN --comments`) specifies exact test code.
Follow it precisely — do not improvise.

### 7. Fix imports in the test file

`hash()` returns `UInt`, not `Int`. `assert_equal_int(a: Int, b: Int)` will NOT work.
Use `assert_equal[T: Comparable]` instead.

Add any missing imports (`assert_equal`, `assert_true`) to the test file's import block.

### 8. Register the new test in `main()`

Add the call after the existing related test call.

### 9. Commit with conventional format

```
test(utility): activate __hash__ test and add different-values test

Port __hash__ implementation from issue-2722 branch into extensor.mojo,
then activate the commented-out test_hash_immutable test and add
test_hash_different_values to verify distinct hashes for unequal tensors.

Closes #3163
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `assert_equal_int` for hash comparison | Called `assert_equal_int(hash_a, hash_b, ...)` directly since that was the existing pattern in the file | `hash()` returns `UInt`, `assert_equal_int` only accepts `Int` — type mismatch | Always check the return type of `hash()` before choosing the assert helper; use `assert_equal[T: Comparable]` for `UInt` |
| Assume `__hash__` was in main | Proceeded toward test activation without first grepping for the implementation | Implementation only existed on the `issue-2722` feature branch, never merged | grep for the function/method FIRST before touching the test file |
| Wait for the blocked PR to merge | The issue description says "now that `__hash__` is implemented" — assumed it had landed | The PR existed only on a feature branch (`2722-auto-impl`) | Check `git log --oneline main | grep <keyword>` or grep in `shared/` to confirm before assuming |

## Results & Parameters

### Hash implementation ported (Mojo)

```mojo
fn __hash__(self) -> UInt:
    """Compute hash based on shape, dtype, and data."""
    from shared.core.dtype_ordinal import dtype_to_ordinal

    var h: UInt = 0
    for i in range(len(self._shape)):
        h = h * 31 + UInt(self._shape[i])
    h = h * 31 + UInt(dtype_to_ordinal(self._dtype))
    for i in range(self._numel):
        var val = self._get_float64(i)
        var int_bits = Int(val * 1000000.0)
        h = h * 31 + UInt(int_bits)
    return h
```

### Test pattern (Mojo)

```mojo
fn test_hash_immutable() raises:
    """Test __hash__ for immutable tensors."""
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var b = arange(0.0, 3.0, 1.0, DType.float32)
    var hash_a = hash(a)
    var hash_b = hash(b)
    assert_equal(hash_a, hash_b, "Equal tensors should have same hash")


fn test_hash_different_values() raises:
    """Test __hash__ produces different values for different tensors."""
    var a = arange(1.0, 4.0, 1.0, DType.float32)  # [1, 2, 3]
    var b = arange(4.0, 7.0, 1.0, DType.float32)  # [4, 5, 6]
    assert_true(
        hash(a) != hash(b),
        "Tensors with different values should have different hashes",
    )
```

### Import fix required

```mojo
# Before
from tests.shared.conftest import (
    assert_equal_int,
    assert_almost_equal,
)

# After — add assert_equal and assert_true
from tests.shared.conftest import (
    assert_equal_int,
    assert_equal,
    assert_almost_equal,
    assert_true,
)
```
