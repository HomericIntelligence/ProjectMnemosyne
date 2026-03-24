---
name: mojo-extensor-utility-method-implementation
description: "Implementing utility methods for AnyTensor/ExTensor in Mojo (copy, clone, item, etc). Use when: (1) adding convenience wrappers around existing tensor methods, (2) implementing NumPy-style free functions for Mojo tensor types."
category: architecture
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags: [mojo, tensor, utility, anytensor, extensor, copy, clone]
---

# Implementing ExTensor Utility Methods in Mojo

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Objective** | Implement utility methods for ExTensor: copy(), clone(), item(), tolist(), __setitem__, __len__, __hash__, and related operations |
| **Outcome** | Successfully implemented `copy()` as a free function delegating to `AnyTensor.clone()`, with full test coverage including independence verification. PR #5078 created. |

## When to Use

- Adding NumPy-style convenience free functions that wrap existing AnyTensor methods
- Implementing utility operations for the dual-type tensor system (AnyTensor + Tensor[dtype])
- Writing tests that verify tensor independence (deep copy semantics)
- Working with the `shared/tensor/any_tensor.mojo` module

## Verified Workflow

### Quick Reference

```bash
# Run tests for the utility module
just test-group "tests/shared/core" "test_utility.mojo"

# Run all shared/core tests
just test-group "tests/shared/core" "test_*.mojo"

# Check existing free functions in any_tensor.mojo
grep "^fn " shared/tensor/any_tensor.mojo | head -30
```

### Detailed Steps

1. **Check existing implementations first**: Many operations listed in the issue (clone, item, diff, __len__, __setitem__, __str__, __repr__) already exist as methods on AnyTensor or as free functions. Read the full `any_tensor.mojo` file and the test file before writing new code.

2. **Implement as free functions**: The project pattern for utility operations is to create module-level free functions (e.g., `fn copy(tensor: AnyTensor) raises -> AnyTensor`) that delegate to AnyTensor methods. These live near the bottom of `shared/tensor/any_tensor.mojo` in the utility functions section.

3. **Update imports in test file**: Add the new function to the import line in the test file (e.g., `from shared.tensor.any_tensor import AnyTensor, zeros, ones, full, arange, copy, clone, item, diff`).

4. **Test independence for copy operations**: When testing `copy()`, verify both value equality AND independence by mutating the copy and asserting the original is unchanged:
   ```mojo
   var b = copy(a)
   b.set(0, Float64(99.0))
   assert_almost_equal(b._get_float64(0), 99.0, 1e-6, "Copy should be modified")
   assert_value_at(a, 0, 3.0, 1e-6, "Original unchanged after copy modification")
   ```

5. **Use existing test helpers**: The test infrastructure provides `assert_value_at`, `assert_almost_equal`, `assert_shape`, and `assert_dtype` from `tests/shared/conftest.py`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Implementing all operations from scratch | Tried to implement every operation in the issue | Most operations (clone, item, diff, __len__, __setitem__, __str__, __repr__, __int__, __float__) already existed in AnyTensor | Always grep for existing implementations before writing new code. The issue description lists desired operations, not necessarily missing ones. |
| Using `__copyinit__` for copy | Considered using Mojo's built-in copy init | The free function pattern `fn copy(tensor) -> AnyTensor` is more consistent with the NumPy-style API the project follows | Follow existing patterns (clone, item, diff are all free functions wrapping methods) |

## Results & Parameters

### Key Implementation Pattern

```mojo
# Free function wrapper pattern used throughout any_tensor.mojo
fn copy(tensor: AnyTensor) raises -> AnyTensor:
    """Create an independent deep copy of the tensor."""
    return tensor.clone()
```

### Test Results

- 241/247 tests passed (6 pre-existing failures unrelated to this change)
- Independence test confirms deep copy semantics (mutation of copy doesn't affect original)

### Architecture Notes

- `copy()` vs `clone()`: Both create deep copies. `copy()` follows NumPy naming convention, `clone()` follows PyTorch convention. Both are provided for API familiarity.
- The dual-type tensor system means utility functions operate on `AnyTensor` (runtime-typed) while SIMD-optimized internals use `Tensor[dtype]` (compile-time typed).
- Free functions are placed in the utility section near the bottom of `any_tensor.mojo`, after the `AnyTensor` struct definition.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #2722, PR #5078 | ExTensor utility methods implementation |
