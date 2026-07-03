---
name: planning-pr-body-numeric-claims-source-derived
description: "When a PR-open plan writes a body that STATES specific quantitative claims (parameter counts, tensor counts, file counts, test counts, epoch counts, dataset sizes), the plan MUST either (a) derive the number from a grep/read command on the actual source and cite the command inline, OR (b) treat the number as a placeholder for the executor to fill from a specific command; the plan MUST NOT invent an explanation with fabricated arithmetic. A concrete anti-pattern from ProjectOdyssey #5527 planning: claimed '110 trainable tensors' with the arithmetic '3 + 78 + 2 = 83 core params, then 110 after including per-block bias tensors' — the arithmetic does not sum to 110 (83 ≠ 110) and the source was never read. Reviewers may miss the mismatch; even if they catch it, the plan has lost credibility. The correct pattern: for MobileNetV1 tensor counts, the plan should specify `pixi run mojo run -c 'from projectodyssey.models.mobilenetv1 import Model; var m = Model(); print(len(m.trainable_tensors()))'` (or the analogous grep over the constructor), leave the number as `<<TRAINABLE_TENSOR_COUNT>>` in the body template, and let the executor substitute. Use when: (1) drafting a PR body that includes any specific integer count of source artifacts (params, tensors, files, tests, lines), (2) writing plan prose that includes 'arithmetic to justify a number' (e.g. `3 + 78 + 2 = 83`), (3) catching yourself citing a number sourced from analogy, memory, or a similar model's spec rather than the branch under test."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pr-body
  - numeric-claims
  - source-derived
  - parameter-count
  - tensor-count
  - fabrication-hazard
  - placeholder-substitution
  - arithmetic-error
---

# Planning: PR-Body Numeric Claims Must Be Source-Derived

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | When a PR body states a quantitative claim about source artifacts (parameter count, tensor count, file count), the plan must either derive the number from a probe command on the actual source at run time, or leave it as a placeholder for the executor to fill — never invent the number with fabricated arithmetic. |
| **Outcome** | PLAN ONLY — captured after a planning session for ProjectOdyssey #5527 produced a PR body claiming '110 trainable tensors' with the arithmetic `3 + 78 + 2 = 83 core params, then 110 after including per-block bias tensors`. The sum does not reach 110 and the source (`train.mojo`) was never read; the plan's credibility collapses on inspection. |
| **Verification** | unverified |

## When to Use

- Drafting a PR body that includes a specific integer count derived from source artifacts: parameter counts, trainable-tensor counts, layer counts, file counts, test-file counts, dataset sample counts, line-of-code counts.
- Writing plan prose that includes any "arithmetic explanation" of a number (e.g. `3 + 78 + 2 = 83`) — the arithmetic itself is a hazard because it invites the reader to trust it without checking, and the planner rarely runs the sum.
- Any planning session where a number in the plan came from analogy ("MobileNetV1 has similar architecture to X, so probably ~110 tensors") rather than a probe against the branch under test.
- Planning a PR body that cites both a "high-level count" (e.g. "83 core params") AND a "detailed breakdown" — the breakdown that fails to sum to the high-level count is a durable-embarrassment signal.

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed: the specific probe commands below (e.g. `mojo run -c 'print(len(model.trainable_tensors()))'`)
> were NOT run against a live MobileNetV1 model in this session; the Mojo API for
> introspecting a model's trainable tensor list may differ from the shape assumed
> here. Treat the specific probe commands as templates — verify against your model
> class's actual introspection surface before using.

### Quick Reference

```bash
# BAD (from ProjectOdyssey #5527 plan — do not repeat):
#   "The model has 110 trainable tensors:
#    3 stem params + 78 depthwise-separable block params + 2 head params = 83 core,
#    then 110 after including per-block bias tensors."
# Problems:
#   (a) 3 + 78 + 2 = 83, not 110 — the arithmetic contradicts itself
#   (b) no source was read to confirm any of these numbers
#   (c) the plan reads confidently, so a reviewer may miss the internal mismatch

# GOOD — leave a placeholder + a probe command in the plan:
#   PR body: "The model has <<TRAINABLE_TENSOR_COUNT>> trainable tensors."
#   Executor script:
grep -cE '^\s*(var|self\.)\w+\s*=\s*(Tensor|AnyTensor)' src/projectodyssey/models/mobilenetv1/model.mojo
# OR (if the model has an introspection API):
pixi run mojo run -c 'from projectodyssey.models.mobilenetv1 import Model; var m = Model(); print(len(m.trainable_tensors()))'

# GOOD — derive in the plan itself when the number is small and stable:
n=$(grep -cE 'trainable_tensor' src/projectodyssey/models/mobilenetv1/model.mojo)
echo "The model has $n trainable tensors (grep: 'trainable_tensor' in model.mojo)."
```

