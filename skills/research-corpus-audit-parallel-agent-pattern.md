---
name: research-corpus-audit-parallel-agent-pattern
description: "Strict 10-dimension quality audit of AI architecture research corpora using parallel agent delegation. Use when: (1) auditing a large set of research/summary docs for structural compliance, (2) enforcing citation standards and TPOT framing conventions across a corpus, (3) grading research output with file:line evidence, (4) reviewing individual idea research docs for KV cache / quantization numerical correctness, (5) writing or reviewing numeric claims not backed by a paper (inline derivation format), (6) auditing exec summaries where FLOPs and TPOT overhead diverge."
category: architecture
date: 2026-04-18
version: "2.0.0"
user-invocable: false
verification: verified-local
history: research-corpus-audit-parallel-agent-pattern.history
tags: [research, audit, corpus, tpot, citation, parallel-agents, myrmidon, kv-cache, quantization, remediation, wave-based, terminology-drift, derivation, inline, exec-summary, overhead, honesty]
absorbed: "research-corpus-inline-derivation-standard (v1.1.0), research-corpus-exec-summary-overhead-honesty (v1.0.0) on 2026-05-03"
---

# Research Corpus Audit — Parallel Agent Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-17 |
| **Objective** | Strict evidence-based quality audit of 68-file AI architecture research corpus across 10 dimensions; extended to per-idea numerical correctness review for KV cache quantization papers; inline derivation standard; exec summary overhead honesty |
| **Outcome** | Absorbed research-corpus-inline-derivation-standard + research-corpus-exec-summary-overhead-honesty on 2026-05-03. Successful — all 10 dimensions graded with file:line evidence; 3 structural issues identified and fixed; overall grade raised from B to A. Per-idea review of TurboQuant (5.1) found 2 critical inherited errors and 3 moderate issues. |
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
- Writing a numeric value (memory size, TPOT, bandwidth, parameter count) that comes from a formula, not a cited paper
- Reviewing existing research docs for derivation tag completeness — any time you would write `[derived from first principles]` bare, show the computation instead
- Adding a Notes cell to a comparison table where the value is analytically computed
- A table has a block-level note like "All calculations derived from first principles using canonical head dimensions from SHARED_PRELUDE.md" with no per-row derivations — this is the antipattern
- Writing an executive summary comparison table for an AI architecture idea that increases per-token latency (TPOT)
- Auditing research docs where FLOPs overhead and TPOT overhead diverge by more than an order of magnitude
- Reviewing proposals for in-architecture AR loops, iterative refinement, speculative decoding variants, or diffusion-based decoders
- Any idea where the overhead is dominated by sequential passes rather than raw compute

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
   | ------- | ----------- | ---------- |
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

## Inline Derivation Standard

When writing numeric claims derived analytically (not from a paper), always show the full computation inline.

### Quick Reference

```
# Correct format — show the full computation inline:
~5 MB [derived: 512 tokens × 5120 dims × 2 bytes (BF16) = 5,242,880 bytes ≈ 5 MB]

# Wrong format — bare label gives no verifiable information:
~5 MB [derived from first principles — no direct experimental citation]

# Multi-step derivation — chain the arithmetic:
~4.10 GB [derived: W_out = V × d × 2 bytes = 250,112 × 8,192 × 2 = 4,097,835,008 bytes ≈ 4.10 GB;
           LM head fraction = 4.10/145.1 ≈ 2.83% of total model weights]

# Multi-baseline derivation (show per-baseline substitution):
**Derivation:** KV cache = L × 2 × H_kv × head_dim × s × 2 bytes (BF16).
A1: 32×2×8×128×32768×2 = 4.29 GB. A2: 64×2×8×128×32768×2 = 8.59 GB.
A3: 64×2×4×128×32768×2 = 4.29 GB. A4: 64×2×16×128×32768×2 = 17.18 GB.
```

### Detailed Steps

1. **Identify the claim type.** Is the number from a paper (→ use `[Author et al., Year] — p.N, §X.Y`)? Or is it analytically derived from known constants (→ use the inline derivation format)?

2. **Write the formula with variable substitution.** Always replace variable names with actual values so the reader can verify without looking up definitions:
   - Bad: `n_layers × 2 × n_heads × head_dim × seq_len × bytes`
   - Good: `64 layers × 2 × 8 KV heads × 128 dims × 32,768 tokens × 2 bytes (BF16)`

