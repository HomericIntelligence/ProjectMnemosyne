---
name: odyssey-functional-optimizer-step-api
description: "Use when: (1) calling any Odyssey exotic optimizer (ADOPT, Sophia, Adan, Muon-Hyperball, LionMuon, MGUP-Muon, SOAP, FTRL) from Mojo, (2) wiring a runtime --optimizer dispatch over several optimizers into a training loop, (3) resolving the import path for an optimizer (it is odyssey.training.optimizers.X, NOT odyssey.optimizers.X), (4) sizing per-parameter state buffers for one of these optimizers, (5) debugging wrong-arity or wrong tuple-unpack errors from a <name>_step call."
category: optimization
date: 2026-07-22
version: "1.1.0"
user-invocable: false
tags:
  - mojo
  - odyssey
  - optimizer
  - functional-api
  - adopt
  - sophia
  - adan
  - muon
  - lionmuon
  - soap
  - ftrl
  - anytensor
  - state-arity
  - optimizer-dispatch
  - cli-dispatch
  - kwargs-routing
---

# Odyssey Functional Optimizer-Step API (Mojo)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-17 |
| **Category** | optimization |
| **Language** | Mojo v1.0.0b2 |
| **Objective** | Canonical reference for calling any of Odyssey's exotic optimizers from Mojo: the shared pure-functional `<name>_step(...)` contract, the correct import root, and a per-optimizer state-arity table so a caller can size state buffers and unpack the return tuple without a compile error. |
| **Outcome** | Operational — signatures/paths/arities confirmed by direct source inspection at the pinned SHA. |
| **Verification** | verified-exercise |
| **Source dir** | `src/odyssey/training/optimizers/` at Odyssey SHA `00080fd85ab85fa90d6ba31917fda2ea85bb7513` |

This generalizes [`optimizer-shampoo-matrix-form-api`](./optimizer-shampoo-matrix-form-api.md)
(single-optimizer) to the whole exotic-optimizer family and pins the cross-cutting contract they
all share. If you are working with Shampoo specifically, read that entry too — it carries the
Newton-Schulz / eligibility detail this entry does not.

## When to Use

Use this skill when working with any Odyssey optimizer beyond plain SGD/Adam and any of these apply:

1. Calling ADOPT, Sophia, Adan, Muon-Hyperball, LionMuon, MGUP-Muon, SOAP, or FTRL from Mojo.
2. Building a runtime `--optimizer <name>` dispatch that routes one training step to any of them.
3. Resolving the import path (the directory is under `training/`, not at the package root).
4. Deciding how many per-parameter state buffers to allocate and in what order to pass them.
5. Fixing a "wrong number of return values" / wrong tuple-index compile error from a step call.

Do NOT rely on this for exact update math — read the source module's docstring for the algorithm.
This entry pins the **calling contract** (path, signature shape, state arity), not the numerics.

## Verified Workflow

### Quick Reference

| Fact | Value |
| ---- | ----- |
| **Import root** | `odyssey.training.optimizers.<name>` — **NOT** `odyssey.optimizers.<name>` |
| **Function form** | pure free-function `def <name>_step(...)` + a defaulted `def <name>_step_simple(...)` |
| **State ownership** | caller owns ALL state; nothing is stored on a struct — every buffer is passed in and a new one returned |
| **Return** | `Tuple[new_params, ...new_state]` — same order as the state args in the signature |
| **`_simple` variant** | same params/state args, hyperparameters dropped to their defaults (fewer keyword args to pass) |
| **Param/grad dtype** | `AnyTensor`; scalars are `Float64`; step counters are `Int` |

```mojo
# CORRECT import (note the `.training.` segment)
from odyssey.training.optimizers.adopt import adopt_step, adopt_step_simple
from odyssey.training.optimizers.soap import soap_step
# WRONG — this path does not exist:
# from odyssey.optimizers.adopt import adopt_step
```

### Per-optimizer state-arity table

`state buffers` = AnyTensor buffers the caller must allocate (zeros/`full_like`) and thread across
steps. `extra` = non-tensor per-step args beyond `(params, grads, ..., learning_rate)`. `returns` =
tuple arity = `1 (params) + N state buffers`.

| Optimizer | `<name>_step` state args (in order) | state buffers | extra step args | returns (arity) |
| --------- | ----------------------------------- | :-----------: | --------------- | :-------------: |
| **ADOPT** | `momentum, second_moment` | 2 | — | 3 |
| **Sophia** | `momentum, hessian_moment` | 2 | (Hessian estimate maintained externally by caller) | 2 |
| **Adan** | `exp_avg, exp_avg_diff, exp_avg_sq, prev_grad` | 4 | `step: Int` | 5 |
| **Muon-Hyperball** | `momentum` | 1 | — | 2 |
| **LionMuon** | `lion_momentum, muon_momentum` | 2 | `step_index: Int` | 3 |
| **MGUP-Muon** | `momentum` | 1 | — | 2 |
| **SOAP** | `exp_avg, exp_avg_sq, gg_left, gg_right, q_left, q_right` | 6 | `step: Int` (rank-2 params only) | 7 |
| **FTRL** | `z, n` | 2 | — | 3 |

