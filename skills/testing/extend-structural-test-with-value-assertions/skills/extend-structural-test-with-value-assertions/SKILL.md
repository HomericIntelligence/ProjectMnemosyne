---
name: extend-structural-test-with-value-assertions
description: "Pattern for closing the value-correctness gap in Mojo tensor tests that only assert structure (strides, contiguity) but not element values. Use when: existing test verifies is_contiguous() or strides but skips element value checks after as_contiguous()."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | extend-structural-test-with-value-assertions |
| **Category** | testing |
| **Language** | Mojo |
| **Issue** | #3842 (follow-up from #3274) |
| **PR** | #4812 |

Captures the pattern for extending an existing Mojo test that only checks
structural properties (strides, `is_contiguous()`) to also verify that
element values are correctly reordered after `as_contiguous()` on a
transposed tensor.

The key gap: a test can pass `is_contiguous() == True` and have correct
`_strides` while silently producing wrong element values if the copy
implementation uses flat indexing instead of stride-based indexing.
Closing this gap requires appending `assert_almost_equal` calls that
derive expected values from the transpose stride mapping.

## When to Use

- An existing test asserts `is_contiguous()` and `_strides[n]` after
  `as_contiguous()` but has no element-value assertions
- A follow-up issue requests value-correctness regression coverage for
  `as_contiguous()` after `transpose()` or `transpose_view()`
- You want to verify that a non-contiguous copy operation remaps elements
  (not just metadata) correctly
- The tensor was built with `arange` + `reshape` + `.transpose()`, giving
  predictable values that can be derived by hand

## Verified Workflow

### Quick Reference

- **Source tensor**: `arange(0.0, N, 1.0)` reshaped to `(rows, cols)`,
  transposed to `(cols, rows)`
- **Expected value formula**: `c._get_float64(j * rows + i)` == original
  value at row `i`, col `j` == `i * cols + j`
- **Assertion helper**: `assert_almost_equal(c._get_float64(flat_idx), expected, 1e-6, msg)`
- **Tolerance**: `1e-6` for `DType.float32`

1. **Locate the existing structural test** — find the function that calls
   `as_contiguous()` and asserts only `is_contiguous()` and `_strides`.

2. **Identify the tensor construction** — confirm it uses `arange` or a
   similar sequential fill so values are predictable. Example:

   ```mojo
   var a = arange(0.0, 12.0, 1.0, DType.float32)
   var b = a.reshape(shape)   # shape (3, 4)
   var t = b.transpose(0, 1)  # shape (4, 3), non-contiguous
   var c = as_contiguous(t)
   ```

3. **Derive expected values by hand** using the transpose mapping.
   For a `(rows=3, cols=4)` source transposed to `(cols=4, rows=3)`:

   ```
   c[j, i] = original[i, j] = i * cols + j   (0-indexed)

   Flat layout of c (row-major (4,3)):
     index 0 → c[0,0] = original[0,0] = 0
     index 1 → c[0,1] = original[1,0] = 4
     index 2 → c[0,2] = original[2,0] = 8
     index 3 → c[1,0] = original[0,1] = 1
     index 4 → c[1,1] = original[1,1] = 5
     ...
   ```

4. **Append assertions** directly after the existing stride assertions,
   with a comment block explaining the mapping:

   ```mojo
   # Verify element values are correctly reordered per transpose stride mapping.
   # Original (3,4) row-major: a[i,j] = i*4 + j (values 0..11)
   # After transpose to (4,3), reading row-major: t[j,i] = a[i,j]
   # Row 0 of transpose = col 0 of original: 0, 4, 8
   assert_almost_equal(c._get_float64(0), 0.0, 1e-6, "c[0,0] should be 0")
   assert_almost_equal(c._get_float64(1), 4.0, 1e-6, "c[0,1] should be 4")
   assert_almost_equal(c._get_float64(2), 8.0, 1e-6, "c[0,2] should be 8")
   # Row 1 of transpose = col 1 of original: 1, 5, 9
   assert_almost_equal(c._get_float64(3), 1.0, 1e-6, "c[1,0] should be 1")
   assert_almost_equal(c._get_float64(4), 5.0, 1e-6, "c[1,1] should be 5")
   assert_almost_equal(c._get_float64(5), 9.0, 1e-6, "c[1,2] should be 9")
   # ... all N elements
   ```

5. **Verify no new imports are needed** — `assert_almost_equal` is
   typically already imported in Mojo utility test files.

6. **Run the test** to confirm it passes (values are correct) or reveals
   a bug (implementation uses flat copy):

   ```bash
   just test-group "tests/shared/core" "test_utility.mojo"
   ```

## Results & Parameters

- **Source shape**: `(3, 4)` is the canonical minimal non-square case — clear
  row/column ordering, 12 total elements (exhaustive but not tedious to enumerate)
- **Value fill**: `arange(0.0, 12.0, 1.0, DType.float32)` — sequential, easy
  to trace
- **Transpose**: `.transpose(0, 1)` swaps dims 0 and 1 (same as `transpose_view`)
- **Result shape**: `(4, 3)` — all 12 elements must be checked
- **Tolerance**: `1e-6` for float32
- **Test file**: `tests/shared/core/test_utility.mojo`
- **Function extended**: `test_contiguous_on_noncontiguous()`
- **Assertions added**: 12 `assert_almost_equal` calls (one per element)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3842, PR #4812 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking only strides and contiguity | Original test asserted `is_contiguous() == True` and `_strides[0] == 3`, `_strides[1] == 1` | Structural metadata can be correct while element values are wrong (flat copy instead of stride copy) | Always append element-value assertions after structural checks |
| Using `_get_float64(i)` on the non-contiguous tensor before `as_contiguous()` | Asserting values on `t` (the transposed view) before copying | `_get_float64(i)` reads flat memory index `i`, ignoring strides — gives original row-major order, not transpose order | Assert values on `c` (the contiguous result), not on the non-contiguous view |
| Manually overwriting `_strides` to create non-contiguous tensor | Alternative approach from `mojo-as-contiguous-stride-verification` skill | Harder to control predictable values when stride override decouples logical and physical layout | When the tensor is built with `arange + reshape + transpose`, the value mapping is derivable without stride manipulation — prefer the simpler path |
