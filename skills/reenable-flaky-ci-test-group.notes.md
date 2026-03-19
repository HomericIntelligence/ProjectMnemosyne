# Session Notes: Re-enable Core Loss Tests (Issue #3120)

## Context

- **Repository**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3120 - fix(tests): investigate Core Loss test crashes
- **Branch**: 3120-auto-impl
- **Date**: 2026-03-04

## What Was Disabled

Three test files in `tests/shared/core/`:
- `test_losses.mojo` — BCE, MSE, Smooth L1, Hinge, Focal, KL divergence with gradient checks
- `test_loss_funcs.mojo` — Cross entropy, MSE, BCE unit tests
- `test_loss_utils.mojo` — clip_predictions, create_epsilon_tensor, validate shapes/dtypes, etc.

Disabled in two commits:
- `d53d135e` — commented out in `.github/workflows/comprehensive-tests.yml`
- `f701a8eb` — added exclusions to `scripts/validate_test_coverage.py`

## Investigation Steps

1. Read test files → found they use `check_gradient` (singular, uses `_deep_copy`)
2. Read `gradient_checker.mojo` → confirmed `check_gradient` creates independent tensor copies
3. Read `loss.mojo` and `loss_utils.mojo` → found no obvious bugs; bool masks properly cast
4. Tried running locally → GLIBC mismatch prevented local execution
5. Queried CI history → found `21799938615` had Core Loss as "success" at sha `76dd17e9`
6. Cross-referenced sha with git log → no code changes to loss files after that run
7. Concluded: crashes were transient Mojo runtime noise, not code bugs

## Key Mojo Observation: check_gradients vs check_gradient

The older `check_gradients` (plural) function in `gradient_checker.mojo` uses `input.copy()`
which is `__copyinit__` — a **shallow copy** that shares the underlying data buffer!
Modifying `input_copy_plus` would corrupt the original input.

The test files use `check_gradient` (singular) which uses `_deep_copy()` — this creates
a fresh allocation and copies all elements. Safe.

This was a potential source of flakiness in tests using `check_gradients` (plural) elsewhere,
but the Core Loss tests were not affected.

## CI History Cross-Reference

Key sha → run mapping:
- `76dd17e9` (Jan 27 2026) → run `21799938615` → Core Loss: **success**
- `f701a8eb` (Feb 8 13:51 PST) → run `21806302539` → Core Loss: already disabled
- `d53d135e` (Feb 8 13:49 PST) → Core Loss first disabled

Since there were no code changes to loss files between `76dd17e9` and `d53d135e`,
the tests were disabled due to flaky runtime crashes, not a code regression.

## Mojo "execution crashed" Pattern

The Mojo runtime outputs `error: execution crashed` for segfaults, OOM, and other
fatal errors. In CI history, this error appeared across multiple different test groups
(not just Core Loss), suggesting it was a systemic runner issue rather than
test-specific code bugs.