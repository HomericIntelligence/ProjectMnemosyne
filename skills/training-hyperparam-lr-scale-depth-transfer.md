---
name: training-hyperparam-lr-scale-depth-transfer
description: "Use when: (1) you tuned learning-rate scales at one model geometry (e.g. 2L MLP) and are about to reuse them on a deeper/wider model (e.g. 8-layer CNN) without re-screening, (2) a sweep that worked at one depth suddenly diverges (top-1 ≈ 1/n_classes, train CE close to ln(n_classes)) at a deeper/wider target, (3) you see `clip_fires` correlate with `--use-adam` and want to know whether to attribute them to Adam or to an under-scaled LR, (4) you are about to design a `larger-model` follow-up to an already-completed `smaller-model` sweep and want a checklist before starting."
category: training
date: 2026-07-22
version: "1.0.0"
user-invocable: false
tags:
  - hyperparameter
  - lr-scale
  - lr-screen
  - model-depth
  - model-width
  - scale-transfer
  - divergence-diagnosis
  - alexnet
  - sweep-design
  - short-horizon-screen
---

# Training: LR-Scale Does Not Transfer Across Model Depth

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-22 |
| **Category** | training |
| **Objective** | Codify the rule that per-(rule, optimizer) LR-scales tuned at one model geometry generally **do not** transfer to a substantially deeper and/or wider geometry — and the cheap mitigation (a short-horizon target-scale screen before full-epoch tuning). |
| **Outcome** | Operational — empirical falsification of the carry-over assumption on AlexNet-CIFAR with full evidence collected and a reproducible harness committed. |
| **Verification** | verified-exercise |
| **Applies to** | Any fixed-`base_LR × lr_scale` runner where the base LR was set for one geometry and the scale was tuned for a shallower/narrower geometry. |

This entry generalizes a finding first observed on a PC-vs-BP optimizer bake-off at
8-layer AlexNet/CIFAR-10, where the LR-scales were inherited from a 2L MLP sweep and the
very first full-epoch cell collapsed to chance. The mitigation — a 5-batch target-scale
screen — is presented as a reusable harness pattern.

## When to Use

Use this skill when any of these apply:

1. You have a fixed `learning_rate = BASE × lr_scale` formula, the BASE was set for one
   model geometry, and you are about to apply a new `lr_scale` that was tuned for a
   geometry that differs from the current target in either **depth** or **width** by
   more than ~1.5×.
2. A sweep that converged at scale *s* on a smaller model diverges or collapses to
   chance (top-1 ≈ 1/n_classes; train CE ≈ ln(n_classes); `clip_fires` saturating) on
   a deeper/wider model at the same `lr_scale`.
3. You are about to claim an *Adam-fix* story (e.g. "Adam diverges, so clip it") and
   the only evidence is `clip_fires` correlation on the target geometry.
4. You are designing a sweep that will burn ≥30 minutes per cell on a target
   architecture and the cost of a single wrong-scale bad result is comparable to the
   cost of a screen.

**Do not** use this entry to claim that LR-scales *never* transfer across depths —
some optimizers *do* transfer within a small enough depth-ratio. Use it to require
*evidence at the target scale* before trusting carry-over.

## Verified Workflow

### Quick Reference

| Fact | Value |
| ---- | ----- |
| **Rule** | LR-scales tuned at one model geometry generally do **not** transfer to a substantially deeper/wider geometry. |
| **Test signal** | Short-horizon train CE at fixed batch count on the target architecture. |
| **Screen budget** | `--max-batches N` per cell, N small (≈5 works on CNNs); duration per cell is sub-minute. |
| **Selection rule** | Within `(rule, optimizer)`: pick smallest `lr_scale` whose finite CE at N batches is meaningfully below `ln(n_classes)`; tie-break on smaller scale. |
| **Compatibility** | Compatible with any unified dispatch CLI: `--optimizer <name> --opt-arg k=v --lr-scale X --max-batches N`. |
| **PC / BP parity** | Both arms run the same screen — the runner's PC invariant (ΔW from PC, post-processed by named optimizer) is preserved per cell. |

