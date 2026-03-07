---
name: mojo-validation-loop-accuracy-tracking
description: "Fix a Mojo ValidationLoop that hardcodes accuracy=0.0 in metrics updates and add a follow-up test verifying metrics.val_accuracy is updated. Use when: a ValidationLoop.run() passes placeholder 0.0 for accuracy, a GitHub issue asks for a test verifying val_accuracy is non-zero after run(), or you need to avoid Mojo tuple-return syntax."
category: testing
date: 2026-03-07
user-invocable: false
---

# Skill: Mojo Validation Loop Accuracy Tracking

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Category** | testing |
| **Objective** | Fix `ValidationLoop.run()` to pass real accuracy to `TrainingMetrics.val_accuracy` and add a test verifying it |
| **Outcome** | Added second-pass accuracy computation in `run()` using `AccuracyMetric`; test confirms `metrics.val_accuracy > 0.0` |
| **Context** | Issue #3183 - follow-up from #3082: `ValidationLoop.run()` was calling `metrics.update_val_metrics(val_loss, 0.0)` |

## When to Use

Use this skill when:

- A `ValidationLoop.run()` (or equivalent) calls `metrics.update_val_metrics(loss, 0.0)` with a hardcoded accuracy placeholder
- A GitHub issue asks for a follow-up test proving `metrics.val_accuracy` is updated after `run()` with `compute_accuracy=True`
- You need a deterministic Mojo test for accuracy: use all-zero data + all-zero int32 labels so `argmax` always picks class 0 and accuracy = 1.0
- You want to avoid Mojo tuple return syntax (`-> Tuple[T1, T2]`) and keep the `validate()` function signature unchanged

Do NOT use when:

- The validation loop already tracks accuracy internally (check for `metrics.update_val_metrics(loss, accuracy)` where accuracy is non-zero)
- The fix requires changing public API signatures (e.g., `validate()` is called externally with tuple unpacking)

## Verified Workflow

### Step 1: Locate the Placeholder

Search for the hardcoded `0.0` accuracy:

```bash
grep -n "update_val_metrics" <training-loops-dir>/validation_loop.mojo
```

Look for `metrics.update_val_metrics(val_loss, 0.0)` with a comment like `# Accuracy placeholder.`

### Step 2: Choose the Fix Strategy

**Option A (chosen): Second-pass in `run()`** — keeps `validate()` signature unchanged.

Add an `AccuracyMetric` accumulation loop after `validate()` returns, resetting the loader:

```mojo
var val_accuracy = Float64(0.0)
if self.compute_accuracy:
    var accuracy_metric = AccuracyMetric()
    val_loader.reset()
    while val_loader.has_next():
        var batch = val_loader.next()
        var predictions = model_forward(batch.data)
        accuracy_metric.update(predictions, batch.labels)
    val_accuracy = accuracy_metric.compute()

metrics.update_val_metrics(val_loss, val_accuracy)
```

**Option B (avoided): Tuple return from `validate()`** — change `-> Float64` to `-> Tuple[Float64, Float64]`.

Avoid this unless multiple callers of `validate()` need the accuracy. Mojo's tuple-return guidelines
require `-> Tuple[T1, T2]` syntax (NOT `-> (T1, T2)`), and tuple destructuring is non-idiomatic
in the existing codebase. The second-pass approach is simpler.

### Step 3: Write the Test

Use deterministic data where all predictions match all labels:

```mojo
fn test_validation_loop_run_updates_val_accuracy() raises:
    """Test that ValidationLoop.run() updates metrics.val_accuracy when compute_accuracy=True."""
    print("Testing ValidationLoop.run() updates val_accuracy...")

    # 4 samples, 3 features (2D so argmax selects predicted class)
    var data_shape = List[Int]()
    data_shape.append(4)
    data_shape.append(3)
    var data = ExTensor(data_shape, DType.float32)  # all zeros

    # Labels: shape [4], dtype int32, all zeros (class 0)
    var labels_shape = List[Int]()
    labels_shape.append(4)
    var labels = ExTensor(labels_shape, DType.int32)  # all zeros = class 0

    var val_loader = DataLoader(data, labels, batch_size=4)
    var validation_loop = ValidationLoop(compute_accuracy=True)
    var metrics = TrainingMetrics()

    assert_equal(metrics.val_accuracy, 0.0, "val_accuracy starts at 0.0")

    _ = validation_loop.run(
        mock_model_forward, mock_compute_loss, val_loader, metrics
    )

    # mock_model_forward returns input unchanged (zeros, shape [4,3])
    # argmax of all-equal values picks index 0 = class 0 = matches all labels
    assert_true(
        metrics.val_accuracy > 0.0,
        "val_accuracy updated to non-zero after run()",
    )

    print("  ✓ ValidationLoop.run() updates val_accuracy correctly")
```

