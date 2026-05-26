---
name: training-multi-metric-best-checkpoint-min-after-max
description: "Capture *transitions* (regime changes) in long-running training runs, not just absolute extrema, by tracking multiple metrics with per-metric modes (max / min / both / min_after_max / max_after_min). Use when: (1) designing checkpointing for a grokking or phase-transition study where the interesting test loss is the one *after* it has spiked and come back down, (2) the naive `if test_loss < best_test_loss` tracker is trivially won at epoch 1 because loss starts highest and falls monotonically, (3) you want to diagnose overfitting valleys / spikes / weight-norm regrowth and the absolute min/max is uninformative, (4) you want one checkpoint per (metric, mode_kind) tuple with weights + JSON sidecar, (5) extending an existing single-metric CheckpointManager to N metrics without changing on-disk format, (6) detecting change-of-regime in any time-series metric pipeline (LR scheduling, overfitting detection, anomaly detection over training metrics)."
category: training
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - checkpointing
  - grokking
  - phase-transition
  - training-dynamics
  - regime-change
  - min-after-max
  - max-after-min
  - multi-metric
  - overfitting-detection
  - transition-tracking
---

# Multi-Metric Best Checkpoints with `min_after_max` Transition Tracking

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Capture diagnostically useful "best" checkpoints in long training runs where the *interesting* extremum is not the absolute one but the extremum that occurs *after a regime change*. Generalize beyond a single tracked metric. |
| **Outcome** | One CheckpointManager per (metric, mode_kind) tuple. Five mode kinds total: `max`, `min`, `min_after_max`, `max_after_min`, with `both` = {`max`, `min`, `min_after_max`, `max_after_min`}. Selected via single comma-separated CLI flag `--track-metric NAME:MODE,...`. |
| **Verification** | verified-ci - ProjectOdyssey PR #5453 (grokking-experiment scaffold for `examples/grok/lenet_emnist/`) ran a dry-run end-to-end and produced 7 checkpoint subdirectories (`test_acc_best/`, `test_loss_best/`, `test_loss_min/`, `test_loss_min_after_max/`, `test_loss_max_after_min/`, `train_loss_best/`, `weight_l2_norm_best/`) plus `final/`, each containing weights and a `meta.json` sidecar. Pre-commit clean. |

## When to Use

Use this pattern when designing or extending checkpointing for any of the following:

1. **Grokking / delayed generalization studies.** Phase 2 of grokking is a test loss *spike*; Phase 3 is collapse to low loss. The valuable checkpoint is the post-spike minimum, not the trivial epoch-1 minimum.
2. **Overfitting / double-descent diagnosis.** You want the test accuracy that *recovers* after a valley, or the weight L2 norm that *regrows* after decay finishes.
3. **Anomaly detection in training time-series.** Anywhere "did this metric change regime?" matters more than "what was the absolute extremum across all of training?"
4. **Replacing a naive `if metric < best: save()` tracker** that is trivially won at epoch 1 (loss starts high and falls monotonically) and therefore captures nothing useful for late-training dynamics.
5. **Extending an existing single-metric `CheckpointManager`** to N metrics without inventing a new on-disk format.

Do NOT use this pattern if:

- You only need the single absolute best checkpoint and the metric is genuinely monotonic-trend-then-reverse (then `max` or `min` alone is fine).
- Your training run is short enough (< ~50 epochs) that no regime change can plausibly occur.
- You need a heavy time-series-database-backed metric pipeline; this skill is a lightweight CLI-driven pattern that overwrites one file per (metric, mode_kind).

## Verified Workflow

### Quick Reference

```text
CLI flag (single, comma-separated; parser doesn't accept repeated list args):
  --track-metric test_acc:max,test_loss:both,train_loss:min,weight_l2_norm:max

Effective on-disk layout under ${ckpt_dir}/:
  test_acc_best/                weights + meta.json
  test_loss_best/               weights + meta.json   (max-of-loss; rare, but symmetric)
  test_loss_min/                weights + meta.json
  test_loss_min_after_max/      weights + meta.json   <-- grokking-relevant
  test_loss_max_after_min/      weights + meta.json
  train_loss_best/              weights + meta.json
  weight_l2_norm_best/          weights + meta.json
  final/                        weights + meta.json   (always)

meta.json sidecar:
  {"metric": "test_loss", "mode_kind": "min_after_max", "value": 0.0421, "epoch": 173}
```

### Five Mode Kinds

| Mode kind | Trigger | Files saved (per metric `N`) | Diagnostic purpose |
| --- | --- | --- | --- |
| `max` | new highest value | `N_best/` | Headline best (e.g. test accuracy) |
| `min` | new lowest value | `N_best/` | Trivially won at epoch 1 for monotonically-decreasing losses; only useful if metric is bounded-below and you genuinely want the absolute floor |
| `min_after_max` | new minimum, **gated** on `has_seen_max` | `N_min_after_max/` | THE key innovation. Captures the loss collapse *after* a peak. Without the gate, "min loss" is trivially epoch 1 |
| `max_after_min` | new maximum, **gated** on `has_seen_min` | `N_max_after_min/` | Symmetric. Captures weight-norm regrowth, test-accuracy recovery from a valley, etc. |
| `both` | shorthand for all four kinds | `N_best/`, `N_min/`, `N_min_after_max/`, `N_max_after_min/` | One-flag way to "tell me everything interesting about this metric" |

