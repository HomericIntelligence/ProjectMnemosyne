---
name: dataloader-reset-verification
description: 'Test pattern to verify DataLoader reset behavior in training/validation
  loops. Use when: confirming an iterator''s reset() is called before iteration, or
  verifying a loop does not silently skip batches on a partially-consumed loader.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | testing |
| Language | Mojo |
| Issue | #3186 (ProjectOdyssey) |
| Pattern | Self-proving test via catastrophic failure mode |

## When to Use

- You need to prove an iterator-consuming loop calls `reset()` before iteration
- A validation/training loop accepts a pre-existing loader that may be partially consumed
- The failure mode (division by zero from zero batches) is clearly distinct from success (valid finite loss)
- You want a test that doesn't require mock objects — direct field mutation suffices

## Verified Workflow

### 1. Identify the reset call in the implementation

Read the source to confirm where `reset()` is called (e.g., `validation_loop.mojo:255`):

```mojo
val_loader.reset()
while val_loader.has_next() and num_batches < max_batches:
    ...
var avg_loss = total_loss / Float64(num_batches)  # division by zero if reset() absent
```

### 2. Pre-exhaust the loader via direct field mutation

```mojo
var loader = create_val_loader(n_batches=2)
# Advance current_batch to num_batches so has_next() returns False
loader.current_batch = loader.num_batches
assert_true(not loader.has_next())
```

### 3. Call the function under test with max_batches matching loader capacity

```mojo
var val_loss = vloop.run_subset(simple_forward, simple_loss, loader, 2, metrics)
```

### 4. Assert the result is a valid finite number

```mojo
# Valid loss proves 2 batches were processed after reset (not 0)
assert_greater(val_loss, Float64(-1e-10))
assert_less(val_loss, Float64(1e10))
```

Without `reset()`: `num_batches == 0` → `total_loss / 0.0` → `NaN` or raises.
With `reset()`: `num_batches == 2` → valid finite loss.

### 5. Why this is self-proving

The test does not require mocking. The failure mode (division by zero / NaN / raise) is
categorically different from the success mode (valid bounded Float64). No spy object needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Mock-based approach | Wrapping DataLoader to count reset() calls | Mojo structs don't support vtable-based mocking easily; no trait for spy | Use direct field mutation + observable side effects instead |
| Checking batch count post-call | Asserting `loader.current_batch == 2` after run_subset | run_subset may call reset() again at end or leave loader in partial state | Assert on the output (loss) not loader state after the call |
| Asserting exact loss value | `assert_almost_equal(val_loss, Float64(1.0), ...)` | Relies on loss function returning exactly 1.0; brittle if loss function changes | Use range assertions (`> -eps` and `< large`) for robustness |

## Results & Parameters

```mojo
# Copy-paste test template
fn test_run_subset_resets_loader() raises:
    var vloop = ValidationLoop()
    var loader = create_val_loader(n_batches=2)  # small loader to keep test fast
    loader.current_batch = loader.num_batches    # exhaust loader
    assert_true(not loader.has_next())           # confirm pre-condition
    var metrics = TrainingMetrics()
    var val_loss = vloop.run_subset(
        simple_forward, simple_loss, loader, 2, metrics
    )
    assert_greater(val_loss, Float64(-1e-10))    # finite: reset() was called
    assert_less(val_loss, Float64(1e10))
    print("  test_run_subset_resets_loader: PASSED")
```

**Key parameters:**

- `n_batches=2`: Minimum batches that allows `max_batches=2` to be meaningful
- `max_batches=2`: Must equal `n_batches` so that all batches are consumed after reset
- Range bounds: `-1e-10` to `1e10` — wide enough to tolerate any valid loss function
