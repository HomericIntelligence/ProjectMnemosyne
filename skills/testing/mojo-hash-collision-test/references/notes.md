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

---

## Session Context (Issue #4056)

Implemented as part of ProjectOdyssey GitHub issue #4056 (worktree `4056-auto-impl`, branch `4056-auto-impl`).

## Objective

Add `test_hash_same_dtype_different_shapes()` to `tests/shared/core/test_hash.mojo` asserting that
tensors with identical data and dtype but different shapes (e.g. [2,3] vs [6]) produce different hashes.

## Steps Taken

1. Read `.claude-prompt-4056.md` to understand requirements
2. Found the existing test file at `tests/shared/core/test_hash.mojo`
3. Read the file to understand existing patterns (NaN tests, shape sensitivity tests, dtype sensitivity tests)
4. Discovered the existing `test_hash_shape_sensitivity` test only tested different-size shapes ([2] vs [3]) — not same-total-elements different-shape
5. Added `test_hash_same_dtype_different_shapes()` function testing [2,3] vs [6] tensors both filled with 1.0 as float32
6. Added the test call to `main()`
7. Ran tests — all 17 tests passed
8. Committed with `git add` + `git commit`
9. Pushed to origin
10. Created PR #4860 with `gh pr create`

## Key Code Patterns Observed

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

Registration in `main()`:

```mojo
print("Running test_hash_same_dtype_different_shapes...")
test_hash_same_dtype_different_shapes()
```

## Environment Details

- Host OS: WSL2 Ubuntu (GLIBC 2.35) — compatible with Mojo runtime
- Tests ran successfully locally: all 17 tests passed
- Used `just test-group "tests/shared/core" "test_hash.mojo"` to run tests

## Commit

Committed on branch `4056-auto-impl` in ProjectOdyssey worktree at
`/home/mvillmow/ProjectOdyssey/.worktrees/issue-4056/`.

Commit hash: `c0ecf9c8` (test(hash): add hash collision test for same dtype different shapes)
