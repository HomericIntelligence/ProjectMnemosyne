---
name: sampling-degeneration-seed-token-debugging
description: "Debug seed-driven LLM sampling degeneration by stopping at the first bad token and inspecting the next-token distribution. Use when: (1) the same prompt, weights, backend, and generation config differ only by seed, (2) top-k/top-p/temperature changes alter garbled-output rates, (3) a logging top-N limit may have been confused with sampler support."
category: debugging
date: 2026-07-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - llm
  - sampling
  - seed
  - logits
  - top-k
  - top-p
  - degeneration
  - xllm
  - issue-257
---

# Sampling Degeneration Seed Token Debugging

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-09 |
| **Objective** | Diagnose LLM garbled output when matched runs differ only by seed, and separate bad random draws from prompt, weight, tokenizer, backend, or deterministic-forward differences. |
| **Outcome** | Successful locally. The useful pivot was asking why seed mattered: seed changes the random draw from the next-token distribution, not the prompt, weights, tokenizer, or deterministic forward pass. That moved the investigation from whole-trace comparison to the first bad sampled token in one trace. |
| **Verification** | verified-local. Evidence came from redacted Inference360 issue #257 scripts, dense-model sweeps, direct XLLM checks, and manual review. ProjectMnemosyne CI validation is pending for this skill PR. |

## When to Use

- The same model, prompt, backend, tokenizer, and generation config produce readable output for one seed and garbled output for another.
- A generation degenerates into repeated ellipsis, newline loops, prompt-framing leakage, or similar hard corruption after an apparently valid prefix.
- You need to decide whether top-k, top-p, greedy, temperature, or stop-token behavior is changing the actual sampler support.
- A trace-diff approach is producing too much noise and not explaining why a specific seed fails.
- A script reports `top_k=N`, but there is any chance `N` is only the top-N dump/reporting limit instead of the sampler's support.

## Verified Workflow

Verified locally only through redacted Inference360 issue #257 scripts and manual review. Do not claim verified-ci until this skill PR's `validate` and `markdownlint` checks pass.

### Quick Reference

```bash
# Capture a per-step trace for one failing seed.
python <trace-script>.py \
  --model <model-id> \
  --prompt-file <REDACTED_PROMPT_FILE> \
  --seed 116 \
  --temperature 1 \
  --top-k 20 \
  --top-k-dump 50 \
  --output <REDACTED_ARTIFACT_ROOT>/seed-116-trace.jsonl

# Inspect the selected token rank and probability near the first hard-corruption step.
python <analyze-trace-script>.py \
  <REDACTED_ARTIFACT_ROOT>/seed-116-trace.jsonl \
  --window 80:100 \
  --top-n 20

# Replay the divergence step by forcing plausible alternatives.
python <force-token-script>.py \
  --trace <REDACTED_ARTIFACT_ROOT>/seed-116-trace.jsonl \
  --force-step 90 \
  --force-rank 1,2,3,4 \
  --output <REDACTED_ARTIFACT_ROOT>/forced-alternatives.jsonl
```

### Detailed Steps