### Detailed Steps

1. **When you write a number in a plan**, ask: "did I derive this from a command against the branch under test, or did I sum/estimate/recall it?" If not derived, mark it `<<TOKEN>>` and specify the probe.
2. **When you write arithmetic in a plan** (`3 + 78 + 2 = 83`), run the sum. Every time. Do not commit "obvious" arithmetic without verifying the sum — an off-by-N sum in a plan is a durable-embarrassment signal that undermines the plan's credibility even when the final number is correct.
3. **When two numbers appear in the same plan** (a subtotal and a total), check they are consistent. In the #5527 case, "83 core params" and "110 total including biases" cannot both be right without an unstated +27 that the plan does not derive.
4. **Prefer introspection APIs over grep** when the model class supports it (`len(model.trainable_tensors())`, `sum(p.numel() for p in model.parameters())` in PyTorch equivalents). Grep counts are best-effort; the model's own accessor is authoritative.
5. **When the probe requires the branch to be built and the plan is being written pre-implementation**, treat the number as a placeholder for the executor to fill AT PR-open time, not at plan time. The plan should specify the probe command; the number appears only in the assembled PR body.
6. **In review**, if a reviewer catches an arithmetic mismatch in a plan's numbers, treat it as a signal to distrust every other number in the plan, not as a local typo to patch.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 planning session: state that MobileNetV1 has 110 trainable tensors, with the explanatory arithmetic `3 + 78 + 2 = 83 core params, then 110 after including per-block bias tensors`. | Two failure modes: (a) the arithmetic `3 + 78 + 2` sums to 83, not 110 — the explanation is internally inconsistent; (b) the source file (`train.mojo` and the model definition) was never read, so neither 83 nor 110 was verified. The plan reads confidently, hiding two independent errors. | Do not invent numbers. Do not invent arithmetic to justify a number. If the number matters, derive it from a probe command against the branch and cite the command; otherwise leave a placeholder. |
| Attempt 2 | Include the number without arithmetic ("The model has 110 trainable tensors"). | Same root cause: the number was not derived from source. A reviewer trusts the confident-sounding number until they run the probe and find something different. | Arithmetic-free fabrication is still fabrication. The pattern is unchanged: probe-then-cite, or placeholder-for-executor. |

## Results & Parameters

### Configuration

```yaml
plan-pattern:
  numeric-claims:
    require-source-derivation: true
    allowed-forms:
      - inline-derived:
          example: "The model has $(grep -cE 'trainable_tensor' src/…/model.mojo) trainable tensors (grep: …)"
      - placeholder-for-executor:
          example: "The model has <<TRAINABLE_TENSOR_COUNT>> trainable tensors."
          executor-probe: "grep -cE 'trainable_tensor' src/…/model.mojo"
    forbidden-forms:
      - inline-fabricated: "The model has 110 trainable tensors."
      - inline-with-arithmetic-explanation: "3 + 78 + 2 = 83 core, then 110 with biases"
    guards:
      - "every numeric claim in a plan MUST have a citation to the probe command that produced it"
      - "every arithmetic expression in a plan MUST sum on inspection"
```

### Expected Output

- Every specific integer in a plan is either:
  - inline-derived with the citation `(grep: <pattern>, N matches)` or `(mojo run: <expr>, output=<N>)`, OR
  - a `<<TOKEN>>` placeholder with a specified probe command the executor runs at PR-open time.
- No plan contains "explanation arithmetic" (`3 + 78 + 2 = 83`) whose sum has not been run.
- No plan states two related counts (a subtotal and a total) whose difference is unexplained.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5527 planning session (2026-07-02) — captured the anti-pattern (invented '110 tensors' with contradicting arithmetic `3+78+2=83`). Corrective pattern PLAN ONLY, not executed. | See ProjectOdyssey issue #5527 comments. |

## References

- [mojo-planning-verify-type-semantics-and-source-counts](mojo-planning-verify-type-semantics-and-source-counts.md) — sibling skill; overlapping domain (verify Mojo source counts by direct probe) but focused on planning Mojo IMPLEMENTATION code, whereas this skill covers PR-body prose.
- [planning-pr-body-extract-sibling-artifact-at-runtime](planning-pr-body-extract-sibling-artifact-at-runtime.md) — companion skill for artifacts from sibling issues.
- [planning-pr-open-file-scope-via-git-diff](planning-pr-open-file-scope-via-git-diff.md) — companion skill for file-path claims.
- [planning-pr-open-load-bearing-assumption-hygiene](planning-pr-open-load-bearing-assumption-hygiene.md) — companion skill for probing repo settings.
