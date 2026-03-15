---
name: validate-tuple-return
description: "Refactor Mojo validation functions to return Tuple[Float64, Float64] (loss, accuracy) to eliminate redundant data loader passes. Use when: validate() discards accuracy internally and the caller re-computes it with a second loop."
category: architecture
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-15 |
| **Objective** | Unify accuracy computation in validate() to eliminate a duplicate forward pass over the validation set |
| **Outcome** | Success — validate() now returns (loss, accuracy) tuple; ValidationLoop.run() reduced from 3× to 2× forward passes per batch |
| **Issue** | ProjectOdyssey #3683 |

## When to Use

- A `validate()` (or equivalent evaluation) function computes accuracy internally but **discards it** and returns only the loss
- The **caller re-runs** the entire data loader a second time to collect accuracy
- The model forward pass runs **3× per batch** when `compute_accuracy=True` (once in `validation_step`, once inside `validate`'s accuracy branch, once in the caller's extra loop)
- You need to surface accuracy alongside loss without paying the cost of an extra pass
- The caller already has a `metrics.update_val_metrics(loss, accuracy)` call that expects both values

## Verified Workflow

### Quick Reference

```mojo
# Before: validate() returns only Float64 loss
fn validate(...) raises -> Float64:
    ...
    if compute_accuracy:
        var accuracy = accuracy_metric.compute()
        print("  Accuracy: " + String(accuracy))
    return avg_loss  # accuracy discarded!

# Caller had to re-compute accuracy with a second loop:
var val_loss = validate(...)
var val_accuracy = Float64(0.0)
if self.compute_accuracy:
    var accuracy_metric = AccuracyMetric()
    val_loader.reset()
    while val_loader.has_next():
        var batch = val_loader.next()
        var predictions = model_forward(batch.data)
        accuracy_metric.update(predictions, batch.labels)
    val_accuracy = accuracy_metric.compute()

# After: validate() returns Tuple[Float64, Float64]
fn validate(...) raises -> Tuple[Float64, Float64]:
    ...
    var accuracy = Float64(0.0)
    if compute_accuracy:
        accuracy = accuracy_metric.compute()
        print("  Accuracy: " + String(accuracy))
    return (avg_loss, accuracy)

# Caller uses tuple directly — no extra loop:
var result = validate(...)
var val_loss = result[0]
var val_accuracy = result[1]
metrics.update_val_metrics(val_loss, val_accuracy)
```

### Step-by-Step

1. **Identify the duplicate**: Search for patterns where `validate()` is called, then immediately
   followed by a second data-loader loop that recomputes accuracy.

2. **Change the return type**: Update the function signature from `-> Float64` to
   `-> Tuple[Float64, Float64]`.

3. **Capture accuracy in a local variable** before the conditional print:

   ```mojo
   var avg_loss = total_loss / Float64(num_batches)
   var accuracy = Float64(0.0)   # default: 0.0 when compute_accuracy=False

   if compute_accuracy:
       accuracy = accuracy_metric.compute()
       print("  Accuracy: " + String(accuracy))

   return (avg_loss, accuracy)
   ```

4. **Update the caller** to destructure the tuple instead of the second loop:

   ```mojo
   var result = validate(model_forward, compute_loss, val_loader,
                         self.compute_accuracy, self.compute_confusion,
                         self.num_classes)
   var val_loss = result[0]
   var val_accuracy = result[1]
   ```

   Or using Mojo tuple destructuring syntax:

   ```mojo
   var (val_loss, val_accuracy) = validate(...)
   ```

5. **Update all direct callers of validate()** in tests to destructure the tuple:

   ```mojo
   # Before
   var avg_loss = validate(simple_forward, simple_loss, loader)

   # After
   var (avg_loss, _) = validate(simple_forward, simple_loss, loader)
   ```

6. **Add tests** for the tuple return specifically:
   - Both components accessible via index (`result[0]`, `result[1]`)
   - Tuple destructuring with `var (loss, acc) = ...`
   - `_` discard for unused component
   - `accuracy == 0.0` when `compute_accuracy=False`
   - `accuracy` in `[0.0, 1.0]` when `compute_accuracy=True`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Returning named struct | Considered creating a `ValidationResult` struct with `loss` and `accuracy` fields | Adds unnecessary type complexity for a 2-value return; Mojo Tuple syntax is well-supported | Prefer Tuple for small fixed-arity returns; structs add overhead |
| Keeping accuracy computation only in caller | Leave validate() unchanged and just pass the accuracy metric out | Would require exposing internal AccuracyMetric state or running an extra pass | The accuracy data is already computed inside validate(); returning it is free |
| Using Optional[Float64] for accuracy | Return Optional to signal "not computed" | More verbose to destructure; 0.0 sentinel is sufficient since accuracy is always in [0.0, 1.0] | Use 0.0 sentinel for "not computed" accuracy — simpler contract |

## Results & Parameters

### Return Type Pattern

```mojo
fn validate(
    model_forward: fn (ExTensor) raises -> ExTensor,
    compute_loss: fn (ExTensor, ExTensor) raises -> ExTensor,
    mut val_loader: DataLoader,
    compute_accuracy: Bool = True,
    compute_confusion: Bool = False,
    num_classes: Int = 10,
) raises -> Tuple[Float64, Float64]:
    """Returns: Tuple of (avg_loss, accuracy). accuracy=0.0 when compute_accuracy=False."""
```

### Mojo Tuple Destructuring Syntax

Both forms work in Mojo v0.26.1+:

```mojo
# Form 1: index access
var result = validate(...)
var loss = result[0]
var acc  = result[1]

# Form 2: destructuring
var (loss, acc) = validate(...)

# Form 3: discard unused component
var (loss, _) = validate(...)
```

### Performance Impact

| Scenario | Before | After |
|----------|--------|-------|
| `compute_accuracy=True` | 3× forward passes per batch | 2× forward passes per batch |
| `compute_accuracy=False` | 2× forward passes per batch | 2× forward passes per batch (unchanged) |

### Files Changed (ProjectOdyssey #3683)

```text
shared/training/loops/validation_loop.mojo   — validate() signature + run() simplification
tests/shared/training/test_validation_loop.mojo  — update 2 direct callers
tests/shared/training/test_validate_returns_tuple.mojo  — 6 new tuple-specific tests
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3683, PR #4895 | [notes.md](../references/notes.md) |
