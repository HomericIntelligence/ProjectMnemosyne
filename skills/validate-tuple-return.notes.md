# Session Notes: validate-tuple-return

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3683 — "Unify accuracy computation between validate() and run()"
- **PR**: #4895
- **Date**: 2026-03-15
- **Branch**: `3683-auto-impl`

## Problem Description

After the fix in issue #3183, accuracy was computed twice when `compute_accuracy=True`:

1. Inside `validate()` — stored in a local variable, printed, then **discarded** (the return type was
   only `Float64` for loss)
2. In a second loop inside `ValidationLoop.run()` — the entire validation data loader was iterated
   again to accumulate `AccuracyMetric`

This meant the model forward pass ran **3× per batch** during `run()` with `compute_accuracy=True`:

- Once in `validation_step()` for loss
- Once in the `if compute_accuracy or compute_confusion:` branch inside `validate()`
- Once more in the explicit second loop in `run()` that re-computed accuracy

## Root Cause

`validate()` was designed to return only `Float64` (avg loss). When accuracy was added (issue #3183),
it was computed and printed inside `validate()` but not surfaced to the caller. The caller worked
around this by adding a second full-loader pass.

## Solution

Changed `validate()` return type from `Float64` to `Tuple[Float64, Float64]`:

- `result[0]` = average validation loss
- `result[1]` = accuracy (0.0 when `compute_accuracy=False`)

`ValidationLoop.run()` was simplified by removing the entire second loop (lines 214-223 of the
original file) and replacing it with tuple destructuring.

## Files Modified

```
shared/training/loops/validation_loop.mojo
  - validate(): return type Float64 -> Tuple[Float64, Float64]
  - validate(): declare var accuracy = Float64(0.0), assign inside if-block, include in return
  - ValidationLoop.run(): remove 10-line second-pass loop, replace with result[0]/result[1]

tests/shared/training/test_validation_loop.mojo
  - test_validate_runs_full_loader(): var avg_loss = validate(...) -> var (avg_loss, _) = validate(...)
  - test_validate_returns_positive_loss(): same pattern

tests/shared/training/test_validate_returns_tuple.mojo  [NEW]
  - 6 tests covering tuple return shape, destructuring, accuracy=0.0 branch
```

## Mojo Tuple Syntax Verified

All three destructuring forms tested and working in Mojo v0.26.1:

```mojo
var result = validate(...)       # index access: result[0], result[1]
var (a, b) = validate(...)       # full destructuring
var (a, _) = validate(...)       # discard second element
```

## Existing Patterns Used as Reference

Found these tuple destructuring patterns in the codebase to confirm syntax:

```
shared/data/batch_utils.mojo:104:  var (batch_images, batch_labels) = extract_batch_pair(...)
shared/core/dropout.mojo:48:       var (output, mask) = dropout(...)
shared/core/utils.mojo:231:        var (values, indices) = top_k(t, 3)
```