1. **Ask why seed matters before comparing whole traces.** With the same prompt, weights, backend, tokenizer, and generation config, seed should only affect random sampling from the next-token distribution. It should not change the deterministic forward pass. This narrows the first question to: which sampled token draw sent the trace into a bad basin?
2. **Collect per-step token evidence.** For each generated step, log the selected token id/text, selected rank, selected probability, logits or post-filter probabilities, top-N alternatives, active sampler config, stop/control-token flags, and the decoded prefix.
3. **Stop at the first hard-corruption token.** Do not start by explaining every downstream token. Find the first selected token after which the continuation becomes repeated ellipsis/newline variants, prompt-framing leakage, or another stable corruption pattern.
4. **Inspect selected rank and nearby alternatives.** A low-probability selected token can be a valid sampler draw even when rank 1 is overwhelmingly more likely. The key diagnostic is whether the selected token was inside the configured sampler support and whether higher-ranked alternatives preserve readable continuation.
5. **Force plausible alternatives at the divergence step.** Replay from the same prefix while forcing rank-1, rank-2, rank-3, and the originally selected token. If the top alternatives stay readable and the original draw degenerates, the corruption is primarily a sampling-tail trajectory, not a whole-trace backend mismatch.
6. **Sweep sampler support deliberately.** Compare greedy or top-k=1, small top-k, larger top-k, no top-k, and top-p thresholds such as 0.9, 0.95, 0.99, and 0.999. Keep dense-model and MoE results separate, and label partial MoE data as revalidation-needed.
7. **Separate sampler controls from diagnostic dumps.** `--top-k` should control sampler support. A separate `--top-k-dump` or `--top-n-dump` should only limit the logged alternatives. Logs must print both actual sampler support and dump size.
8. **Manually review labels.** Do not auto-label every newline or comma-adjacent ellipsis fragment as corruption. Repeated ellipsis bursts, newline loops, and prompt-framing leakage are the meaningful class. Numeric-array fragments such as `,...`, `...,`, `,…`, or `…,'` can be benign formatting artifacts and need context.
9. **Treat stop/control-token artifacts separately.** If a suspicious case is caused by a special stop/control token or a harness stop condition, record it as an artifact unless the decoded continuation itself demonstrates model-output corruption.
10. **Record verification honestly.** Local sweeps and manual review support `verified-local`. Only mark `verified-ci` when the skill PR's validation gates are observed green.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Compare whole good/bad traces first | Diffed two generations that differed only by seed | The diff grew after divergence and obscured the causal draw | Ask what seed changes, then stop at the first bad sampled token in one failing trace |
| Treat newline spam alone as corruption | Counted newline-heavy output as bad without reviewing decoded context | Some newline behavior was prompt or formatting related, not hard model degeneration | Label repeated ellipsis bursts, newline loops, and prompt-framing leakage; manually review ambiguous cases |
| Use top-k dump count as sampler top-k | A script reported `top_k=N` from the logged top-N dump limit while actual `sampling_top_k` was infinite | The report implied a bounded sampler even when the sampler could draw from the full distribution | Use `--top-k` for sampler support and `--top-k-dump` only for diagnostic logging |
| Assume low-probability draw means backend bug | Treated a very unlikely selected token as impossible | Sampling at temperature 1 can draw low-probability in-support tokens | Inspect rank/probability and replay forced alternatives before blaming logits computation |
| Mistake stop-token artifacts for corruption | Counted special control or stop-token effects as bad model output | The harness boundary, not the model's decoded continuation, caused some suspicious cases | Track stop/control-token status and keep those cases out of true corruption counts |

## Results & Parameters

### Representative Local Finding

A redacted 4B dense-model run with temperature explicitly set to 1, top-k=20, and seed 116 selected an ellipsis-family token around step 90. The selected token was rank 4 at about 0.01% probability while rank 1 was about 75%. After that draw, the next-token distribution flattened into ellipsis and newline variants and the text degenerated. Replaying the divergence while forcing rank-1, rank-2, or rank-3 alternatives kept the continuation readable.

Direct XLLM sweeps showed greedy/top-k=1 removed the observed failures. Top-k=5, top-k=20, and no top-k still had failures. Top-p 0.9 and 0.95 mostly or entirely removed true ellipsis degeneration in the reviewed dense sweep.

### Top-p Sweep Evidence

The following are local issue #257 dense-model manual-review rates across 256 seeds per model where runs completed. Treat them as redacted local evidence, not ProjectMnemosyne CI evidence.

| Sampler | 4B | 7B | 32B | 36B | Notes |
|---------|----|----|-----|-----|-------|
| top-p 0.9 | 0/256 | 0/256 | 0/256 | 0/256 | No manually reviewed true bad dense cases where runs completed |
| top-p 0.95 | 0/256 | 2/256 suspicious | 0/256 | 0/256 | The 7B suspicious cases looked likely to be stop-token artifacts rather than true ellipsis degeneration |
| top-p 0.99 | 1/256 | 2/256 | 2/256 | 0/256 | Low reviewed true bad rates |
| top-p 0.999 | 3/256 | 5/256 | 14/256 | 20/256 | Higher reviewed true bad rates as the tail widened |

MoE partial data from the same investigation is revalidation-needed and should not be generalized until dense and MoE runs complete under the same review protocol.

### Config Contract

Use separate flags for sampler behavior and diagnostic visibility:

```text
--top-k 20        # sampler support: only ranks inside top 20 are eligible
--top-k-dump 50   # diagnostic dump: log up to 50 alternatives, does not affect sampling
--top-p 0.95      # sampler support: nucleus threshold
--temperature 1   # explicit temperature, not an implicit default
```

Sanity checks for trace/report scripts:

- The emitted report field for sampler support must come from the actual sampling config, not the dump limit.
- The logged top-N count may exceed sampler support if it is used only for diagnostics.
- The trace should record selected rank after all active sampler filters.
- The manual-review label should distinguish true degeneration from formatting fragments and stop/control-token artifacts.

### Review Caveat

Comma-adjacent ellipsis fragments in numeric arrays, including `,...`, `...,`, `,…`, and `…,'`, should not be auto-labeled as corruption. Review decoded context. Meaningful corruption is repeated ellipsis bursts, newline loops, or prompt-framing leakage that persists after the first bad draw.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| LLM360/Inference360 | Redacted issue #257 local scripts and manual review, 2026-07-09 | Dense-model traces and sweeps supported the first-bad-token workflow, forced-alternative replay, top-k/top-p findings, and the sampler-vs-dump caution. MoE partial data remains revalidation-needed. |
