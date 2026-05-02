---
name: mojo-view-semantics-test
description: 'Add Mojo tests asserting view/shared-memory semantics for tensor slicing.
  Use when: a slice() method claims view semantics but lacks a mutation test, or adding
  regression coverage for copy-vs-view bugs.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Mojo View Semantics Test

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-07 |
| Objective | Add regression test asserting that `slice()` shares memory with the original tensor |
| Outcome | Test added to `test_slicing.mojo`, PR created, all pre-commit hooks pass |

## When to Use

- A `slice()` method docstring claims view semantics but no test mutates through the slice
- Adding regression coverage to catch copy-vs-view regressions in tensor ops
- Writing TDD tests for a new `slice()` implementation before coding it
- Completing a test suite that only checks values read from a slice (not writes through it)

## Verified Workflow

1. **Read the existing test file** to understand existing patterns (`_set_float32`, `_get_float32`, `assert_almost_equal`)
2. **Add the test function** after the last view-semantics test:
   - Create a tensor, fill with known values
   - Slice a sub-range
   - Write through the slice (`s._set_float32(0, 99.0)`)
   - Assert the original tensor reflects the write at the corresponding index
3. **Call the function in `main()`** under the "View semantics tests" block
4. **Commit**: pre-commit hooks run `mojo format` automatically — no manual formatting needed
5. **Push and create PR** with `gh pr create`, link to the issue with "Closes #N"

### Pattern (copy-paste ready)

```mojo
fn test_slice_mutation_visible_in_original() raises:
    """Verify that mutating a slice element is visible in the original tensor.

    Asserts true view semantics: slice shares memory with original, so
    writes through the slice are reflected when reading the original.
    """
    var tensor = zeros([10], DType.float32)
    for i in range(10):
        tensor._set_float32(i, Float32(i))

    # slice [2:6] -> indices 2,3,4,5 of original
    var s = tensor.slice(2, 6, axis=0)

    # Mutate element 0 of the slice (corresponds to index 2 of original)
    s._set_float32(0, 99.0)

    # The original tensor must reflect the change at index 2
    assert_almost_equal(
        Float64(tensor._get_float32(2)), 99.0, tolerance=1e-6
    )

    print("PASS: test_slice_mutation_visible_in_original")
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3298, PR #3898 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `pixi run mojo test` locally | Executed `mojo test tests/shared/core/test_slicing.mojo` on the host | GLIBC version mismatch — host has GLIBC 2.31, Mojo requires 2.32+ | This repo runs Mojo inside Docker/CI; local execution is not supported on older Linux hosts |
| Using `just test-group` | Tried `just test-group "tests/shared/core" "test_slicing.mojo"` | `just` not in PATH on the host | Use `pixi run mojo test` or rely on CI — don't assume `just` is installed outside Docker |

## Results & Parameters

- **File modified**: `tests/shared/core/test_slicing.mojo`
- **Test added at**: after `test_multiple_slices_share_refcount`, before `test_slice_empty_range`
- **Registered in**: `main()` under `# View semantics tests`
- **Commit message format**: `test(slicing): add test asserting slice() result shares memory with original`
- **Pre-commit hooks that run**: `mojo format`, `trailing-whitespace`, `end-of-file-fixer`, `check-added-large-files`
- **CI**: runs in Docker (`ghcr.io/homericintelligence/projectodyssey:main`)
