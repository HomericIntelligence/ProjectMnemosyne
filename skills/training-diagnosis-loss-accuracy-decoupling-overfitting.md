---
name: training-diagnosis-loss-accuracy-decoupling-overfitting
description: "Diagnose late-stage supervised-classification runs where training loss keeps falling but test accuracy plateaus and slowly regresses. Use when: (1) user reports loss-down-accuracy-flat from a long epoch log, (2) user hoped for grokking but is seeing slow test regression instead, (3) auditing a fixed-epoch training run with no validation split."
category: training
date: '2026-05-25'
version: '1.0.0'
user-invocable: false
verification: unverified
tags:
  - overfitting
  - early-stopping
  - cross-entropy
  - diagnostics
  - lenet
  - emnist
  - grokking
---

# Training Diagnosis: Loss/Accuracy Decoupling = Late-Stage Cross-Entropy Overfitting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-25 |
| **Objective** | Diagnose the "training loss keeps dropping, test accuracy plateaus then regresses" pattern in long supervised-classification runs and distinguish it from grokking, LR misconfiguration, and bugs. |
| **Outcome** | Detection recipe verified on a real 500-epoch LeNet-5/EMNIST log; prescriptive remediation (early stopping / regularization re-run) was recommended but not re-executed. |
| **Verification** | **unverified** — see warning below. |

## When to Use

- A long supervised run's log shows `Average Loss` continuing to fall after `Test Accuracy` has plateaued.
- Test accuracy slowly regresses by tenths-of-a-percent over hundreds of epochs after a peak.
- The log filename hints at hoping for grokking (e.g., `grok_*.log`) but the curve is the opposite shape: smooth descent + slow regression rather than a sudden late jump.
- A fixed-epoch training run was kicked off with no validation split and no periodic checkpoints, and the user is asking "is this overfitting or something else?"
- You need to confirm the fingerprint before recommending early stopping or regularization tweaks.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. The *detection* part (the Python regex extractor below) was actually run against a real 500-epoch LeNet-5 log and produced the numbers reported in "Results & Parameters". The *prescriptive remediation* part (early stop at the `first99` epoch, add weight decay, add a val split and re-run) was delivered as advice and has **not** been re-executed to confirm it recovers the lost accuracy. Treat the remediation as a hypothesis until a re-run confirms it.

### Quick Reference

```python
# Diagnose late-stage overfitting from an epoch-by-epoch training log
import re

log = open('training.log').read()
losses = [float(x) for x in re.findall(r'Average Loss:\s+([\d.]+)', log)]
accs   = [float(x) for x in re.findall(r'Test Accuracy:\s+([\d.]+)\s*%', log)]

peak_acc = max(accs)
peak_ep  = accs.index(peak_acc) + 1
print(f"peak={peak_acc:.4f}% @ ep {peak_ep}, loss_there={losses[peak_ep-1]:.4f}")
print(f"final acc={accs[-1]:.4f}% (delta={accs[-1]-peak_acc:+.4f} pp), final loss={losses[-1]:.4f}")
print(f"loss_drop_after_peak={losses[peak_ep-1]-losses[-1]:.4f}")
print(f"epochs_below_peak_after_peak="
      f"{sum(1 for a in accs[peak_ep-1:] if a < peak_acc-0.05)}/{len(accs)-peak_ep+1}")

# Sweet-spot checkpoint epoch: first one reaching 99% of peak
target99 = 0.99 * peak_acc
first99 = next(i+1 for i, a in enumerate(accs) if a >= target99)
print(f"first ep reaching 99% of peak: {first99}")
```

### Detailed Steps

