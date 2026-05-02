---
name: citation-verification-arxiv-abstract-fetch
description: "Verify every numeric claim in a corpus citation against the cited paper's arXiv abstract via parallel WebFetch agents. Use when: (1) a research corpus or technical doc makes numeric claims attributed to specific arXiv papers, (2) pattern-based scrubs have declared the corpus clean but no claim-to-source check has run, (3) the corpus contains post-knowledge-cutoff arXiv IDs where you must distinguish 'fabricated paper' from 'real paper, misquoted', (4) the corpus has blanket 'UNVERIFIED' flags that may be over-cautious, (5) a pre-release citation-hygiene gate before publication."
category: documentation
date: 2026-04-21
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [citation, verification, arxiv, webfetch, primary-source, fabrication-detection, parallel-agents, research-corpus]
---

# Citation Verification via arXiv Abstract WebFetch

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-20 |
| **Objective** | Verify every numeric claim in a corpus citation (percentage, ratio, PPL, bytes, accuracy points, speedup multiplier) against the cited paper's actual arXiv abstract, using parallel WebFetch agents, so fabricated ranges, swapped numbers, reversed polarity, and paper-body-figures-quoted-as-abstract are detected before publication. |
| **Outcome** | Successful on ArchIdeas research corpus (39 files, ~60 numeric citations checked by 6 parallel agents): surfaced 6 HIGH-severity fabrications (including fabricated range "2.9–4.1×" when abstract said "~3×"; swapped Quest self-attn vs end-to-end speedups; wrong compute-savings figure for GateSkip; headline understating a Nemotron-Flash qualifier; wrong PV-Tuning author list; truncated paper title) and ~17 MEDIUM over-specifications of paper-body figures as abstract quotes. All cited papers were real; the fabrications were in how the corpus quoted them. No text pattern catches this — only direct primary-source verification does. |
| **Verification** | verified-local (6 parallel agents, 30 WebFetch calls each, run end-to-end on ArchIdeas corpus 2026-04-20; no external CI). |

## When to Use

