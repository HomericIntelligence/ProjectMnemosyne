---
name: training-smoke-mechanism-ci-gate
description: "Build a CI gate that proves each ML training ENTRYPOINT's training MECHANISM works — the arg parser wires, synthetic data flows through the model, the loss is computed and printed — WITHOUT downloading a dataset or checking convergence (per ADR-014). Two entrypoint flags (--smoke to build in-process synthetic tensors, --max-batches N to cap batches per epoch), an --epochs 1 gate invocation, a mechanism-not-convergence assertion (exit 0 + >=2 finite parseable loss lines, never monotonic decrease), and a per-model GitHub Actions matrix so N models compile+run in parallel instead of one serial job. Use when: (1) building a CI gate for ML training entrypoints, (2) a smoke run needs synthetic data instead of a dataset download, (3) a training gate times out because it ran all 200 epochs, (4) deciding mechanism-vs-convergence assertions, (5) parallelizing N model smoke-runs via a CI matrix. Concrete IMPLEMENTATION of a training-smoke gate; distinct from planning-unmerged-parent-contract-compile-smoke-gate (PLANNING such a gate) and tooling-dry-run-smoke-full-profile-dispatcher (a dry/smoke/full PROFILE dispatcher)."
category: ci-cd
date: 2026-07-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ml-training
  - smoke-test
  - ci-gate
  - synthetic-data
  - github-actions
  - matrix-job
  - fail-fast-false
  - max-batches
  - epochs-cap
  - mechanism-not-convergence
  - adr-014
  - training-entrypoint
  - loss-line-parsing
  - wall-clock-budget
  - avx-512-sigill
  - mojo-target-cpu
  - save-weights-guard
  - one-hot-labels
---