### Implementation Recipe

1. **Parse the CLI flag.** Single string, comma-separated `NAME:MODE` pairs. Split on `,` then on `:`. Validate `MODE in {max, min, both, min_after_max, max_after_min}`. Do NOT try to make the arg parser accept repeated `--track-metric` flags - the project's `create_training_parser()` does not support list-typed args and ~30 min was wasted attempting that in this skill's source session.
2. **Expand `both` -> four kinds** during parsing so downstream code only deals with `{max, min, min_after_max, max_after_min}`.
3. **One CheckpointManager per (metric, mode_kind) tuple.** Wrap the existing single-metric `CheckpointManager` N times. No new on-disk format, no new shared code.
4. **Maintain two booleans per metric**: `has_seen_max`, `has_seen_min`. Update them *before* evaluating the `min_after_max` / `max_after_min` triggers each epoch.
5. **Overwrite-when-better policy.** Each (metric, mode_kind) keeps exactly 1 checkpoint on disk; the file is overwritten when a strictly-better value is observed.
6. **Sidecar `meta.json`** with `{metric, mode_kind, value, epoch}` for downstream tooling and to make checkpoints self-describing.
7. **Inline the wrapper in the example's `train.mojo` first.** Only extract to the shared library if a second caller appears (YAGNI).

### Defaults that proved useful

For a grokking experiment on LeNet/EMNIST (PR #5453):

```text
--track-metric "test_acc:max,test_loss:both,train_loss:min,weight_l2_norm:max"
#                ^ headline   ^ all four    ^ sanity        ^ Omnigrok regrowth
#                  best        kinds for      that train-     signal
#                  ever        test_loss      loss converges
```

The `test_loss:both` is what makes the run diagnostically rich: `test_loss_min_after_max/` is the actual "grokked" checkpoint, while `test_loss_best/` (max-of-loss) is mostly a sanity-check artifact.

### Verification artifact (PR #5453 dry-run output)

After a dry-run, the checkpoint directory contained exactly:

```text
test_acc_best/                weights + meta.json
test_loss_best/               weights + meta.json
test_loss_min/                weights + meta.json
test_loss_min_after_max/      weights + meta.json
test_loss_max_after_min/      weights + meta.json
train_loss_best/              weights + meta.json
weight_l2_norm_best/          weights + meta.json
final/                        weights + meta.json
```

7 mode-driven subdirectories + `final/`, each with weights and a `meta.json` sidecar matching the schema above. Pre-commit clean.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Naive "best test loss" tracker | Save checkpoint whenever `test_loss < best_test_loss` | Trivially "best" at epoch 1: loss starts highest and falls monotonically across early epochs. The useful signal - late-training loss spike followed by recovery - is invisible because no later value beats the early one | Need state about whether a *regime change* has happened (`has_seen_max`), not just the absolute extremum. This is the entire motivation for `min_after_max` |
| Repeated `--track-metric` CLI flags | Tried to make `create_training_parser()` accept `--track-metric` multiple times (list-typed arg) | Project's arg parser doesn't support list-typed flags; modifying it cascaded into unrelated parser changes. Burned ~30 min | Use a single comma-separated string and split internally. Don't reshape the parser just to make CLI ergonomics nicer |
| Invent a new on-disk checkpoint format for multi-metric | Considered a single multi-slot checkpoint file indexed by (metric, mode_kind) | Pure overhead - no existing tool reads it, breaks the existing `CheckpointManager` contract, no benefit over N independent dirs | Wrap the existing single-metric CheckpointManager N times. Reuse beats reinvention |
| Track `min_after_max` without the `has_seen_max` gate | Just save whenever `test_loss < best_min_after_max_loss` | Identical to naive tracker - epoch 1 always wins | The boolean gate is load-bearing, not decorative. It must be updated *before* the trigger check each epoch |

## Results & Parameters

**Verification status**: `verified-ci`. ProjectOdyssey PR #5453 ran a dry-run end-to-end and produced the 8-directory checkpoint layout shown in "Verification artifact" above. Pre-commit clean.

**Parameters used in the verifying run**:

| Parameter | Value |
| --- | --- |
| Example | `examples/grok/lenet_emnist/` (ProjectOdyssey) |
| CLI flag | `--track-metric "test_acc:max,test_loss:both,train_loss:min,weight_l2_norm:max"` |
| Mode kinds emitted | `max`, `min`, `min_after_max`, `max_after_min` (via `both`) |
| Checkpoints per (metric, mode_kind) | 1 (overwrite-when-better) |
| Sidecar | `meta.json` with `{metric, mode_kind, value, epoch}` |
| Extra always-saved | `final/` |
| Total directories after run | 8 (7 mode-driven + `final/`) |

**Generality**: The pattern applies to any time-series metric pipeline where transitions matter more than absolute extrema - LR scheduling, overfitting detection, training-dynamics research, anomaly detection. Not specific to grokking or to Mojo.

**Future work** (do NOT do these speculatively; only if a second caller appears):

- Extract the multi-CheckpointManager wrapper into a shared library helper.
- Add a `--track-metric` form that accepts a JSON config file for very large metric sets.
- Add `min_after_max_n` / `max_after_min_n` variants gated on N peaks/troughs rather than 1, for runs with multiple regime changes.
