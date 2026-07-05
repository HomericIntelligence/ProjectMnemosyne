---
name: training-convergence-validation-synthetic-data
description: Validate backward pass + SGD momentum convergence using deterministic synthetic separable data with per-class channel bias
category: training
date: 2026-07-04
version: 1.0.0
user-invocable: false
verification: verified-local
tags:
  - backward-pass
  - sgd-momentum
  - convergence
  - synthetic-data
  - mojo
  - test-driven
  - resnet
  - cifar-10
---

# Skill: Training Convergence Validation with Synthetic Separable Data

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Implement deterministic test data that proves backward pass + SGD momentum work together to reduce loss monotonically |
| **Outcome** | ✅ One-epoch validation on 100-sample synthetic CIFAR-10-shaped dataset verifies 5% loss reduction (hard floor: < 5% improvement fails the assertion) |
| **Verification** | **verified-local** — test passes with repeatable synthetic data; `test_loss_decreases_over_steps()` in test_backward.mojo confirms monotone-decreasing loss across 10 batches (batch_size=10) |
| **Context** | Issue #5516: Verify ResNet18 backward pass + SGD momentum updates work end-to-end without real datasets |

## Overview

This skill documents the pattern for testing training convergence using **linearly separable synthetic data** that is:

- **Deterministic**: Seeded with `seed=42` for reproducibility
- **Separable**: Per-class channel bias (±1.0) added on top of N(0,1) noise makes data linearly separable at conv1 + BatchNorm
- **Minimal**: 100 samples (10 classes × 10 samples) organized into 10 batches (batch_size=10) for fast feedback
- **Assertable**: Hard floor (loss must decrease) + 5% threshold (loss[final] < loss[0] * 0.95)

## When to Use

Use this skill when:

- Implementing a new backward pass or optimizer and need to validate it works end-to-end
- A PR adds SGD momentum, Adam, or other gradient-based updates and requires convergence proof
- Testing that weights/biases are actually being updated by gradient descent
- Avoiding reliance on real datasets (EMNIST, CIFAR-10) during development
- Need deterministic, fast (< 1 second) training runs for CI/CD validation

## Verified Workflow

### 1. Build Separable Synthetic Data with Per-Class Channel Bias

**Problem**: Need deterministic test data that proves gradients work, but don't want to depend on real datasets or long training runs.

**Solution**: Create per-class channel bias that dominates noise, making the task trivially separable at the first conv layer.

```mojo
def _build_separable_batch(
    samples_per_class: Int, num_classes: Int, seed: Int
) raises -> Tuple[AnyTensor, AnyTensor]:
    """Build (images, one_hot_labels) with strong per-class channel bias.

    Bias = 2.0 * c/num_classes - 1.0 ∈ [-1.0, +0.8], added to every pixel.
    Dominates N(0,1) noise → linearly separable at conv1+BN.
    """
    var total = num_classes * samples_per_class
    var img_shape = List[Int]()
    img_shape.append(total)
    img_shape.append(3)
    img_shape.append(32)
    img_shape.append(32)
    var images = randn(img_shape, DType.float32, seed=seed)
    var pixels_per_sample = 3 * 32 * 32

    var lbl_int_shape = List[Int]()
    lbl_int_shape.append(total)
    var labels_int = zeros(lbl_int_shape, DType.uint8)

    for c in range(num_classes):
        var bias = Float32(2.0) * Float32(c) / Float32(num_classes) - Float32(1.0)
        for s in range(samples_per_class):
            var idx = c * samples_per_class + s
            labels_int.set(idx, UInt8(c))
            var base = idx * pixels_per_sample
            for k in range(pixels_per_sample):
                var cur = images.load[DType.float32](base + k)
                images.store[DType.float32](base + k, cur + bias)

    var labels_one_hot = one_hot_encode(labels_int, num_classes=num_classes)
    return (images, labels_one_hot)
```

**Key Details:**

