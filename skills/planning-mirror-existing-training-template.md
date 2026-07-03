---
name: planning-mirror-existing-training-template
description: "Uncertain assumptions and reviewer risks baked into a PLAN that adds a manual backward-pass training loop to a Mojo ML model by mirroring an existing sibling training script in the same repo (MobileNetV1 mirroring VGG16 in ProjectOdyssey). Planning done by reading source files only — nothing was built, compiled, or run. The core lesson: a working reference implementation in the same repo is NOT a verified spec — sibling backward primitives return different types (GradientTriple vs bare Tuple), the reference's loss-call convention may not match the dataset it's paired with, and issue-body parameter counts routinely disagree with the actual model struct. Use when: (1) writing a training-loop plan that mirrors an existing per-block forward-with-caching + reverse backward + in-place SGD-momentum script in the same repo, (2) enumerating trainable parameters for a manual backward pass where the GitHub issue's parameter count disagrees with the model struct, (3) about to copy a sibling training script's `cross_entropy(logits, labels)` or similar loss call verbatim without independently verifying the dataset's label shape, (4) mirroring backward-primitive call sites where sibling primitives (conv2d_backward vs batch_norm2d_backward vs linear_backward) may return DIFFERENT types (GradientTriple field access vs bare Tuple index unpack), (5) the training loop discards mutating state returned by a primitive (BN running_mean/running_var, dropout masks) — this is a correctness gap for inference, not just a code comment, (6) putting a new smoke test under `tests/<newdir>/` and unsure whether the runner discovers it."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning-methodology
  - mirror-sibling-pattern
  - training-loop
  - manual-backward-pass
  - reference-implementation-not-spec
  - api-return-type-drift
  - gradient-triple-vs-tuple
  - batch-norm-running-stats
  - loss-input-contract
  - parameter-enumeration
  - test-discovery-path
  - projectodyssey
  - mojo
  - unverified
---

# Planning: Mirror an Existing Training-Loop Template — a Working Reference Is Not a Verified Spec

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-02 |
| **Objective** | Capture durable planning-risk learnings from producing an implementation plan (not code) for ProjectOdyssey GitHub issue #5525: implementing MobileNetV1's manual backward pass + inlined training step + SGD-momentum update by mirroring the existing VGG16 CIFAR-10 training script (`examples/vgg16_cifar10/train.mojo:41-685`). Planning was done by reading source files only; nothing was built or run. |
| **Outcome** | Plan produced; NOT executed. These are the risks a reviewer must gate on and an implementer must not take on faith when mirroring a "working" sibling training script. |
| **Verification** | unverified — read-only planning artifact; no compilation, no test run, no observed gradient values |
| **History** | v1.0.0: initial capture from ProjectOdyssey #5525 (MobileNetV1 mirroring VGG16). Five learnings: (1) sibling backward primitives return different types; (2) reference's loss-call convention may not match its dataset; (3) issue's parameter count lies — enumerate from source; (4) new `tests/<subdir>/` may not be on runner's discovery path; (5) discarded BN running stats are a real inference-correctness gap. |

> This skill is about the **PLANNING-RISK / mirror-a-training-loop** angle, not the mechanics of
> *how* to write a manual backward pass. For gradient-checking mechanics see
> `mojo-tensor-unit-test-and-gradient-checking`; for the general "mirror a sibling pattern"
> planning risk see `planning-mirror-sibling-pattern-thread-all-consumers` (config-hardening
> domain) and `planning-cpp-sibling-submodule-test-mirroring` (C++ GTest domain). This skill is
> specific to what silently breaks when you mirror a same-repo Mojo training script for a manual
> backward pass and assume the reference has been verified end-to-end.

## When to Use

- Writing a plan that mirrors an existing per-block "forward-with-caching + reverse backward +
  in-place SGD-momentum" training script in the same repo (e.g., planning MobileNetV1 training by
  mirroring VGG16's `examples/vgg16_cifar10/train.mojo`).
- Enumerating trainable parameters for a manual backward pass and the GitHub issue's parameter
  count disagrees with what you count in the model struct (issue #5525 said 136; direct enumeration
  gave 110 — BN running stats are non-trainable, conv biases are trainable).
- About to copy a sibling training script's `cross_entropy(logits, labels)` or equivalent loss call
  VERBATIM without independently verifying the dataset's label shape and dtype.
- Mirroring backward-primitive call sites where sibling primitives may return DIFFERENT types —
  `depthwise_conv2d_backward` and `conv2d_backward` return `GradientTriple` (field access:
  `.grad_input`, `.grad_weights`, `.grad_bias`), but `batch_norm2d_backward` returns a bare
  `Tuple[AnyTensor, AnyTensor, AnyTensor]` (must be unpacked by index: `t[0], t[1], t[2]`).
