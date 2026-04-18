---
name: research-corpus-exec-summary-overhead-honesty
description: "Ensures executive summary tables in research docs surface the dominant overhead metric, not just the smallest one. Use when: (1) writing exec summaries for latency-increasing ideas, (2) auditing comparison tables where FLOPs and TPOT diverge, (3) reviewing AR loop / iterative refinement / diffusion decoder proposals."
category: documentation
date: 2026-04-18
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [research, corpus, exec-summary, overhead, TPOT, FLOPs, latency, honesty, audit]
---

# Research Corpus Exec Summary Overhead Honesty

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-18 |
| **Objective** | Prevent misleading executive summaries that bury the dominant cost metric in body sections while showing only a favorable metric up front |
| **Outcome** | Rule established during remediation of research_6_1_inarch_ar_loop.md where FLOPs overhead was +0.18% but TPOT overhead was W x 1.5-2.5x — the exec summary only showed FLOPs |
| **Verification** | verified-local |

## When to Use

- Writing an executive summary comparison table for an AI architecture idea that increases per-token latency (TPOT)
- Auditing research docs where FLOPs overhead and TPOT overhead diverge by more than an order of magnitude
- Reviewing proposals for in-architecture AR loops, iterative refinement, speculative decoding variants, or diffusion-based decoders
- Any idea where the overhead is dominated by sequential passes rather than raw compute

## Verified Workflow

### Quick Reference

```markdown
# Pattern: When TPOT >> FLOPs for an idea, the exec summary table MUST include:

| Metric | Baseline | With Idea | Delta |
|--------|----------|-----------|-------|
| Params | 32B | 32.06B | +0.18% |
| FLOPs/token | X TFLOPs | X+Y TFLOPs | +0.18% |
| **TPOT** | **T ms** | **W x T ms** | **W x 1.5-2.5x** |

> **Warning — TPOT dominates:** Although FLOPs overhead is negligible (+0.18%),
> this idea introduces W sequential decoding passes per token. Wall-clock TPOT
> scales as W x 1.5-2.5x because each pass is memory-bandwidth-bound, not
> compute-bound. The FLOPs row understates the real cost.
```

### Detailed Steps

1. **Identify the overhead type.** For any architecture idea, compute both:
   - FLOPs overhead (compute cost per token)
   - TPOT overhead (wall-clock latency per output token)

2. **Check for divergence.** If TPOT overhead is more than 5x the FLOPs overhead percentage, the idea is latency-dominated, not compute-dominated.

3. **Surface the dominant metric in the exec summary table.** The TPOT row must:
   - Be bolded
   - Include a warning callout below the table explaining why it dominates
   - Appear in the table itself (not just referenced to a later section)

4. **Never show only FLOPs when TPOT is the binding constraint.** Ideas that add sequential passes (AR loops, iterative refinement, multi-step decoding) are always TPOT-dominated because each pass is memory-bandwidth-bound during inference.

5. **Explain the mechanism.** The warning callout should state why FLOPs understates the cost — typically because each sequential pass pays the full memory-bandwidth cost of loading model weights, and modern LLM inference is memory-bandwidth-bound, not compute-bound.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Exec summary with FLOPs-only overhead row | Showed +0.18% FLOPs overhead in exec summary table; TPOT multiplier buried in section 6 | Creates misleading first impression that the idea is nearly free; reader who skims only the exec summary concludes overhead is negligible | The exec summary is the most-read section — it must contain the most important cost metric, even if unfavorable |
| TPOT mentioned in prose below table but not in the table itself | Added a sentence after the table mentioning TPOT | Readers scan the table, not the prose; the table is the "contract" of the exec summary | The dominant overhead metric must be a row in the table, not prose commentary |

## Results & Parameters

### Decision rule

```
IF idea introduces sequential passes (W > 1) per output token:
  TPOT_overhead = W × (1.0 to 2.5) × baseline_TPOT
  FLOPs_overhead = small (shared weights, tiny extra params)

  → TPOT row is the most important row in exec summary
  → Bold the TPOT row
  → Add warning callout explaining the divergence
```

### Ideas where this rule applies

- **In-architecture AR loops** (e.g., research_6_1): W sequential passes per token, each paying full weight-load cost
- **Iterative refinement decoders**: Multiple forward passes to refine each output token
- **Diffusion-based text decoders**: N denoising steps per token, each a full forward pass
- **Speculative decoding (draft model overhead)**: Draft model adds sequential latency even when FLOPs are small

### Ideas where this rule does NOT apply

- Ideas that only add parameters (e.g., wider FFN, more attention heads) — FLOPs and TPOT scale together
- Ideas that reduce latency (e.g., KV cache compression, quantization) — no overhead to disclose
- Ideas that add parallel computation (e.g., mixture of experts routing) — FLOPs may increase but TPOT stays flat

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas corpus | Quality remediation of research_6_1_inarch_ar_loop.md | Apr 2026 — exec summary was missing TPOT row; FLOPs showed +0.18% while TPOT was W x 1.5-2.5x; added TPOT row with warning callout |
