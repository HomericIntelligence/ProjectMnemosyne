---
name: research-corpus-audit-parallel-agent-pattern
description: "Strict 10-dimension quality audit of AI architecture research corpora using parallel agent delegation. Use when: (1) auditing a large set of research/summary docs for structural compliance, (2) enforcing citation standards and TPOT framing conventions across a corpus, (3) grading research output with file:line evidence, (4) reviewing individual idea research docs for KV cache / quantization numerical correctness."
category: architecture
date: 2026-04-17
version: "1.3.0"
user-invocable: false
verification: verified-local
history: research-corpus-audit-parallel-agent-pattern.history
tags: [research, audit, corpus, tpot, citation, parallel-agents, myrmidon, kv-cache, quantization, remediation, wave-based, terminology-drift]
---

# Research Corpus Audit — Parallel Agent Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-17 |
| **Objective** | Strict evidence-based quality audit of 68-file AI architecture research corpus across 10 dimensions; extended to per-idea numerical correctness review for KV cache quantization papers |
| **Outcome** | Successful — all 10 dimensions graded with file:line evidence; 3 structural issues identified and fixed; overall grade raised from B to A. Per-idea review of TurboQuant (5.1) found 2 critical inherited errors and 3 moderate issues. |
| **Verification** | verified-local |
| **History** | [changelog](./research-corpus-audit-parallel-agent-pattern.history) |

## When to Use

- Auditing a set of research summary files for structural compliance (TTFT/TPOT rows, section headers, baseline splits)
- Enforcing citation standards (`[Author et al., Year] — p.N, §X.Y` or `[derived from first principles]`) across a large corpus
- Grading research output where every claim above F must cite a specific file:line
- Running parallel quality checks across 30+ files without bloating main context
- Deep per-idea review of KV cache quantization research docs (context length mislabeling, head_dim errors, TPOT overstatement)
- Running a remediation pass after audit — fixing arithmetic errors, terminology drift, or missing structural sections across many files in parallel
- Capturing what failed during an in-flight remediation so future sessions don't repeat the same mistakes

## Verified Workflow

### Quick Reference

```bash
# Wave 1: dispatch 4 parallel agents for the 10 dimensions
# Group by tool type: grep-heavy vs read-heavy
# Agent A: D1(completeness) + D3(baseline split) + D4(TTFT/TPOT) + D7(accuracy section) — grep-driven
# Agent B: D2(citation spot-check) — read 5 files, check 15 numeric values
# Agent C: D5(TPOT direction) + D6(novelty verdicts) — targeted reads
# Agent D: D8(matrix) + D9(ranking) + D10(spec accuracy) — read 4 artifacts

# Wave 2: synthesize in main context, apply structural-F cap rule
# D3=F or D10=F caps overall at C regardless of other grades
```

### Detailed Steps

1. **Pre-flight (main context):** `ls` the corpus directory, count `research_*.md` and `summary_*.md` files. Note any stray files outside the expected naming pattern.

2. **Wave 1 — 4 parallel agents (single message, 4 tool calls):**

   | Agent | Dimensions | Strategy |
   |-------|-----------|----------|
   | A (Haiku OK) | D1, D3, D4, D7 | Grep entire corpus for presence strings: `Baseline A1`, `Baseline A2`, `Baseline B`, `Baseline C`, `TTFT`, `TPOT`, `Accuracy`. Return per-file miss list. |
   | B (Sonnet) | D2 | Read 5 seeded summary files. For each, find first 3 numeric values in comparison tables; verify citation block or first-principles marker. Report 15/15 tally. |
   | C (Sonnet) | D5, D6 | Read 5 targeted summaries for TPOT direction. Read priority_ranking.md; pick 5 EXISTS/NOVEL verdicts; verify Prior Art Gap names papers. |
   | D (Sonnet) | D8, D9, D10 | Read cross_reference_matrix.md (count IDs, synergies, conflicts), priority_ranking.md (count ranked ideas, verify rank-1), implementation_spec_phase1.md (4 numeric cross-checks vs source summaries). |

