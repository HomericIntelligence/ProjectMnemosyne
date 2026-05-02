# Session Notes: mojo-api-name-reconciliation

## Issue

GitHub issue #3222: "Update test_packaging.mojo placeholder tests to match actual API names"

Follow-up from #3093 (import audit). The 12 placeholder tests in
`tests/shared/integration/test_packaging.mojo` were written against originally planned API names.
After the import audit, many names are known to use different identifiers.

## Name Mappings Applied

| Old (planned) | New (actual) | Struct/file location |
| --- | --- | --- |
| `Conv2D` | `Conv2dLayer` | `shared/core/layers/conv2d.mojo` — `struct Conv2dLayer` |
| `ReLU` | `ReLULayer` | `shared/core/layers/relu.mojo` — `struct ReLULayer` |
| `Tensor` | `ExTensor` | `shared/core/extensor.mojo` |
| `Accuracy` | `AccuracyMetric` | `shared/training/metrics/__init__.mojo` — exported as `AccuracyMetric` |
| `DataLoader` | `BatchLoader` | `shared/data/__init__.mojo` — `BatchLoader` exported at line 126 |
| `TensorDataset` | `ExTensorDataset` | `shared/data/` |

## Key Finding: Linear is NOT stale

When searching for old names, `Linear` appeared in both old planned names and current code.
Grep confirmed: `struct Linear(Copyable, Movable)` exists in `shared/core/layers/linear.mojo`.
The comment on line 119 of `shared/__init__.mojo` (`shared.core.layers.Linear`) is correct.

## Files Changed

- `tests/shared/integration/test_packaging.mojo`: Updated the commented-out
  `test_public_api_exports` body (the `expected_exports` list within double-commented block)
- `shared/__init__.mojo`: Updated 8 locations — docstring Usage section, Example code block,
  and 6 commented-out import/API-listing lines

## Environment Notes

- Mojo binary cannot run locally (GLIBC 2.32/2.33/2.34 required, not available on host)
- All verification done via pre-commit hooks: `pixi run pre-commit run --all-files`
- Tests will run in Docker CI via GitHub Actions

## PR

- Branch: `3222-auto-impl`
- PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3756
- Auto-merge enabled with rebase strategy