Note Sophia returns a **2-tuple** `(new_params, new_momentum)` even though it takes a
`hessian_moment` in — the Hessian buffer is caller-maintained across steps and passed through, not
re-emitted by the step. Adan and SOAP take a 1-indexed `step: Int` that the caller increments
**before** the call.

### Exact signatures (source-verified at SHA 00080fd8)

```mojo
adopt_step(params, gradients, momentum, second_moment, learning_rate,
           beta1=0.9, beta2=0.9999, epsilon=1e-6, clip_value=1.0e30, weight_decay=0.0)
    -> Tuple[AnyTensor, AnyTensor, AnyTensor]                           # params, momentum, second_moment

sophia_step(params, gradients, momentum, hessian_moment, learning_rate,
            beta1=0.96, gamma=1.0, rho=0.04, epsilon=1e-12, weight_decay=0.0)
    -> Tuple[AnyTensor, AnyTensor]                                      # params, momentum

adan_step(params, gradients, exp_avg, exp_avg_diff, exp_avg_sq, prev_grad, step, learning_rate,
          beta1=0.98, beta2=0.92, beta3=0.99, epsilon=1e-8, weight_decay=0.0)
    -> Tuple[AnyTensor, AnyTensor, AnyTensor, AnyTensor, AnyTensor]     # params, exp_avg, exp_avg_diff, exp_avg_sq, prev_grad

muon_hyperball_step(params, gradients, momentum, learning_rate,
          weight_norm_max=1.0, update_norm_max=0.1, momentum_beta=0.95, weight_decay=0.01,
          ns_steps=5, nesterov=True)
    -> Tuple[AnyTensor, AnyTensor]                                      # params, momentum

lionmuon_step(params, gradients, lion_momentum, muon_momentum, learning_rate, step_index,
          period=4, lion_beta1=0.9, lion_beta2=0.99, muon_beta=0.95, weight_decay=0.0,
          ns_steps=5, nesterov=True)
    -> Tuple[AnyTensor, AnyTensor, AnyTensor]                           # params, lion_momentum, muon_momentum

mgup_muon_step(params, gradients, momentum, learning_rate,
          selected_fraction=0.25, select_scale=2.0, momentum_beta=0.95, weight_decay=0.01,
          ns_steps=5, nesterov=True)
    -> Tuple[AnyTensor, AnyTensor]                                      # params, momentum

soap_step(params, gradients, exp_avg, exp_avg_sq, gg_left, gg_right, q_left, q_right, step, learning_rate,
          beta1=0.95, beta2=0.95, shampoo_beta=0.95, weight_decay=0.01,
          precondition_frequency=10, epsilon=1e-8, correct_bias=True)
    -> Tuple[AnyTensor, AnyTensor, AnyTensor, AnyTensor, AnyTensor, AnyTensor, AnyTensor]
       # params, exp_avg, exp_avg_sq, gg_left, gg_right, q_left, q_right  (rank-2 params only)

ftrl_step(params, gradients, z, n, learning_rate,
          alpha=0.1, beta=1.0, lambda1=0.0, lambda2=0.0)
    -> Tuple[AnyTensor, AnyTensor, AnyTensor]                           # params, z, n
```

Every optimizer also exposes a `<name>_step_simple(params, gradients, <state...>, learning_rate[, step/step_index])`
that takes only the state args + LR (+ the Int step counter where the full signature has one) and
uses default hyperparameters — use it when you don't need to tune betas/decay.

### Dispatch pattern (runtime `--optimizer <name>`)

Because arities differ, a single dispatch cannot store one uniform state buffer. Allocate the max
state set per parameter (or a per-optimizer state struct) and branch on the optimizer name, unpacking
exactly the returned arity for that branch:

```mojo
if opt == "adopt":
    var r = adopt_step(w, g, m, v, lr)
    w = r[0]; m = r[1]; v = r[2]
elif opt == "soap":
    var r = soap_step(w, g, m, v, ggl, ggr, ql, qr, step, lr)
    w = r[0]; m = r[1]; v = r[2]; ggl = r[3]; ggr = r[4]; ql = r[5]; qr = r[6]
# ... one branch per optimizer, unpacking its exact arity from the table above
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | `from odyssey.optimizers.adopt import adopt_step` | The optimizers package lives under `training/`, not at the package root | Import root is `odyssey.training.optimizers.<name>` |
| 2 | `grep '^fn <name>_step'` to find signatures | These are `def` functions, not `fn` — a `^fn` grep returns nothing | Grep for `def <name>_step` (Odyssey optimizers use `def`, and top-level, not indented) |
| 3 | Unpacking Sophia's return as a 3-tuple by analogy with ADOPT | Sophia returns `(params, momentum)` — a 2-tuple; the caller-maintained `hessian_moment` is not re-emitted | Return arity ≠ input-state count for Sophia; use the per-optimizer table, don't assume symmetry |
| 4 | Assuming every optimizer takes only `(params, grads, state..., lr)` | Adan/LionMuon/SOAP additionally take a 1-indexed `step`/`step_index: Int` incremented before the call | Check the "extra step args" column before wiring the dispatch |
| 5 | Maintain one `--use-<name>` boolean flag per exotic optimizer (plus a parallel `--bp-use-<name>` to keep the PC/BP arms in lockstep) | 17 separate flags × 2 arms = 34 CLI surface entries to keep in sync with the dispatch surface; adding a new optimizer required patching the CLI parser, both switches, and the dispatch table in three places, and any drift caused silent dead-code paths on the runner | Collapse to `--optimizer <name> --opt-arg k=v`: one string flag identifies the optimizer; each `--opt-arg k=v` is forwarded to that optimizer's `<name>_step(...)` kwargs. The dispatch table in `unified_step.mojo::dispatch_step` is the single source of truth; `scripts/optimizers.py` (24-name SSoT) enforces the dispatch-key inventory |

## Unified CLI Surface (`--optimizer <name> --opt-arg k=v`)

The legacy per-optimizer boolean flags (`--use-adopt`, `--use-sophia`, `--use-adan`,
`--use-muon-hyperball`, `--use-lionmuon`, `--use-mgup-muon`, `--use-soap`, ...)
were replaced by **one** `--optimizer <name>` token plus any number of
`--opt-arg k=v` pairs. Every exotic optimizer and every baseline optimizer
(plain SGD, momentum, Adam, AdamW, RMSProp, LARS, ...) routes through this
same surface:

```bash
# Legacy (now removed): one boolean flag per optimizer × two arms
mojo run src/training/run_sweep_variant.mojo \
    --use-muon-hyperball --bp-use-muon-hyperball

# Unified surface: one flag, one arm-pair, kwargs as separate k=v pairs
mojo run src/training/run_sweep_variant.mojo \
    --optimizer muon-hyperball --opt-arg ns-steps=5 --opt-arg weight-norm-max=1.0
```

The runner strips `--opt-arg k=v` pairs and maps them to the dispatch table's
keyword arguments for that optimizer. Optimizers that require per-call
auxiliaries (Adam's gated LR, Adan's `step: Int`, FTRL's `alpha`/`beta`)
pass through `--opt-arg` cleanly without bespoke flags.

The PC arm always supplies the named optimizer above a PC-derived local `ΔW`;
the BP arm applies the same named optimizer to a true backprop gradient.
**The runner's PC invariant is preserved per cell:** PC never falls back to
backprop for the gradient direction — only the post-processing optimizer is
the named one. This invariant is the single most-load-bearing property
baked into the dispatch surface; deviation would silently collapse the
PC-vs-BP comparison into BP-vs-BP.

The unified surface is also what
[`training-hyperparam-lr-scale-depth-transfer`](./training-hyperparam-lr-scale-depth-transfer.md)
relies on for its `lr-scale` short-horizon screen — the screen runs every
`(rule, optimizer, lr_scale)` cell through the same `--optimizer --opt-arg`
entry point and only emits `--max-batches N` cells for the winners.

## Results & Parameters

- **Import root:** `odyssey.training.optimizers.<name>` for all of adopt / sophia / adan /
  muon_hyperball / lionmuon / mgup_muon / soap / ftrl (module basename == optimizer name).
- **Contract:** pure functional, caller-owns-all-state, `Tuple[new_params, ...new_state]` in the same
  order as the state args. `_simple` sibling for default-hyperparameter calls.
- **State arities:** ADOPT 2 · Sophia 2 (return 2) · Adan 4 (+step) · Muon-Hyperball 1 ·
  LionMuon 2 (+step_index) · MGUP-Muon 1 · SOAP 6 (+step, rank-2 only) · FTRL 2.
- **Verified against:** Odyssey SHA `00080fd85ab85fa90d6ba31917fda2ea85bb7513`, files
  `src/odyssey/training/optimizers/{adopt,sophia,adan,muon_hyperball,lionmuon,mgup_muon,soap,ftrl}.mojo`.
  At capture time (v1.0.0) the dispatch wiring was not yet CI-verified — hence
  `verified-local`. In v1.1.0 the unified CLI surface was exercised
  end-to-end against the 8-layer AlexNet/CIFAR-10 bake-off after a
  per-optimizer LR screen (see
  [`training-hyperparam-lr-scale-depth-transfer`](./training-hyperparam-lr-scale-depth-transfer.md)).
  Every exotic optimizer + every baseline optimizer listed in
  `scripts/optimizers.py` (the 24-name SSoT) was reached through
  `--optimizer <name>` against both PC and BP arms on the hermes box.
  Verification status bumped to `verified-exercise` for v1.1.0
  (state-arity + import-path verified-ci; CLI-surfacing verified-exercise).