3. **Wave 2 — Synthesize:** Assemble per-dimension blocks (grade + evidence + issues + justification). Apply structural-F cap: if D3 or D10 = F, overall cannot exceed C. Render summary table. Pick top-3 remediation issues.

4. **Fix identified issues** by direct file edits.

5. **Verify fixes** with targeted greps confirming old patterns gone and new patterns present.

## Remediation Workflow (Post-Audit)

### Quick Reference — Parallel Fix Agents

```bash
# Two-pass remediation (run passes sequentially — not simultaneously):
# Pass 1: arithmetic + framing fixes (Critical + Major issues)
# Pass 2: structural + systemic fixes (section additions, terminology, citation format)

# Split file list explicitly between parallel agents — never assign same file to two agents
# Use isolation: "worktree" per agent so edits land in a clean copy
```

### Wave-Based Parallel Fix Agents

After an audit identifies issues, dispatch fix agents in waves. Key rules:

1. **Group fixes by file overlap.** Never assign the same file to two parallel agents — merge conflicts are guaranteed. When fixing systemic issues across many files (e.g., terminology drift across 29 files), split the file list explicitly between agents.

2. **Two-pass fix pattern.** First pass: arithmetic and framing fixes (Critical + Major severity issues). Second pass: structural and systemic fixes (section additions, terminology normalization, citation format). Running both passes simultaneously causes conflicts — run passes sequentially.

3. **Isolation per agent.** Use `isolation: "worktree"` on each fix agent so edits land in a clean copy. Each agent reads its assigned files, makes targeted edits, and returns. The main context merges results.

4. **Background agents for long batches — prefer foreground.** Background agents (`run_in_background: true`) have a higher failure rate on long-running tasks (~2M tokens / 77 tool uses observed failure point with "API Error: ConnectionRefused"). Prefer foreground agents with a clear scope, or split large batches into smaller foreground agents.

### Terminology Drift Fix (S-03 pattern)

When fixing a term that refers to a baseline layer in some contexts but appears in paper titles in others:

- **Replace** when the term refers to the A1/B architecture component (a model name being used as a label)
- **Preserve** when the term appears in a paper title, citation, verbatim quote from another paper's search space enumeration, or the paper's own abstract
- Use `replace_all: false` in Edit calls — review each occurrence individually

### Structural Section Addition (D5 pattern)

When appending new sections to files:

- Append after the last numbered section body
- Place **before** a `## Citations` section if one exists (not after it)
- For files using the numbered section template (G1), the new appended section gets no number
- Do NOT renumber existing sections

### Exec-Summary vs Body Inconsistency