### Step 1: Detect a carry-over risk before scheduling the sweep

Answer YES to any of these → you need a screen:

- [ ] Source geometry has ≤2 layers; target geometry has ≥5 layers.
- [ ] Source `hidden_dim` (or filter base) divides target by ≥2.
- [ ] Source `lr_scale` choice was made by *min-CE*, not by *stable-not-diverged* — i.e. you
      never explicitly screened for "smallest scale that didn't diverge."
- [ ] The runner uses a *single fixed `BASE_LR`* per layer family and applies `lr_scale`
      multiplicatively to it.

### Step 2: Instantiate a short-horizon screen harness

The harness is identically reusable for any (rule × optimizer × lr_scale) cell
combination. Empirically validated shape (from
`scripts/gen_alexnet_lr_screen_specs.py`):

```python
# Emitted cells: rule ∈ {pc, bp} × optimizer ∈ 17 × lr_scale ∈ 6
# Total cells: rule_count * opt_count * scale_count
# Per cell: --optimizer <name> --opt-arg k=v --lr-scale <s> --max-batches 5
# Screen ladder: descending from the divergence ceiling, e.g. (1.0, 0.25, 0.063, 0.016, 0.004, 0.001)
```

The descending ladder matters. **Start at the scale that just worked on the source
geometry, then go *down* by ~4× per step.** Going *up* burns the same budget but fails
informatively less often.

### Step 3: Run the screen, capture one JSON record per cell

Each cell must record at least:

- `label`, `rule`, `optimizer`, `lr_scale`
- `final_avg_train_ce` (or analogous N-batch CE)
- `grad_clip_fires` (PC arm — BP arm has none)
- `final_test_top1` (informational; not the selection signal)
- `wall_s` (budget guard)

The signal is **`final_avg_train_ce`** at the fixed batch count, *not* test accuracy.
Stable training pushes CE down in 5 batches; failed scales leave it at or above
`ln(n_classes)`.

### Step 4: Pick the winner per `(rule, optimizer)`

For each `(rule, optimizer)`:

1. Drop cells with non-finite CE (crashed / NaN).
2. Drop cells whose CE is **not meaningfully below `ln(n_classes)`** — a 5-batch
   stable run will be visibly below the chance floor.
3. From the survivors, pick the **lowest CE**; tie-break on the **smaller scale**
   (more safety margin if the screen is shorter than a real epoch).
4. If no cell survives, fall back to the smallest finite-CE cell and **flag it**
   `[unstable]` — never silently drop the optimizer.

### Step 5: Emit only the winners to the full-epoch sweep spec

The collector must emit one spec line per `(rule, optimizer)` winner. The full-epoch
sweep then runs only the cells that the screen selected, not the full grid. This
typically cuts a 200+ cell grid down to 30–50 cells.

### Compatibility with the unified CLI dispatch surface

The screen works with any runner that accepts:

```
--optimizer <name>            # e.g. adam, sgd, adopt, sophia, adan, muon-hyperball, ...
--opt-arg k=v                 # e.g. lr=0.001 (LR-gated optimizers)
--lr-scale <float>            # multiplier on the runner's per-layer BASE_LR
--max-batches <int>           # bounded horizon for the screen
```

