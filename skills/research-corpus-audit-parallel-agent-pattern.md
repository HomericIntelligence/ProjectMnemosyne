---
name: research-corpus-audit-parallel-agent-pattern
description: "Strict 10-dimension quality audit of AI architecture research corpora using parallel agent delegation. Use when: (1) auditing a large set of research/summary docs for structural compliance, (2) enforcing citation standards and TPOT framing conventions across a corpus, (3) grading research output with file:line evidence."
category: architecture
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [research, audit, corpus, tpot, citation, parallel-agents, myrmidon]
---

# Research Corpus Audit — Parallel Agent Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Strict evidence-based quality audit of 68-file AI architecture research corpus across 10 dimensions |
| **Outcome** | Successful — all 10 dimensions graded with file:line evidence; 3 structural issues identified and fixed; overall grade raised from B to A |
| **Verification** | verified-local |

## When to Use

- Auditing a set of research summary files for structural compliance (TTFT/TPOT rows, section headers, baseline splits)
- Enforcing citation standards (`[Author et al., Year] — p.N, §X.Y` or `[derived from first principles]`) across a large corpus
- Grading research output where every claim above F must cite a specific file:line
- Running parallel quality checks across 30+ files without bloating main context

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
   | A (Haiku OK) | D1, D3, D4, D7 | Grep entire corpus for presence strings: `Baseline A1`, `Baseline A2`, `Baseline B`, `TTFT`, `TPOT`, `Accuracy`. Return per-file miss list. |
   | B (Sonnet) | D2 | Read 5 seeded summary files. For each, find first 3 numeric values in comparison tables; verify citation block or first-principles marker. Report 15/15 tally. |
   | C (Sonnet) | D5, D6 | Read 5 targeted summaries for TPOT direction. Read priority_ranking.md; pick 5 EXISTS/NOVEL verdicts; verify Prior Art Gap names papers. |
   | D (Sonnet) | D8, D9, D10 | Read cross_reference_matrix.md (count IDs, synergies, conflicts), priority_ranking.md (count ranked ideas, verify rank-1), implementation_spec_phase1.md (4 numeric cross-checks vs source summaries). |

3. **Wave 2 — Synthesize:** Assemble per-dimension blocks (grade + evidence + issues + justification). Apply structural-F cap: if D3 or D10 = F, overall cannot exceed C. Render summary table. Pick top-3 remediation issues.

4. **Fix identified issues** by direct file edits.

5. **Verify fixes** with targeted greps confirming old patterns gone and new patterns present.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single-agent corpus read | Reading all 68+ files in main context for a comprehensive audit | Context bloat; impractical at scale | Use parallel agents; each reads a subset; synthesize results in main context |
| Narrative TPOT section | Using `## TPOT Impact Analysis` prose section instead of standard table rows | Invisible to corpus-wide grep; fails D4 audit automatically | TTFT and TPOT MUST appear as explicit `| TTFT (8K prompt) |` and `| TPOT (batch=1) |` rows in each comparison table |
| `↑ negligible` for zero-overhead ideas | Using `↑ negligible` in TPOT cells for ideas with < 0.1% overhead | Corpus convention requires `≈ ref` for true no-overhead ideas; `↑` implies a real compute addition | TPOT direction: `↑` = real overhead, `≈ ref` = negligible/zero, `↓` = improvement |
| Wrong section header | Using `## Quality Tradeoff Evidence` instead of `## Accuracy / Quality Tradeoff` | D7 grep for "Accuracy" missed the section entirely | Section header must match corpus standard exactly: `## Accuracy / Quality Tradeoff` |

## Results & Parameters

### Corpus conventions (must match exactly for audit to pass)

```
# Required comparison table structure (per baseline A1/A2/B):
| Metric | Baseline | This Idea | Change | Notes |
|--------|----------|-----------|--------|-------|
| TTFT (8K prompt) | ref | ... | ... | [citation or first-principles] |
| TPOT (batch=1) | ref | ... | ↑/↓/≈ ref | [citation or first-principles] |

# Required section headers:
## Benefits vs Baseline A1 (Qwen3.5-27B Hybrid)
## Benefits vs Baseline A2 (Qwen3-32B Dense)
## Benefits vs Baseline B (Qwen3.5-397B-A17B MoE)
## Accuracy / Quality Tradeoff

# TPOT direction conventions:
↑          = real compute addition (e.g., 3.4 Recursive Internal State, 5.6 Double Attention)
≈ ref      = negligible / zero overhead (e.g., 3.8 Trainable Activation, 4.4 Skip List Layers)
↓          = improvement (e.g., 5.1 TurboQuant, 5.4 Linked Attention)

# Citation standard:
[Author et al., Year] — p.N, §X.Y "Section Heading"
[derived from first principles — no direct experimental citation]
```

### Grading thresholds

```
D2 Citation: A=15/15, B=12-14/15, C=9-11/15, F<9/15
D3 Baseline: A=all 34 have A1+A2+B, F=any file missing BOTH A1 AND A2, C=1-3 missing one
D4 TTFT/TPOT: A=all 34 have both, C=1-3 missing one, F=any missing both
D5 Overhead: A=all 5 pass, F=any of 3.4/4.6/5.6 shows TPOT decreasing
D6 Novelty: A=5/5 paper-specific, C=3/5
D7 Accuracy section: A=all 34 have section, C=1-3 missing
D8 Matrix: A=34×34 + synergy≥10 + conflict≥3, C=≥30 ideas covered, F<30
D9 Ranking: A=34 ranked with citations, C≥28, F<25
D10 Spec: A=all 4 cross-checks pass, C=3/4, F=any fabricated number

Structural cap: D3=F OR D10=F → overall capped at C
```

### Audit agent prompts (key instructions)

Each agent prompt must include:
1. Dimension criteria verbatim with grade thresholds
2. "Start at F; raise only with file:line evidence. No 'probably fine.'"
3. Return format: `[file:line] → [finding] → [PASS/FAIL]`
4. Response length cap (~300 words per dimension)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas corpus | 34 ideas, 68 files, 5 artifacts | Audit Apr 2026 — found D4/D5/D7 issues in summary_5_3 and summary_3_8; all fixed |
