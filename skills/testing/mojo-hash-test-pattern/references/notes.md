# Session Notes: mojo-hash-test-pattern

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3381 — Add `test_hash_different_dtypes_differ` for ExTensor
- **Branch**: `3381-auto-impl`
- **PR**: #4057
- **Date**: 2026-03-07

## Objective

Add one missing test to `tests/shared/core/test_utility.mojo` verifying that `ExTensor.__hash__`
returns different values for tensors with identical logical values but different dtypes
(`float32` vs `float64`).

## Implementation Details

### `__hash__` implementation (from `shared/core/extensor.mojo`)

The hash implementation includes `dtype_to_ordinal` which maps each `DType` to a unique integer
and XORs it into the hash seed. This guarantees dtype-based differentiation:

```mojo
hash_value = hash_value ^ dtype_to_ordinal(self.dtype())
```

### File modified

`tests/shared/core/test_utility.mojo` — one function added after `test_hash_small_values_distinguish`

### Insertion point

After `test_hash_small_values_distinguish` function definition, before the next section.

### `main()` update

Added call after `test_hash_small_values_distinguish()` in the existing `# __hash__` block.

## Test Added

```mojo
fn test_hash_different_dtypes_differ() raises:
    """Test that tensors with same values but different dtypes hash differently."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    var t_f32 = full(shape, Float64(1.0), DType.float32)
    var t_f64 = full(shape, Float64(1.0), DType.float64)
    if hash(t_f32) == hash(t_f64):
        raise Error(
            "float32 and float64 tensors with identical values should hash differently"
        )
```

## Environment

- Mojo version: v0.26.1 (via pixi)
- GLIBC issue: Host system too old (Debian 10, GLIBC 2.28) — Mojo requires 2.32+
- Verification: CI-only (cannot run locally)
- Pre-commit hooks: All passed (mojo format, test count badge validator, trailing whitespace, etc.)

## Commit

`cb2f4342` — "test(utility): add test_hash_different_dtypes_differ for ExTensor"

## Pre-commit Hook Notes

The repository validates a test-count badge in CI. Adding a new test function increments the
count and the badge validator re-runs automatically as part of the pre-commit suite. No manual
badge update is needed.
