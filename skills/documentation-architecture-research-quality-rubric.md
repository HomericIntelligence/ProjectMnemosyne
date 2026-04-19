---
name: documentation-architecture-research-quality-rubric
description: "6-dimension weighted rubric for auditing AI architecture research documents, with canonical baseline geometry for LLM-scale proposals. Use when: (1) grading research docs for structural compliance, citations, baseline accuracy, TTFT/TPOT tables, TPOT direction honesty, and novelty verdicts, (2) performing corpus-scale quality audits on AI architecture proposals, (3) checking for the A2 KV@32K error (68 GB vs correct 8.59 GB), (4) enforcing D5 TPOT honesty rules for sequential-pass mechanisms, (5) verifying D6 novelty verdict format."
category: documentation
date: 2026-04-18
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [rubric, grading, research-docs, tpot, novelty-verdict, baseline-geometry, kv-cache, citation, architecture-research, audit, d1-d6]
---

# AI Architecture Research Document Quality Rubric (6 Dimensions)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-18 |
| **Objective** | Provide a weighted rubric for grading AI architecture research documents across 6 dimensions, plus canonical baseline geometry for LLM-scale proposals |
| **Outcome** | Verified — rubric applied to 39 documents; all passed after remediation |
| **Verification** | verified-local |

## When to Use

- Auditing AI architecture research documents for structural and content quality
- Grading research proposals against the standard 6-dimension rubric
- Checking for the common A2 KV@32K error (68 GB vs correct 8.59 GB)
- Enforcing TPOT direction honesty for sequential-pass mechanisms
- Verifying novelty verdict presence and canonical format
- Performing corpus-scale quality sweeps (use Myrmidon swarm — see below)

## Verified Workflow

### Quick Reference

```
Weighted score = D1×25 + D2×20 + D3×15 + D4×15 + D5×15 + D6×10
Bands:  A≥90  B≥80  C≥70  D≥60  F<60
GO = all dims ≥ B  |  WATCH = any dim < B  |  NO-GO = weighted < 60
```

### The 6 Dimensions

| Dim | Name | Weight | Grade A Criteria | Common Failure |
|-----|------|--------|-----------------|----------------|
| D1 | Structure | 25% | All sections §1–§8 in order (standard) or `## Benefits vs Baseline X` sections (thematic) | Missing §5 Risks or §6 Open Questions |
| D2 | Citations | 20% | ≥90% of paper claims have `[N]` inline + author/venue/year/arXiv in References | Named papers without `[N]` markers |
| D3 | Baselines | 15% | All 4 baselines A1/A2/B/C present with correct geometry | A2 KV@32K shown as ~68 GB instead of ~8.59 GB |
| D4 | TTFT/TPOT tables | 15% | Both metrics with Change column (↓/↑/≈) for all 4 baselines | TPOT missing for one baseline |
| D5 | TPOT direction honesty | 15% | Sequential-pass mechanisms use `↓* (⚠ upper bound, unverified)` | Clean ↓ in table contradicted by caveat in body text |
| D6 | Novelty verdict | 10% | Exactly one line in canonical format (EXISTS/PARTIAL/NOVEL) | Absent, or uses "open questions" phrasing instead |

### Grading Procedure

1. Read the document and score each dimension A/B/C/D/F (100/85/75/65/50)
2. Compute weighted score
3. Assign band and verdict (GO/WATCH/NO-GO)
4. Flag any dimension below B as a WATCH item requiring remediation

### D1 — Structure (25%)

Two valid templates:

**Standard template:**
```
§1 Idea Description → §2 Feasibility → §3 Literature Review
→ §4 Comparison Tables → §5 Risks → §6 Open Questions → §7 Appendix
```

**Thematic template:** `## Benefits vs Baseline X` sections  
(exempt from strict §1–§7 order check for D1)

Most common failures: missing §5 Risks, missing §6 Open Questions.

### D2 — Citations (20%)

Every paper claim must have:
- `[N]` inline citation marker in the text
- Corresponding entry in References with: author, venue/conference, year, arXiv ID

Failure mode: "As shown by Smith et al." without `[N]` or no References entry.

### D3 — Baselines (15%)

**Canonical baseline geometry (A1/A2/B/C):**

| Baseline | Description | H_q | H_kv | head_dim | d_model | Layers | KV@32K |
|----------|-------------|-----|------|----------|---------|--------|--------|
| A1 | 27B Hybrid (DeltaNet-style) | 16 | 4 | 256 | 5120 | 64 (16 full-attn) | **2.15 GB** |
| A2 | 32B Dense | 64 | 8 | 128 | 8192 | 64 | **8.59 GB** |
| B | 397B MoE | 64 | 8 | 128 | — | — | **≈8.59 GB** |
| C | K2 72.55B Dense | 64 | 8 | 128 | — | — | **≈8.59 GB** |

**KV formula:**
```
KV_bytes = L_full_attn × 2 × H_kv × head_dim × seq_len × 2
```

