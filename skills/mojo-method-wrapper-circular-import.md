---
name: mojo-method-wrapper-circular-import
description: 'Add ergonomic method wrappers to Mojo structs that delegate to standalone
  functions, avoiding circular imports via local-scope imports inside method bodies.
  Use when: adding method-style API alongside existing functional API where the functional
  module imports the struct.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Need `tensor.tile([3])` method-style calls alongside existing `tile(tensor, [3])` functional calls |
| **Constraint** | `shape.mojo` (functional implementations) imports `ExTensor` at module level — adding a top-level import of `shape` in `extensor.mojo` creates a circular import |
| **Solution** | Local-scope imports inside each method body defer resolution to call time |
| **Pattern** | Thin wrapper: method body is 1-2 lines that import and call the functional implementation |
| **Outcome** | PR #3803 merged, all pre-commit hooks pass, no logic duplication |

## When to Use

1. A struct (`ExTensor`) needs ergonomic method-style wrappers for operations that live in a separate module
2. The operations module imports the struct at module level (creating a circular dependency at top-level)
3. The goal is DRY — no logic duplication, just delegation
4. The functional API must remain available alongside the method API (backwards compatibility)

## Verified Workflow

### Step 1: Identify the circular dependency

```
extensor.mojo  ──imports──▶  (nothing from shape.mojo at module level)
shape.mojo     ──imports──▶  ExTensor from extensor.mojo
```

Adding `from shared.core.shape import tile` at the top of `extensor.mojo` would create:
```
extensor.mojo  ──imports──▶  shape.mojo  ──imports──▶  extensor.mojo  ✗ CIRCULAR
```

### Step 2: Add wrapper methods with local-scope imports

Place wrappers after the existing method they logically extend (e.g., after `slice()`):

```mojo
fn tile(self, reps: List[Int]) raises -> ExTensor:
    """Tile tensor by repeating along each dimension.

    Delegates to the functional `tile()` in `shared.core.shape`.

    Args:
        reps: Number of repetitions along each dimension.

    Returns:
        Tiled tensor with shape[i] = input_shape[i] * reps[i].

    Raises:
        Error: If reps is empty.

    Example:
    ```mojo
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var b = a.tile([3])  # [0, 1, 2, 0, 1, 2, 0, 1, 2]
    ```
    """
    from shared.core.shape import tile as _tile
    return _tile(self, reps)
```

Key details:
- Import is **inside the method body** (`from shared.core.shape import tile as _tile`)
- Use `as _tile` alias to avoid shadowing the method name itself
- For methods returning owned values (`List[ExTensor]`), use the `^` transfer operator: `return _split(self, num_splits, axis)^`

### Step 3: Handle ownership for List-returning methods

```mojo
fn split(self, num_splits: Int, axis: Int = 0) raises -> List[ExTensor]:
    from shared.core.shape import split as _split
    return _split(self, num_splits, axis)^  # ^ transfers ownership
```

### Step 4: Write tests that compare method vs functional output

```mojo
fn test_tile_method_1d() raises:
    var a = arange(0.0, 3.0, 1.0, DType.float32)
    var reps = List[Int]()
    reps.append(3)

    var expected = tile(a, reps)   # functional
    var actual = a.tile(reps)      # method wrapper

    assert_equal(actual.numel(), expected.numel())
    for i in range(actual.numel()):
        assert_almost_equal(Float64(actual[i]), Float64(expected[i]), tolerance=1e-6)
```

### Step 5: Verify pre-commit passes

```bash
git add shared/core/extensor.mojo tests/shared/core/test_extensor_method_api.mojo
git commit -m "feat(extensor): add tile/repeat/permute/split method wrappers"
# Mojo Format: Passed
# Validate Test Coverage: Passed
# Check for deprecated List[Type](args) syntax: Passed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Top-level import | Added `from shared.core.shape import tile, repeat, permute, split` at top of `extensor.mojo` | Would create circular import: `extensor → shape → extensor` | Mojo resolves module-level imports eagerly; circular deps at module level are fatal |
| Re-implementing logic | Copying the implementation from `shape.mojo` into each method | Violates DRY; doubles maintenance burden; bugs fixed in one place don't propagate | Never duplicate logic; use delegation |
| `alias` trick | Tried using `alias` to defer the import | Alias is compile-time constant, not a deferred import mechanism | Only function-body imports in Mojo can avoid circular resolution |

## Results & Parameters

### Methods added (copy-paste template)

```mojo
fn tile(self, reps: List[Int]) raises -> ExTensor:
    from shared.core.shape import tile as _tile
    return _tile(self, reps)

fn repeat(self, n: Int, axis: Int = -1) raises -> ExTensor:
    from shared.core.shape import repeat as _repeat
    return _repeat(self, n, axis)

fn permute(self, dims: List[Int]) raises -> ExTensor:
    from shared.core.shape import permute as _permute
    return _permute(self, dims)

fn split(self, num_splits: Int, axis: Int = 0) raises -> List[ExTensor]:
    from shared.core.shape import split as _split
    return _split(self, num_splits, axis)^
```

### Placement rule

Insert wrappers **after** the last existing method that they logically extend.
In this case, `tile/repeat/permute/split` were placed after `slice()` — the
analogous existing method that is already a method wrapper for a shape operation.

### Test file pattern

Create `tests/shared/core/test_extensor_method_api.mojo` with:
- For each method: one test comparing method output to functional output
- One test verifying correct element values (not just size)
- One test verifying output shape for multi-dim operations
- `main()` that runs all tests in order with `print()` checkpoints
