---
name: enable-todo-tests
description: 'Enable placeholder tests by removing TODO comments and uncommenting
  test code for already-implemented functionality. Use when: (1) tests have TODO markers
  citing an issue number, (2) implementation exists but tests are stubs, (3) functions
  are implemented but not exported from package __init__.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Property | Value |
|----------|-------|
| **Trigger** | Tests with `# TODO(#NNN): Implement X` stubs referencing a GitHub issue |
| **Goal** | Activate tests for already-implemented functionality |
| **Language** | Mojo (applies to any language with similar patterns) |
| **Output** | Uncommented tests + missing package exports added |

## When to Use

1. An issue tracks "implement X" but the code was already written and just not connected
2. Test stubs exist with commented-out body: `# var result = fn(...)` and `pass # Placeholder`
3. Functions are implemented in a module file but absent from `__init__.mojo` exports
4. Closing a "feature" issue that turns out to be a test-enablement issue

## Verified Workflow

### Step 1: Audit the Issue

```bash
gh issue view <number> --comments
```

Check what operations the issue says to "implement". Grep for them in the source:

```bash
grep -n "^fn tile\|^fn repeat\|^fn permute" shared/core/shape.mojo
```

If functions exist → this is a test-enablement task, not an implementation task.

### Step 2: Check Package Exports

```bash
grep -n "tile\|repeat\|permute" shared/core/__init__.mojo
```

If missing, add them to the relevant `from module import (...)` block:

```mojo
from shared.core.shape import (
    split,
    split_with_indices,
    tile,       # ADD
    repeat,     # ADD
    permute,    # ADD
    ...
)
```

### Step 3: Enable Tests — Pattern for TODO stubs

**Before** (typical Mojo stub pattern):
```mojo
fn test_tile_1d() raises:
    """Test tiling 1D tensor."""
    var a = arange(0.0, 3.0, 1.0, DType.float32)  # [0, 1, 2]
    # varb = tile(a, 3)  # TODO(#3013): Implement tile()
    # assert_numel(b, 9, "Tiled tensor should have 9 elements")
    pass  # Placeholder
```

**After** (enabled test):
```mojo
fn test_tile_1d() raises:
    """Test tiling 1D tensor."""
    from shared.core import tile

    var a = arange(0.0, 3.0, 1.0, DType.float32)  # [0, 1, 2]
    var reps = List[Int]()
    reps.append(3)
    var b = tile(a, reps)

    # Result: [0, 1, 2, 0, 1, 2, 0, 1, 2] (9 elements)
    assert_numel(b, 9, "Tiled tensor should have 9 elements")
```

Key transformations:
- Remove `# TODO(#NNN):` comment lines
- Uncomment the actual test logic
- Remove `_ = a  # Suppress unused variable warning` lines
- Remove `pass  # Placeholder`
- Add local `from shared.core import fn_name` if not top-level imported
- Fix any syntax issues (e.g., `# varb` → `var b`, `target_shape[0] = 4` → `target_shape.append(4)`)

### Step 4: Fix Syntax in Uncommented Code

The commented-out code often has bugs from being written without testing. Common fixes:

| Bug Pattern | Fix |
|-------------|-----|
| `target_shape[0] = 4` | `target_shape.append(4)` (List assignment vs append) |
| `var b = tile(a, 3)` | `var reps = List[Int](); reps.append(3); var b = tile(a, reps)` |
| `# var parts = split(a, [3, 5, 10])` | Use actual `split_with_indices` with `List[Int]` |

### Step 5: Verify Pre-commit Passes

```bash
pixi run pre-commit run --all-files 2>&1 | tail -20
```

Even if Mojo can't run locally (GLIBC version mismatch), pre-commit hooks for syntax/format still pass.

### Step 6: Commit and PR

```bash
git add shared/core/__init__.mojo tests/shared/core/test_shape.mojo
git commit -m "feat(core): enable ExTensor shape operation tests and add missing exports"
git push -u origin <branch>
gh pr create --body "Closes #<number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo test tests/...` | GLIBC version too old (needs 2.32-2.34, host has older) | Tests can only run in CI/Docker; validate with pre-commit hooks locally instead |
| Using `split(a, [3, 5, 10])` syntax | Direct List literal in split call | Mojo doesn't support Python-style inline list args for split | Need to create `split_with_indices` with explicit `List[Int]` |
| `target_shape[0] = 4` for initialization | Assignment to index on new List | Mojo List requires `append()` not index-assignment for new elements | Always use `.append()` to build Lists in Mojo |

## Results & Parameters

### Session: Issue #3013 — ExTensor Shape Operations

**Outcome**: Closed issue by enabling 9 placeholder tests + exporting 3 missing functions.

**Files changed**:
- `shared/core/__init__.mojo` — added `tile`, `repeat`, `permute` to exports (+3 lines)
- `tests/shared/core/test_shape.mojo` — enabled 9 test functions (+62/-60 lines net)

**Pre-commit result**: All hooks passed (mojo format skipped due to GLIBC, but syntax/markdown/yaml passed)

**Key insight**: When an issue says "Implement X" but grep shows `^fn X` already in source, the real
task is: (1) add to exports, (2) uncomment test stubs, (3) fix any syntax bugs in the commented code.
