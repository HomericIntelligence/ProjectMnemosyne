---
name: mojo-bounds-test-pattern
description: 'Pattern for adding symmetric boundary condition tests in Mojo by mirroring
  existing analogous tests. Use when: (1) adding a missing bounds check test, (2)
  implementing follow-up coverage for __setitem__/__getitem__ boundary conditions.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Name | mojo-bounds-test-pattern |
| Category | testing |
| Trigger | Adding missing boundary condition test that mirrors an existing one |
| Output | New test function + main() call following existing pattern |

## When to Use

- Issue asks to add a negative index test analogous to an out-of-bounds test
- You need to cover the `index < 0` branch of a bounds check
- An existing test covers `index >= size` and you need the symmetric `index < 0` case
- Adding follow-up test coverage identified in code review

## Verified Workflow

1. **Find the analogous test first** — search for `test_setitem_out_of_bounds` or similar
2. **Read the full test file** to understand the pattern (try/except with `raised` flag)
3. **Copy the test function** and change only the index value and error message
4. **Add the call in `main()`** after the analogous test
5. **Commit** — pre-commit hooks will validate (mojo format, test count badge)
6. **Note**: Mojo tests cannot run locally on older GLIBC systems; CI validates correctness

## Pattern

```mojo
fn test_setitem_negative_index() raises:
    """Test that __setitem__ raises error for negative index."""
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.float32)

    var raised = False
    try:
        t[-1] = 1.0
    except:
        raised = True

    if not raised:
        raise Error("__setitem__ should raise error for negative index")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run mojo test locally | `pixi run mojo test tests/shared/core/test_utility.mojo` | GLIBC_2.32/2.33/2.34 not found on host OS | Mojo tests must run in Docker/CI on this dev machine |

## Results & Parameters

- **File modified**: `tests/shared/core/test_utility.mojo`
- **Lines added**: 17 (function + main() call)
- **Pre-commit hooks**: All passed (mojo format, validate-test-coverage, trailing whitespace)
- **PR**: #4065 on ProjectOdyssey with auto-merge enabled
- **Issue**: #3387 (follow-up from #3165)
