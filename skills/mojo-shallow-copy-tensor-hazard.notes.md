# Session Notes: Mojo Shallow-Copy Tensor Hazard

## Date

2026-03-07

## Issue

HomericIntelligence/ProjectOdyssey#3225 — "Investigate check_gradients (plural) shallow copy memory hazard"

Follow-up from #3120.

## Root Cause

`check_gradients` and `check_gradients_verbose` in `shared/testing/gradient_checker.mojo` used
`input.copy()` to create temporary perturbed tensors for finite-difference gradient checking.

In Mojo, `tensor.copy()` calls `__copyinit__`, which for `ExTensor` is a **shallow copy**: the new
struct shares the same `_data` pointer as the original. When the finite-difference loop then calls
`input_copy_plus._set_float64(i, original_val + epsilon)`, it writes through the shared pointer and
mutates the caller's tensor.

The singular `check_gradient` function at lines 766/775 already used `_deep_copy` correctly.

## Fix

Replace all four `input.copy()` calls (two in `check_gradients`, two in `check_gradients_verbose`)
with `_deep_copy(input)`.

## Files Changed

- `shared/testing/gradient_checker.mojo` — lines 120–121, 229–230
- `tests/shared/testing/test_gradient_checker_meta.mojo` — added regression test
  `test_check_gradients_does_not_mutate_input`

## Key Observations

- Mojo's `__copyinit__` for custom structs does NOT guarantee deep copy unless the struct
  explicitly implements it. When a struct holds a raw pointer field, `__copyinit__` copies
  the pointer value, not the pointed-to data.
- The restoration at the end of each loop iteration (`_set_float64(i, original_val)`) was
  misleading — it wrote back through the same shared pointer, so the caller's tensor was already
  corrupted on each iteration before restoration.
- The fix is minimal: 4-line change + regression test. No API changes needed.
- Pre-commit hooks (mojo format, coverage validation) passed without modification.

## Regression Test Pattern

```mojo
fn test_function_does_not_mutate_input() raises:
    var x = full([2, 2], 1.0, DType.float32)
    var before = List[Float64]()
    for i in range(x.numel()):
        before.append(x._get_float64(i))

    _ = check_gradients(forward, backward, x, epsilon=1e-5, tolerance=1e-2)

    for i in range(x.numel()):
        assert_equal(x._get_float64(i), before[i],
            "check_gradients mutated input at index " + String(i))
```