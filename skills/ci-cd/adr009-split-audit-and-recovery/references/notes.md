# Session Notes: ADR-009 Split Audit and Recovery

**Date**: 2026-03-07
**Issue**: #3470 — fix(ci): split test_gradient_checking.mojo (16 tests)
**Branch**: 3470-auto-impl
**PR**: #4305

## What Happened

The issue asked to split `test_gradient_checking.mojo` (16 tests) into 2 files of ≤8 tests each.
When we started work, the split had **already been done** in commit `8a78d3aa` as part of a bulk split:

- `test_gradient_checking_basic.mojo` (8 tests)
- `test_gradient_checking_dtype.mojo` (5 tests)

Total in split: **13 tests**, but original had **16 tests** → 3 were dropped silently.

## Dropped Tests Found via Git History

```bash
SPLIT_COMMIT=8a78d3aa
git show $SPLIT_COMMIT -- "tests/shared/core/test_gradient_checking.mojo" | grep "^-fn test_"
```

Output showed 16 original tests. The 3 missing:
1. `test_relu_mixed_inputs` — tests ReLU with mixed +/- inputs
2. `test_conv2d_gradient_fp16` — Conv2D gradient in FP16 (actually uses FP32 compute)
3. `test_cross_entropy_gradient_fp16` — CrossEntropy gradient in FP16

## Secondary Violation Found

While auditing the CI group pattern in `comprehensive-tests.yml`:

```
pattern: "... test_gradient_validation.mojo ..."
```

`test_gradient_validation.mojo` had **12 tests** — violating ADR-009's ≤10 limit.
This file was from a different commit (`9505a576`) and had never been split.

It was also missing the required ADR-009 header comment entirely.

## Resolution

1. Added 3 dropped tests back to their respective split files
2. Added exact ADR-009 header comment to `test_gradient_checking_basic.mojo` and `test_gradient_checking_dtype.mojo`
3. Split `test_gradient_validation.mojo` (12 → 8 + 4):
   - `test_gradient_validation_activations.mojo` (8 tests: ReLU x5, Sigmoid x3)
   - `test_gradient_validation_layers.mojo` (4 tests: Tanh, GELU, Conv2D, Linear)
4. Renamed original to `.DEPRECATED` per project convention
5. Updated CI workflow to reference new filenames

## Files Changed

- `tests/shared/core/test_gradient_checking_basic.mojo` — +ADR-009 header, +test_relu_mixed_inputs (→ 9 tests)
- `tests/shared/core/test_gradient_checking_dtype.mojo` — +ADR-009 header, +2 FP16 tests (→ 7 tests)
- `tests/shared/core/test_gradient_validation_activations.mojo` — new (8 tests)
- `tests/shared/core/test_gradient_validation_layers.mojo` — new (4 tests)
- `tests/shared/core/test_gradient_validation.mojo.DEPRECATED` — renamed
- `.github/workflows/comprehensive-tests.yml` — Core Gradient group updated

## ADR-009 Header Format (Required)

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

NOT equivalent: prose docstrings like `"Note: Split from X due to ADR-009."` — the acceptance criteria
specified the exact comment format.