3. **Show the intermediate and final result.** Use `=` to chain steps:
   ```
   64 × 2 × 8 × 128 × 32768 × 2 = 8,589,934,592 bytes ≈ 8.0 GB
   ```

4. **Add a one-sentence note** (optional) when the formula measures something non-obvious:
   ```
   [derived: 64×2×8×128×32768×2 = 8.59 GB; KV cache at 32K context for A2 (32B dense, BF16)]
   ```

5. **For multi-step derivations**, chain them with a semicolon:
   ```
   [derived: weight_BW = 32B params × 2 bytes = 64 GB;
             KV_BW = 68.7 GB (at 262K ctx);
             TPOT improvement = (64+68.7)/(64+17.2) = 132.7/81.2 ≈ 1.63×;
             note: INT4 compresses KV by 4×, weight BW unchanged]
   ```

6. **For multi-baseline tables**, show each baseline's substitution explicitly (not just the formula). Use a `**Derivation:**` block before or after the table listing each baseline's parameter values and result.

7. **Placement.** In table cells, put the derivation inline after the value. In prose, put it immediately after the value in brackets. Never defer it to a footnote or endnote — the goal is on-the-spot verifiability.

### When to cite a paper instead

Use `[Author et al., Year] — p.N, §X.Y` when:
- The value comes from a measurement in an experiment (throughput, accuracy, latency)
- The value is a design choice from a specific model architecture (e.g., n_heads=8 from Qwen3-32B spec)
- The formula itself is from a paper (e.g., the KIVI quantization error bound formula)

Use `[derived: ...]` when:
- The value follows mechanically from known constants (dimensions, bytes per dtype, sequence length)
- The value is a ratio or improvement computed from two other values
- The arithmetic is straightforward enough that a reader can verify it in under 30 seconds

## Exec Summary Overhead Honesty

When an idea increases per-token latency (TPOT), the executive summary table must surface the dominant overhead metric, not just FLOPs.

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

### Ideas where exec-summary honesty rule applies

- **In-architecture AR loops** (e.g., research_6_1): W sequential passes per token, each paying full weight-load cost
- **Iterative refinement decoders**: Multiple forward passes to refine each output token
- **Diffusion-based text decoders**: N denoising steps per token, each a full forward pass
- **Speculative decoding (draft model overhead)**: Draft model adds sequential latency even when FLOPs are small

### Ideas where this rule does NOT apply