See [`odyssey-functional-optimizer-step-api`](./odyssey-functional-optimizer-step-api.md)
for the per-optimizer state-arity contract that the dispatch must honor.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Carry a 2-layer MLP-tuned `lr_scale` value directly onto an 8-layer AlexNet | First cell collapsed to chance (top-1 0.10, train CE 2.398 ≈ ln(10)) | Source-geometry optimality does not imply target-geometry optimality; depth and width both shift the loss landscape |
| 2 | Interpret `clip_fires` correlation with `--use-adam` on AlexNet as the *cause* | The correlation saturated at the same LR that diverged for adan/sgd/muon at the same source-geometry scale; rescreening at LR ~1/100× dropped `clip_fires` drastically *without* touching the optimizer | `clip_fires` are a *symptom* of too-large LR, not a property of the optimizer; always rescreen the LR before diagnosing the optimizer |
| 3 | Run a full 73-minute epoch at AlexNet scale to check every `(rule, opt, lr_scale)` cell | Would have burned ≈74 CPU-hours on a 68-cell grid where most cells diverged; only the *first* cell produced a useful signal | A 5-batch screen costs sub-minute per cell; use it as the *first* gate, not the *last* |
| 4 | Pick LR-screen winners by *highest test top-1 at the screen horizon* | Test top-1 at N=5 batches on CIFAR-10 is uninformative (~0.10–0.20 for any stable LR) | The screen signal is train CE at the fixed horizon, not test top-1 — test top-1 only becomes a meaningful signal after roughly one full epoch |
| 5 | Drop the `lr_scale=1.0` cell from the screen because "we know it diverged" | Buyers of the screen came in cold; silently removing ceilings hides which scales are *stable* vs *unstable* | Always include the source-geometry-best scale in the screen — *seeing it fail* is the verification evidence |
| 6 | Try to pick a single global `lr_scale` that works for *all* optimizers | Different optimizers have different effective-LR sensitivity at depth (Muon-Normalized vs Adam vs raw SGD scale differently) | Pick per-(rule, optimizer); a single global scale is a re-introduction of the bug |

## Results & Parameters

| Field | Value |
| ----- | ----- |
| **Carry-over heuristic** | Refuse LR-scale carry-over when `(target_depth / source_depth) ≥ 1.5` OR `(target_width / source_width) ≥ 1.5`. |
| **Screen ladder** | `[1.0, 0.25, 0.063, 0.016, 0.004, 0.001]` (each step ÷4) — covers ~3 orders of magnitude below the source-best. |
| **Screen horizon** | `--max-batches 5` is the validated default for CNNs at CIFAR-scale; reduce to 3 for very large models, raise to 10 only if 5-batch CE is visibly noisy. |
| **Screen signal** | `final_avg_train_ce` (lower is better); floor = `ln(n_classes)`. |
| **Collector flag** | If no cell beats the `ln(n_classes)` floor, emit winner `[unstable]`; never silently drop. |
| **Cost saved per grid** | At the recorded worker's concurrency and per-cell wall time, a `200+`-cell 5-batch screen costs on the order of hours; the equivalent `200+`-cell full-epoch grid at the target-architecture per-cell wall time would have produced mostly chance-level noise. See the per-project notes for the exact numbers. |
| **PC / BP parity** | Achieved — both arms route through the same `--optimizer/--opt-arg/--lr-scale` surface; PC arm remains local-only (PC-derived ΔW post-processed by the named optimizer), BP arm applies true backprop. |
| **Adam-clip reframing** | The original "Adam needs special treatment" hypothesis was *falsified* by grade-matched per-optimizer LR screening at the target scale — `clip_fires` are downward-biased outputs of LR screens at the target LR, not an Adam defect. |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| `<project-root>` (8-layer CNN, CIFAR-10 class-scale) | The PR cycle that stopped a 68-cell bake-off at its first diverged cell, then replaced it with a 204-cell 5-batch screen | See [`training-hyperparam-lr-scale-depth-transfer.notes.md`](./training-hyperparam-lr-scale-depth-transfer.notes.md). |

## Cross-references

- [`odyssey-functional-optimizer-step-api`](./odyssey-functional-optimizer-step-api.md) — the per-optimizer state-arity contract the screen + collector rely on.
- [`testing-dynamic-import-sys-path-resolution`](./testing-dynamic-import-sys-path-resolution.md) — the `pythonpath = scripts` plumbing that lets the collector be pytest-loaded without symlink surgery.
- [`architecture-import-time-assert-anti-pattern`](./architecture-import-time-assert-anti-pattern.md) — the validation discipline the screen options registry follows.