- The training loop discards mutating state returned by a primitive (BN `running_mean`, `running_var`;
  dropout masks between steps) — this is a real inference-correctness gap, not just a code comment.
  Must be flagged in the PR body, not buried in a `# TODO` inside the training step.
- Creating a smoke test under a NEW `tests/<subdir>/` (e.g., `tests/examples/`) and unsure whether
  `just test-mojo` (or the equivalent group runner) discovers it, or whether CI wiring is required.

## Verified Workflow

<!-- Section title per honest verification level: PROPOSED WORKFLOW (unverified). The
"## Verified Workflow" heading is retained only because scripts/validate_plugins.py requires that
literal token; this content is a PROPOSAL, not a verified procedure. See the warning banner below. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. No code was built or run. It is the
> reviewer/implementer checklist distilled from an *unexecuted* plan (ProjectOdyssey #5525) produced
> by reading source files only. Treat every item as a hypothesis until CI confirms.

### Quick Reference

```bash
# === Pre-flight for "mirror the sibling training script's manual backward pass" plan ===
# Example: MobileNetV1 mirroring examples/vgg16_cifar10/train.mojo for ProjectOdyssey issue #5525.

MODEL_NEW="src/projectodyssey/models/mobilenetv1"     # model getting the new training script
REF_TRAIN="examples/vgg16_cifar10/train.mojo"          # sibling training script (reference)
DATASET="src/projectodyssey/datasets/cifar10.mojo"     # dataset the reference is paired with

# 0. PARAMETER-COUNT TRUTH — trust the struct, not the issue text.
#    Issue #5525 said "136 trainable parameters"; direct enumeration of the model struct gave 110.
grep -nE "^\s+(var|self\.)\s+\w+_(weight|bias|weights|running_)" "$MODEL_NEW"/model.mojo | wc -l
# Then hand-classify: BN running_mean/running_var → NOT trainable; conv/BN weight+bias → trainable.

# 1. RETURN-TYPE PER PRIMITIVE — copy-pasting the reference's unpacking pattern will compile-fail.
#    conv2d_backward, depthwise_conv2d_backward → GradientTriple (field access .grad_input, etc.)
#    batch_norm2d_backward → bare Tuple[AnyTensor, AnyTensor, AnyTensor] (index unpack t[0], t[1], t[2])
grep -nE "fn (conv2d|depthwise_conv2d|batch_norm2d|linear)_backward" src/projectodyssey/**/*.mojo
grep -n "GradientTriple\|Tuple\[AnyTensor" src/projectodyssey/autograd/*.mojo

# 2. LOSS INPUT CONTRACT — do NOT copy the reference's `cross_entropy(logits, labels)` verbatim.
#    Read the dataset's label shape/dtype AND the loss's docstring/signature independently.
grep -n "fn cross_entropy" src/projectodyssey/losses/*.mojo    # requires logits.shape() == targets.shape()?
grep -nE "labels\s*:|labels_shape|Uint8|one_hot" "$DATASET"    # (N,) uint8 index, or (N,C) one-hot?

# 3. MUTATING STATE THE STEP DROPS — inference-correctness gap, not a code comment.
#    batch_norm2d(...) returns (out, new_running_mean, new_running_var). If the training loop writes
#    `out, _, _ = batch_norm2d(...)` and never persists the running stats, forward(training=False)
#    silently uses the init values (0/1) forever.
grep -nE "batch_norm2d\(.*\)$|=\s*batch_norm2d\(" "$REF_TRAIN" "$MODEL_NEW"/model.mojo
grep -nE "running_mean|running_var" "$MODEL_NEW"/model.mojo

# 4. TEST DISCOVERY PATH — is the new tests subdir on the runner's path?
ls tests/                                    # existing subdirs the runner already discovers
grep -nE "tests/.*\*\.mojo|test-group" justfile .github/workflows/*.yml
# If tests/examples/ is new, either move the smoke test into an existing discovered subdir or
# wire the new subdir into just test-mojo / CI explicitly.

# 5. PARAM COUNT vs ISSUE — flag the discrepancy in the PR body so reviewers know why.
echo "Issue said 136; struct enumeration gives 110. Document the delta (BN running stats NOT trainable)."
```

### Detailed Steps

1. **Enumerate trainable parameters from the model struct, not the ticket.** Issue #5525 said
   "136 trainable parameters"; direct enumeration of MobileNetV1's `model.mojo` gave 110
   (initial conv 4 + 13 blocks × 8 + FC 2). BN `running_mean` / `running_var` are non-trainable
   statistics, not parameters; conv biases ARE trainable. Always enumerate from the struct fields
   and hand-classify. Document the discrepancy in the plan so reviewers know why the count differs.

2. **For every backward primitive in the plan, open its source and confirm the return type.** Copy-
   pasting the reference training script's unpacking pattern is a compile-failure trap. In
   ProjectOdyssey, `conv2d_backward` and `depthwise_conv2d_backward` return `GradientTriple` (field
   access: `.grad_input`, `.grad_weights`, `.grad_bias`), but `batch_norm2d_backward` returns a
   plain `Tuple[AnyTensor, AnyTensor, AnyTensor]` and MUST be unpacked by index (`t[0]`, `t[1]`,
   `t[2]`) — no field names. The VGG16 template uses `GradientTriple` throughout because VGG16
   doesn't use BN in the same block layout MobileNetV1 does. Copy-pasting the VGG16 pattern
   verbatim will silently compile-fail (or worse, mislead a reader). Verify each primitive's
   return signature by reading its `fn` declaration.

3. **Verify the loss's input contract against the dataset — do NOT trust the reference's call
   convention.** The VGG16 training script calls `cross_entropy(logits, labels)` where `labels`
   comes from `CIFAR10Dataset`. But `cross_entropy` requires `logits.shape() == targets.shape()`
   (one-hot targets), while `CIFAR10Dataset` labels are shape `(N,)` uint8 class indices — NOT
   `(N, 10)` one-hot. Either the reference training script is latently broken, the dataset shape
   changed under it, or an implicit conversion exists that you haven't found. When mirroring,
   don't propagate the call convention without independently verifying the input contract on
   both sides (loss signature AND dataset label shape/dtype). For a smoke test, sidestep the
   ambiguity by constructing synthetic one-hot labels; but flag the reference-may-be-broken risk
   in the PR body so it isn't propagated to the next mirror-plan.

4. **Flag any state the training loop drops as a PR-body item, not a code comment.** The
   MobileNetV1 model calls `batch_norm2d(...)` which returns `(out, new_running_mean, new_running_var)`,
   but the current model code binds `out, _, _ = batch_norm2d(...)` (`model.mojo:218, 230, 350`) and
   never persists the running stats back into `self`. The `forward(training=False)` path uses
   `initial_bn_running_mean` and `initial_bn_running_var` — which will remain their init values
   (0 and 1) forever. Post-training inference will be silently wrong. This is a correctness gap,
   NOT a stylistic note; must be surfaced in the PR body as a follow-up so it doesn't ship silently.

5. **Confirm the test subdir is on the runner's discovery path before creating a new one.** The
   plan puts a new smoke test at `tests/examples/test_mobilenetv1_train_step.mojo`, but existing
   tests live in `tests/models/`, `tests/projectodyssey/`, etc. Before creating a new
   `tests/<subdir>/`, verify it is picked up by `just test-mojo` (or the equivalent test-group
   runner) — grep the justfile and CI workflows for the test discovery glob. If it isn't wired in,
   either colocate the smoke test into an already-discovered subdir OR add the new subdir to the
   runner/CI wiring in the SAME plan.

6. **A "working reference implementation in the same repo" is not a verified spec.** The four
   traps above (return-type drift, loss-input-contract drift, dropped mutating state, undiscovered
   test path) all follow from treating a sibling script as a specification. It is a starting
   point — every callee it uses must be re-verified in the callee's source, and every input it
   consumes must be re-verified against the source of that input. Hold this as an explicit review
   gate: "reference-implementation-not-spec: verified every callee and every input contract
   independently — Y/N per item."

7. **Do NOT claim verification for planning-only work.** If the plan was produced by reading
   source only and `mojo build` / `just test-mojo` / `just shell -c ...` was never executed, the
   verification level is `unverified` and every "verification step" in the plan is prescribed, not
   observed. Mark the PR body accordingly so reviewers gate on compilation and test-run before
   merge, not on the plan's confidence.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume `batch_norm2d_backward` returns `GradientTriple` like `conv2d_backward` | Planned to unpack BN backward with `.grad_input`, `.grad_weights`, `.grad_bias` field access, mirroring the VGG16 template's uniform pattern | Reading the primitive's source showed `batch_norm2d_backward` returns a bare `Tuple[AnyTensor, AnyTensor, AnyTensor]` — no field names; MUST be unpacked by index (`t[0], t[1], t[2]`). Copy-pasting the VGG16 pattern would compile-fail | Sibling backward primitives return different types even when they look parallel. Open each primitive's `fn` declaration; never assume uniformity across a family of backward ops. |
| Copy `cross_entropy(logits, labels)` verbatim from the VGG16 template | Assumed the reference training script's loss call was verified, and mirrored `cross_entropy(logits, labels)` where `labels` came from `CIFAR10Dataset` | `cross_entropy` requires `logits.shape() == targets.shape()` (one-hot targets), but `CIFAR10Dataset` labels are `(N,)` uint8 class indices — NOT `(N, 10)` one-hot. Either the reference is latently broken or the dataset shape changed under it; the mirror-plan would propagate the bug | A working reference implementation in the same repo is not a verified spec. Verify each input contract (loss signature AND dataset label shape) independently — never propagate the reference's call convention without doing so. |
| Trust issue #5525's "136 trainable parameters" number | Started scoping the parameter enumeration to match the issue's 136 | Direct inspection of the MobileNetV1 model struct gave 110 (initial conv 4 + 13 blocks × 8 + FC 2). The issue's number was stale — likely counted BN running stats (non-trainable) or was written before a refactor | Enumerate parameters from the source struct, not the ticket. Document the discrepancy in the plan so reviewers know why the count differs and don't gate on the wrong number. |
| Put the smoke test at `tests/examples/test_mobilenetv1_train_step.mojo` without checking discovery | Planned to create a new `tests/examples/` subdirectory for the smoke test | Existing tests live under `tests/models/`, `tests/projectodyssey/`, etc. — no evidence `tests/examples/` is on `just test-mojo`'s discovery path or wired into CI. The smoke test could pass "vacuously" by not running at all | Before creating a new `tests/<subdir>/`, verify the runner discovers it (grep the justfile and CI workflow globs). If not, colocate into an existing discovered subdir OR wire the new subdir explicitly in the same plan. |
| Treat "BN running stats discarded" as a code comment | Planned to write `out, _, _ = batch_norm2d(...)` in the training step and note the dropped running stats in a `# TODO` comment | `forward(training=False)` uses `initial_bn_running_mean` / `initial_bn_running_var` — which remain init values (0/1) forever if never persisted. Post-training inference is silently wrong; a `# TODO` inside the training step will not surface to reviewers or users | Discarded mutating state returned by a primitive is a correctness gap, not a style note. Flag it in the PR body as a mandatory follow-up so it can't ship silently. |
| Claim "verified" for a plan produced by reading source only | Planned to run `just shell -c "mojo build ..."` but did not actually execute any command; treated the prescribed steps as verification | Nothing was compiled, run, or observed. Verification level is `unverified` and every "verification step" in the plan is a hypothesis. Claiming verification would mislead reviewers into gating on the plan's confidence rather than on CI results | A read-only plan is a hypothesis. Mark verification as `unverified`, use "Proposed Workflow" (not "Verified Workflow"), and make compile-and-test a mandatory pre-merge gate in the PR. |

## Results & Parameters

### Core facts verified by READING source during planning

- **Parameter count**: MobileNetV1 has **110 trainable parameters** (initial conv 4 + 13 blocks × 8 + FC 2), NOT 136 as issue #5525 states. Enumerated from `model.mojo` struct fields. BN `running_mean` / `running_var` are non-trainable; conv/BN weight+bias are trainable.
- **Return-type drift**: `conv2d_backward` and `depthwise_conv2d_backward` return `GradientTriple` (field access `.grad_input`, `.grad_weights`, `.grad_bias`); `batch_norm2d_backward` returns bare `Tuple[AnyTensor, AnyTensor, AnyTensor]` (index unpack `t[0], t[1], t[2]`).
- **Dataset-vs-loss contract**: `CIFAR10Dataset` labels are shape `(N,)` uint8 class indices. `cross_entropy` requires `logits.shape() == targets.shape()` (one-hot). VGG16 template calls `cross_entropy(logits, labels)` verbatim — a latent contract mismatch may exist in the reference itself.
- **Dropped BN state**: `model.mojo:218, 230, 350` bind `out, _, _ = batch_norm2d(...)`, dropping `new_running_mean` / `new_running_2var`. The training-step plan preserves this pattern → inference-time forward uses init values.
- **Test discovery**: existing tests are in `tests/models/`, `tests/projectodyssey/`, etc. `tests/examples/` is a NEW subdir with no confirmed discovery wiring.

### Plan-review checklist a future planner can paste

```markdown
### Mirror-a-training-template review gate (paste into plan review)

- [ ] Parameter count enumerated from the model struct (NOT the issue text). Delta vs issue documented.
- [ ] For every backward primitive called, its `fn` signature was opened and the return type recorded.
      (GradientTriple → field access; bare Tuple → index unpack. Do not assume uniformity.)
- [ ] Loss input contract verified against the dataset's label shape/dtype independently — NOT copied
      from the reference training script. If the reference's call convention may itself be broken,
      that risk is flagged in the PR body.
- [ ] Any mutating state returned by a primitive but discarded by the training step (BN running_mean/
      running_var, dropout masks between steps, EMA buffers) is flagged in the PR BODY as a follow-up
      — not just a `# TODO` inside the training step.
- [ ] Any new `tests/<subdir>/` is either on `just test-mojo`'s discovery path or wired in the same
      plan. Confirmed by reading the justfile and CI workflow test globs.
- [ ] Verification level: `unverified` if `mojo build` / `just test-mojo` was NOT executed. Do not
      use "Verified Workflow" language.
- [ ] Reference-implementation-not-spec discipline: every callee's return type verified; every input
      contract verified against source-of-truth (dataset for labels, primitive docstring for tensors).
```

### The return-type-drift pattern (open every primitive)

```mojo
# INCORRECT — assumes GradientTriple uniformly (copy-paste from VGG16 template)
grads = batch_norm2d_backward(grad_out, x, gamma, beta, ...)
grad_x = grads.grad_input       # AttributeError at compile time — no such field
grad_gamma = grads.grad_weights
grad_beta = grads.grad_bias

# CORRECT — batch_norm2d_backward returns bare Tuple[AnyTensor, AnyTensor, AnyTensor]
grads = batch_norm2d_backward(grad_out, x, gamma, beta, ...)
grad_x = grads[0]
grad_gamma = grads[1]
grad_beta = grads[2]

# ALSO CORRECT — conv2d_backward and depthwise_conv2d_backward DO return GradientTriple
conv_grads = conv2d_backward(grad_out, x, weight, bias, ...)
grad_x = conv_grads.grad_input
grad_w = conv_grads.grad_weights
grad_b = conv_grads.grad_bias
```

### The BN-running-stats persistence gap (flag in PR body)

```mojo
# In model.mojo — drops the new running stats
out, _, _ = batch_norm2d(x, gamma, beta, self.bn_running_mean, self.bn_running_var, ...)
# self.bn_running_mean is NEVER updated; forward(training=False) uses the init value forever.

# What the plan MUST flag in the PR body (not just a code comment):
# > This PR does NOT persist BN running_mean/running_var between training steps. As a result,
# > post-training inference (`forward(training=False)`) will use the init values (0/1) and produce
# > incorrect outputs. Follow-up issue REQUIRED before this model is used for inference.
```

### Most uncertain assumptions — reviewer gates

1. **`unverified`**: nothing was built or run. Every claim in the plan (parameter count math, unpacking pattern, loss call correctness, test discovery) is a hypothesis until CI confirms.
2. **`cross_entropy(logits, labels)` vs `CIFAR10Dataset`**: the reference training script uses this call verbatim, but the dataset labels are `(N,)` uint8 class indices while `cross_entropy` requires one-hot. Either the reference is latently broken or a conversion exists that was not found in planning.
3. **`tests/examples/` discovery**: assumed the runner would find the new subdir. Not verified against `just test-mojo` or `.github/workflows/*.yml` globs. Smoke test may pass vacuously by not running at all.
4. **BN running stats persistence**: plan explicitly discards them, mirroring `model.mojo`'s existing bug. This is a known correctness gap for `forward(training=False)` and MUST be flagged in the PR body.
5. **Parameter count of 110**: enumerated by hand from the struct; not cross-checked against a serialization or state-dict count. If the model's serialization enumerates parameters differently, the count in the PR body may still mislead reviewers.
6. **Backward-primitive signatures**: `batch_norm2d_backward` bare-Tuple return was verified for the current primitive source at plan time; if the primitive is refactored to return `GradientTriple` before the impl PR lands, the plan's unpacking pattern becomes wrong. Re-verify at implementation time.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey (`src/projectodyssey/models/mobilenetv1/`, `examples/vgg16_cifar10/train.mojo`) | Planning GitHub issue #5525 "MobileNetV1 backward-pass + training-step implementation" by mirroring the VGG16 CIFAR-10 training script; read-only, nothing built or run | unverified — assumptions captured for reviewer/implementer. Row to be updated with impl-PR result when the implementation lands. |