- Ideas that only add parameters (e.g., wider FFN, more attention heads) — FLOPs and TPOT scale together
- Ideas that reduce latency (e.g., KV cache compression, quantization) — no overhead to disclose
- Ideas that add parallel computation (e.g., mixture of experts routing) — FLOPs may increase but TPOT stays flat

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Single-agent corpus read | Reading all 68+ files in main context for a comprehensive audit | Context bloat; impractical at scale | Use parallel agents; each reads a subset; synthesize results in main context |
| Narrative TPOT section | Using `## TPOT Impact Analysis` prose section instead of standard table rows | Invisible to corpus-wide grep; fails D4 audit automatically | TTFT and TPOT MUST appear as explicit `TTFT (8K prompt)` and `TPOT (batch=1)` rows in each comparison table |
| `↑ negligible` for zero-overhead ideas | Using `↑ negligible` in TPOT cells for ideas with < 0.1% overhead | Corpus convention requires `≈ ref` for true no-overhead ideas; `↑` implies a real compute addition | TPOT direction: `↑` = real overhead, `≈ ref` = negligible/zero, `↓` = improvement |
| Wrong section header | Using `## Quality Tradeoff Evidence` instead of `## Accuracy / Quality Tradeoff` | D7 grep for "Accuracy" missed the section entirely | Section header must match corpus standard exactly: `## Accuracy / Quality Tradeoff` |
| Trust "32K ctx" label for A2 KV cache | Accepting the "32K ctx" label on KV cache figures without verifying the formula arithmetic | The 68.7 GB figure requires 262,144 tokens, not 32,768 — the label was wrong while the arithmetic used the full max context | Always re-derive: `64×2×8×128×32768×2 = 8 GB` (actual 32K), not 68.7 GB; the inherited error is context 32,768→262,144 |
| Trust FlashInfer "4x speedup" for total TPOT | Using the attention-kernel 4× figure to claim "4× TPOT improvement" for INT4 KV | FlashInfer's speedup is for the attention kernel only; TPOT also includes weight loading (~64 GB for 32B model) which is unchanged | Always compute realistic TPOT: `total_BW_before / total_BW_after = (weight_BW + KV_BW) / (weight_BW + KV_BW/4)`; for A2 at 262K: ~1.6× not 4× |
| Using `[derived from first principles]` tags for numeric claims | Added the tag to numeric table cells with no further detail; user rejected bare labels during 39-file audit ("bare tags are useless to a reader — they signal 'trust me' without showing the work") | User prefers the actual arithmetic shown inline in the Notes cell; bare label carries zero verifiable information | Show the full derivation chain in the Notes cell (e.g., `A×B×C×D = X bytes; TPOT = before/after = N×`) — the tag alone is not sufficient |
| `[derived from first principles — no direct experimental citation]` extended label | Extended the bare tag with an explanation of why there's no citation | Still no verifiable arithmetic; just a longer "trust me" | The explanation of why there's no citation is irrelevant — what matters is showing the derivation |
| Treating D7 (Accuracy section) as uniformly required | Graded D7=F because 29/39 files lacked `## Accuracy / Quality Tradeoff` | Groups 1–4 and 6.x use different section naming conventions — some use `## Quality` or embed accuracy tradeoff discussion in `## Technical Analysis` subsections | When auditing D7 on a heterogeneous corpus, also grep for `## Quality`, `## Tradeoff`, and `## Accuracy` as acceptable alternatives; strict `## Accuracy / Quality Tradeoff` header is only enforced for corpus-standard docs (groups 1–5, excluding Phase A docs) |
| Auditing group 6 docs with group 1–5 structural expectations | Counted group 6 thematic docs as missing TTFT/TPOT rows | Group 6 docs (Phase A research) use a thematic section template, not the standard 7-section numbered template | Pre-flight the audit by checking which docs follow the standard template vs thematic template; apply structural checks only to standard-template docs (see Structural Deficit Remediation Pattern above) |
| SendMessage to in-flight background agent | Tried to send a mid-flight instruction change to an already-launched background agent via SendMessage | Tool not available in this context; background agents are fire-and-forget | Cannot change instructions for an in-flight background agent. Only option: wait for completion, assess damage, launch a corrective agent afterward |
| Background agents for S-04 derivation tag addition (large batch) | Launched two `run_in_background: true` agents to add inline derivation tags across 29 files | Both failed with "API Error: Unable to connect to API (ConnectionRefused)" after ~2M tokens / 77 tool uses — background agents have higher failure rate on long-running tasks | Prefer foreground agents with clear scopes; split large batches into smaller foreground agents; avoid background agents for tasks that run >50 tool calls |
| Broadcasting wrong tag standard to background agents | Launched background agents with `[derived from first principles]` bare tag instruction; user corrected the standard mid-session to require inline arithmetic | Could not propagate correction to in-flight background agents; correction only reached agents not yet started | Finalize all standards and formats before launching agents. If user corrects a standard mid-session, abort/ignore in-flight agents and re-launch with correct instructions |
| Parallel fix agents on overlapping file sets | Dispatched two remediation agents whose file lists were not explicitly partitioned | Both agents edited some of the same files; merge produced conflicts | Always partition the file list explicitly between parallel agents — never rely on agents to "avoid" the same file organically |
| Treating 5.9/5.10 as standard-template docs | Audited research_5_9 and research_5_10 with standard-template expectations (numbered sections 1–8) | They use the thematic template (like Group 6); structural checks D1/D3/D4/D7 failed spuriously | Pre-flight must identify which docs are thematic-template; 7 files total use thematic template (Group 6 + 5.9/5.10). Declare schema variants in SHARED_PRELUDE.md |
| Bibliography entries without paper-internal locators | Group 5 and Group 6 files used numbered bibliography format `[N]: Author... arXiv:XXXX` with no `§X.Y` or `Table N` locators | D2 citation audit requires locators at the bibliography entry level, not just in-text prose | When a file uses numbered bibliography format, locators must be added to each entry — fetch arXiv abstract page and add the most relevant section/table locator |
| impl_spec numeric drift from source doc | `implementation_spec_phase1.md` claimed k̄_l=7 TPOT as `0.74–0.79×`; source doc `research_1_3.md` derives `0.68×` via `(k̄_l/11) × 0.88 + 0.12` | Range claims (0.74–0.79×) were not cross-checked against the exact formula in the source research doc | Always cross-check spec numeric claims against source research docs using the exact formula — range claims are especially prone to drifting from point estimates |
| Deferring arithmetic to a notes.md file | Wrote `[derived — see notes.md §3.2]` in a research doc | Reader must switch files to verify; breaks the audit flow | Inline derivations must be self-contained; the reader should never have to leave the file |
| Using variable names without substitution in derivation | Wrote `n_layers × n_heads × head_dim × seq × bytes` in a derivation tag | Reader can't verify without looking up each variable | Substitute actual values in the formula so the arithmetic is checkable on the spot |
| Block-level derivation disclaimer at table top | Wrote "All calculations derived from first principles using canonical head dimensions from SHARED_PRELUDE.md" above the table with no per-row derivations | Reader still must redo the math for each row; the block note is a collective "trust me" at table scope rather than row scope | Same rule applies at block scope: every derived value needs its own inline computation, not a shared disclaimer |
| Exec summary with FLOPs-only overhead row | Showed +0.18% FLOPs overhead in exec summary table; TPOT multiplier buried in section 6 | Creates misleading first impression that the idea is nearly free; reader who skims only the exec summary concludes overhead is negligible | The exec summary is the most-read section — it must contain the most important cost metric, even if unfavorable |
| TPOT mentioned in prose below exec summary table but not in the table itself | Added a sentence after the table mentioning TPOT | Readers scan the table, not the prose; the table is the "contract" of the exec summary | The dominant overhead metric must be a row in the table, not prose commentary |

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

