---
name: mojo-validation-loop-accuracy-tracking
description: "Fix a Mojo ValidationLoop that hardcodes accuracy=0.0 in metrics updates and add tests verifying metrics.val_accuracy is updated. Use when: a ValidationLoop.run() passes placeholder 0.0 for accuracy, a GitHub issue asks for a test verifying val_accuracy is non-zero after run(), you need to avoid Mojo tuple-return syntax, or the implementation is already fixed and only the test is missing."
category: testing
date: 2026-03-07
user-invocable: false
---

# Skill: Mojo Validation Loop Accuracy Tracking

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 (updated 2026-03-15) |
| **Category** | testing |
| **Objective** | Fix `ValidationLoop.run()` to pass real accuracy to `TrainingMetrics.val_accuracy` and add tests verifying it |
| **Outcome** | Second-pass accuracy computation in `run()` using `AccuracyMetric`; tests confirm `metrics.val_accuracy` is set correctly |
| **Context** | Issue #3183 (fix + initial test), Issue #3685 (follow-up: stronger assertion test only) |

## When to Use

Use this skill when:

- A `ValidationLoop.run()` (or equivalent) calls `metrics.update_val_metrics(loss, 0.0)` with a
  hardcoded accuracy placeholder
- A GitHub issue asks for a follow-up test proving `metrics.val_accuracy` is updated after `run()`
  with `compute_accuracy=True`
- The implementation is already fixed but only an assertion-based test is missing
- You need a deterministic Mojo test for accuracy: use all-zero data + all-zero int32 labels so
  `argmax` always picks class 0 and accuracy = 1.0
- You want to avoid Mojo tuple return syntax (`-> Tuple[T1, T2]`) and keep the `validate()`
  function signature unchanged

Do NOT use when:

- The validation loop already tracks accuracy internally (check for
  `metrics.update_val_metrics(loss, accuracy)` where accuracy is non-zero)
- The fix requires changing public API signatures (e.g., `validate()` is called externally with
  tuple unpacking)

## Verified Workflow

### Step 0: Check If Implementation Is Already Fixed

Before writing any implementation code, check:

```bash
grep -n "update_val_metrics" <training-loops-dir>/validation_loop.mojo
grep -n "val_accuracy" <training-loops-dir>/validation_loop.mojo
```

If `run()` already contains a second-pass `AccuracyMetric` loop and passes `val_accuracy` (not
`0.0`) to `update_val_metrics`, the implementation is done — **skip directly to Step 3**.

This happened in Issue #3685: the fix from Issue #3183 was already committed to the branch.
Only the test was missing.

### Step 1: Locate the Placeholder (if needed)

Search for the hardcoded `0.0` accuracy:

```bash
grep -n "update_val_metrics" <training-loops-dir>/validation_loop.mojo
```

Look for `metrics.update_val_metrics(val_loss, 0.0)` with a comment like `# Accuracy placeholder.`

### Step 2: Choose the Fix Strategy (if needed)

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

**Option B (avoided): Tuple return from `validate()`** — change `-> Float64` to
`-> Tuple[Float64, Float64]`.

Avoid this unless multiple callers of `validate()` need the accuracy. Mojo's tuple-return
guidelines require `-> Tuple[T1, T2]` syntax (NOT `-> (T1, T2)`), and tuple destructuring is
non-idiomatic in the existing codebase. The second-pass approach is simpler.

### Step 3: Write the Test

Two valid patterns depending on what helpers exist in the test file:

**Pattern A: Using existing test helpers (preferred when available)**

If the test file already has `simple_forward` (returns `ones([batch, C])`) and
`create_val_loader` (creates loader with `zeros` labels), use them directly:

```mojo
fn test_validation_loop_run_accuracy_tracked() raises:
    """Test ValidationLoop.run() stores computed accuracy in TrainingMetrics.val_accuracy.

    simple_forward returns ones([batch, 10]) -> argmax of each row is index 0
    (all values equal, first index wins). Labels are zeros([n, 1]) -> all label=0.
    argmax=0 == label=0 -> accuracy = 1.0.
    """
    var vloop = ValidationLoop()  # compute_accuracy=True by default
    var loader = create_val_loader(n_batches=3)
    var metrics = TrainingMetrics()
    _ = vloop.run(simple_forward, simple_loss, loader, metrics)
    # All predictions correct -> accuracy = 1.0
    assert_almost_equal(metrics.val_accuracy, Float64(1.0), Float64(1e-5))
    print("  test_validation_loop_run_accuracy_tracked: PASSED")
```

**Pattern B: Custom mock with explicit tensor construction**

Use when no helpers exist. Create tensors manually:

```mojo
fn test_validation_loop_run_updates_val_accuracy() raises:
    """Test that ValidationLoop.run() updates metrics.val_accuracy when compute_accuracy=True."""
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

    _ = validation_loop.run(
        mock_model_forward, mock_compute_loss, val_loader, metrics
    )

    # argmax of all-equal values picks index 0 = class 0 = matches all labels
    assert_true(
        metrics.val_accuracy > 0.0,
        "val_accuracy updated to non-zero after run()",
    )
```

**When to use exact vs. `> 0.0` assertion**:

- `assert_almost_equal(acc, 1.0, 1e-5)` — use when helpers produce well-defined 1.0 accuracy
  (e.g., `simple_forward` with `ones` data, `zeros` labels)
