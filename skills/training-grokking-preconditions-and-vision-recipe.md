---
name: training-grokking-preconditions-and-vision-recipe
description: "Catalog the necessary conditions for grokking (delayed generalization) and provide a proposed recipe to attempt it on small vision tasks (MNIST/EMNIST with MLP or LeNet). Use when: (1) a user reports overfitting after long training and asks why they don't see grokking, (2) planning a grokking experiment on supervised vision data, (3) tuning weight decay / AdamW / epochs / dataset-size for delayed-generalization studies, (4) deciding whether a task is structurally capable of grokking, (5) distinguishing grokking from ordinary overfitting or ordinary late convergence, (6) reviewing claims that 'training longer' alone will produce grokking."
category: training
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - grokking
  - delayed-generalization
  - weight-decay
  - adamw
  - omnigrok
  - phase-transition
  - lenet
  - mnist
  - emnist
  - memorization-plateau
---

# Grokking Preconditions and a Proposed Vision Recipe

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Document the necessary conditions for grokking (Power et al. 2022) and provide a proposed recipe to attempt it on small vision tasks such as MNIST/EMNIST with an MLP or LeNet, so practitioners stop confusing "train longer" with grokking. |
| **Outcome** | Reference catalog only. The recipe is synthesized from published work but was not executed. |
| **Verification** | unverified - synthesized from Power et al. 2022, Nanda 2023, Liu et al. 2023 (Omnigrok), Thilak et al. 2022. No run was performed by the author or user. |

> WARNING - PROPOSED WORKFLOW, NOT VERIFIED
>
> The recipe in this skill has not been executed by the author or the
> user who triggered this skill's creation. The conditions and mechanism
> description are drawn directly from the cited literature; the specific
> parameter combinations for a LeNet/EMNIST attempt are extrapolations
> from those papers. Treat the recipe as a starting hypothesis and
> expect to iterate. Most plausibly, the recipe will need adjustment in
> dataset-size, weight-decay magnitude, or architecture (MLP vs conv)
> before producing a clear Phase 1 -> Phase 3 trajectory.

## When to Use

- A user trained a supervised vision model (e.g. LeNet on EMNIST) for hundreds of epochs hoping for grokking and saw textbook overfitting instead.
- Planning an experiment to attempt grokking on a small vision benchmark (MNIST, EMNIST, CIFAR-10).
- Tuning weight decay, optimizer choice, or training budget specifically for delayed-generalization studies.
- Someone proposes "train longer" as the fix for overfitting and attributes the missing grok to insufficient epochs alone.
- Reviewing a claim that a non-algorithmic, non-compositional vision task should produce a grok-style phase transition.
- Distinguishing genuine grokking (test_acc snap-up while train_loss already at 0 for many epochs) from late convergence (test_acc improving while train_loss is still falling).

## Verified Workflow

> The headers below are the required structure for this repository's skill
> validator. This section is a Proposed Workflow - see the warning at the top.

### Quick Reference - the five necessary conditions for grokking

All five must hold together. Missing any one is sufficient to prevent grokking.

| Condition | Required value | Why |
| --- | --- | --- |
| Train loss during memorization phase | approximately 0 (perfect memorization), maintained for thousands of epochs | The mechanism is "slow weight decay outcompetes the already-established memorization circuit". Without a fully established memorization circuit, there is nothing to outcompete. |
| Weight decay (`wd`) | approximately 1.0 (not 1e-4, not 1e-2 - one) | The slow norm-shrink is the mechanism, not a generic regularizer. Typical regularization values are 1000x too small. |
| Optimizer | AdamW or SGD with decoupled decay | Plain Adam with L2 penalty in the loss folds decay into the per-parameter adaptive learning rates and breaks the steady norm-reduction signal. |
| Time past memorization | 10x to 100x the epochs needed to memorize | In published reports the memorization phase ends in approximately 100 epochs and the grok occurs at approximately 10k - 50k epochs. |
| Train-set size | Small enough to be fully memorized. Empirically a sweet spot of 30 - 50 percent of available data, or a few hundred to a few thousand samples for vision. | If the model cannot drive train_loss to approximately 0, Phase 1 never completes and grokking is structurally impossible. |

Two further conditions that gate whether grokking is achievable at all:

| Condition | Required property |
| --- | --- |
| Task structure | Compositional or algorithmic, or possesses a discoverable low-norm circuit. Modular arithmetic, group operations, and small logical rules satisfy this; arbitrary handwriting pattern recognition does not. |
| Architecture | Small. Original results used a small Transformer or a small MLP (Omnigrok). Convolutional networks bring a generalizing inductive bias and tend to generalize from epoch 1, so Phase 1 (memorization with chance-level test accuracy) never forms. |

### Mechanism summary (one paragraph)

Two solutions compete in the loss landscape: a brittle high-norm
**memorization circuit** that fits training only, found quickly; and a
low-norm **generalization circuit** with compositional structure that
also happens to fit test, found slowly. Weight decay applies steady
pressure toward low-norm solutions. Phase 1: model converges to the
memorization circuit; train_loss approaches 0 and test_acc is at chance.
Phase 2 (long plateau): weight decay keeps shrinking weights; the
memorization circuit slowly degrades but still classifies training while
the generalization circuit is shaped in the low-norm region. Phase 3
(grok): the generalization circuit becomes dominant; test_acc snaps up
while train_loss remains near 0.

### Why standard supervised vision is hostile to grokking

MNIST, EMNIST, and CIFAR-10 are statistical-pattern-recognition tasks,
not algorithmic ones. There is no compact rule for distinguishing a
handwritten 'g' from a 'q'; the answer is an aggregation over thousands
of pixel patterns. No matter how long you train, there is no parsimonious
low-norm circuit waiting to be discovered, only noisier or smoother
interpolations of the training pixels. Liu et al. 2023 ("Omnigrok")
obtained grokking-like behavior on MNIST with small MLPs and heavy
tuning; conv networks and EMNIST were not part of the demonstrated set.

### Proposed Workflow - attempt grokking on LeNet+EMNIST

> Unverified. All five changes are required together. Setting any one
> in isolation will not produce grokking.

1. **Subsample the train set to 500 - 2000 examples.** Keep the full test set. The goal is to make the train set small enough that the network can drive train_loss to approximately 0 and maintain it.
2. **Use AdamW with `weight_decay = 1.0`.** Verify your framework's AdamW implements *decoupled* weight decay; do not substitute plain Adam with an L2 penalty in the loss.
3. **Train for 30,000 - 100,000 epochs.** Wall-clock is roughly comparable to a full-data run since each epoch is approximately 50x shorter.
4. **Log train_acc, test_acc, and weight norm every epoch (or every 10 - 100 epochs in the saved log).** The diagnostic for Phase 1 completion is train_acc = 100 percent flat and test_acc near chance flat for many consecutive epochs. Without that signal you cannot tell whether the run is on track.
5. **Save checkpoints periodically** so you can locate the grok moment post-hoc.

Optional but recommended: no dropout (it interferes with reaching
train_loss approximately 0); `batch_size = 64` or full-batch;
`lr = 1e-3`.

### Two-step pragmatic plan to reduce risk

1. **First replicate on MNIST with an MLP only.** Remove the conv layers from LeNet and use the FC stack as a 2-layer MLP. MNIST + small MLP + the five changes above is the configuration closest to a known-published result (Omnigrok). If grokking does not appear here, EMNIST + convs is hopeless.
2. **Only if step 1 succeeded**, swap MNIST -> EMNIST and gradually reintroduce convs. Each addition makes grokking less likely; you are charting the regime boundary.

### Realistic outcome distribution

