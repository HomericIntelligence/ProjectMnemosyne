---
name: mojo-hash-collision-test
description: "Add hash collision resistance tests for Mojo tensors with same values but different dtypes. Use when verifying __hash__ distinguishes float32 vs float64 tensors."
category: testing
date: 2026-03-07
user-invocable: true
---

# Mojo Hash Collision Test Skill

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Add `test_hash_same_values_different_dtype()` asserting that tensors with identical numeric values but different dtypes (float32 vs float64) produce different hashes. |
| Outcome | Successful — test added, pre-commit hooks passed, PR created |

## When to Use

- Adding hash collision resistance tests to `tests/shared/core/test_utility.mojo`
- Verifying that `__hash__` encodes dtype information (not just values and shape)
- Following TDD to guard against regressions in tensor hash uniqueness
- Expanding hash test coverage alongside `test_hash_different_values` and `test_hash_small_values_distinguish`

## Verified Workflow

### Quick Reference

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

1. **Locate insertion point** — find `test_hash_small_values_distinguish` in `tests/shared/core/test_utility.mojo`
2. **Add function** — insert `test_hash_same_values_different_dtype()` immediately after that function
3. **Register in main()** — add a call to the new function in the `main()` runner at the bottom of the file
4. **Commit** — run pre-commit hooks; the "Validate Test Count Badge" hook requires no extra action if counts are updated automatically
5. **Push and create PR** — branch naming: `<issue-number>-<description>`

### Pattern Notes

- Shape setup: `var shape = List[Int](); shape.append(1)` (not a literal, append required)
- Tensor creation: `full(shape, value, DType.float32)` (imported from `shared.core.utility`)
- Hash assertion: use `if hash_a == hash_b: raise Error(...)` — NOT `assert_equal` or similar macros
- Function signature: `fn test_hash_same_values_different_dtype() raises:`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3379, worktree `3379-auto-impl` | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| `pixi run mojo test tests/shared/core/test_utility.mojo` locally | GLIBC_2.32/2.33/2.34 not found — host OS (Debian Buster) too old | Mojo tests require Docker or CI environment; do not expect local `mojo test` to work outside container |
| `just test-mojo` locally | `just` command not found outside Docker | The `justfile` recipes are designed for use inside the container; use CI to verify test execution |

## Results & Parameters

- Test function name: `test_hash_same_values_different_dtype`
- File: `tests/shared/core/test_utility.mojo`
- Insert after: `test_hash_small_values_distinguish()`
- Register in: `main()` at the bottom of the same file
- Pre-commit hooks that run: `mojo format`, `Validate Test Count Badge`, `trailing-whitespace`, `end-of-file-fixer`
- All hooks passed on first attempt when following exact existing code style

## References

- `tests/shared/core/test_utility.mojo` — test file containing hash tests
- `.claude/shared/mojo-anti-patterns.md` — common Mojo test failure patterns
- ProjectOdyssey issue #3379 — original work item
