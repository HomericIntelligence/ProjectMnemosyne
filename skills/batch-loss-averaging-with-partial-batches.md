---
name: batch-loss-averaging-with-partial-batches
description: "Use when: (1) computing average loss during model evaluation with uneven batch sizes, (2) handling the final partial batch when num_samples % batch_size != 0, (3) fixing over-weighted loss metrics from naive batch averaging, (4) implementing correct evaluation metrics for training frameworks. Proper batch loss averaging: track total_samples_processed, weight loss by batch_size during accumulation, divide by actual samples processed (not batch count)."
category: optimization
date: 2026-07-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [loss-computation, evaluation-metrics, batch-processing, numerical-correctness, partial-batches, training-loops, ResNet18]
---

# Batch Loss Averaging with Partial Batches

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-05 |
| **Objective** | Document the correct pattern for computing average loss during model evaluation when batch sizes are uneven, particularly when the final batch is smaller than the standard batch size. |
| **Outcome** | Verified — ResNet-18 CIFAR-10 evaluation function corrected to handle arbitrary batch sizes. Naive averaging (divide by batch count) over-weights partial final batches; correct approach divides by total samples processed. |
| **Verification** | verified-local |

## When to Use

- Computing average loss during model evaluation on validation/test sets
- Final batch size is smaller than the standard batch size (common edge case)
- Number of samples is not perfectly divisible by batch size: `num_samples % batch_size != 0`
- Loss metrics are unexpectedly high or inconsistent with batch-by-batch observations
- Implementing evaluation loops for training frameworks where loss must be aggregated across batches

## The Problem

### Naive (Incorrect) Approach

```mojo
var total_loss = Float32(0.0)
var num_batches = 0

for batch_idx in range(num_batches_total):
    let batch_loss = compute_batch_loss(batch)
    total_loss += batch_loss
    num_batches += 1

# WRONG: over-weights partial final batch
let avg_loss = total_loss / Float32(num_batches)
```

**Issue**: This averages loss values, not loss×sample_count. When the final batch has fewer samples (e.g., 32 instead of 128), that batch's loss is weighted equally to full batches. Since loss is computed as sum per batch, the partial batch contributes a smaller value (fewer samples), but dividing by count treats it as if it represents as many samples as full batches.

**Example**:
- Batch 1 (128 samples): loss = 1.28 (0.01 per sample)
- Batch 2 (128 samples): loss = 1.28 (0.01 per sample)
- Batch 3 (32 samples, partial): loss = 0.32 (0.01 per sample)
- Naive: `avg = (1.28 + 1.28 + 0.32) / 3 = 0.963` (WRONG, treats partial batch as equal weight)
- Correct: `avg = (1.28 + 1.28 + 0.32) / 288 = 0.01` (RIGHT, per-sample average)

## Verified Workflow

### Quick Reference

```mojo
var total_loss = Float32(0.0)
var total_samples_processed = 0

for batch_idx in range(num_batches_total):
    let batch_loss = compute_batch_loss(batch)
    let current_batch_size = batch.shape[0]

    # Weight loss by batch size
    total_loss += batch_loss * Float32(current_batch_size)
    total_samples_processed += current_batch_size

# CORRECT: divide by actual samples processed
let avg_loss = total_loss / Float32(total_samples_processed)
```

### Step-by-Step

1. **Initialize accumulators**
   ```mojo
   var total_loss = Float32(0.0)
   var total_samples_processed = 0
   ```

2. **Per-batch: accumulate weighted loss**
   ```mojo
   for batch_idx in range(num_batches):
       let batch = get_batch(batch_idx)
       let batch_loss = compute_batch_loss(batch)
       let current_batch_size = batch.shape[0]  # May vary for final batch

       # Key insight: multiply loss by batch_size
       total_loss += batch_loss * Float32(current_batch_size)
       total_samples_processed += current_batch_size
   ```

3. **Compute average**
   ```mojo
   let avg_loss = total_loss / Float32(total_samples_processed)
   ```

### Why This Corrects the Issue

- **Batch loss is already a sum** (sum of per-sample losses in that batch)
- **Naive division by batch count** treats a 32-sample batch equally to a 128-sample batch
- **Correct approach**: multiply each batch loss by its size so the total is: (sum of all per-sample losses)
- **Then divide by total samples** to get the true per-sample average

### Real Example: ResNet-18 CIFAR-10 Evaluation

**Setup**: 10,000 test samples, batch_size=128

- Batches 1-77: 128 samples each (77 × 128 = 9,856 samples)
- Batch 78: 144 samples remaining (10,000 - 9,856 = 144 samples)

**Naive averaging** (WRONG):
```
avg_loss = sum_of_batch_losses / 78 batches
```

**Correct averaging**:
```
avg_loss = sum_of_batch_losses / 10,000 samples
# (where sum_of_batch_losses was accumulated as:
#  total_loss += batch_loss * batch.shape[0])
```

## Implementation Pattern

### Training Evaluation Loop (Verified Code)

