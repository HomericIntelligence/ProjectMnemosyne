---
name: multi-agent-dual-blind-validation-adjudication
description: "Validate every field/item of a structured dataset with TWO independent, mutually blind agents (one may edit in place, one is strictly read-only) and reconcile them with a deterministic merge plus a third adjudicator for high-stakes disagreements. Use when: (1) per-field validation accuracy matters and a single LLM pass is demonstrably unreliable on a large fraction of items, (2) you need 'fully confirmed' to mean two independent confirmations rather than one agent's say-so, (3) you must distinguish genuinely-unconfirmable fields from confirmable ones instead of asserting either way."
category: testing
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [multi-agent, validation, dual-blind, adjudication, cross-check, deterministic-merge, provenance]
---
# Skill: multi-agent-dual-blind-validation-adjudication

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-06-19 |
| Objective | Make per-field validation of a large structured dataset trustworthy when a single LLM agent's per-field judgment is unreliable |
| Technique | Two mutually-blind agents validate every field (one editing, one read-only), a deterministic script merges them, a third agent adjudicates only high-stakes conflicts |
| Outcome | "Fully confirmed" count nearly doubled vs the prior single-agent pass; unconfirmable fields were flagged rather than asserted |
| Verification | verified-local — executed end-to-end on a real ~2,900-field dataset (not in CI) |

## When to Use

Use this skill when:
- You ran a single-agent validation pass over a structured dataset and you do not trust it field-by-field — an LLM's per-item verdicts are often wrong on a large fraction of items even when the aggregate looks fine.
- The cost of an unconfirmed-but-asserted field is high (e.g. anything downstream treats "confirmed" as ground truth), so you want the strongest verdict to require corroboration.
- You need to cleanly separate three outcomes per field: confirmed-by-two-sources, confirmed-by-one-source-plus-recompute (weaker), and genuinely-cannot-confirm — rather than collapsing them.
- You already batch large validation sweeps with a workflow tool and want a reconciliation layer on top (builds directly on `workflow-batched-validation-resume-rate-limits` for the batching/resume mechanics, and on `documentation-field-provenance-metadata-generation` for the per-field provenance JSON schema).

Do NOT reach for this when a single pass is good enough, when the dataset is small enough to fully re-read by hand, or when there is no objective source to cross-check against (two blind agents reading the same ambiguous source will just disagree without resolution).

## Verified Workflow

The core idea: validate EVERY field twice, independently and blindly, then reconcile deterministically and escalate only the few genuine conflicts.

### Step 1: Define two agent roles — one editing, one read-only

- **Agent A (editor)** validates fields and may EDIT the source in place to fix what it finds.
- **Agent B (checker)** validates the SAME fields strictly READ-ONLY. It records what it WOULD change but never writes. Its output is a pure independent opinion.

### Step 2: Order the runs to avoid races and preserve a clean baseline

