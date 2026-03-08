# Notes

## Session Context

Implemented as part of ProjectOdyssey GitHub issue #3379 (worktree `3379-auto-impl`, branch `3379-auto-impl`).

## Objective

Add `test_hash_same_values_different_dtype()` to `tests/shared/core/test_utility.mojo` asserting that
tensors with identical numeric values but different dtypes (float32 vs float64) produce different hashes.

## Steps Taken

1. Read `.claude-prompt-3379.md` to understand requirements
2. Used Explore agent to locate `test_hash_different_values` and the `__hash__` implementation
3. Read `tests/shared/core/test_utility.mojo` to understand existing test patterns (shape setup, hash assertion style)
4. Searched the `main()` function to find where tests are registered
5. Added `test_hash_same_values_different_dtype()` after `test_hash_small_values_distinguish()`
6. Registered the new test in `main()`
7. Committed with pre-commit hooks — all passed on first attempt
8. Pushed branch and created PR

## Environment Details

- Host OS: Debian Buster (GLIBC 2.28) — too old for Mojo runtime
- Mojo runtime requires: GLIBC_2.32, GLIBC_2.33, GLIBC_2.34
- Local test execution: not possible; requires Docker or CI
- `just` command: only available inside Docker container

## Key Code Patterns Observed

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

Registration in `main()`:

```mojo
test_hash_same_values_different_dtype()
```

## Pre-commit Hooks Encountered

- `mojo format` — auto-formats `.mojo` files (no changes needed; code was already correctly formatted)
- `Validate Test Count Badge` — checks test count badge in README is consistent with actual test count
- `trailing-whitespace` — passed
- `end-of-file-fixer` — passed
- `check-yaml` — passed

## Commit

Committed on branch `3379-auto-impl` in ProjectOdyssey worktree at
`/home/mvillmow/Odyssey2/.worktrees/issue-3379/`.

Commit hash: `45163b87` (test(utility): add hash collision resistance test for same-shape different-dtype tensors)