### Schema Variant Declaration Pattern (for SHARED_PRELUDE.md)

When a corpus contains documents that follow different templates, declare the schema variants
explicitly in SHARED_PRELUDE.md so auditors know which structural checks apply to which files:

```markdown
## Schema Variants

This corpus uses two document templates:

**Standard template** (Groups 1–5, excluding 5.9/5.10):
- Numbered sections 1-8 under Executive Summary

**Thematic template** (Group 6 + research_5_9, research_5_10 — 7 files total):
- Unnumbered sections + per-baseline ## Benefits vs Baseline X sections

Audit dimensions D1/D3/D4/D7 apply only to standard-template docs.
Thematic-template docs verified against their own structural checklist.
```

### 4-Fix Remediation Order (for post-audit fix sessions)

When a final audit finds a small set of remaining issues (4–10 fixes), apply in this order
to minimize time and avoid blocking dependencies:

1. **Single-line numeric corrections** (fastest, no dependencies) — Fix immediately in main context
2. **Table row insertions** (fast, targeted) — Fix in main context
3. **Schema/documentation declarations** (e.g., SHARED_PRELUDE.md Schema Variants) — Fix in main context
4. **Bibliography PDF fetches** (~76+ papers) — Dispatch 4 parallel worktree agents last (one per file, never overlap file sets)

Rationale: Steps 1–3 are fast (seconds each) and unblocking. Step 4 (arXiv abstract fetches) is
the slowest and should always be parallelized and deferred until after fast fixes are confirmed.

### TTFT Row Template for KV-Cache-Only Quantization

For ideas where quantization applies only to KV cache (not weights), TTFT is always `≈ ref`
because prefill is compute-bound and KV quantization only affects decode-time KV reads:

```
| TTFT (8K prompt) | ref | ≈ ref | ≈ ref | Prefill is compute-bound at 8K; KV quantization affects decode-time KV reads only, not prefill FLOPs; attention-kernel dequant overhead <2% (§4.2) |
```

This row is baseline-independent — use `≈ ref` for all baselines (A1/A2/B/C) for these ideas.

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
| ------- | --------- | ------------- | ---------- | ------------------------ | ---------------------- |
| A1 (27B Hybrid) | 32K | ~2.0 GB | ~54 GB | ~1.03× | ~4× (kernel only) |
| A2 (32B Dense) | 32K | ~8.0 GB | ~64 GB | ~1.13× | ~4× (kernel only) |
| A2 (32B Dense) | 262K | ~68.7 GB | ~64 GB | ~1.63× | ~4× (kernel only) |
| B (397B MoE) | 32K | ~1.0 GB | ~34 GB (active) | ~1.02× | ~4× (kernel only) |

### Inline Derivation — Canonical Format

```
# Single-step derivation:
<value> [derived: <formula with values substituted> = <result>]

# Single-step with explanatory note:
<value> [derived: <formula> = <result>; <1-sentence note on what it measures>]

# Multi-step derivation:
<value> [derived: <step 1 formula> = <step 1 result>;
                  <step 2 formula using step 1 result> = <step 2 result>;
                  <optional note>]

# Multi-baseline (use a Derivation: block before or after the table):
**Derivation:** <formula in symbolic form (BF16)>.
<Baseline A>: <substitution> = <result>.
<Baseline B>: <substitution> = <result>.
```