When an executive summary value conflicts with a detailed body derivation, the body derivation is almost always correct. The summary was written first (or copied) and wasn't updated when the detailed calculation was refined. Fix the summary to match the body — not the reverse.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single-agent corpus read | Reading all 68+ files in main context for a comprehensive audit | Context bloat; impractical at scale | Use parallel agents; each reads a subset; synthesize results in main context |
| Narrative TPOT section | Using `## TPOT Impact Analysis` prose section instead of standard table rows | Invisible to corpus-wide grep; fails D4 audit automatically | TTFT and TPOT MUST appear as explicit `| TTFT (8K prompt) |` and `| TPOT (batch=1) |` rows in each comparison table |
| `↑ negligible` for zero-overhead ideas | Using `↑ negligible` in TPOT cells for ideas with < 0.1% overhead | Corpus convention requires `≈ ref` for true no-overhead ideas; `↑` implies a real compute addition | TPOT direction: `↑` = real overhead, `≈ ref` = negligible/zero, `↓` = improvement |
| Wrong section header | Using `## Quality Tradeoff Evidence` instead of `## Accuracy / Quality Tradeoff` | D7 grep for "Accuracy" missed the section entirely | Section header must match corpus standard exactly: `## Accuracy / Quality Tradeoff` |
| Trust "32K ctx" label for A2 KV cache | Accepting the "32K ctx" label on KV cache figures without verifying the formula arithmetic | The 68.7 GB figure requires 262,144 tokens, not 32,768 — the label was wrong while the arithmetic used the full max context | Always re-derive: `64×2×8×128×32768×2 = 8 GB` (actual 32K), not 68.7 GB; the inherited error is context 32,768→262,144 |
| Trust FlashInfer "4x speedup" for total TPOT | Using the attention-kernel 4× figure to claim "4× TPOT improvement" for INT4 KV | FlashInfer's speedup is for the attention kernel only; TPOT also includes weight loading (~64 GB for 32B model) which is unchanged | Always compute realistic TPOT: `total_BW_before / total_BW_after = (weight_BW + KV_BW) / (weight_BW + KV_BW/4)`; for A2 at 262K: ~1.6× not 4× |
| Using `[derived from first principles]` tags for numeric claims | Added the tag to numeric table cells with no further detail | User prefers the actual arithmetic shown inline in the Notes cell | Show the full derivation chain in the Notes cell (e.g., `A×B×C×D = X bytes; TPOT = before/after = N×`) — the tag alone is not sufficient |
| Treating D7 (Accuracy section) as uniformly required | Graded D7=F because 29/39 files lacked `## Accuracy / Quality Tradeoff` | Groups 1–4 and 6.x use different section naming conventions — some use `## Quality` or embed accuracy tradeoff discussion in `## Technical Analysis` subsections | When auditing D7 on a heterogeneous corpus, also grep for `## Quality`, `## Tradeoff`, and `## Accuracy` as acceptable alternatives; strict `## Accuracy / Quality Tradeoff` header is only enforced for corpus-standard docs (groups 1–5, excluding Phase A docs) |
| Auditing group 6 docs with group 1–5 structural expectations | Counted group 6 thematic docs as missing TTFT/TPOT rows | Group 6 docs (Phase A research) use a thematic section template, not the standard 7-section numbered template | Pre-flight the audit by checking which docs follow the standard template vs thematic template; apply structural checks only to standard-template docs (see Structural Deficit Remediation Pattern above) |
| SendMessage to in-flight background agent | Tried to send a mid-flight instruction change to an already-launched background agent via SendMessage | Tool not available in this context; background agents are fire-and-forget | Cannot change instructions for an in-flight background agent. Only option: wait for completion, assess damage, launch a corrective agent afterward |
| Background agents for S-04 derivation tag addition (large batch) | Launched two `run_in_background: true` agents to add inline derivation tags across 29 files | Both failed with "API Error: Unable to connect to API (ConnectionRefused)" after ~2M tokens / 77 tool uses — background agents have higher failure rate on long-running tasks | Prefer foreground agents with clear scopes; split large batches into smaller foreground agents; avoid background agents for tasks that run >50 tool calls |
| Broadcasting wrong tag standard to background agents | Launched background agents with `[derived from first principles]` bare tag instruction; user corrected the standard mid-session to require inline arithmetic | Could not propagate correction to in-flight background agents; correction only reached agents not yet started | Finalize all standards and formats before launching agents. If user corrects a standard mid-session, abort/ignore in-flight agents and re-launch with correct instructions |
| Parallel fix agents on overlapping file sets | Dispatched two remediation agents whose file lists were not explicitly partitioned | Both agents edited some of the same files; merge produced conflicts | Always partition the file list explicitly between parallel agents — never rely on agents to "avoid" the same file organically |

## Results & Parameters

### Corpus conventions (must match exactly for audit to pass)

```
# Required comparison table structure (per baseline A1/A2/B):
| Metric | Baseline | This Idea | Change | Notes |
|--------|----------|-----------|--------|-------|
| TTFT (8K prompt) | ref | ... | ... | [citation or first-principles] |
| TPOT (batch=1) | ref | ... | ↑/↓/≈ ref | [citation or first-principles] |

# Required section headers (corpus-standard docs, groups 1–5):
## Benefits vs Baseline A1 (Qwen3.5-27B Hybrid)
## Benefits vs Baseline A2 (Qwen3-32B Dense)
## Benefits vs Baseline B (Qwen3.5-397B-A17B MoE)
## Benefits vs Baseline C (<Baseline C model name>)
## Accuracy / Quality Tradeoff

# TPOT direction conventions:
↑          = real compute addition (e.g., 3.4 Recursive Internal State, 5.6 Double Attention)
≈ ref      = negligible / zero overhead (e.g., 3.8 Trainable Activation, 4.4 Skip List Layers)
↓          = improvement (e.g., 5.1 TurboQuant, 5.4 Linked Attention)

# Citation standard:
[Author et al., Year] — p.N, §X.Y "Section Heading"
# PREFERRED for derived numeric claims — show full arithmetic inline in Notes cell:
# e.g. "total_BW_before=54+2.15=56.15 GB; after=53.71 GB; TPOT=53.71/56.15=0.956≈0.955×"
# DO NOT use bare [derived from first principles] tags without the supporting arithmetic
```