Run **B first**, against the clean pre-edit state, then a barrier, then **A**. This:
- gives B a true independent baseline (it never sees A's edits), and
- eliminates read/write races (B is done reading before A starts writing).

### Step 3: Enforce blindness

Neither agent may read the other's output, nor any prior pass's results. Disable any skip-cache / "take prior verdict on faith" behavior for the validation read itself, so each agent re-derives every verdict from the underlying sources. (The per-item JSON output can still act as a *resumability* cache across crashes — that is different from letting an agent read a peer's verdict.)

### Step 4: Raise the bar for the strongest verdict

Define verdict tiers explicitly:
- **fully confirmed** = TWO independent sources agree, OR one source plus an independent recomputed cross-check.
- **single-source / weakly confirmed** = exactly one source, no corroboration — a distinctly weaker verdict, not the same as fully confirmed.
- **cannot confirm** = no usable source.

### Step 5: Emit structured per-item JSON from each agent

Each agent (and each batch) writes `{rows:[{field, value, verdict, sources_count, ...}]}`. Structured output makes the later diff/merge deterministic, and the JSON files double as a resumable skip-cache for reruns. Batch by natural grouping with a small cap (~12 items per batch) so each agent stays focused and you stay under the workflow agent cap.

### Step 6: Diff A vs B per field and classify disagreements

After both finish, diff every field. The disagreements fall into two buckets:
- **Benign** (the majority): field-granularity / coverage splits (one agent reported a field the other grouped differently) or pure confidence-level differences where both agree on the *value*.
- **High-stakes** (~5%): a true value conflict, or a verdict that crosses the confirmed / cannot-confirm line.

### Step 7: Merge benign disagreements deterministically — with a plain script, not an agent

The merge is a deterministic script encoding two rules:
- **Union of field coverage** — keep every field either agent reported.
- **Stronger-verdict-on-agreement** — when both agents independently arrive at the same value, upgrade to the stronger verdict. Two independent confirmations *is* the corroboration that earns "fully confirmed."

Do NOT make the merge an agent. Only true divergences become agent work.

### Step 8: Route only high-stakes conflicts to a third adjudicator agent

For each high-stakes disagreement, dispatch a THIRD adjudicator agent that re-reads the underlying sources itself (it does not trust A or B) and issues the deciding verdict.

### Step 9: Pass the adjudication work-list correctly

EMBED the adjudication work-list as a `const` literal inside the orchestration script file. Do NOT pass it via a large `args` object — large args do not reliably reach the script (observed: the workflow exited with 0 agents spawned and an empty result because `args.items` arrived empty; embedding the list as a const fixed it).

### Quick Reference

```
ORDER:  B (read-only, clean baseline)  →  barrier  →  A (validates + edits)
BLIND:  no agent reads a peer's or prior pass's verdicts; skip-cache off for the read
TIERS:  fully-confirmed = 2 sources OR 1 source + recompute
        single-source   = weaker
        cannot-confirm   = no source
DIFF A vs B per field:
  benign  (~95%, coverage/confidence) → deterministic merge:
        • union of coverage
        • both-agree-on-value ⇒ upgrade to fully-confirmed
  high-stakes (~5%, value conflict OR crosses confirmed/cannot line)
        → 3rd adjudicator re-reads sources, decides
OUTPUT: each agent writes {rows:[{field,value,verdict,sources_count}]}  (also = skip-cache)
MERGE:  deterministic script, NOT an agent
ARGS:   embed adjudication list as a const in the script, NOT a big args object
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | ------- | ------- | ------- |
| Deliver work-list via args | Passed the adjudication work-list to the workflow tool as a large `args` object | The workflow spawned 0 agents and returned an empty result — `args.items` arrived empty; large args do not reliably reach the script | Embed the work-list as a `const` literal directly in the orchestration script file |
| One agent per disagreement | Dispatched a separate adjudicator agent for each of the ~1,600 raw A-vs-B disagreements | Far too many agents; most disagreements were benign coverage/confidence splits not worth an agent | First CLASSIFY disagreements; resolve the ~95% benign ones deterministically and route only the ~5% high-stakes ones to agents |
| Both agents edit | Let agent A and agent B both edit the source files in place | Read/write races — B's reads collided with A's writes and B no longer had an independent baseline | Make B strictly read-only and run B BEFORE A against the clean pre-edit state |
| Merge by agent | Considered an LLM agent to reconcile every A-vs-B pair | Non-deterministic and expensive for what is a mechanical rule | Encode "union coverage" + "stronger-verdict-on-agreement" in a plain deterministic script; only true divergences become agent work |
| Trust prior pass / skip-cache | Let agents read prior verdicts to save work | Defeats independence — a wrong verdict gets inherited rather than re-checked | Keep agents blind for the validation read; disable skip-cache for the read (it may still serve crash-resume only) |

## Results & Parameters

Executed end-to-end on a real structured dataset of ~2,900 fields (verified-local; not run in any CI).

Empirical findings — direct evidence a single-agent pass is unreliable:
- The two independent agents **disagreed on ~56% of fields**. A single-agent pass is therefore questionable on more than half of its own work.
- In the adjudicated high-stakes conflicts, the **read-only checker (B) was the correct party ~65% of the time** — the independent read-only opinion was more often right than the editing agent's.
- After the deterministic merge, the **"fully confirmed" count nearly doubled** versus the prior single-agent pass — because two independent agreements were correctly upgraded to corroborated.
- Genuinely-unconfirmable fields were **flagged as cannot-confirm rather than asserted**, preserving the integrity of the "confirmed" tier.

Parameters:
- Run order: B (read-only) → barrier → A (editor).
- Batch cap: ~12 items per agent batch, batched by natural grouping.
- Verdict tiers: fully-confirmed (2 sources OR 1 source + recompute) > single-source > cannot-confirm.
- Disagreement routing: ~95% benign → deterministic merge; ~5% high-stakes → third adjudicator agent.
- Merge rules: union of field coverage; both-agree-on-value upgrades to fully-confirmed.
- Per-item output: `{rows:[{field, value, verdict, sources_count, ...}]}`, doubling as a resumable skip-cache.
- Orchestration: adjudication work-list embedded as a `const` in the script, never via a large `args` object.

Builds on `workflow-batched-validation-resume-rate-limits` (batching + `resumeFromRunId`) and `documentation-field-provenance-metadata-generation` (the per-field provenance JSON schema).
