# Session Notes: ADR-009 Split with Explicit CI Workflow Update

## Context

- **Issue**: #3400 — `tests/shared/core/test_activations.mojo` had 45 `fn test_` functions
- **PR**: #4111
- **Branch**: `3400-auto-impl`
- **Date**: 2026-03-07

## Problem

`test_activations.mojo` contained 45 `fn test_` functions, exceeding ADR-009's ≤10 hard limit
and ≤8 target. CI group "Core Activations & Types" was failing non-deterministically (13/20 runs)
due to Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault).

## Key Difference from Previous ADR-009 Splits

Previous split (issue #3397, `test_assertions.mojo`) used a glob pattern in CI:
```yaml
pattern: "testing/test_*.mojo"
```
New files were auto-discovered — no workflow update needed.

This split (issue #3400, `test_activations.mojo`) used an explicit filename in CI:
```yaml
pattern: "test_activations.mojo test_activation_funcs.mojo ..."
```
New split files had to be explicitly added to the `pattern:` field.

## Files Changed

- `tests/shared/core/test_activations.mojo` — deleted
- `tests/shared/core/test_activations_part1.mojo` — created (8 tests: ReLU, Leaky ReLU basic)
- `tests/shared/core/test_activations_part2.mojo` — created (8 tests: Leaky ReLU backward, PReLU, Sigmoid basic)
- `tests/shared/core/test_activations_part3.mojo` — created (8 tests: Sigmoid stability/dtype, Tanh, Softmax basic)
- `tests/shared/core/test_activations_part4.mojo` — created (8 tests: Softmax, GELU basic)
- `tests/shared/core/test_activations_part5.mojo` — created (8 tests: GELU, Swish, Mish basic)
- `tests/shared/core/test_activations_part6.mojo` — created (5 tests: Mish, ELU, Integration)
- `.github/workflows/comprehensive-tests.yml` — updated pattern for "Core Activations & Types"
- `tests/shared/README.md` — updated file listing

## Verification

All pre-commit hooks passed on commit:

- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Markdown Lint: Passed
- Check YAML: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
- Fix Mixed Line Endings: Passed

## Activation Functions Covered

The 10 activation functions from the original file:

1. ReLU (`relu`, `relu_backward`)
2. Leaky ReLU (`leaky_relu`, `leaky_relu_backward`)
3. PReLU (`prelu`, `prelu_backward`)
4. Sigmoid (`sigmoid`, `sigmoid_backward`)
5. Tanh (`tanh`, `tanh_backward`)
6. Softmax (`softmax`, `softmax_backward`)
7. GELU (`gelu`, `gelu_backward`)
8. Swish (`swish`, `swish_backward`)
9. Mish (`mish`, `mish_backward`)
10. ELU (`elu`, `elu_backward`)