### Grading thresholds

```
D2 Citation: A=15/15, B=12-14/15, C=9-11/15, F<9/15
D3 Baseline: A=all docs have A1+A2+B+C, F=any file missing BOTH A1 AND A2, C=1-3 missing one; grep pattern `## Benefits vs Baseline A[^12]` catches A1/A2 headers — now 4 baselines expected
D4 TTFT/TPOT: A=all docs have both rows (N_docs×4 expected hits), C=1-3 missing one, F=any missing both; expected counts scale as N_docs×4 (not ×3)
D5 Overhead: A=all 5 pass, F=any of 3.4/4.6/5.6 shows TPOT decreasing
D6 Novelty: A=5/5 paper-specific, C=3/5
D7 Accuracy section: A=all 34 have section, C=1-3 missing
D8 Matrix: A=34×34 + synergy≥10 + conflict≥3, C=≥30 ideas covered, F<30
D9 Ranking: A=34 ranked with citations, C≥28, F<25
D10 Spec: A=all 4 cross-checks pass, C=3/4, F=any fabricated number

Structural cap: D3=F OR D10=F → overall capped at C
```

### Structural Deficit Remediation Pattern

Some docs (e.g., Phase A thematic research docs — groups 6.x and late-Phase-A additions like 5.9/5.10) are produced with a thematic section template and never received the standard `## Benefits vs Baseline X` + TTFT/TPOT table structure. This is a known schema variance — the content is correct but the structural layer is missing.

**Pre-flight check:** Before auditing, determine which docs use the standard 7-section numbered template vs the thematic template. Apply structural checks (D1/D3/D4/D7) only to standard-template docs. Mark thematic-template docs as `[schema-variant: Phase A thematic]` and exclude from those dimensions.

**Remediation approach (when adding structure to thematic docs):**

1. Read the existing complexity analysis sections in the doc (typically titled `## Technical Analysis`, `## Complexity`, or `## Implementation Notes`).
2. From those sections, derive the TTFT/TPOT/KV/Weight values using the canonical formula (see KV Cache Quantization Numerical Checklist above). Show full arithmetic inline in the Notes cell.
3. Insert `## Benefits vs Baseline A1`, `## Benefits vs Baseline A2`, `## Benefits vs Baseline B`, `## Benefits vs Baseline C` sections with standard tables (TTFT/TPOT/KV/Weight rows) immediately **before** the `<!-- CITATION MANIFEST -->` block.
4. Do NOT rewrite or remove existing sections — only insert the new structural sections.
5. Verify insertion with `grep -n "Benefits vs Baseline" <file>` to confirm all 4 are present.

### Audit agent prompts (key instructions)

Each agent prompt must include:
1. Dimension criteria verbatim with grade thresholds
2. "Start at F; raise only with file:line evidence. No 'probably fine.'"
3. Return format: `[file:line] → [finding] → [PASS/FAIL]`
4. Response length cap (~300 words per dimension)

### KV Cache Quantization Numerical Checklist (for per-idea review)

When reviewing a research doc about KV cache quantization (ideas referencing KIVI, KVQuant, TurboQuant, RotateKV, FireQ, etc.):

