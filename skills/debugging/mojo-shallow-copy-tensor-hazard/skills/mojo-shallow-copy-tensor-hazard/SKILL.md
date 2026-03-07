---
name: mojo-shallow-copy-tensor-hazard
description: "Fix Mojo tensor mutation caused by shallow copy sharing _data pointer. Use when: a function mutates a tensor copy but silently corrupts the caller's original tensor."
category: debugging
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `tensor.copy()` in Mojo is `__copyinit__` — a shallow copy sharing the underlying `_data` buffer |
| **Symptom** | Mutations to the copy silently corrupt the caller's original tensor |
| **Fix** | Replace `tensor.copy()` with `_deep_copy(tensor)` to get an independent buffer |
| **Context** | Discovered in `shared/testing/gradient_checker.mojo` during finite-difference gradient checking |
| **Affects** | Any code that copies a tensor and then calls `_set_float64` / `_set_float32` on the copy |

## When to Use

- A function receives a tensor argument, makes a "copy", mutates the copy, and the caller sees unexpected value changes
- Numerical gradient checks produce wrong results despite correct mathematical derivations
- Tests pass individually but fail when run together (shared buffer corruption)
- Debugging silent data corruption in Mojo tensor operations involving `.copy()`

## Verified Workflow

1. **Identify the shallow copy** — search for `.copy()` on tensor variables passed into functions that mutate them:

   ```bash
   grep -n "\.copy()" shared/testing/gradient_checker.mojo
   ```

2. **Confirm shared buffer** — add a debug print of the pointer address before and after mutation to verify the addresses match.

3. **Replace with deep copy** — swap `input.copy()` for `_deep_copy(input)`:

   ```mojo
   # Before (shallow copy — shares _data pointer)
   var input_copy_plus = input.copy()
   var input_copy_minus = input.copy()

   # After (deep copy — independent buffer)
   var input_copy_plus = _deep_copy(input)
   var input_copy_minus = _deep_copy(input)
   ```

4. **Add regression test** — snapshot all element values before the call, run the function, assert values unchanged:

   ```mojo
   fn test_function_does_not_mutate_input() raises:
       var x = full([2, 2], 1.0, DType.float32)

       var before = List[Float64]()
       for i in range(x.numel()):
           before.append(x._get_float64(i))

       _ = check_gradients(forward, backward, x, epsilon=1e-5, tolerance=1e-2)

       for i in range(x.numel()):
           assert_equal(x._get_float64(i), before[i],
               "function mutated input at index " + String(i))
   ```

5. **Apply to all sites** — grep for every `input.copy()` / `.copy()` call in functions that subsequently call `_set_float64` / `_set_float32` on the copy.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Restoring value after each loop iteration | Already done — `input_copy_plus._set_float64(i, original_val)` at end of loop | Does not help: restoration writes to the same shared buffer, so the caller's tensor is already mutated before restoration | Restoration cannot fix a shared buffer; only independent allocation can |
| Using `__copyinit__` directly | `__copyinit__` is exactly what `.copy()` calls — same shallow behaviour | Identical to the original bug | Mojo `__copyinit__` for ExTensor is explicitly shallow |

## Results & Parameters

**Working fix** (two call sites in `gradient_checker.mojo`):

```mojo
# check_gradients (lines 120-121)
var input_copy_plus = _deep_copy(input)
var input_copy_minus = _deep_copy(input)

# check_gradients_verbose (lines 229-230, inside diagnostic recompute block)
var input_copy_plus = _deep_copy(input)
var input_copy_minus = _deep_copy(input)
```

**`_deep_copy` signature** (already in same file, line 672):

```mojo
fn _deep_copy(tensor: ExTensor) raises -> ExTensor:
    ...  # allocates fresh _data buffer and copies element by element
```

**PR reference**: HomericIntelligence/ProjectOdyssey#3755
**Issue reference**: HomericIntelligence/ProjectOdyssey#3225