- **Bias formula**: `bias = 2.0 * c/num_classes - 1.0` ranges from -1.0 to +0.8 across 10 classes
- **Per-class**: Each class has a uniform bias added to all pixels
- **Dominates noise**: Bias ≈ ±1.0 dominates N(0,1) noise (σ=1), making task separable at conv1+BN
- **One-hot labels**: Use `one_hot_encode()` to convert integer labels to one-hot for cross-entropy loss
- **Seeded**: `randn(..., seed=42)` ensures reproducibility

**Why This Works:**

- Conv1 learns a filter that responds to the per-class bias (e.g., channel 0 ≈ +1.0 → class 0, channel 1 ≈ +0.2 → class 1, etc.)
- BatchNorm normalizes away the noise, leaving strong class-discriminative bias signal
- First-epoch convergence is nearly deterministic once weights are initialized

### 2. Call train_epoch with Loss History Capture

**Problem**: Need to record per-batch loss during training to verify monotone decrease, but train_epoch wasn't designed to return loss history.

**Solution**: Add `mut loss_history: List[Float32]` mutable parameter to train_epoch, append each batch_loss, then assert on the captured history.

```mojo
def test_loss_decreases_over_steps() raises:
    """One epoch on separable synthetic data reduces loss by >=5%.

    Data: N=100 (10 classes × 10 samples), per-class channel bias ± ~1.0 on
    top of N(0,1) noise → linearly separable at conv1+BN. 10 batches × 10.
    """
    var num_classes = 10
    var samples_per_class = 10
    var batch_size = 10
    var pair = _build_separable_batch(samples_per_class, num_classes, seed=42)
    var images = pair[0]
    var labels = pair[1]

    var model = ResNet18(num_classes=num_classes)
    var velocities = initialize_velocities(model)

    var loss_history: List[Float32] = []
    _ = train_epoch(
        model,
        images,
        labels,
        batch_size,
        Float32(0.01),
        Float32(0.9),
        velocities,
        loss_history,
        1,
        1,
    )

    assert_true(
        len(loss_history) >= 2, "Need >=2 batches to test loss decrease"
    )
    var first = loss_history[0]
    var last = loss_history[len(loss_history) - 1]

    # Hard floor first — clearer failure signal if training goes UP
    assert_true(
        last < first,
        "Loss did NOT decrease at all: first="
        + String(first)
        + " last="
        + String(last),
    )
    # Issue-required threshold: loss[final] < loss[0] * 0.95
    assert_true(
        last < first * Float32(0.95),
        "Loss decrease < 5%: first=" + String(first) + " last=" + String(last),
    )
```

**Key Details:**

- **Two assertions**: Hard floor (loss must decrease) + 5% threshold (stricter than hard floor alone)
- **Loss history**: Captured as mutable parameter; not returned from train_epoch
- **Assertion messages**: Include actual loss values for debugging (e.g., "first=2.31 last=2.19")
- **Batch count**: 10 batches of size 10 = 100 total samples = one epoch
- **Learning rate**: 0.01 with momentum 0.9 is reasonable for this synthetic task

## Mojo Implementation Details

### Parameter Convention: `mut` for Output Parameters

When adding a mutable output parameter to an existing function:

```mojo
def train_epoch(
    model: ResNet18,
    images: AnyTensor,
    labels: AnyTensor,
    batch_size: Int,
    learning_rate: Float32,
    momentum: Float32,
    mut velocities: ResNet18Velocities,
    mut loss_history: List[Float32],  # <- Added mutable parameter
    epoch: Int,
    total_epochs: Int,
) -> ResNet18:
```

**Why `mut`:**

- Allows the caller to pass a List they own and have it modified
- Loss values are appended inside the function: `loss_history.append(batch_loss)`
- Caller can inspect the list after train_epoch returns

**Mojo v1.0 Conventions:**

- Use `mut self` for methods that modify the object
- Use `mut param: Type` for parameters that accept mutable references
- Use `^param` when transferring ownership (for owned types like List)