```python
# 1. ALWAYS re-derive KV cache sizes from scratch
# Formula: num_KV_layers × 2 × n_KV_heads × head_dim × seq_len × bytes_per_element
#
# Canonical baselines (from SHARED_PRELUDE.md + canonical corrections):
#   A1: 16 layers, 4 KV heads, head_dim=256 → 16×2×4×256×seq×2 bytes (BF16)
#   A2: 64 layers, 8 KV heads, head_dim=128 → 64×2×8×128×seq×2 bytes (BF16)
#   B:  15 layers, 2 KV heads, head_dim=256 → 15×2×2×256×seq×2 bytes (BF16)
#
# Common error: doc says "32K ctx" but formula uses 262144 tokens
# Check: 64×2×8×128×32768×2 = 8 GB (NOT 68.7 GB)
#        64×2×8×128×262144×2 = 68.7 GB ← this is what produces 68.7

# 2. ALWAYS compute realistic TPOT (batch=1), not just attention kernel speedup
# weight_BW = num_active_params × bytes_per_param  (BF16 = 2 bytes)
# KV_BW_before = KV_cache_bytes_at_seq_len
# KV_BW_after  = KV_cache_bytes_at_seq_len / compression_ratio
# TPOT_improvement = (weight_BW + KV_BW_before) / (weight_BW + KV_BW_after)
#
# Example — A2 at 262K context, INT4 KV:
# weight_BW  = 32B × 2 = 64 GB
# KV_BW_before = 68.7 GB
# KV_BW_after  = 17.2 GB
# Realistic TPOT = (64+68.7)/(64+17.2) = 132.7/81.2 ≈ 1.63× (NOT 4×)

# 3. Check canonical head_dim corrections
# A1 full-attention layers: canonical head_dim=256 (not 128 from older SHARED_PRELUDE)
# B GatedAttn layers: canonical 2 KV heads × head_dim=256 (product = 512, same as 4×128)
# → A1 KV cache is 2× what old-prelude says; B is unchanged (product invariant)

# 4. Check citation for "4× bandwidth reduction"
# BF16→INT4 is 4× by definition (2 bytes → 0.5 bytes); needs no experimental citation
# Do NOT cite an INT8 paper (4× vs FP32) for an INT4 vs BF16 claim
```

### Realistic TPOT Improvement Table (for reference)

| Model | Seq len | KV BW before | Weight BW | Realistic INT4 KV TPOT | Attention kernel only |
|-------|---------|-------------|----------|------------------------|----------------------|
| A1 (27B Hybrid) | 32K | ~2.0 GB | ~54 GB | ~1.03× | ~4× (kernel only) |
| A2 (32B Dense) | 32K | ~8.0 GB | ~64 GB | ~1.13× | ~4× (kernel only) |
| A2 (32B Dense) | 262K | ~68.7 GB | ~64 GB | ~1.63× | ~4× (kernel only) |
| B (397B MoE) | 32K | ~1.0 GB | ~34 GB (active) | ~1.02× | ~4× (kernel only) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas corpus | 34 ideas, 68 files, 5 artifacts | Audit Apr 2026 — found D4/D5/D7 issues in summary_5_3 and summary_3_8; all fixed |
| ArchIdeas idea 5.1 (TurboQuant) | Per-idea review with 5-agent swarm | Apr 2026 — found context length mislabel (68.7 GB at 262K labeled "32K"), A1 head_dim error, TPOT overstatement |
| ArchIdeas corpus (post Phase C/D) | 39 ideas, 4-baseline grading | Apr 2026 — D1=F (7 Phase A thematic docs missing all 4 baseline sections), D4=F (94/156 TTFT, 125/156 TPOT), D5=F (research_6_4 no TPOT rows), D7=F (10/39 have strict Accuracy header), D3/D6/D8/D9/D10=A; overall grade D; synthesis artifacts excellent, per-file structural compliance poor |
| ArchIdeas corpus remediation (post-audit) | Wave-based parallel fix agents across 39-file corpus | Apr 2026 — two-pass remediation: Pass 1 fixed arithmetic/framing (Critical + Major); Pass 2 fixed terminology drift (S-03) and section additions (D5); background agents failed at ~2M tokens; foreground agents succeeded; all fixes confirmed, no remaining bare tags |
