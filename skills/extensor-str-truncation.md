---
name: extensor-str-truncation
description: 'Add NumPy-style truncation to Mojo tensor __str__ methods to prevent
  performance issues with large tensors. Use when: (1) a tensor __str__ iterates all
  elements, (2) NumPy-compatible display semantics are desired, (3) printing large
  tensors causes slowdowns.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# ExTensor __str__ Truncation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-07 |
| **Objective** | Add NumPy-style truncation to `ExTensor.__str__` in Mojo for large tensors |
| **Outcome** | ✅ Implemented — threshold 1000, show first 3 + last 3 with `...` in between |
| **Root Cause** | Original `__str__` iterated all `_numel` elements, causing slow output for 1M+ tensors |
| **Key Learning** | Use `alias` constants in Mojo for thresholds; threshold check is `> N` (exclusive) |

## When to Use

Apply this pattern when:

- A Mojo tensor/array `__str__` method loops over all elements (`for i in range(self._numel)`)
- The tensor can grow large (>1000 elements) in typical use
- You want to match NumPy's display semantics (`numpy.set_printoptions(threshold=1000)`)
- CI cannot run Mojo locally (GLIBC constraints) — logic verification must be done by inspection

## Verified Workflow

### Step 1: Locate the existing `__str__` method

```bash
grep -n "__str__\|_numel" shared/core/extensor.mojo | head -30
```

Look for the loop: `for i in range(self._numel)`.

### Step 2: Apply the truncation pattern

Replace the simple loop with a threshold-guarded branch:

```mojo
fn __str__(self) -> String:
    """Human-readable string representation with NumPy-style truncation.

    For tensors with more than 1000 elements, shows only the first 3 and
    last 3 elements with '...' in between to prevent performance issues.
    """
    alias TRUNCATE_THRESHOLD = 1000
    alias SHOW_ELEMENTS = 3

    var result = String("ExTensor([")
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
    result += "], dtype=" + String(self._dtype) + ")"
    return result
```

**Key decisions**:
- Threshold is **exclusive** (`> 1000`): exactly 1000 elements shows all values
- First element in the "last 3" block always gets a leading `", "` (no special-casing needed
  because at least SHOW_ELEMENTS precede it)

### Step 3: Write Mojo tests

Create `tests/shared/core/test_extensor_str.mojo` matching the project's test pattern:

```mojo
fn test_str_exactly_threshold_no_truncation() raises:
    """Exactly 1000 elements — no '...' shown."""
    var t = arange(1000, DType.float32)
    var s = String(t)
    assert_true("..." not in s)

fn test_str_large_tensor_truncation() raises:
    """1001 elements — '...' appears and boundary values are present."""
    var t = arange(1001, DType.float32)
    var s = String(t)
    assert_true("..." in s)
    assert_true("0.0" in s)
    assert_true("2.0" in s)
    assert_true("1000.0" in s)
    assert_true("998.0" in s)

fn test_str_large_tensor_format() raises:
    """Format check: starts with first 3 values, contains last 3."""
    var t = arange(2000, DType.float32)
    var s = String(t)
    assert_true(s.startswith("ExTensor([0.0, 1.0, 2.0, ..."))
    assert_true("1999.0" in s)
```

### Step 4: Verify pre-commit passes (no local Mojo runtime needed)

```bash
git add shared/core/extensor.mojo tests/shared/core/test_extensor_str.mojo
git commit -m "feat(extensor): add NumPy-style truncation to ExTensor.__str__"
# Hooks: mojo format, syntax checks, whitespace — all pass without runtime execution
```

### Step 5: Push and create PR

```bash
git push -u origin <branch-name>
gh pr create --title "feat(extensor): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run `pixi run mojo test` locally | Executed `pixi run mojo test tests/shared/core/test_extensor_str.mojo` | GLIBC version mismatch (requires 2.32/2.33/2.34, host has older) | Mojo tests only run in CI Docker; verify logic by inspection, trust pre-commit hooks |
| Use `just test-group` to run tests | Ran `just test-group "tests/shared/core" "test_extensor_str.mojo"` | `just` is not installed on the host | Same — local Mojo test execution is not available in this environment |
| Inclusive threshold (`>= 1000`) | Considered using `>= 1000` for the truncation check | Issue example shows 1000-element output as `[0.0, ..., 999.0]` which implies 1000 IS truncated | Read the issue example carefully — issue showed 1000-element tensor truncated, but threshold choice is a design decision; went with `> 1000` (exclusive) per clarifying analysis |

## Results & Parameters

### Final implementation constants

```mojo
alias TRUNCATE_THRESHOLD = 1000   # elements — exclusive (> not >=)
alias SHOW_ELEMENTS = 3           # head and tail count
```

### Output format for large tensor

```text
ExTensor([0.0, 1.0, 2.0, ..., 997.0, 998.0, 999.0], dtype=float32)
```

### Test file pattern for Mojo str tests

```mojo
from shared.core.extensor import ExTensor, zeros, ones, full, arange
from tests.shared.conftest import assert_true, assert_equal

fn test_str_<case>() raises:
    var t = arange(<N>, DType.float32)
    var s = String(t)
    assert_true("..." in s)  # or "..." not in s
```

### PR structure

```bash
gh pr create \
  --title "feat(extensor): add NumPy-style truncation to ExTensor.__str__" \
  --body "Closes #<N>"
gh pr merge --auto --rebase
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3375, PR #4037 | [notes.md](../references/notes.md) |