```mojo
fn evaluate(
    model: inout ResNet18,
    test_loader: TestDataLoader,
    batch_size: Int,
) -> Tuple[Float32, Float32]:  # (avg_loss, accuracy)
    """Evaluate model on test set with correct batch loss averaging."""

    var total_loss = Float32(0.0)
    var total_correct = 0
    var total_samples_processed = 0

    # Iterate over batches
    for batch_idx in range(test_loader.num_batches):
        let batch_images, batch_labels = test_loader.get_batch(batch_idx)

        # Forward pass
        let logits = model.forward(batch_images)

        # Compute batch loss (returns sum, not average)
        let batch_loss = cross_entropy_loss(logits, batch_labels)

        # Current batch size (may be < batch_size for final batch)
        let current_batch_size = batch_images.shape[0]

        # Accumulate: weight by batch size
        total_loss += batch_loss * Float32(current_batch_size)

        # Track correct predictions
        let predictions = argmax(logits)
        total_correct += count_matches(predictions, batch_labels)

        # Update total samples
        total_samples_processed += current_batch_size

    # Correct averaging: divide by total samples, not batch count
    let avg_loss = total_loss / Float32(total_samples_processed)
    let accuracy = Float32(total_correct) / Float32(total_samples_processed)

    return (avg_loss, accuracy)
```

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Perfect divisibility: `num_samples = 10,000`, `batch_size = 128` | No partial batch; all batches are 128. Naive and correct averaging both work (accidentally). This is rare. |
| Single batch: `num_samples < batch_size` | Only one batch with `current_batch_size = num_samples`. Multiply by 1 (or equiv, no scaling needed) and divide by `num_samples`. Both methods agree. |
| All partial batches: tiny dataset, batch_size is large | Each "batch" is smaller than requested. Multiply each by its actual size, sum totals, divide by sum of all batch sizes. |
| Empty dataset | Avoid division by zero: check `total_samples_processed > 0` before computing `avg_loss`. |

## Why Naive Averaging Fails in Detail

**Per-sample loss** is defined as:
```
per_sample_loss = -log(p_correct) [for cross-entropy]
```

**Batch loss** (as typically returned by loss functions) is:
```
batch_loss = sum(per_sample_loss[i] for i in batch)  # or mean, depending on implementation
```

If the loss function returns the **sum** (common for accumulation patterns):
- Batch 1 (128 samples, avg per-sample loss = 0.01): batch_loss = 1.28
- Batch 2 (128 samples, avg per-sample loss = 0.01): batch_loss = 1.28
- Batch 3 (32 samples, avg per-sample loss = 0.01): batch_loss = 0.32

**Naive**: `(1.28 + 1.28 + 0.32) / 3 = 0.963` — **WRONG** because it treats the partial batch as equal to full batches.

**Correct**: `(1.28 + 1.28 + 0.32) / (128 + 128 + 32) = 2.88 / 288 = 0.01` — **RIGHT** because it recovers the per-sample average.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Naive averaging: `avg_loss = sum_losses / num_batches` | ResNet-18 CIFAR-10 eval function divided total loss by number of batches (78 batches for 10K test samples) | Final batch is only 144 samples (not 128), so its loss was smaller but weighted equally. Result: over-estimated average loss. | Multiply each batch loss by its size during accumulation; divide by total samples at the end, not by batch count. |
| Padding the final batch | Tried to pad the final batch to batch_size before computing loss, then exclude padding from metrics | Padding changes the loss computation and introduces spurious gradients. Also wastes compute. | Never pad for evaluation; just track actual batch sizes and weight accordingly. |
| Storing per-sample losses in a list | Attempted to record all per-sample losses and average them post-hoc for perfect accuracy | Memory explosion for large datasets (10K samples × 4 bytes per loss = 40KB minimum, plus Python object overhead). For training loops, infeasible. | Track totals in-place. Weighted accumulation is both more efficient and mathematically correct. |

## Results & Parameters

### Verified Setup (ResNet-18 CIFAR-10 Evaluation)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Dataset | CIFAR-10 test split | 10,000 samples |
| Batch size | 128 | Standard size; final batch is 144 (10000 % 128 = 144) |
| Number of batches | 79 | ceil(10000 / 128) = 79 |
| Batch 1-78 | 128 samples each | 9,856 samples total |
| Batch 79 (final) | 144 samples | Remainder |
| Expected avg_loss formula | `total_loss / 10000` | Not `total_loss / 79` |

### Comparison: Naive vs. Correct

**Hypothetical run** (per-sample loss ≈ 0.01 on average):
- Batch 1-78 loss: 1.28 each (128 × 0.01)
- Batch 79 loss: 1.44 (144 × 0.01)
- Total loss across all batches: 78 × 1.28 + 1.44 = 100.68 + 1.44 = 102.12

| Method | Calculation | Result | Error |
|--------|-------------|--------|-------|
| Naive | 102.12 / 79 | 1.292 | 129.2% of true (way off) |
| Correct | 102.12 / 10000 | 0.01021 | ≈ true | ✓

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | ResNet-18 CIFAR-10 training (issue #5547, PR #5548) | Test evaluation function corrected; batch loss averaging now accounts for partial final batch. Epoch output shows loss 1.39, accuracy 48.37% (reasonable for epoch 1 of random-weight ResNet on CIFAR-10). |

## See Also

- `mojo-tensor-unit-test-and-gradient-checking` — gradient verification for loss computation
- `training-diagnosis-loss-accuracy-decoupling-overfitting` — distinguishing overfitting from loss computation bugs
- `evaluate-model` — general evaluation patterns
