---
name: mojo-hash-collision-test
description: "Pattern for adding hash collision tests to Mojo ExTensor test files. Use when: (1) issue requests verifying hash distinguishes same-dtype tensors with different shapes, (2) verifying __hash__ distinguishes float32 vs float64 tensors, (3) adding collision tests for shape/dtype/value sensitivity."
category: testing
date: 2026-03-15
user-invocable: false
---

# Mojo Hash Collision Test Skill

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-15 |
| Objective | Add hash collision resistance tests verifying ExTensor `__hash__` distinguishes tensors by shape, dtype, and values |
| Outcome | Successful — tests added, pre-commit hooks passed, PRs created |

## When to Use

- Issue requests adding a hash collision test for same dtype, different shapes (e.g. [2,3] vs [6])
- Adding hash collision resistance tests to `tests/shared/core/test_hash.mojo` or similar files
- Verifying that `__hash__` encodes shape, dtype, and value information in ExTensors
- Following TDD to guard against regressions in tensor hash uniqueness
- Expanding hash test coverage alongside existing shape/dtype/value sensitivity tests

## Verified Workflow

### Quick Reference — Same Dtype, Different Shapes ([2,3] vs [6])

```mojo
fn test_hash_same_dtype_different_shapes() raises:
    var shape_2x3 = List[Int]()
    shape_2x3.append(2)
    shape_2x3.append(3)
    var shape_6 = List[Int]()
    shape_6.append(6)
    var a = full(shape_2x3, 1.0, DType.float32)
    var b = full(shape_6, 1.0, DType.float32)
    if hash(a) == hash(b):
        raise Error(
            "Tensors with same dtype/data but different shapes ([2,3] vs [6]) should not collide on hash"
        )
```

### Quick Reference — Same Values, Different Dtype

```mojo
fn test_hash_same_values_different_dtype() raises:
    var shape = List[Int]()
    shape.append(1)
    var tensor_f32 = full(shape, 1.0, DType.float32)
    var tensor_f64 = full(shape, 1.0, DType.float64)
    var hash_f32 = hash(tensor_f32)
    var hash_f64 = hash(tensor_f64)
    if hash_f32 == hash_f64:
        raise Error(
            "Hash collision: float32 and float64 tensors with same values should have different hashes"
        )
```

### Step-by-Step Workflow

1. **Read the existing test file** to understand existing patterns before adding anything
2. **Find the right insertion point** — place new test function near related tests (shape/dtype section)
3. **Follow the `if hash(a) == hash(b): raise Error(...)` pattern** used by all collision tests
4. **Use `full(shape, value, DType)` to create tensors** with identical data
5. **Construct shapes with `List[Int]` + `.append()`** for each dimension (required — shape literals not supported)
6. **Register the test in `main()`** with a print statement followed by the function call
7. **Run tests** with `just test-group "tests/shared/core" "test_hash.mojo"` to verify all pass
8. **Commit, push, create PR** with `Closes #NNNN` in body

### Pattern Notes

- Shape setup: `var shape = List[Int](); shape.append(2); shape.append(3)` (not a literal, append each dim)
- Tensor creation: `full(shape, value, DType.float32)` (imported from `shared.core`)
- Hash assertion: use `if hash_a == hash_b: raise Error(...)` — NOT `assert_equal` or similar macros
- Function signature: `fn test_hash_...() raises:`
- Registration in `main()`: typically a print statement + direct function call

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3379, branch `3379-auto-impl` — same values, different dtype | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #4056, branch `4056-auto-impl` — same dtype, different shapes | [notes.md](../../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run mojo test` locally | Running tests on host Debian Buster | GLIBC_2.32/2.33/2.34 not found — host OS too old | Mojo tests require Docker or CI environment |
| `just test-mojo` locally | Running `just` outside Docker | `just` command not found outside container | Use CI to verify test execution |
| N/A (issue #4056) | Implementation was direct — no failed attempts | — | Reading existing patterns first made implementation straightforward |

## Results & Parameters

### Issue #4056 (same dtype, different shapes)

- **Test added**: `test_hash_same_dtype_different_shapes()`
- **File**: `tests/shared/core/test_hash.mojo`
- **Shapes tested**: `[2, 3]` vs `[6]` (same 6 total elements, different rank/shape)
- **DType**: `float32` (same for both)
- **Value**: `1.0` for all elements (same data)
- **All 17 tests passed** after the addition
- **PR**: #4860

### Issue #3379 (same values, different dtype)

- **Test added**: `test_hash_same_values_different_dtype()`
- **File**: `tests/shared/core/test_utility.mojo`
- **Dtypes tested**: `float32` vs `float64` (same scalar value `1.0`)
- **Shape**: `[1]`
- **Pre-commit hooks**: `mojo format`, `Validate Test Count Badge`, `trailing-whitespace`, `end-of-file-fixer` — all passed

## References

- `tests/shared/core/test_hash.mojo` — hash test file (issue #4056)
- `tests/shared/core/test_utility.mojo` — utility test file (issue #3379)
- `.claude/shared/mojo-anti-patterns.md` — common Mojo test failure patterns
- ProjectOdyssey issue #4056 — same dtype, different shapes hash collision test
- ProjectOdyssey issue #3379 — same values, different dtype hash collision test