1. **Extract per-epoch loss and accuracy** with the regex above (adjust patterns to match the project's log format).
2. **Compute the three diagnostic ratios:**
   - `loss_drop_after_peak / loss_at_peak` — fraction of remaining loss the optimizer chewed through *after* the test-accuracy peak.
   - `peak_acc - final_acc` (percentage points) — absolute regression from peak.
   - `epochs_below_peak_after_peak / (num_epochs - peak_ep + 1)` — fraction of post-peak epochs that were strictly worse than peak.
3. **Apply the diagnosis criteria — all three must hold:**
   - `loss_drop_after_peak / loss_at_peak > 0.10` (loss kept meaningfully dropping)
   - `peak_acc - final_acc > 0.3 pp` (real regression, not noise)
   - `epochs_below_peak_after_peak / post_peak_epochs > 0.5` (majority of post-peak epochs are below peak — monotonic, not jitter)

   If all three hold, the diagnosis is **late-stage cross-entropy overfitting**.
4. **Verify the fingerprint matches** (rules out other causes):
   - Training loss is small (well under 1.0 for cross-entropy) and falling **smoothly**, not oscillating → not LR-too-high.
   - Per-batch loss within a single epoch is essentially flat → model has converged on the training distribution.
   - Test accuracy regression is **slow and monotonic**, not a collapse → not a bug or data corruption.
   - If train accuracy is logged, it pins at 95–100% while test stays at its peak.
5. **Explain the mechanism to the user.** Cross-entropy loss is `−log p_correct`. Once an example is classified correctly at 80% probability, gradient descent still pushes that probability toward 99%. Each push:
   - Decreases `−log p_correct` substantially (loss drops noticeably).
   - Doesn't change `argmax(predictions)` (train accuracy unchanged).
   - On the test set, the same *overconfidence* transfers to incorrectly-classified ambiguous examples, slightly degrading test accuracy.
6. **Recommend remediation (hypotheses — re-run to confirm):**
   - **(a) Earlier checkpoint.** If checkpoints were saved every K epochs, restore the one closest to `first99`. That's typically the best generalization point.
   - **(b) Add early stopping.** Carve a val split out of train (e.g., 10%), monitor val accuracy each epoch, stop when it hasn't improved for N epochs (patience=10–20 is reasonable).
   - **(c) Re-run with regularization.** Add weight decay (1e-4 is a common default), dropout, or label smoothing. Stack with early stopping — regularization alone won't fix the lack of a val split, it just slows the overshoot.
7. **Rule out grokking explicitly** if the user hoped for it. Grokking requires AdamW with weight_decay ≈ 1.0, a tiny dataset (e.g., modular arithmetic), train loss reaching ~0, and 10×–100× the memorization-time of epochs. It manifests as a **sudden test-accuracy jump** after a long plateau, not a slow regression. None of those apply in standard supervised vision; saying "this is grokking" to such a user is wrong.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Diagnose as grokking | User named the log `grok_lenet.log`; first instinct was to read the loss-down-accuracy-flat shape as a pre-grokking memorization phase. | Grokking requires AdamW + weight_decay ≈ 1.0 + tiny dataset + train loss reaching ~0, and it manifests as a sudden test-accuracy jump, not a slow regression. The fingerprint here is the *opposite* (overfitting, not delayed generalization). | Diagnose by fingerprint shape (smooth descent + monotonic regression), not by what the user hoped to see. |
| Recommend "just add weight decay" | Suggested adding `weight_decay=1e-4` to the existing LeNet setup as the one-line fix. | Doesn't address the root issue: there's no val split to early-stop on, so the model will still overshoot — just more slowly. Regularization is additive, not foundational. | Early stopping on a held-out val split is the foundational fix. Weight decay / dropout / label smoothing stack on top, they don't replace it. |
| Trust the final-epoch checkpoint | Assumed the saved `lenet5_weights/` from epoch 500 was the model to use. | Peak test accuracy was at epoch 246 (86.72 %); the saved final-epoch checkpoint is 85.91 %. Without periodic checkpoints, the best weights were already gone — irrecoverable without re-running. | Always checkpoint every K epochs (or every epoch) in long runs, not just at the end. Even better: also save a `best_val_acc.pt` checkpoint updated whenever val accuracy improves. |

## Results & Parameters

### Verified detection run

**Setup:** LeNet-5 on EMNIST Balanced (47 classes, 112,800 train / 18,800 test), batch_size=32,
lr=0.001, optimizer=SGD with no weight decay, fp32, 500 epochs, no val split, only final-epoch
checkpoint saved.

**Per-epoch milestones extracted by the Quick Reference script:**

| Milestone | Epoch | Avg train loss | Test accuracy |
|---|---|---|---|
| Start | 1 | 3.0867 | 46.70 % |
| 95 % of peak acc | 22 | 0.4929 | 82.53 % |
| 99 % of peak acc | 89 | 0.3408 | 85.86 % |
| Peak test acc | 246 | 0.2562 | 86.7181 % |
| End of run | 500 | 0.1891 | 85.9149 % |

**Computed diagnostic ratios:**

| Ratio | Value | Threshold | Triggered? |
|---|---|---|---|
| `loss_drop_after_peak / loss_at_peak` | (0.2562 − 0.1891) / 0.2562 = 0.262 | > 0.10 | yes |
| `peak_acc − final_acc` | 86.7181 − 85.9149 = 0.803 pp | > 0.3 pp | yes |
| `epochs_below_peak / post_peak_epochs` | 251 / 254 = 0.988 | > 0.5 | yes |

All three criteria triggered → diagnosis: late-stage cross-entropy overfitting.

**Per-batch flatness at epoch 500:** batch losses were ~0.188 with no downward trend within
the epoch, confirming the model had converged on the training distribution and was no
longer learning anything new per-pass.

### Recommended re-run parameters (unverified hypothesis)

```text
optimizer        = SGD (unchanged) or AdamW
lr               = 0.001 (unchanged)
weight_decay     = 1e-4
val_split        = 10% of train (stratified)
early_stopping   = patience=15 epochs on val_acc
checkpoint_every = 5 epochs  AND  best_val_acc.pt updated on each improvement
max_epochs       = 150  # peak was at 246 without regularization; with wd expect earlier
```

Expected — but **not confirmed by re-running** — that this recovers ≥ peak accuracy (86.72 %)
with the saved `best_val_acc.pt` and avoids the slow regression.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | LeNet-5 / EMNIST Balanced 500-epoch run, log file `grok_lenet.log`, detection recipe run against the log via Python regex extractor. | Detection numbers in the table above are from the actual log; remediation is hypothesis only. |
