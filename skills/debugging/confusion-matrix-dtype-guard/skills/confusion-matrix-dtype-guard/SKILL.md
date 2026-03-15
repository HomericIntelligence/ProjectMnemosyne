---
name: confusion-matrix-dtype-guard
description: "Add dtype validation guards to Mojo metric structs that use bitcast to read tensor data, preventing silent corruption when callers pass float tensors. Use when: a metric update() silently accepts float32 labels, a bitcast fallback branch accepts any non-primary dtype, or adding input validation to Mojo structs consuming typed tensors."
category: debugging
date: 2026-03-15
user-invocable: false
---

# Skill: Confusion Matrix Dtype Guard

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-15 |
| **Category** | debugging |
| **Objective** | Guard Mojo metric `update()` methods against float dtype tensors passed as integer labels |
| **Outcome** | Added fast-fail dtype validation; 6 regression tests; PR merged to main |
| **Context** | Issue #3686 — ConfusionMatrix.update() silently accepts float32 labels |

## When to Use

Use this skill when:

- A Mojo metric's `update()` accepts an `ExTensor` for labels and uses `bitcast` to read values
- The `else` branch of a dtype check (`if dtype == DType.int32 ... else bitcast[Int64]`) silently
  accepts floats, reinterpreting their bits as large integers
- Callers can accidentally pass `DType.float32` tensors (common when reusing data pipeline outputs)
- The symptom is either silent garbage class indices or an out-of-range error with no dtype context
- You need to add validation without changing the happy-path behavior for `int32`/`int64` inputs

## Verified Workflow

### Quick Reference

```mojo
# Guard pattern for Mojo metric update()
if labels._dtype != DType.int32 and labels._dtype != DType.int64:
    raise Error(
        "ConfusionMatrix.update() requires int32 or int64 labels, got "
        + str(labels._dtype)
    )
```

### Step 1: Identify the vulnerable pattern

Look for code that reads an `ExTensor` via `bitcast` with an `else` fallback that implicitly
accepts all other dtypes:

```mojo
# VULNERABLE: float32 falls into the else branch
if labels._dtype == DType.int32:
    true_label = Int(labels._data.bitcast[Int32]()[i])
else:
    true_label = Int(labels._data.bitcast[Int64]()[i])  # float32 bits → huge int
```

### Step 2: Add the dtype guard after structural validation

Place the guard *after* batch-size and shape checks, *before* the per-element loop:

```mojo
if pred_classes._numel != labels._numel:
    raise Error("ConfusionMatrix.update: batch sizes must match")

# Validate label dtype — float bits bitcast to int64 produces garbage indices
if labels._dtype != DType.int32 and labels._dtype != DType.int64:
    raise Error(
        "ConfusionMatrix.update() requires int32 or int64 labels, got "
        + str(labels._dtype)
    )
```

### Step 3: Handle the 1D vs 2D prediction split

For metrics that accept either 1D class indices or 2D logits, only validate 1D inputs —
the 2D path goes through `argmax()` which always returns `int32`:

```mojo
# Validate predictions dtype for 1D inputs (2D logits go through argmax → int32)
if len(pred_shape) == 1:
    if pred_classes._dtype != DType.int32 and pred_classes._dtype != DType.int64:
        raise Error(
            "ConfusionMatrix.update() requires int32 or int64 predictions, got "
            + str(pred_classes._dtype)
        )
```

### Step 4: Update the docstring Raises section

```mojo
"""...
Raises:
    Error: If shapes are incompatible, labels out of range,
           or labels/predictions dtype is not int32 or int64.
"""
```

### Step 5: Write regression tests (ADR-009: ≤10 tests per file)

Test the three rejection cases and three acceptance cases:

| Test | Checks |
|------|--------|
| `test_float32_labels_raises` | `DType.float32` labels → raises with "int32 or int64" in message |
| `test_float64_labels_raises` | `DType.float64` labels → raises |
| `test_float32_predictions_1d_raises` | 1D `DType.float32` predictions → raises |
| `test_int32_labels_accepted` | `DType.int32` labels → no error (regression guard) |
| `test_int64_labels_accepted` | `DType.int64` labels → no error (regression guard) |
| `test_float32_logits_2d_accepted` | 2D `DType.float32` logits → no error (argmax path exempt) |

Test pattern for error message assertion:

```mojo
var raised = False
try:
    cm.update(preds, labels)
except e:
    raised = True
    var msg = str(e)
    assert_true(
        "int32 or int64" in msg,
        "Error message should mention 'int32 or int64', got: " + msg,
    )
assert_true(raised, "Expected Error for float32 labels was not raised")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Guard after loop | Placing the check inside the per-element loop | Redundant work; raises on first iteration instead of fast-failing before any loop | Always validate inputs before iterating — guards belong before the loop |
| Validate 2D predictions | Adding dtype check for `pred_classes` after the 2D argmax path | `argmax()` always returns `int32`, so the guard would never trigger and adds dead code | Only validate 1D inputs; document the 2D exemption explicitly |
| Generic "invalid dtype" message | Using `raise Error("invalid dtype")` without mentioning accepted types | Forces callers to read source to fix; poor UX | Error messages should include accepted values: "requires int32 or int64, got X" |

## Results & Parameters

**Files changed:**

- `shared/training/metrics/confusion_matrix.mojo` — dtype guard in `update()`, updated docstring
- `tests/training/test_confusion_matrix_dtype_guard.mojo` — 6 regression tests (new file)

**Guard placement:** after batch-size check, before per-element loop

**Error message format:**

```text
ConfusionMatrix.update() requires int32 or int64 labels, got float32
```

**Test file naming convention:** `test_<component>_<feature>.mojo` in
`tests/training/` alongside existing split test files

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3686, PR #4769 | [notes.md](../references/notes.md) |