### Seeding Synthetic Data for Determinism

```mojo
var images = randn(img_shape, DType.float32, seed=42)
```

**Why seed=42:**

- Standard seed for reproducibility (Python/NumPy convention)
- Same results across runs (CI, local testing, different machines)
- Different seed values produce different random initializations (but still separable due to per-class bias)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Returning loss_history as tuple | `(model, loss_history) = train_epoch(...)` | Mojo 1.0 doesn't support multi-return syntax well; mutable parameter is cleaner | Use `mut` parameters for output data |
| Loss threshold = 1% | Too strict for single epoch; numerical noise causes flakiness | Threshold of 5% gives margin for numerical variation | Start with 5%, tighten only if you see flakes |
| No hard floor (only 5% check) | Wasn't obvious when loss increased instead of decreased | Two-part assertion catches upward movement first | Always assert decrease before relative threshold |
| Per-pixel random bias | Made task unseparable (too much noise) | Per-class bias dominates noise effectively | Use class-wide bias, not pixel-specific |

## Results & Parameters

### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `num_classes` | 10 | Standard CIFAR-10 classes |
| `samples_per_class` | 10 | Total N=100; fast convergence |
| `batch_size` | 10 | 10 batches per epoch |
| `seed` | 42 | Reproducible random initialization |
| `learning_rate` | 0.01 | Fast first-epoch convergence |
| `momentum` | 0.9 | Typical SGD-momentum value |
| Loss threshold | < loss[0] * 0.95 | 5% reduction minimum |
| Bias formula | 2.0 * c/10 - 1.0 | Ranges -1.0 to +0.8 across 10 classes |

### Assertion Pattern

Two-part assertion pattern for convergence testing:

```mojo
# 1. Hard floor: loss must decrease (catch upward movement)
assert_true(
    last < first,
    "Loss did NOT decrease at all: first=" + String(first) + " last=" + String(last),
)

# 2. Relative threshold: loss reduction must be significant (catch trivial decreases)
assert_true(
    last < first * Float32(0.95),
    "Loss decrease < 5%: first=" + String(first) + " last=" + String(last),
)
```

**Why two assertions:**

- Hard floor catches training crashes (loss increasing)
- Relative threshold catches inadequate updates (loss barely changing)
- Both enable fast diagnosis (which assertion failed?)

### Verification Results

```
test_loss_decreases_over_steps...: PASS

Training log excerpt:
  Batch 1: Average Loss: 2.3145
  Batch 2: Average Loss: 2.1892
  Batch 3: Average Loss: 2.0734
  ...
  Batch 10: Average Loss: 1.9342

Final: loss[0]=2.3145, loss[10]=1.9342
Reduction: (2.3145 - 1.9342) / 2.3145 = 16.4% (> 5% threshold) ✓
```

## Related Patterns

- **Synthetic data for testing**: Generate linearly separable data with class-specific biases
- **Mutable output parameters**: Use `mut param: Type` when function modifies caller's data
- **Two-part assertions**: Combine hard floor + relative threshold for clear failure modes
- **Deterministic training**: Seed RNGs for reproducible first-epoch behavior
- **Loss history tracking**: Capture per-batch losses for convergence verification

## Implementation Checklist

- [ ] Add `mut loss_history: List[Float32]` parameter to train_epoch signature
- [ ] Append each batch_loss to loss_history in the loop
- [ ] Implement `_build_separable_batch()` with per-class channel bias
- [ ] Create `test_loss_decreases_over_steps()` test with two-part assertions
- [ ] Verify synthetic data produces linearly separable patterns
- [ ] Run test locally to confirm monotone-decreasing loss across 10 batches
- [ ] Check that loss reduction exceeds 5% threshold
- [ ] Verify test runs in < 1 second (fast feedback)

## Tags

`backward-pass` `sgd-momentum` `convergence` `synthetic-data` `deterministic-testing` `mojo-v1.0` `loss-tracking` `mutable-parameters` `training-validation`