- Research corpus or technical doc makes numeric claims attributed to specific arXiv papers, and you need those claims to survive reviewer scrutiny.
- Pattern-based scrubs (literal-phrase, semantic-judgment, frontmatter, etc.) have declared the corpus clean — but no claim-to-source check has run yet. Pattern scrubs can never detect a misquote of a real paper.
- Corpus contains post-knowledge-cutoff arXiv IDs (for Claude's January 2026 cutoff, that is `arXiv:26XX.XXXXX` and later). You must distinguish "this paper doesn't exist" from "this paper exists and the corpus misquoted it"; blanket "UNVERIFIED" flags collapse both cases.
- Corpus has legacy blanket "UNVERIFIED" / "POST-CUTOFF" flags that may be over-cautious. The flags should be replaced with abstract-grounded specific language (verified claim with exact numbers, or `[per Table X, §Y of paper body]` annotation), not left as blanket hedges.
- Pre-release / pre-publication final citation-hygiene gate, alongside structural scrubs.

## Verified Workflow

### Quick Reference

```python
# 1. Partition corpus into 6 non-overlapping file groups (~6-7 files per agent).
# 2. Launch 6 parallel verification agents in a single message.
Agent(
    subagent_type="general-purpose",
    description="Verify citations group N (files ...)",
    prompt="""You are a ruthless citation verifier for <corpus path>.

Your assigned files:
  - file_a.md
  - file_b.md
  - ... (~6-7 files, non-overlapping with other agents)

Do NOT touch any other files.

## Mission
For each assigned file, find every citation that makes a SPECIFIC NUMERIC CLAIM
(percentage, ratio, bytes, tokens, PPL, speedup, accuracy points) attributed to
a named paper with an arXiv ID. For each, WebFetch https://arxiv.org/abs/<ID>
and verify:
  (1) Paper exists at that arXiv ID
  (2) Title and authors in corpus match the abstract page
  (3) The specific numeric claim is supported by the abstract
  (4) Direction/polarity is not reversed (improvement vs degradation)
  (5) Ranges are not fabricated — if corpus says '2.9-4.1×' and abstract
      says '~3×', that is fabricated precision.

Skip bibliography-completeness audits. Focus only on body numeric claims.
Skip pre-2024 foundational papers (Transformer, Mamba, LoRA, RoPE) unless
the claim is surprising.

## WebFetch prompt template
url: https://arxiv.org/abs/<ID>
prompt: 'Return exact title, authors, submission date, and abstract verbatim.
Quote any numeric claim matching <specific claim from corpus>.
If the ID does not resolve, say so explicitly.'

## Report format
Per issue: File:line, Corpus text (verbatim), Cited paper (arXiv ID + title),
Abstract says (verbatim), Discrepancy (fabricated / swapped / polarity /
misattribution), Recommended fix (exact replacement text).

## Constraints
- READ-ONLY. Do not edit files. Just report.
- Budget: up to 30 WebFetch calls per agent.
- Prioritize executive summaries, §4 Technical Analysis, §8 Accuracy /
  Quality Tradeoff, and derivation-tag-adjacent citations.
- Concise report; end with tally (N checked, M verified OK, K flagged).
""",
    run_in_background=True,
)
```

### Detailed Steps

1. **Enumerate** every citation with a specific numeric claim. Use `grep -n 'arXiv:[0-9]{4}\.[0-9]{4,5}' <corpus glob>` to find citations, then filter for those adjacent to specific numbers (%, ×, PPL, GB, tokens, accuracy points).

2. **Partition** the corpus into 6 non-overlapping file groups, sized to respect the ~30-WebFetch-call budget per agent (~6-7 files each works for typical research docs with 5-10 numeric citations per file).

3. **Dispatch 6 parallel agents** in a single message (concurrent execution). Each gets `subagent_type: "general-purpose"`, an explicit non-overlapping file list, and the rubric above. Use `run_in_background: true` so the main conversation is not blocked.

4. **Per-citation verification** (inside each agent): WebFetch `https://arxiv.org/abs/<ID>` with a prompt asking for title, authors, submission date, abstract verbatim, and the specific claim you expect to see. The abstract page is reliable ground truth for title/authors/date; for numeric claims, it is ground truth only for claims that actually appear in the abstract — claims from paper body tables are not verifiable from arXiv abstract pages alone (they may still be correct; the remedy is annotation, not deletion).

5. **Verify five dimensions** per citation:
   (a) paper exists at that arXiv ID,
   (b) title/authors match the corpus,
   (c) the numeric claim is supported by the abstract,
   (d) direction/polarity is correct (improvement vs degradation),
   (e) ranges are not fabricated precision.

6. **Apply remedies** based on finding type:
   - **Body-level number is correct but not in abstract** → annotate `[per Table X / §Y of paper body]` rather than implying abstract support. This is the most common finding.
   - **Number is fabricated or polarity-reversed** → replace with the abstract's actual claim, verbatim where possible.
   - **Author list or paper title is wrong** → correct from the arXiv metadata.
   - **Blanket UNVERIFIED flag on a real paper** → replace with verified abstract-grounded language and remove the flag.

7. **Re-run a final sweep** after remediation to confirm no residual fabricated claims. Pattern scrubs can never catch this class, so the verification pass itself is the only gate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding `[post-cutoff, unverified]` flags as a shortcut on every post-knowledge-cutoff arXiv ID | Before any WebFetch check, flagged 37 `arXiv:26XX.XXXXX` citations with blanket "contents unverified" markers, assuming post-knowledge-cutoff IDs might be hallucinated | Subsequent WebFetch verification showed all 37 IDs resolved to real papers with matching titles and authors. The blanket flag was the lazy answer; it obscured which citations actually had verification problems and which were simply "recent". | The flag is not a substitute for verification. Post-cutoff-ness tells you nothing about whether the paper exists or whether the corpus quoted it correctly. Fetch the abstract; then decide whether to flag a specific claim or not. Replace blanket flags with abstract-grounded specific language. |
| Trusting existing blanket `UNVERIFIED` / `POST-CUTOFF` flags in the corpus | Several files in the corpus carried legacy flags from earlier sessions ("**POST-CUTOFF (March 2026) — UNVERIFIED. Use as directional pointer only.**"). Initial instinct was to leave them as-is since the legacy authors presumably knew something. | Verification showed the flagged papers were real and in many cases the specific numeric claims were in the abstract. The flags were over-cautious relics; leaving them reduced the corpus's credibility for no real safety gain. | Treat existing blanket flags as hypotheses requiring the same verification. If the paper resolves and the claim is supported by the abstract, the flag should be replaced with specific abstract-grounded language. If the claim is paper-body, annotate `[per Table X, §Y]`. Don't let legacy caution propagate unchallenged. |
| Attempting to verify every bibliography entry | One agent tried to verify the full bibliography of an assigned file (30+ citations including foundational pre-2024 papers like Mamba, LoRA, Transformer) | Exhausted the 30-WebFetch-call budget before reaching the highest-risk body numeric claims. Bibliography completeness is a separate audit dimension and doesn't benefit from abstract-level checks for well-known foundational papers. | Focus verification on body numeric claims. Explicitly skip pre-2024 well-known foundational papers (Transformer, Mamba, LoRA, RoPE, MoE foundational papers) unless the corpus makes a surprising claim about them. Prioritize Executive Summary, §4 Technical Analysis, §8 Accuracy / Quality Tradeoff, and derivation-tag-adjacent citations. |
| Searching for a grep pattern that flags fabricated numeric claims | Attempted to extend the pattern-based scrub pipeline with regexes that might catch "too-precise ranges" or "numbers that don't appear in cited abstracts" | No text pattern can distinguish a fabricated range ("2.9–4.1×") from a real one — both look like legitimate content. A pattern also cannot tell whether a number attributed to a paper actually appears in that paper. Reversed polarity ("+17% degradation" when the paper's own method is the improvement direction) survives any text-only scrub. | Citation fabrication is a structurally different hazard class from text residue. It cannot be caught by regex — only by direct primary-source verification. Any corpus that relies on cited papers for load-bearing numeric claims needs this check as a separate gate from text scrubs. |

## Results & Parameters

### Defect sub-classes this technique catches

All examples below are from the ArchIdeas corpus verification pass, 2026-04-20, on papers with real resolving arXiv IDs. The pattern in each case: the cited paper is real, the cited title/authors are approximately right, but the specific numeric claim the corpus makes is either absent from the abstract, fabricated in precision, reversed in direction, or attributed to the wrong source location.

| # | Defect | Concrete example | Remedy |
| --- | -------- | ------------------ | -------- |
| 1 | **Fabricated numeric range** — corpus specifies a range where the abstract only gives a single approximate value | `arXiv:2604.11035` (I-DLM): corpus said "2.9–4.1× throughput at high concurrency"; abstract says "about 3× higher throughput than prior state-of-the-art DLMs" | Replace fabricated range with abstract's exact phrasing; if corpus needs precision, sourcing must come from paper-body tables with explicit `[per Table X]` citation |
| 2 | **Swapped numbers** — two legitimate numbers from the abstract assigned to each other's roles | `arXiv:2406.10774` (Quest): corpus said "Up to 7.03× self-attention speedup, 2.23× end-to-end speedup"; abstract says "up to 2.23× self-attention speedup... reduces inference latency by 7.03×" | Swap back to abstract's assignment; also grep for the bug propagating via copy-paste to other files (in ArchIdeas: same swap appeared in 2 files) |
| 3 | **Wrong compute / accuracy figure with wrong model attribution** | `arXiv:2510.13876` (GateSkip): corpus said ">90% baseline accuracy at 25% compute savings on Llama-3.1-8B"; abstract says "up to 15% compute while retaining over 90% of baseline accuracy" on long-form reasoning, and "match baseline quality near 50% savings" on instruction-tuned models (neither 25% nor Llama-3.1-8B is in the abstract) | Replace with abstract's verified figures and task qualifiers; if corpus previously attributed the number to a specific model, verify whether that attribution is in the paper body or entirely invented |
| 4 | **Headline number understating a qualifier** — corpus cites the most favorable single data point as if it applies generally | `arXiv:2511.18890` (Nemotron-Flash): corpus headline said "over 45× higher throughput than comparable Transformer baselines"; abstract specifies "18.7× / 45.6× higher throughput compared to Qwen3-1.7B / 0.6B respectively" — the 45× applies only to the smaller-model comparison | Restore the abstract's paired qualifiers; avoid headlining the most favorable single number without the comparison model |
| 5 | **Paper-body quotes labeled as abstract quotes** | `arXiv:2602.06208` (Xu et al., Emergent Low-Rank Training Dynamics): corpus cited `Abstract (arXiv:2602.06208):` with three verbatim quotes; only one is actually in the abstract, the other two are paper-body Theorem / §3 content | Re-attribute body quotes to `[paper-body §Theorem / §3]`; do not imply abstract-level support |
| 6 | **Wrong author list in bibliography entry** | `arXiv:2405.14852` (PV-Tuning): corpus listed 6 authors "Malinovskiy, Kuznedelev, Frantar, Panda, Alistarh, Hoefler"; arXiv page lists 8 authors "Malinovskii, Mazur, Ilin, Kuznedelev, Burlachenko, Yi, Alistarh, Richtárik" — completely different list with multiple name spellings corrected | Replace with arXiv's exact author list; this catches hallucinated author names that pattern scrubs cannot see |
| 7 | **Truncated paper title** | `arXiv:2601.13599`: corpus bibliography title was "Reclaiming Global Coherence in Semi-Autoregressive Diffusion"; actual title is "Diffusion In Diffusion: Reclaiming Global Coherence in Semi-Autoregressive Diffusion" — dropped prefix | Restore full title; also fixes discoverability of the paper from bibliography alone |
| 8 | **Reversed polarity / ambiguous framing** — the numbers are right but the direction or causality is muddled | `arXiv:2601.13599` (same paper): corpus said "+17% PPL degradation" from the paper; the paper's own proposed method in fact reduces PPL from 25.7 to 21.9. Corpus framing was directionally defensible (plain block-diffusion vs draft-then-refine is a +17.4% gap) but ambiguous without context | Rewrite to state the comparison explicitly: "plain semi-AR block-diffusion PPL is 25.7 vs 21.9 for draft-then-refine global bidirectional (+17.4% gap under semi-AR vs bidirectional refinement on OpenWebText)"; preserve direction and source semantics |

### WebFetch prompt template

Copy-paste verbatim into the per-citation verification step:

```text
url: https://arxiv.org/abs/<ID>
prompt:
  Return the paper's: (1) exact title, (2) authors, (3) submission date,
  (4) abstract verbatim, (5) any explicit numeric claim matching
  <specific claim from corpus — e.g., "2.9-4.1× throughput", "+17% PPL",
  "25% compute savings on Llama-3.1-8B">. Quote verbatim from the
  abstract. If the arXiv ID does not resolve to a real paper, say so
  explicitly.
```

### Parallel-agent partition pattern

For a corpus with N files and average C numeric citations per file, dispatch `ceil(N / 7)` agents with `max(30, 2*C)` WebFetch call budget each. Each agent gets a non-overlapping file list; all agents launch in a single message for true parallel execution:

```text
Group 1 (agent A): files 1_1 .. 1_7
Group 2 (agent B): files 2_1, 2_2, 3_1 .. 3_4
Group 3 (agent C): files 3_5 .. 3_8, 4_1, 4_2
Group 4 (agent D): files 4_3 .. 4_7, 5_1
Group 5 (agent E): files 5_2 .. 5_7
Group 6 (agent F): files 5_8 .. 5_10, 6_1, 6_2, 6_4, 6_5
```

(Sizing from ArchIdeas corpus: 39 files, ~60 load-bearing body numeric citations, ~10 min wall-clock per agent with 25-30 WebFetch calls each.)

### Report tally from verified execution

| Severity | Count | Example finding |
| ---------- | ------- | ----------------- |
| HIGH | 6 | Fabricated range (I-DLM 2.9-4.1×), swapped numbers (Quest), wrong model/percentage (GateSkip), understated headline (Nemotron-Flash), paper-body quoted as abstract, missing paper-body attribution for load-bearing claim |
| MEDIUM | ~17 | Over-specification of paper-body figures as abstract quotes; specific model/task qualifiers not in abstract (SwitchHead, BASED, NSA, Looped Transformers, CoLA, FP6-LLM, Fast-dLLM v2, Nguyen & Lin, CSV-Decode, etc.) |
| LOW | ~15 | Minor venue-label drift, author-list typos, title truncation, body-table numbers needing `[per Table X]` annotation |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas research corpus | Pre-release hunt-the-next-class audit, 2026-04-20; 39 research_*.md files + SHARED_PRELUDE.md; 6 parallel verification agents; ~60 body numeric citations checked | Surfaced all 8 defect sub-classes above; corpus remediated in a single commit. Lessons integrated into `documentation-corpus-myrmidon-parallel-remediation` v1.6.0 as Pass 7 (this skill is the deep-dive on that pass). |
