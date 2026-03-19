---
name: mojo-moveinit-list-corruption
description: 'Diagnose Mojo 0.26.1 bug where ^ transfer of List in __moveinit__ corrupts
  in-place-mutated values. Use when: struct move breaks assertions on List-derived
  data, or considering switching .copy() to ^ in __moveinit__ for performance.'
category: debugging
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Mojo version | 0.26.1 |
| Affected type | `List[T]` fields in `__moveinit__` |
| Symptom | List element values wrong after move; assertions on shape/stride fail |
| Root cause | In-place mutations to List elements (`list[i] = val`) are lost when the List is then moved via `^` in a `deinit` move constructor |
| Fix | Keep `.copy()` for List fields in `__moveinit__`; document why |

## When to Use

Trigger this skill when:

1. A test assertion on a value derived from a List field (shape, strides, etc.) suddenly fails with an unexpected value
2. You are debugging why `ExTensor.slice()` or any method that mutates `_shape[i]`/`_strides[i]` in-place and then returns via `return result^` produces wrong shapes
3. A PR proposes replacing `.copy()` with `^` in `ExTensor.__moveinit__` (or any struct with List fields that are mutated in-place before being moved)
4. CI shows `Core Tensors` or `test_slicing.mojo` failing with `Batch shape[N]` assertion error after a change to `__moveinit__`

## Verified Workflow

### Step 1: Identify the pattern

Look for this combination in Mojo code:

```mojo
fn some_method(self, ...) raises -> Self:
    var result = self.copy()        # __copyinit__: makes new List
    result._shape[axis] = new_val  # in-place mutation of List element
    return result^                 # __moveinit__: transfers result
```

If `__moveinit__` uses `existing._shape^`, the `new_val` written at step 2 may be lost.

### Step 2: Reproduce with a minimal case

```mojo
fn test_moveinit_list_mutation():
    # Create struct, mutate a list field, return via ^
    var t = ExTensor(...)
    var sliced = t.slice(2, 5, axis=0)
    assert sliced.shape()[0] == 3  # This will FAIL if ^ is used in __moveinit__
```

### Step 3: Confirm the fix

Keep `.copy()` in `__moveinit__` for List fields. The `.copy()` creates a fresh list that correctly captures the mutated state:

```mojo
fn __moveinit__(out self, deinit existing: Self):
    """Move constructor - transfers ownership.

    For safety, we copy the List fields instead of moving them with ^
    to avoid potential corruption issues with List's internal buffer.
    """
    self._data = existing._data
    self._shape = existing._shape.copy()    # NOT existing._shape^
    self._strides = existing._strides.copy()  # NOT existing._strides^
    self._dtype = existing._dtype
    # ... scalar fields can use direct assignment
```

### Step 4: Verify the ADR / comment is accurate

The comment "to avoid potential corruption issues with List's internal buffer" is **correct**. Do not remove it thinking it is wrong. Update the ADR (e.g. ADR-009) to record this finding explicitly so future engineers don't repeat the investigation.

### Step 5: Check CI

After reverting `^` to `.copy()`, confirm:
- `test_slicing.mojo` passes (especially `test_batch_extraction_uses_view`)
- `test_trait_based_serialization.mojo` stops crashing
- All shape-dependent assertions pass

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Replace `.copy()` with `^` in `ExTensor.__moveinit__` | Hypothesis: `.copy()` orphaned source List buffers, causing heap corruption at 15+ tests | `test_slicing.mojo` assertion `Batch shape[2]` failed — `slice()` mutates `result._shape[axis]` in-place then returns `result^`; the `^` transfer loses the mutation | In Mojo 0.26.1, `^` on a List field in `__moveinit__` does not preserve in-place element mutations made before the move |
| Checking other structs that use `^` | `attention.mojo`, `variable.mojo`, `tape_types.mojo` all use `^` for List — so it should work for ExTensor too | Those structs never mutate List elements in-place before moving; ExTensor's `slice()` does, which is the key difference | `^` on List is safe only when the List was not mutated in-place between `__copyinit__` and `__moveinit__` |
| Consolidating 5 split test files into one `test_lenet5_layers.mojo` | If `__moveinit__` was the root cause, 24 tests in one file should now be safe | The `^` fix was wrong, so consolidation was premature; would likely re-introduce original heap corruption at 15+ tests | Do not reconsolidate until the actual root cause of the heap corruption is confirmed |

## Results & Parameters

### Confirmed behavior in Mojo 0.26.1

```
ExTensor.slice(start, end, axis) pattern:
  1. var result = self.copy()          # __copyinit__: OK, list is fresh copy
  2. result._shape[axis] = end-start   # in-place mutation: OK so far
  3. return result^                    # __moveinit__ triggered:
     - with .copy(): shape[axis] = end-start ✅
     - with ^:       shape[axis] = original value ❌ (mutation lost)
```

### Diagnostic: which `__moveinit__` variant to use

```
Does the struct have List fields that get mutated in-place BEFORE being moved?
├── YES → Use .copy() in __moveinit__ for those fields
└── NO  → ^ is safe and preferred
```

### Key files in ProjectOdyssey

- `shared/core/extensor.mojo` — `ExTensor.__moveinit__` at line ~417
- `shared/core/extensor.mojo` — `ExTensor.slice()` at line ~604 (the in-place mutation at line ~675)
- `tests/shared/core/test_slicing.mojo` — `test_batch_extraction_uses_view()` is the canary test
- `docs/adr/ADR-009-heap-corruption-workaround.md` — Finding #6 added 2026-03-06

### mojo format fix (separate issue found in same PR)

Three long ternary expressions in `shared/testing/layer_testers.mojo` exceeded line length. CI `mojo format` wraps them:

```mojo
# Before (fails CI pre-commit):
var epsilon = GRADIENT_CHECK_EPSILON_FLOAT32 if dtype == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER

# After (passes CI pre-commit):
var epsilon = (
    GRADIENT_CHECK_EPSILON_FLOAT32 if dtype
    == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER
)
```