| Outcome | Qualitative probability |
| --- | --- |
| Step 1 (MNIST + MLP) shows clear grokking | Plausible - published results exist (Omnigrok) |
| Step 2 (EMNIST + MLP) shows clear grokking | Less plausible - 47 classes vs 10 changes the dynamics |
| Step 2 with even one conv layer | Unlikely |
| Original LeNet (2 convs + FC) on EMNIST | Very unlikely - conv inductive bias generalizes from epoch 1 |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| "Train longer to grok" | Bumped epochs from 10 to 500 on an otherwise standard LeNet/EMNIST training config and waited | Without the other four conditions, more epochs only produces more overfitting. Grokking is not a property of training budget; it is a property of (task x regularization x dataset-size x optimizer). | Vary the configuration, not just the budget. |
| Standard-strength weight decay | Set `weight_decay = 1e-4` or `1e-3` and expected grokking eventually | Grokking-required `wd` is approximately 1.0, roughly 1000x larger than typical regularization values. The required value is mechanism-driven, not search-tuned. | Set `wd = 1.0` directly. Do not include it in a normal hyperparameter sweep range. |
| Plain Adam with L2 penalty | Added an L2 term to the loss with Adam and treated it as equivalent to AdamW | L2-in-loss interacts with Adam's per-parameter adaptive learning rates, washing out the steady norm-reduction signal that grokking depends on. AdamW with decoupled decay does not. | Always verify the decay is decoupled. AdamW != Adam+L2 for this purpose. |
| Grokking on the full EMNIST train set | Trained on all 112,800 EMNIST Balanced samples for many epochs | Model cannot drive train_loss to approximately 0 on the full set, so Phase 1 never completes and Phase 2 / Phase 3 are impossible. | Use a small enough train set that perfect memorization is achievable. |
| LeNet conv layers for grokking | Kept the 2 conv layers of LeNet on the theory that "more expressive should grok eventually" | Convs encode a generalizing prior (translation equivariance, locality), so the network generalizes from epoch 1 and Phase 1 (memorization with chance-level test acc) never forms. | For grokking experiments use the simplest architecture that can memorize the data - prefer MLPs, not convs. |

## Results & Parameters

### Proposed configuration (unverified)

```yaml
# Step 1: MNIST + 2-layer MLP (closest to published Omnigrok configuration)
dataset: MNIST
train_subset: 1000          # 500 - 2000 range
test_set: full
architecture: MLP           # 784 -> hidden -> 10; rip convs out of LeNet
hidden_units: 200           # small
dropout: 0.0
optimizer: AdamW            # decoupled weight decay - verify your framework
weight_decay: 1.0
learning_rate: 1.0e-3
batch_size: 64              # or full-batch
epochs: 100000              # 30k - 100k
log_every_epochs: 10
checkpoint_every_epochs: 1000

# Step 2 (only after Step 1 shows grokking): EMNIST + MLP, then add convs one at a time
```

### Expected diagnostic trajectory

A successful grokking run produces three visually distinct phases on a
single train/test accuracy plot vs epochs (use log-x):

1. **Phase 1 (memorization)**: train_acc climbs to 100 percent within roughly 100 - 1000 epochs; test_acc stays near chance (`1/num_classes`).
2. **Phase 2 (plateau)**: train_acc holds at 100 percent flat; test_acc stays near chance flat. Weight norm visibly decreasing. This phase lasts most of the run (thousands to tens of thousands of epochs).
3. **Phase 3 (grok)**: test_acc rises sharply, often within a few hundred epochs, to a value far above chance. train_acc remains at 100 percent throughout.

If train_acc never reaches 100 percent, Phase 1 never completed - the
train set is too large or the model is too small. If test_acc rises while
train_acc is still climbing, that is ordinary late convergence and not
grokking. If train_acc reaches 100 percent and test_acc also climbs
immediately (no plateau), the architecture's inductive bias is generalizing
from the start and there is no grok to observe - which is the expected
outcome for convnets on natural-image tasks.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| N/A | This skill records a synthesized recipe; it has not been executed. The triggering session (ProjectOdyssey, LeNet on EMNIST Balanced, 500 epochs) observed textbook overfitting and motivated the catalog, but did not attempt the recipe. | See References for the source papers. |

## References

- Power, A., Burda, Y., Edwards, H., Babuschkin, I., Misra, V. (2022). *Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets*. <https://arxiv.org/abs/2201.02177>
- Nanda, N., Chan, L., Lieberum, T., Smith, J., Steinhardt, J. (2023). *Progress measures for grokking via mechanistic interpretability*. <https://arxiv.org/abs/2301.05217>
- Liu, Z., Michaud, E. J., Tegmark, M. (2023). *Omnigrok: Grokking Beyond Algorithmic Data*. <https://arxiv.org/abs/2210.01117>
- Thilak, V., Littwin, E., Zhai, S., Saremi, O., Paiss, R., Susskind, J. (2022). *The Slingshot Mechanism: An Empirical Study of Adaptive Optimizers and the Grokking Phenomenon*. <https://arxiv.org/abs/2206.04817>
- Loshchilov, I., Hutter, F. (2019). *Decoupled Weight Decay Regularization* (AdamW). <https://arxiv.org/abs/1711.05101>
