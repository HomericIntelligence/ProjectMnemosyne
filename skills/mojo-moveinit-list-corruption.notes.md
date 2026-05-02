# Session Notes: mojo-moveinit-list-corruption

**Date**: 2026-03-06
**Issue**: ProjectOdyssey #2942 — heap corruption in ExTensor-heavy tests
**PR**: #3657

## What was tried

Plan said: replace `.copy()` with `^` in `ExTensor.__moveinit__` for `_shape` and `_strides`
fields, because `.copy()` in a `deinit` move constructor "orphans" the source List buffers.

## What actually happened

CI `Core Tensors` job failed on `test_slicing.mojo`:
```
Unhandled exception caught during execution: Batch shape[2]
```

This is `assert_equal(batch.shape()[2], 2, "Batch shape[2]")` failing —
meaning `batch.shape()[2]` was NOT `2` after slicing a `[10, 3, 2]` tensor.

## Root cause of the NEW failure

`ExTensor.slice()` at line ~675:
```mojo
var result = self.copy()
result._shape[axis] = end - start   # in-place mutation
return result^                       # triggers __moveinit__
```

With `^` in `__moveinit__`, the in-place mutation `result._shape[0] = 3`
is NOT preserved after the move. `batch.shape()[0]` came back as `10` (original)
instead of `3` (sliced).

## Evidence that `.copy()` was correct

- `test_slicing.mojo` passed on every branch before our change
- `3216-auto-impl` run at 2026-03-06T16:24:55Z: Core Tensors PASSED with `.copy()`
- Our PR run: Core Tensors FAILED after switching to `^`

## Other structs that use `^` safely

`variable.mojo`, `tape_types.mojo`, `attention.mojo` — all use `^` for List fields,
but none of them have a pattern where a List element is mutated in-place and then the
struct is immediately moved. They build Lists incrementally via `.append()` and then
move the whole struct.

## What we actually shipped

1. `shared/testing/layer_testers.mojo` — mojo format fix (3 long ternaries wrapped)
2. `docs/adr/` heap corruption workaround ADR — revision 1.1 with finding #6

The heap corruption root cause (why 15+ ExTensor tests in one file crash)
remains unresolved. The file-splitting workaround stays in place.