### Inline Derivation — Real Examples from the ArchIdeas Corpus

```
# KV cache size:
~8.0 GB [derived: 64 layers × 2 × 8 KV heads × 128 dims × 32,768 tokens × 2 bytes (BF16) = 8,589,934,592 bytes ≈ 8.0 GB]

# TPOT improvement:
~1.63× [derived: weight_BW = 32B × 2 = 64 GB; KV_BW_before = 68.7 GB (262K ctx, BF16); KV_BW_after = 17.2 GB (INT4, 4× compression); TPOT = (64+68.7)/(64+17.2) = 132.7/81.2 ≈ 1.63×]

# Memory per token:
~5 MB [derived: 512 tokens × 5,120 dims × 2 bytes (BF16) = 5,242,880 bytes ≈ 5 MB; activation memory per forward pass at seq_len=512]

# LM head fraction:
~2.83% [derived: W_out = 250,112 vocab × 8,192 dims × 2 bytes = 4,097,835,008 bytes ≈ 4.10 GB; fraction = 4.10/145.1 ≈ 2.83% of total model weights]

# KV cache — multi-baseline (research_5_4_linked_attention.md):
**Derivation:** KV cache = L × 2 × H_kv × head_dim × s × 2 bytes (BF16).
A1 (7B MQA, s=32K): 32×2×1×128×32768×2 = 0.54 GB.
A2 (32B GQA-8, s=32K): 64×2×8×128×32768×2 = 8.59 GB.
A3 (32B MQA, s=32K): 64×2×1×128×32768×2 = 1.07 GB.
A4 (32B GQA-16, s=32K): 64×2×16×128×32768×2 = 17.18 GB.
```

### Exec Summary Overhead — Decision Rule

```
IF idea introduces sequential passes (W > 1) per output token:
  TPOT_overhead = W × (1.0 to 2.5) × baseline_TPOT
  FLOPs_overhead = small (shared weights, tiny extra params)

  → TPOT row is the most important row in exec summary
  → Bold the TPOT row
  → Add warning callout explaining the divergence
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas corpus | 34 ideas, 68 files, 5 artifacts | Audit Apr 2026 — found D4/D5/D7 issues in summary_5_3 and summary_3_8; all fixed |
| ArchIdeas idea 5.1 (TurboQuant) | Per-idea review with 5-agent swarm | Apr 2026 — found context length mislabel (68.7 GB at 262K labeled "32K"), A1 head_dim error, TPOT overstatement |
| ArchIdeas corpus (post Phase C/D) | 39 ideas, 4-baseline grading | Apr 2026 — D1=F (7 Phase A thematic docs missing all 4 baseline sections), D4=F (94/156 TTFT, 125/156 TPOT), D5=F (research_6_4 no TPOT rows), D7=F (10/39 have strict Accuracy header), D3/D6/D8/D9/D10=A; overall grade D; synthesis artifacts excellent, per-file structural compliance poor |
| ArchIdeas corpus remediation (post-audit) | Wave-based parallel fix agents across 39-file corpus | Apr 2026 — two-pass remediation: Pass 1 fixed arithmetic/framing (Critical + Major); Pass 2 fixed terminology drift (S-03) and section additions (D5); background agents failed at ~2M tokens; foreground agents succeeded; all fixes confirmed, no remaining bare tags |
| ArchIdeas corpus | 4-fix final remediation pass | Apr 2026 — impl_spec numeric corrected (0.68× per research_1_3 formula); 4 TTFT rows added to research_5_1; 77 bibliography locators added across 4 files via arXiv fetch; SHARED_PRELUDE.md Schema Variants section added for 5.9/5.10 thematic-template declaration; all fixes verified via grep |
| ArchIdeas corpus | 39-file audit inline derivation standard, Phase C + D | Apr 2026 — user rejected bare tags mid-session, inline derivation standard applied to multiple files; found and fixed block-level disclaimer antipattern in research_5_4_linked_attention.md |
| ArchIdeas corpus | Exec summary honesty — quality remediation of research_6_1_inarch_ar_loop.md | Apr 2026 — exec summary was missing TPOT row; FLOPs showed +0.18% while TPOT was W x 1.5-2.5x; added TPOT row with warning callout |
| ArchIdeas corpus | Follow-up quality remediation pass (inline derivation) | Apr 2026 — found and fixed block-level disclaimer antipattern in research_5_4_linked_attention.md; added per-baseline KV cache derivation |