- `assert_true(acc > 0.0)` — use when mock data may change or DataLoader is placeholder-based

### Step 4: Also Add the Negative Test (compute_accuracy=False)

Always pair the positive test with a negative case:

```mojo
fn test_validation_loop_run_compute_accuracy_false() raises:
    """When compute_accuracy=False, val_accuracy stays at default 0.0."""
    var vloop = ValidationLoop(compute_accuracy=False)
    var loader = create_val_loader(n_batches=3)
    var metrics = TrainingMetrics()
    var val_loss = vloop.run(simple_forward, simple_loss, loader, metrics)
    assert_almost_equal(metrics.val_accuracy, Float64(0.0), Float64(1e-10))
    print("  test_validation_loop_run_compute_accuracy_false: PASSED")
```

### Step 5: Register the Tests in main()

Add both test calls in `main()` under the `ValidationLoop.run() Tests` section:

```mojo
print("Running ValidationLoop.run() tests...")
test_validation_loop_run_basic()
test_validation_loop_run_updates_metrics()
test_validation_loop_run_compute_accuracy_false()
test_validation_loop_run_accuracy_tracked()  # ADD THIS
```

### Step 6: Verify Pre-Commit Hooks Pass

```bash
pixi run pre-commit run --all-files
# or
SKIP=mojo-format git commit -m "..."  # if mojo-format incompatible locally
```

Expected: all hooks pass (mojo format, syntax validation, test coverage check, trailing whitespace).

## Key Findings

### Check Implementation Before Writing Code

On a follow-up issue (e.g., "add the missing test"), the implementation fix may already be on
the branch from a prior session. Always grep for the actual call site before writing any
implementation. This prevents wasted effort rewriting already-correct code.

### Avoid Tuple Return — Use Second Pass Instead

Mojo tuple-return syntax is `-> Tuple[T1, T2]` (NOT `-> (T1, T2)`). The existing codebase has
zero tuple-return functions. Adding one to `validate()` would be non-idiomatic and risk CI
failure from syntax unfamiliarity. The second-pass approach in `run()` is cleaner: reset the
loader, iterate again with `AccuracyMetric`, compute the scalar, pass it to `update_val_metrics`.

### Deterministic Test Pattern for Accuracy = 1.0

All-zero float32 data (shape `[N, C]`) + all-zero int32 labels → `argmax` always picks class 0
→ matches all labels → accuracy = 1.0. This works with any mock model that returns input
unchanged and any `DataLoader` that produces zero-filled placeholder tensors.

Prefer `ones` data + `zeros` labels if the test file has a `simple_forward` that returns
`ones(data.shape(), data.dtype())` — argmax of equal values picks index 0.

### Reuse Existing Test Helpers

When a test file already has helpers like `simple_forward`, `simple_loss`, `create_val_loader`,
use them. This produces shorter, more consistent tests and avoids duplicating tensor construction
boilerplate. Use `assert_almost_equal(..., 1.0, 1e-5)` for the exact assertion when helpers
produce fully deterministic accuracy.

### Local Mojo Unavailable

The local system has GLIBC version incompatibilities preventing `mojo test` from running.
CI (Docker-based) is required for actual Mojo test execution. Pre-commit hooks still pass locally.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Fix location | `ValidationLoop.run()` in `<training>/loops/validation_loop.mojo` |
| Fix approach | Second-pass `AccuracyMetric` loop after `validate()`, conditional on `self.compute_accuracy` |
| Test assertion (exact) | `assert_almost_equal(metrics.val_accuracy, Float64(1.0), Float64(1e-5))` |
| Test assertion (loose) | `assert_true(metrics.val_accuracy > 0.0, ...)` |
| Test data shape | `[N, C]` float32, all zeros (or ones) |
| Test labels shape | `[N]` or `[N, 1]` int32/float32, all zeros |
| Test batch size | Use n_batches=3 with `create_val_loader` for multi-batch coverage |
| Expected accuracy | `1.0` (all predictions match all labels) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Tuple return `-> (Float64, Float64)` | Changed `validate()` to return `(avg_loss, accuracy)` and unpacked with `val_loss, val_accuracy = validate(...)` | Mojo guidelines say `-> (T1, T2)` is deprecated; no tuple-return patterns exist in this codebase | Avoid tuple returns when the codebase has zero precedent; use a second-pass accumulation instead |
| `assert_equal(metrics.val_accuracy, 1.0)` (non-fuzzy) | Tried exact int equality | Mojo assert_equal is for integers; floating point needs assert_almost_equal | Use `assert_almost_equal(val, expected, tolerance)` for Float64 comparisons |
| Run `pixi run mojo test` locally | Expected to verify test execution | GLIBC version mismatch (`GLIBC_2.32`, `2.33`, `2.34` not found) | Local Mojo requires newer GLIBC; use Docker/CI for actual Mojo test runs |
| Writing new implementation code on follow-up issue | Assumed implementation was missing | Implementation was already committed from prior session (Issue #3183) | Always grep the source file before writing implementation code on follow-up issues |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3678, Issue #3183 (implementation + initial test) | [notes.md](../references/notes.md) |
| ProjectOdyssey | PR #4768, Issue #3685 (follow-up: test with exact assertion) | [notes.md](../references/notes.md) |