# Training Smoke Mechanism CI Gate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-11 |
| **Objective** | Build a CI gate that proves each ML training ENTRYPOINT's training MECHANISM works — arg parser wires, synthetic data flows through the model, loss is computed and printed — WITHOUT downloading a dataset or checking convergence (per ADR-014). |
| **Outcome** | Two entrypoint-level flags (`--smoke`, `--max-batches N`), an in-process synthetic-data pattern, an `--epochs 1` gate invocation, a mechanism-not-convergence assertion, and a per-model GitHub Actions matrix that compiles+runs N models in PARALLEL (wall-clock ≈ one model, not N×). |
| **Verification** | verified-local — the per-model recipe was run end-to-end in-container (resnet18: 5 finite loss lines, exit 0, gate reports OK). The matrix CI job YAML parses and mirrors a known-green sibling test job, but CI on the actual PR (#5583) was still running at capture time. So: matrix CI job authored + YAML-validated + one model verified in-container locally; full 8-model CI run pending. |
| **Category** | ci-cd |

## When to Use

- You are **building a CI gate for ML training entrypoints** and want to prove the training loop actually runs, not just that the binary compiles.
- A **smoke run needs synthetic data** — you must NOT download a real dataset (too slow/flaky for CI), so you build class-correlated tensors in-process.
- A **training gate times out** and you suspect it ran the full epoch loop (e.g. all 200 epochs) despite a batch cap.
- You are **deciding mechanism-vs-convergence assertions** — what a smoke gate should assert (exit code + finite loss lines) vs. what it must NOT (monotonic loss decrease).
- You need to **parallelize N model smoke-runs via a CI matrix** because running them serially in one job blows a wall-clock budget.

## Verified Workflow

### Quick Reference

```python
# 1. TWO ENTRYPOINT-LEVEL FLAGS wired into the arg parser + a TrainingArgs struct.
#    --smoke        : skip the real dataset, build synthetic tensors in-process.
#    --max-batches N: cap batches PER EPOCH (does NOT cap the epoch count — see #3).
parser.add_argument("--smoke", action="store_true")
parser.add_argument("--max-batches", type=int, default=0)   # 0 = no cap
parser.add_argument("--epochs", type=int, default=200)

# 2. SYNTHETIC DATA PATTERN — class-correlated so the loss is meaningful.
if smoke:
    wanted  = max_batches if max_batches > 0 else 3
    n_smoke = wanted * batch_size
    x = zeros([n_smoke, C, H, W])
    for s in range(n_smoke):
        cls = s % num_classes
        x[s] = fill_class_correlated(cls)          # e.g. bias the tensor by class
    # labels: raw uint8 class indices s % num_classes ...
    y = uint8([s % num_classes for s in range(n_smoke)])
    # ... EXCEPT models feeding cross_entropy directly may need one-hot float32:
    #   y = one_hot_f32([s % num_classes ...], num_classes)

# 3. --max-batches caps batches WITHIN one epoch only:
if max_batches > 0 and max_batches < num_batches:
    num_batches = max_batches

# 4. Widen the loss-print gate so tiny runs still emit lines:
if (batch_idx + 1) % 100 == 0 or num_batches <= 10:
    print(f"epoch {epoch} batch {batch_idx+1} loss {loss}")

# 5. Skip weight persistence under smoke (nothing to persist; sidesteps serializer bugs):
if not smoke:
    model.save_weights(path)
```

```bash
# GATE INVOCATION — --epochs 1 is REQUIRED. --max-batches alone does NOT cap the epoch loop.
<entrypoint> --smoke --max-batches 3 --epochs 1
# assert: exit 0 AND >=2 finite, parseable loss lines. NOT monotonic decrease.
```

```yaml
# PER-MODEL MATRIX so N models compile+run in PARALLEL (wall-clock ≈ one model, not N×).
training-smoke:
  needs: [compile-job]          # reuse the compiled artifacts
  strategy:
    fail-fast: false            # one model's failure must not cancel the others
    matrix:
      include:
        - { example: resnet18, entry: train }
        - { example: vgg16,    entry: train }
        # ... one row per model
  timeout-minutes: 10           # mirror the sibling test job's timeout
  steps:
    - uses: ./.github/actions/setup-container   # SAME action + pinned SHAs as sibling
      # strip AVX-512 target-features on masked GHA runners (libKGEN JIT SIGILL workaround):
      env: { MOJO_TARGET_CPU: <safe-cpu> }
    - run: just training-smoke-one ${{ matrix.example }} ${{ matrix.entry }}
```

### Detailed Steps

1. **Add two entrypoint-level flags.** `--smoke` (skip the real dataset, build synthetic
   tensors in-process) and `--max-batches N` (cap batches PER epoch). Wire BOTH into the arg
   parser AND the `TrainingArgs` struct the training loop reads from — a flag that parses but
   is never threaded into the loop does nothing.

2. **Build class-correlated synthetic data under `if smoke:`.** Compute
   `wanted = max_batches if max_batches > 0 else 3` and `n_smoke = wanted * batch_size`, then
   allocate `zeros([n_smoke, C, H, W])` and fill each sample so it is correlated with its class
   (`cls = s % num_classes`). Class-correlation makes the loss meaningful (a pure-zeros tensor
   gives a degenerate/constant loss). Labels are raw `uint8` class indices `s % num_classes` —
   EXCEPT models that feed `cross_entropy` directly, which may need one-hot `float32` train
   labels. Check the model's loss signature before choosing the label dtype/shape.

3. **Cap batches within the epoch** with
   `if max_batches > 0 and max_batches < num_batches: num_batches = max_batches`. This caps
   batches PER epoch — it does NOT touch the epoch count.

4. **Pass `--epochs 1` in the gate invocation — this is the single most important non-obvious
   gotcha.** Many models loop `for epoch in range(1, epochs+1)` with a default of up to 200.
   `--max-batches` only caps batches WITHIN an epoch, NOT the number of epochs. Omit `--epochs 1`
   and the gate runs the full 200-epoch loop and blows the timeout, even with `--max-batches 3`.

5. **Widen the loss-print gate for tiny runs.** A production loop that prints every 100 batches
   (`(batch_idx+1) % 100 == 0`) emits ZERO lines on a 3-batch smoke run, so the assertion (which
   needs >=2 loss lines) fails spuriously. Change it to
   `(batch_idx+1) % 100 == 0 or num_batches <= 10`.

6. **Guard weight persistence under `if not smoke:`.** There is nothing meaningful to persist
   from 3 tiny synthetic batches, and skipping `model.save_weights()` also sidesteps serializer
   bugs that would otherwise crash an otherwise-passing smoke run.

7. **Assert MECHANISM, not convergence (per ADR-014).** The gate asserts the entrypoint (a) exits
   0 and (b) emits **>=2 finite, parseable loss lines**. Do NOT assert monotonic decrease — loss
   on 3 tiny synthetic batches from random init is noisy and a decrease assertion is flaky. Parse
   each printed loss, confirm it is finite (not NaN/Inf), and count >=2.

8. **Use a per-model matrix job for wall-clock.** N models AOT-compiling serially in one job blows
   a "<5 min" target. Factor a per-model recipe `training-smoke-one <example> <entry>` and drive
   it from a GitHub Actions matrix with `fail-fast: false` and `needs: [compile-job]`, so each
   model compiles+runs in PARALLEL — wall-clock ≈ one model, not N×.

9. **Mirror the sibling test job exactly.** Use the SAME setup-container action, the SAME pinned
   action SHAs, and the SAME timeout as the known-green sibling test job. Divergence is how a new
   matrix job fails for environment reasons unrelated to the gate itself.

10. **Strip AVX-512 target-features on masked GHA runners.** The container invocation must pass a
    `MOJO_TARGET_CPU` var to disable AVX-512 codegen — a known libKGEN JIT SIGILL workaround on
    masked GHA runners. Without it the smoke binary can SIGILL at runtime.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Ran the gate with `--max-batches 3` but no `--epochs 1` | Assumed `--max-batches` bounded the whole run | `--max-batches` only caps batches WITHIN an epoch; the model still looped `for epoch in range(1, epochs+1)` up to the default 200 epochs and blew the timeout | ALWAYS pass `--epochs 1` in the gate invocation — the batch cap does NOT cap the epoch count (the single most important non-obvious gotcha) |
| Asserted the loss decreases monotonically | Added a check that each printed loss < the previous one | Loss on 3 tiny synthetic batches from random init is noisy — it goes up as often as down, so the assertion was flaky | Assert MECHANISM not convergence (ADR-014): exit 0 + >=2 finite, parseable loss lines. Never assert monotonic decrease on a tiny smoke run |
| Ran all 8 models serially in one CI job | Put every model's compile+smoke into a single job | 8 models AOT-compiling serially blew the "<5 min" wall-clock budget | Use a per-model recipe (`training-smoke-one <example> <entry>`) driven by a GitHub Actions matrix (`fail-fast: false`, `needs: [compile-job]`) so models run in PARALLEL — wall-clock ≈ one model, not 8× |
| Let the smoke run hit `model.save_weights()` | Ran the full training path including weight persistence under smoke | The run crashed inside the save_weights serializer, failing an otherwise-passing smoke gate | Guard save under `if not smoke:` — there is nothing to persist from tiny synthetic batches, and skipping it sidesteps the serializer bug |
| Kept the production loss-print gate `(batch_idx+1) % 100 == 0` | Left the 100-batch print cadence unchanged for the smoke run | A 3-batch smoke run emitted ZERO loss lines, so the >=2-loss-line assertion failed spuriously | Widen the gate: `(batch_idx+1) % 100 == 0 or num_batches <= 10` so tiny runs still print |
| Fed raw uint8 labels to a cross_entropy model | Used the default `uint8` `s % num_classes` labels for every model | Models that feed `cross_entropy` directly may need one-hot `float32` train labels; the raw uint8 labels errored on dtype/shape | Check the loss signature per model; use one-hot `float32` train labels for the cross_entropy-direct models, raw uint8 for the rest |

## Results & Parameters

- **Entrypoint flags:** `--smoke` (in-process synthetic data, no dataset download), `--max-batches N`
  (cap batches per epoch: `if max_batches > 0 and max_batches < num_batches: num_batches = max_batches`).
  Both wired into the arg parser AND the `TrainingArgs` struct.
- **Synthetic data:** `wanted = max_batches if max_batches > 0 else 3`; `n_smoke = wanted * batch_size`;
  `zeros([n_smoke, C, H, W])` filled class-correlated (`cls = s % num_classes`) so the loss is meaningful.
  Labels raw `uint8` `s % num_classes` — EXCEPT cross_entropy-direct models need one-hot `float32` train labels.
- **Epoch cap:** `--epochs 1` REQUIRED in the gate invocation. `--max-batches` caps batches WITHIN an
  epoch only; without `--epochs 1` the full (up to 200) epoch loop runs and times out.
- **Assertion (mechanism, not convergence — ADR-014):** exit 0 AND >=2 finite, parseable loss lines.
  Do NOT assert monotonic decrease (flaky on tiny noisy runs).
- **Loss-print gate widened:** `(batch_idx+1) % 100 == 0 or num_batches <= 10` so tiny runs still emit lines.
- **Save guard:** `if not smoke: model.save_weights(...)` — nothing to persist + sidesteps serializer bugs.
- **Matrix CI job:** per-model recipe `training-smoke-one <example> <entry>` driven by a GHA matrix
  (`fail-fast: false`, `needs: [compile-job]`) so N models compile+run in PARALLEL — wall-clock ≈ one
  model, not N×. Mirror the sibling test job exactly (same setup-container action, same pinned SHAs, same timeout).
- **AVX-512 workaround:** pass `MOJO_TARGET_CPU` to strip AVX-512 target-features on masked GHA runners
  (a known libKGEN JIT SIGILL workaround).
- **Cross-links:** related to but DISTINCT from
  `planning-unmerged-parent-contract-compile-smoke-gate` (that PLANS such a gate) and
  `tooling-dry-run-smoke-full-profile-dispatcher` (a dry/smoke/full PROFILE dispatcher). This skill is
  the concrete training-entrypoint IMPLEMENTATION.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/ProjectOdyssey (Odyssey) | Issue #5551 — build a training-smoke CI gate that proves each training entrypoint's mechanism works without dataset download or convergence checks (ADR-014). PR #5583. | verified-local — the per-model recipe was run end-to-end in-container (resnet18: 5 finite loss lines, exit 0, gate reports OK). The matrix CI job YAML parses and mirrors a known-green sibling test job, but CI on PR #5583 was still running at capture time. So: matrix CI job authored + YAML-validated + one model verified in-container locally; full 8-model CI run pending. |
