# Session Notes: mojo-broadcast-edge-case-fix

## Session Context

- **Date**: 2026-03-07
- **Issue**: ProjectOdyssey #3279
- **PR**: ProjectOdyssey #3857
- **Branch**: `3279-auto-impl`

## Objective

Implement edge-case tests and a dimension guard for `broadcast_to` in `shared/core/shape.mojo`
of ProjectOdyssey (a Mojo-based ML framework), following the Python Array API Standard.

## Root Cause Analysis

`are_shapes_broadcastable(shape1, shape2)` in `shared/core/broadcasting.mojo` iterates
`range(max(ndim1, ndim2))`. When `ndim2 = 0` (0-d target_shape), `max_ndim = ndim1`, and
the inner per-iteration logic always produces `dim2_idx < 0`, triggering the `else 1` branch.
Every dimension comparison becomes `shape1[i] vs 1`, which passes if `shape1[i] == 1`.

For a `(1, 1)` tensor broadcasting to `[]`, the check passes vacuously — but the loop still
iterates `ndim1 = 2` times, each time comparing `1 vs 1`, and returns `True`.

For a general `(M, N)` tensor with `M, N > 1`, `are_shapes_broadcastable` correctly returns
`False` because `M != 1`. But the issue description wanted us to explicitly reject ALL cases
where `len(target_shape) < len(shape)`, regardless of the values.

## Files Changed

```
shared/core/shape.mojo            |   4 ++
tests/shared/core/test_shape.mojo | 122 +++++++++++++++++++++++++++++++++++++++
```

### shared/core/shape.mojo change

Added after `var shape = tensor.shape()`:

```mojo
# Cannot reduce number of dimensions (target must have >= dims than source)
if len(target_shape) < len(shape):
    raise Error("broadcast_to: cannot broadcast to fewer dimensions")
```

### tests/shared/core/test_shape.mojo additions

6 new test functions, all registered in `main()`:

1. `test_broadcast_to_0d_scalar` — 0-d scalar → (3, 4), values = 5.0
2. `test_broadcast_to_identity` — (3, 4) → (3, 4), values preserved
3. `test_broadcast_to_multi_axis` — (3,) → (2, 4, 3), values cycle [0,1,2]
4. `test_broadcast_to_leading_dims` — (1, 3) → (5, 3), row-repeated values
5. `test_broadcast_to_middle_dim_expand` — (1, 3, 1) → (5, 3, 7), value = middle dim index
6. `test_broadcast_to_reduce_ndim_raises` — (3, 4) → [4], verifies error

## Key Decisions

1. **Fix in caller not helper**: `are_shapes_broadcastable` is a generic helper used
   elsewhere. Changing its semantics for 0-d would break other callers. The guard belongs
   in `broadcast_to` itself.

2. **No `axis` parameter added**: The issue title mentions "axis support" but the description
   clarifies the real ask is edge-case testing + the dimension guard. Adding an `axis`
   parameter would be scope creep not justified by the issue body.

3. **`full([], 5.0, DType.float32)` for 0-d scalars**: ExTensor constructor computes
   `_numel = product(shape) = 1` for empty shape. The `full` function correctly fills 1 element.

## Test Environment

- Local host: GLIBC 2.28 (too old for Mojo binary)
- Tests run in CI via Docker: `ghcr.io/homericintelligence/projectodyssey:main`
- All pre-commit hooks passed locally (mojo format ran fine)
- CI validation via `just test-group tests/shared/core test_shape.mojo`