---
name: evaluation-baseline-parity-cross-matrix
description: "Prove baseline parity before using any pre-existing baseline number as a comparison anchor, and design a 2x2 cross-matrix (rule x architecture) to de-confound learning-rule claims. Use when: (1) comparing a new training rule/method against a pre-existing baseline run, (2) a reviewer or audit asks whether an accuracy gap is attributable to the rule vs architecture/pipeline differences, (3) planning cross runs to isolate a variable and needing to cost them, (4) citing data artifacts across branches under rebase-merge, (5) deriving wall-clock anchors from logs without per-event timestamps."
category: evaluation
date: 2026-07-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [baseline, parity, confound, cross-matrix, ablation, fair-comparison, experiment-design, provenance]
---

# Baseline Parity and 2x2 Cross-Matrix Evaluation Design

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-11 |
| **Objective** | Make a learning-rule vs backprop accuracy comparison defensible by proving baseline parity and de-confounding rule from architecture/pipeline via a 2x2 cross-matrix |
| **Outcome** | Confound analysis and cross-matrix design passed adversarial audit; the 2x2 cross runs are in flight (numbers pending) |
| **Verification** | verified-local — the confound analysis and experiment design are audit-verified; the cross runs' accuracy numbers are pending |

## When to Use

- Before using any pre-existing baseline number as a gate/comparison anchor for a new method.
- When two runs being compared were built at different times, by different code paths, or from different configs — assume confounds until proven otherwise.
- When designing follow-up runs (cross-matrix, ablation) to isolate which variable explains an observed gap.
- When budgeting compute for cross runs whose cost depends on the swapped variable (e.g., architecture changes that scale a rule's update cost).
- When recording provenance for data artifacts copied across branches in a repo that rebase-merges (SHA-rewriting).
- When deriving wall-clock/timing anchors from logs that lack per-event timestamps.

## Verified Workflow

### Quick Reference

```bash
# 1. Field-by-field delta table: baseline vs treatment (write it into experiment notes)
#    Architecture: strides, widths, FC sizes, dropout, normalization
#    Pipeline: input scaling, augmentation, seeding, drop_last, batch composition
diff <(grep -E "stride|width|channels|fc|dropout" baseline/config) \
     <(grep -E "stride|width|channels|fc|dropout" treatment/config)

# 2. Content-addressed provenance for any copied data artifact
sha256sum data/copied_artifact.bin   # record in notes + PR thread; never cite a branch SHA alone

# 3. Cost both cross directions BEFORE committing; launch the long pole first
```

### Detailed Steps

1. **Parity audit before anchoring.** A baseline number is not a comparison anchor until parity is proven. Enumerate every delta between the baseline run and the treatment run, field by field, in two categories:
   - **Architecture**: e.g., conv1 stride 1 vs 2 (a 4x spatial-compute difference), conv widths (96/256/384/384/256 vs 64/192/384/256/256), FC width (4096 vs 1024), dropout vs none.
   - **Pipeline**: input scaling ([0,1] vs per-channel mean/std), augmentation (none vs crop+flip), seeding (unseeded vs seeded), `drop_last` (false vs true).

   Write the delta table into the experiment notes. If the net bias direction of the deltas is unknown, the gap supports **no** rule claim — say so explicitly.

2. **Design the 2x2 cross-matrix.** With rule R1-on-archA and R2-on-archB already run, add R1-on-archB and R2-on-archA. Key design choice: **each cross run keeps its rule's full protocol** (pipeline, hyperparameters, seeding) **and swaps only the architecture**. This yields:
   - Clean **within-rule** architecture contrasts immediately.
   - Honest **within-arch** rule contrasts up to the (documented) pipeline delta.

   The alternative — also matching pipelines — changes two variables from each source run and orphans the existing cells. State the limitation up front in the notes.

3. **Cost the cross before committing.** The cheap-looking direction may be the expensive one: a rule whose update cost scales with a layer's output spatial size can be quadrupled by a stride change (here: PC-rule-on-BP-arch ~16–21 h vs BP-on-treatment-arch ~2–4 h). Launch the long pole first; run both concurrently if accuracy (not wall-clock) is the metric, and caveat contention in the notes.

4. **Durable cross-branch data provenance.** Under rebase-merge, branch commit SHAs are rewritten, so citing another branch's SHA for a copied data artifact becomes a dangling reference. Instead: copy the file into your branch byte-identical, record its **sha256** (content-addressed, verifiable against the merged file), and cite the issue/PR thread as the fallback locator.

5. **Honest anchor derivation from timestamp-poor logs.** When a run's log lacks per-event timestamps, derive wall-clock as (file mtime − log-start marker) ÷ logged-events, state the method inline, and never assert an interim cadence snapshot as a measured value.

6. **Pre-policy data labeling.** When a policy change truncates or reframes a run mid-flight (e.g., a 12-epoch plan becomes a 1-epoch policy at epoch 7): the policy-compliant datapoint (epoch 0) is the headline; retained extra epochs are labeled "pre-policy bonus trajectory"; the run-stop event is recorded with date + directive; and outcome labels are **not** declared until the re-anchored criteria are approved.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Confounded-anchor near-miss | Nearly used a pre-existing BP baseline (38.5% @1 epoch) as the anchor against the treatment rule (31.2% @1 epoch), attributing the 7.3-pt gap to the rule | Close-out review found the comparison conflated the rule with architecture (stride, widths, FC size, dropout) AND pipeline (scaling, augmentation, seeding, drop_last); net bias direction unknown | Diff architecture and pipeline field-by-field before anchoring; unknown-direction confounds void the claim |
| Dangling-SHA citation | Cited another branch's commit SHA as provenance for a copied data artifact | Rebase-merge rewrote the SHA, leaving a dangling reference; flagged as an audit MAJOR until a fallback sentence was added | Use the copy's sha256 + the issue/PR thread as durable locators; copy artifacts into-branch rather than citing across branches |
| Asserted-cadence anchor | Stated an interim per-epoch cadence snapshot as a measured wall-clock rate | Audit found a 24% error that had propagated into five budget lines | Derive rates from log-start marker + file mtime ÷ logged events, state the method, never assert interim snapshots as measured |
| Assuming the cheap direction is cheap | Assumed the "small" cross run (rule on the other architecture) would be the fast one | The rule's update cost scales with conv1 output spatial size; the stride-1 architecture quadrupled it (~16–21 h vs ~2–4 h for the other direction) | Cost both cross directions from the rule's actual scaling behavior before scheduling; launch the long pole first |

## Results & Parameters

- **Observed (confounded, do not cite as a rule contrast):** BP baseline 38.5% @1 epoch vs treatment rule 31.2% @1 epoch — the 7.3-pt gap is unattributable pending the cross runs.
- **Enumerated confounds (the delta-table template):**
  - Architecture: conv1 stride 1 vs 2 (4x spatial compute); conv widths 96/256/384/384/256 vs 64/192/384/256/256; FC 4096 vs 1024; dropout vs none.
  - Pipeline: [0,1] scaling vs per-channel mean/std; no augmentation vs crop+flip; unseeded vs seeded; drop_last false vs true.
- **Cross-matrix protocol:** each cross run inherits its rule's full protocol; only the architecture is swapped. Limitation (pipeline delta in within-arch contrasts) documented up front.
- **Cost estimates:** PC-rule-on-BP-arch ~16–21 h (stride-1 conv1 quadruples update cost); BP-on-treatment-arch ~2–4 h. Long pole launched first; runs concurrent since accuracy, not wall-clock, is the metric.
- **Provenance recipe:** byte-identical in-branch copy + recorded sha256 + issue/PR-thread citation.
- **Status note:** cross-run accuracy numbers are pending; only the design and confound analysis are verified (adversarial audit passed).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| predictive-coding-mojo (mvillmow/Random) | PC-06/PC-12 baseline close-out + parity-cross-2x2 design; confound analysis passed adversarial audit; 2x2 cross runs in flight | Learning-rule research comparing a predictive-coding rule vs backprop on AlexNet-class models |
