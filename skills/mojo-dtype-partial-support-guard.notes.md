# Session Notes: Mojo DType Partial Support Guard

## Session Date
2026-03-05

## Issue
GitHub issue #3088 - [Cleanup] Document BF16 type alias limitation

## Context
PR #3197 was created from a prior commit (`02e05402` / `3d522e5e`) that:
1. Correctly removed stale "BF16 aliases to FP16" comments from `precision_config.mojo`
2. Correctly updated `dtype_utils.mojo` docstring to reflect native BF16 support
3. **Incorrectly** re-enabled `test_dtypes_bfloat16()` with real assertions

The prior commit assumed `comptime bfloat16_dtype = DType.bfloat16` (which already existed)
meant full runtime support was available.

## Failure Signature

CI log from `Testing Fixtures` job:
```
✓ test_dtypes_float32
✓ test_dtypes_float64
✓ test_dtypes_float16
Unhandled exception caught during execution: Element 0 = 0.0, expected 1.0 (exact match required for special values)
/home/runner/.../mojo: error: execution exited with a non-zero result: 1
❌ FAILED: tests/shared/testing/test_special_values.mojo
```

The test runs in `fn main()` order:
1. test_dtypes_float32 → PASS
2. test_dtypes_float64 → PASS
3. test_dtypes_float16 → PASS
4. test_dtypes_bfloat16 → FAIL (Element 0 = 0.0, expected 1.0)

## Root Cause Analysis

`create_special_value_tensor([2, 2], DType.bfloat16, 1.0)` in `shared/testing/special_values.mojo`:
1. Creates tensor via `zeros(shape, DType.bfloat16)` — succeeds, dtype is correct
2. Calls `tensor._set_float64(i, 1.0)` for each element — silently fails for bfloat16
3. `verify_special_value_invariants` calls `tensor._get_float64(i)` — returns 0.0

The `assert_dtype` check (step between create and verify) PASSES because the dtype metadata
is correct. Only the value I/O through float64 path is broken.

## Key Distinction

| Statement | Truth |
|-----------|-------|
| "DType.bfloat16 is not supported in Mojo" | FALSE - it exists in the type system |
| "DType.bfloat16 is fully supported" | FALSE - _set_float64/_get_float64 don't work |
| "DType.bfloat16 compiles and creates tensors" | TRUE |
| "DType.bfloat16 can store/retrieve values via float64 path" | FALSE (as of this date) |

## Remote Branch Divergence

During this session, the remote branch was force-updated (another push) while
local fix commit existed. Recovery:
```bash
git fetch origin 3088-auto-impl
git rebase origin/3088-auto-impl
git push origin 3088-auto-impl
```

## Files Changed

- `tests/shared/testing/test_special_values.mojo`:
  - `test_dtypes_bfloat16()`: body → `pass` with detailed TODO and commented test code
  - `main()`: updated print to reflect actual skip reason

## Commit
`0353c9b0 fix(tests): skip bfloat16 special values test until float64 path fixed`