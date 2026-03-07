---
name: mojo-confusion-matrix-integration-tests
description: "Pattern for adding ConfusionMatrix integration tests to a Mojo ValidationLoop test file. Use when: a ValidationLoop accepts compute_confusion=True but has no test covering that path, or you need to verify exact ConfusionMatrix cell counts with known binary fixtures."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Issue | #3185 — Add ValidationLoop confusion matrix integration test |
| Language | Mojo v0.26.1+ |
| Files changed | `tests/shared/training/test_validation_loop.mojo` |
| Tests added | 4 (smoke test + 3 unit tests) |

## When to Use

- A `ValidationLoop` struct accepts `compute_confusion=True` / `num_classes=N` but no test exercises that code path
- Need to verify `ConfusionMatrix.update()` cell counts with controlled binary fixtures
- Adding confusion matrix coverage without a working local Mojo runtime (CI-only execution)
- Extending an existing `.mojo` test file with a new section following established patterns

## Verified Workflow

1. **Read the existing test file** to identify import conventions, helper functions, and the `main()` structure.
2. **Read the `ConfusionMatrix` source** (`shared/training/metrics/confusion_matrix.mojo`) to understand:
   - Constructor: `ConfusionMatrix(num_classes=N)`
   - `update(predictions: ExTensor, labels: ExTensor)` — accepts 1D int32 class indices or 2D float logits
   - `normalize(mode="none")` returns `Float64` tensor; raw counts read via `_data.bitcast[Float64]()[idx]`
3. **Read existing ConfusionMatrix tests** (`tests/training/test_confusion_matrix.mojo`) to confirm the
   `ExTensor` construction pattern for int32 class index tensors:
   ```mojo
   var preds_shape = List[Int]()
   preds_shape.append(N)
   var preds = ExTensor(preds_shape, DType.int32)
   preds._data.bitcast[Int32]()[0] = Int32(0)
   ```
4. **Add `ConfusionMatrix` import** to the test file alongside existing metric imports.
5. **Add `assert_equal_int` import** from `tests.shared.conftest` (already available in the project).
6. **Write 4 tests** as a new `# Confusion Matrix Integration Tests` section before `# Test Main`:
   - `test_validation_loop_confusion_matrix_basic`: smoke test — `ValidationLoop(compute_confusion=True, num_classes=2).run()` with 2-column float32 logit data and int32 labels, assert loss >= 0
   - `test_confusion_matrix_binary_counts`: known fixture `y_true=[0,1,0,1]`, `y_pred=[0,1,1,0]`, assert TN=1, FP=1, FN=1, TP=1
   - `test_confusion_matrix_all_correct`: `y_true=y_pred=[0,0,1,1]`, assert TN=2, FP=0, FN=0, TP=2
   - `test_confusion_matrix_all_wrong`: all-swapped predictions, assert zero diagonal
7. **Call the 4 new tests** from `main()` under `print("Running confusion matrix integration tests...")`.
8. **Run `pixi run pre-commit run --all-files`** — all hooks must pass before committing.
9. **Commit, push, create PR** with `Closes #<issue>` in the body.

## Key Patterns

### int32 ExTensor construction (class indices)

```mojo
var shape = List[Int]()
shape.append(4)
var labels = ExTensor(shape, DType.int32)
labels._data.bitcast[Int32]()[0] = Int32(0)
labels._data.bitcast[Int32]()[1] = Int32(1)
```

### Reading raw confusion matrix counts

```mojo
var raw = cm.normalize(mode="none")
# raw is Float64 tensor; matrix[row, col] = raw._data.bitcast[Float64]()[row * num_classes + col]
var tn = Int(raw._data.bitcast[Float64]()[0])  # [true=0, pred=0]
var fp = Int(raw._data.bitcast[Float64]()[1])  # [true=0, pred=1]
var fn_ = Int(raw._data.bitcast[Float64]()[2]) # [true=1, pred=0]
var tp = Int(raw._data.bitcast[Float64]()[3])  # [true=1, pred=1]
```

### Smoke test with ValidationLoop (DataLoader is a placeholder)

The `DataLoader.next()` in this project is a placeholder that returns zero-initialized tensors.
The smoke test only verifies the code path runs without crashing — it does NOT assert exact
confusion matrix counts because the DataLoader does not copy real data into batches.

```mojo
var vloop = ValidationLoop(compute_confusion=True, num_classes=2)
var loader = DataLoader(data^, labels^, batch_size=4)
var metrics = TrainingMetrics()
var val_loss = vloop.run(simple_forward, simple_loss, loader, metrics)
assert_greater(val_loss, Float64(-1e-10))
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo test` locally | Tried to execute Mojo tests to verify correctness | GLIBC version too old (2.31 on Debian Buster, needs 2.32+) — mojo binary exits with version errors | Tests can only run in Docker/CI; write tests by reading existing patterns and source code, not by executing |
| Asserting exact confusion matrix counts in the ValidationLoop smoke test | Tried to check TP/TN/FP/FN after `vloop.run()` | `DataLoader.next()` is a placeholder that returns zero-initialized tensors, not slices of the real dataset | Use the ValidationLoop smoke test only to verify no crash; test exact counts directly on `ConfusionMatrix.update()` |
| Using float32 labels with ValidationLoop | Passed float32 labels to DataLoader expecting ConfusionMatrix to handle them | `ConfusionMatrix.update()` requires int32 or int64 labels; float labels produce wrong index reads | Always use `DType.int32` for class index label tensors passed to ConfusionMatrix |

## Results & Parameters

```text
4 tests added to tests/shared/training/test_validation_loop.mojo
All pre-commit hooks passed (mojo format, trailing-whitespace, end-of-file, check-yaml, etc.)
PR #3679 created, auto-merge enabled
Issue #3185 closed
```

### Imports added

```mojo
from shared.training.metrics import ConfusionMatrix
# In conftest import block:
assert_equal_int,
```

### Test section header convention

```mojo
# ============================================================================
# Confusion Matrix Integration Tests
# ============================================================================
```