**Why this works**: The mock model returns its input unchanged (all zeros, 2D). `AccuracyMetric.update()` calls `argmax(predictions, axis=1)` → picks index 0 for each row (all values equal). Labels are all-zero int32 → match → accuracy = 1.0 > 0.0.

### Step 4: Register the Test in main()

Add the test call in the `main()` function under the `ValidationLoop Tests` section:

```mojo
print("\nValidationLoop Tests (#314)")
print("-" * 70)
test_validation_loop_initialization()
test_validation_loop_run_updates_val_accuracy()  # ADD THIS
```

### Step 5: Verify Pre-Commit Hooks Pass

```bash
pixi run pre-commit run --all-files
# or
git add <files> && git commit -m "..."
```

Expected: all hooks pass (mojo format, syntax validation, test coverage check, trailing whitespace).

## Key Findings

### Avoid Tuple Return — Use Second Pass Instead

Mojo tuple-return syntax is `-> Tuple[T1, T2]` (NOT `-> (T1, T2)`). The existing codebase has
zero tuple-return functions. Adding one to `validate()` would be non-idiomatic and risk CI failure
from syntax unfamiliarity. The second-pass approach in `run()` is cleaner: reset the loader, iterate
again with `AccuracyMetric`, compute the scalar, pass it to `update_val_metrics`.

### Deterministic Test Pattern for Accuracy = 1.0

All-zero float32 data (shape `[N, C]`) + all-zero int32 labels → `argmax` always picks class 0
→ matches all labels → accuracy = 1.0. This works with any mock model that returns input unchanged
and any `DataLoader` that produces zero-filled placeholder tensors. Use `assert_true(acc > 0.0)`
rather than `assert_equal(acc, 1.0)` to be resilient to future DataLoader improvements.

### DataLoader Produces 2D Placeholder Tensors

The `DataLoader.next()` in this codebase returns `ExTensor` of shape `[actual_batch_size, num_features]`
for data and `[actual_batch_size]` for labels. These are zero-filled placeholders (no actual data
slicing). This makes them safe for deterministic accuracy tests.

### Local Mojo Unavailable

The local system had GLIBC version incompatibilities preventing `mojo test` from running.
CI (Docker-based) is required for actual Mojo test execution. Pre-commit hooks still pass locally.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Fix location | `ValidationLoop.run()` in `<training>/loops/validation_loop.mojo` |
| Fix approach | Second-pass `AccuracyMetric` loop after `validate()`, conditional on `self.compute_accuracy` |
| Test assertion | `assert_true(metrics.val_accuracy > 0.0, ...)` |
| Test data shape | `[4, 3]` float32, all zeros |
| Test labels shape | `[4]` int32, all zeros |
| Test batch size | `4` (single batch, all samples at once) |
| Expected accuracy | `1.0` (all predictions match all labels) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Tuple return `-> (Float64, Float64)` | Changed `validate()` to return `(avg_loss, accuracy)` and unpacked with `val_loss, val_accuracy = validate(...)` | Mojo guidelines say `-> (T1, T2)` is deprecated in favor of `-> Tuple[T1, T2]`; no tuple-return patterns exist in this codebase | Avoid tuple returns when the codebase has zero precedent; use a second-pass accumulation instead |
| `assert_equal(metrics.val_accuracy, 1.0)` | Tried to assert exact accuracy of 1.0 | Not chosen — using `> 0.0` is more resilient to future DataLoader changes that might affect placeholder values | Assert `> 0.0` rather than exact values when testing "was it computed" rather than "is it correct" |
| Run `pixi run mojo test` locally | Expected to verify test execution | GLIBC version mismatch (`GLIBC_2.32`, `2.33`, `2.34` not found on this Debian host) | Local Mojo requires newer GLIBC; use Docker/CI for actual Mojo test runs |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3678, Issue #3183 | [notes.md](../references/notes.md) |