**Most common error — A2 KV@32K shown as ~68 GB:**  
Root cause: using H_q=64 (query heads) instead of H_kv=8 (KV heads) in the formula.  
Correct: `64 × 2 × 8 × 128 × 32768 × 2 = 8.59 GB` (not 68 GB).

**A1 derivation:**
```
16 layers × 2 × 4 heads × 256 dim × 32768 seq × 2 bytes = 2.15 GB
```

### D4 — TTFT/TPOT Tables (15%)

Tables must include:
- Both TTFT and TPOT metrics
- A Change column with directional arrows (↓/↑/≈) for each of the 4 baselines
- All 4 baselines covered (A1, A2, B, C)

Common failure: TPOT row missing for one or more baselines.

### D5 — TPOT Direction Honesty (15%)

**Rule:** Any mechanism requiring sequential passes must NOT use a clean ↓ in the Change column.

**Affected mechanism types:**
- AR loop (autoregressive loop)
- Diffusion decoder
- Grammar FSM with unvalidated overhead assumption
- Any mechanism where parallelism is assumed but not proven

**Required format for sequential-pass mechanisms:**
```
↓* (⚠ upper bound, unverified)
```

The `*` footnotes to an exec-summary callout stating the condition under which the improvement holds.

**Failure pattern:** Clean ↓ in the TPOT table with a caveat buried in the body text — the table and body text contradict each other.

### D6 — Novelty Verdict (10%)

**Canonical format (exactly one line, one of three forms):**

```
**Novelty verdict: EXISTS — [one-line rationale with named prior art and arXiv/venue].**
**Novelty verdict: PARTIAL — [what exists vs. what combination is novel].**
**Novelty verdict: NOVEL — [why no prior art covers this].**
```

**Rules:**
- Must be bold, starts with `**Novelty verdict:`
- Must use exactly one of EXISTS / PARTIAL / NOVEL
- Must include a rationale (not just the verdict word)
- Named prior art should include arXiv ID or venue when citing EXISTS/PARTIAL
- Must NOT use "open questions" phrasing as a substitute

### Corpus-Scale Auditing with Myrmidon Swarm

For 39+ file corpora, partition files across 6 agents by file-number range:

| Agent | File range | Example |
|-------|-----------|---------|
| G1 | Files 1.x | research_1_*.md |
| G2 | Files 2.x–3.x | research_2_*.md, research_3_*.md |
| G3 | Files 4.x | research_4_*.md |
| G4 | Files 5.x | research_5_*.md |
| G5 | Files 6.x (first half) | research_6_1 – 6_3 |
| G6 | Files 6.x (second half) | research_6_4 – 6_7 |

Each agent returns per-file scorecards (D1–D6 grades + weighted score + verdict).  
Main context aggregates into corpus scoreboard and flags all WATCH/NO-GO files for remediation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single-agent full corpus | One agent reads all 39 files sequentially | Context overflow; early files forgotten by end | Partition across 6 agents by file range |
| Implicit TPOT direction | Leaving TPOT direction to reader interpretation | Reviewers miss the sequential-pass caveat | Require explicit `↓*` notation with footnote |
| Inline novelty verdict | Embedding verdict in prose conclusion | Hard to scan; often omitted on revision | Require standalone bold line in canonical format |
| Using H_q for KV formula | Computing A2 KV with 64 query heads | Produces ~68 GB instead of correct 8.59 GB | Always use H_kv (KV heads) in KV formula |

## Results & Parameters

### Scorecard Template (per document)

```markdown
## Scorecard: <doc-name>

| Dim | Name | Raw Grade | Score | Weighted |
|-----|------|-----------|-------|---------|
| D1 | Structure | A | 100 | 25.0 |
| D2 | Citations | B | 85 | 17.0 |
| D3 | Baselines | A | 100 | 15.0 |
| D4 | TTFT/TPOT tables | A | 100 | 15.0 |
| D5 | TPOT direction | A | 100 | 15.0 |
| D6 | Novelty verdict | A | 100 | 10.0 |
| **Total** | | | | **97.0** |

**Band:** A | **Verdict:** GO
```

### Grade Conversion

| Letter | Numeric |
|--------|---------|
| A | 100 |
| B | 85 |
| C | 75 |
| D | 65 |
| F | 50 |

### Remediation Priority Order

When fixing documents with multiple failures:
1. D6 (novelty verdict) — fastest to add, highest signal-to-effort
2. D3 (baseline geometry) — correct the A2 KV@32K number
3. D5 (TPOT honesty) — add `*` and footnote for sequential-pass mechanisms
4. D1 (structure) — add missing §5/§6 sections
5. D4 (TTFT/TPOT tables) — fill missing rows
6. D2 (citations) — add `[N]` markers and References entries (most labor-intensive)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | Applied to 39 AI architecture research documents; all passed after remediation | Session 2026-04-18 |
