---
name: mojo-as-contiguous-stride-verification
description: 'TDD pattern for verifying stride-aware memory remapping in Mojo tensor
  as_contiguous(). Use when: writing regression tests for non-contiguous tensor copy
  operations, verifying stride-based indexing before or after a bug fix.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-as-contiguous-stride-verification |
| **Category** | testing |
| **Language** | Mojo |
| **Issue** | #3392 (follow-up from #3166) |
| **PR** | #4087 |

Captures the TDD pattern for writing stride-correct value verification tests
for `as_contiguous()` in Mojo's `ExTensor`. The key insight: pre-existing tests
used `_get_float64(i)` which ignores strides (flat order), so bugs in
stride-aware remapping were invisible. The fix is to construct a tensor with
**manually overwritten strides** and assert against the expected stride-remapped
flat output.

## When to Use

- Writing a test for `as_contiguous()` or any stride-based copy operation
- Creating a regression test before fixing a stride-indexing bug (TDD-first)
- Verifying a non-contiguous tensor (e.g. column-major, transposed) produces
  the correct C-order (row-major) copy after `as_contiguous()`
- Discovering that an existing contiguity test only checks flat order, not
  stride-correct positions

## Verified Workflow

1. **Identify the gap**: check if existing tests use `_get_float64(i)` for value
   assertions — if so, they ignore strides and cannot catch stride-remapping bugs.

2. **Construct a minimal non-contiguous tensor** by creating a normally-shaped
   tensor and **overwriting `_strides` directly**:

   ```mojo
   var shape = List[Int]()
   shape.append(2)
   shape.append(3)
   var t = ExTensor(shape, DType.float32)

   # Fill raw memory sequentially
   for i in range(6):
       t._set_float64(i, Float64(i))

   # Overwrite to column-major strides [1, 2]
   t._strides[0] = 1
   t._strides[1] = 2
   ```

3. **Assert non-contiguity** using `t.is_contiguous()` before calling
   `as_contiguous()`.

4. **Derive expected output by hand** using stride arithmetic:

   ```
   Column-major strides [1, 2] for shape [2, 3]:
     result[0,0] = mem[0*1 + 0*2] = mem[0] = 0.0
     result[0,1] = mem[0*1 + 1*2] = mem[2] = 2.0
     result[0,2] = mem[0*1 + 2*2] = mem[4] = 4.0
     result[1,0] = mem[1*1 + 0*2] = mem[1] = 1.0
     result[1,1] = mem[1*1 + 1*2] = mem[3] = 3.0
     result[1,2] = mem[1*1 + 2*2] = mem[5] = 5.0

   Expected flat row-major output: [0.0, 2.0, 4.0, 1.0, 3.0, 5.0]
   ```

5. **Assert each flat position** in the result using `assert_value_at`:

   ```mojo
   var result = as_contiguous(t)
   assert_true(result.is_contiguous(), "result should be contiguous")
   assert_value_at(result, 0, 0.0, 1e-6, "result[0,0] = 0.0 (mem[0])")
   assert_value_at(result, 1, 2.0, 1e-6, "result[0,1] = 2.0 (mem[2])")
   assert_value_at(result, 2, 4.0, 1e-6, "result[0,2] = 4.0 (mem[4])")
   assert_value_at(result, 3, 1.0, 1e-6, "result[1,0] = 1.0 (mem[1])")
   assert_value_at(result, 4, 3.0, 1e-6, "result[1,1] = 3.0 (mem[3])")
   assert_value_at(result, 5, 5.0, 1e-6, "result[1,2] = 5.0 (mem[5])")
   ```

6. **Register the test in `main()`** after any existing contiguity tests.

7. **Commit in TDD-first style** — the test may intentionally fail until the
   parent bug fix lands, serving as a regression harness.

## Results & Parameters

- **Shape**: 2×3 is the minimum useful shape (not square, clearly shows
  row vs column ordering)
- **Memory fill**: sequential integers starting from 0.0 — easy to trace
- **Stride override**: column-major `[1, 2]` for shape `[2, 3]`
  (C-order would be `[3, 1]`)
- **Tolerance**: `1e-6` for float32 value assertions
- **Test file location**: `tests/shared/core/test_utility.mojo`
- **Naming convention**: `test_contiguous_stride_correct_values`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `transpose_view()` as the non-contiguous source | Create a transposed tensor and assert specific flat positions in the result | `transpose_view` changes shape but the value mapping is harder to control precisely from raw memory | Manually overwriting `_strides` gives full control of the non-contiguous layout |
| Using `_get_float64(i)` for assertions in the original test | Original `test_contiguous_on_noncontiguous` asserted values via `_get_float64(i)` | `_get_float64` ignores strides — it reads flat memory — so stride bugs are invisible | Always use `assert_value_at` on the result flat indices to catch stride-remapping errors |
| Asserting only strides and contiguity, not values | Only checking `is_contiguous()` and `_strides[n]` | Does not verify that elements ended up in the correct positions | Both stride metadata AND value positions must be verified |
