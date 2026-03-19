---
name: mojo-val-accuracy-behavioral-test
description: 'Add a behavioral test asserting metrics.val_accuracy is updated after
  ValidationLoop.run() with compute_accuracy=True. Use when: a GH issue flags that
  only default values are tested but not behavioral effects, or when closing a test
  gap between init-defaults tests and run-effects tests.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Val Accuracy Behavioral Test

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-15 |
| **Category** | testing |
| **Objective** | Close the test gap where `ValidationLoop.run()` effect on `val_accuracy` was untested |
| **Outcome** | Added `test_validation_loop_run_updates_val_accuracy()` to verify `metrics.val_accuracy > 0.0` after run |
| **Context** | Issue #3183 (follow-up from #3082): existing test only verified `compute_accuracy=True` default, not its effect |

## When to Use

Use this skill when:

- A GitHub issue notes that a test verifies a default/init value but not the behavioral effect of a flag
- You need a deterministic Mojo accuracy assertion: use all-zero data + all-zero int32 labels so
  `argmax` always selects class 0, making accuracy predictable (1.0)
- Closing test coverage gap between "default value" tests and "behavioral effect" tests
- A `ValidationLoop.run()` calls `metrics.update_val_metrics(val_loss, 0.0)` and you need to prove
  it was later replaced by a real computed value

Do NOT use when:

- The implementation still passes `0.0` as a placeholder — fix the implementation first
  (see `mojo-validation-loop-accuracy-tracking` skill)
- The test fixture already has non-trivial logits — use a simple fixture (ones tensor, zero labels)
  to keep accuracy deterministic

## Verified Workflow

### Step 1: Identify the Gap

Read the GH issue for the flag pattern:

```bash
gh issue view <number>
```

Look for language like: _"no test verifies that accuracy is actually computed and stored
in `TrainingMetrics.val_accuracy` when `compute_accuracy=True`"_.

### Step 2: Check Existing Tests

```bash
grep -n "val_accuracy\|compute_accuracy" tests/shared/training/test_validation_loop.mojo
```

Confirm: there is a test for the default value (e.g., `test_validation_loop_init_defaults`)
but none that calls `ValidationLoop.run()` and asserts `metrics.val_accuracy > 0.0`.

### Step 3: Choose a Deterministic Fixture

The key to a deterministic accuracy test is making `argmax` predictable:

```mojo
# simple_forward returns ones([batch, 10], float32)
# All logits equal → argmax selects index 0
# Labels are 0 (float32 0.0 read as int32 0)
# All predictions match → accuracy = 1.0
```

This avoids flaky tests that depend on random weights or specific model behavior.

### Step 4: Write the Test

```mojo
fn test_validation_loop_run_updates_val_accuracy() raises:
    """Test ValidationLoop.run() with compute_accuracy=True updates metrics.val_accuracy.

    Verifies that after ValidationLoop.run() completes with compute_accuracy=True,
    metrics.val_accuracy is greater than 0.0 (i.e., it was actually computed and
    stored, not left at the default 0.0).

    Fixture: simple_forward returns ones([batch, 10], float32). argmax(axis=1)
    yields 0 for all samples (all logits equal, first index selected). Labels
    are zeros (float32 0.0, read as 0). All predictions match -> accuracy = 1.0.
    """
    var vloop = ValidationLoop(compute_accuracy=True)
    var loader = create_val_loader(n_batches=3)
    var metrics = TrainingMetrics()
    _ = vloop.run(simple_forward, simple_loss, loader, metrics)
    # accuracy must be stored (non-zero) and a valid fraction
    assert_greater(metrics.val_accuracy, Float64(0.0))
    assert_less(metrics.val_accuracy, Float64(1.0) + Float64(1e-10))
    print("  test_validation_loop_run_updates_val_accuracy: PASSED")
```

Key design choices:

- Use `assert_greater` / `assert_less` instead of exact equality — allows for floating point tolerance
- Upper bound: `1.0 + 1e-10` catches values > 1.0 which would indicate a bug
- The `_ =` pattern discards the return value explicitly (Mojo requires this)

### Step 5: Register in main()

```mojo
fn main() raises:
    # ... other tests ...
    test_validation_loop_run_compute_accuracy_false()
    test_validation_loop_run_updates_val_accuracy()  # Add after the False variant
```

### Step 6: Run and Verify

```bash
just test-group "tests/shared/training" "test_validation_loop.mojo"
```

Expected output:

```text
  test_validation_loop_run_updates_val_accuracy: PASSED
```

### Quick Reference

| Pattern | Code |
|---------|------|
| Deterministic accuracy fixture | `ones([batch, 10])` logits + `zeros` labels → accuracy = 1.0 |
| Discard return value | `_ = vloop.run(...)` |
| Tolerance-safe upper bound | `assert_less(x, Float64(1.0) + Float64(1e-10))` |
| Test ordering | Place after the `compute_accuracy_false` variant |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Exact equality `== 1.0` | Used `assert_equal(metrics.val_accuracy, Float64(1.0))` | Floating point precision — accumulated division may not be exactly 1.0 | Use `assert_greater(x, 0.0)` + `assert_less(x, 1.0 + epsilon)` |
| Skip fixture reuse | Created a new unique fixture for the test | Adds coupling; existing `create_val_loader` + `simple_forward` already produce deterministic all-zero labels with ones logits | Always check if existing fixtures produce the needed determinism before creating new ones |

## Results & Parameters

### Test Configuration

```mojo
# Fixture: reuse existing test helpers
var vloop = ValidationLoop(compute_accuracy=True)
var loader = create_val_loader(n_batches=3)   # 3 batches for statistical confidence
var metrics = TrainingMetrics()
```

### Assertion Pattern

```mojo
# Two-sided bounds for floating point safety
assert_greater(metrics.val_accuracy, Float64(0.0))
assert_less(metrics.val_accuracy, Float64(1.0) + Float64(1e-10))
```

### Commit Message Pattern

```text
test(validation): add val_accuracy tracking test for ValidationLoop.run()

Add test_validation_loop_run_updates_val_accuracy() to verify that
metrics.val_accuracy is updated to a non-zero value after ValidationLoop.run()
when compute_accuracy=True. Previously only the default value was tested; this
test closes the behavioral gap by asserting the effect of the flag.

Closes #<issue-number>
```
