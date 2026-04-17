---
name: arch-research-myrmidon-swarm-review
description: "Parallel AI architecture research review using Myrmidon Swarm pattern: 1 lead agent per idea + 5 parallel sub-agents (citation verifier, complexity auditor, literature gap finder, comparison validator, feasibility checker) + coordinator. Use when: (1) reviewing a corpus of 10+ research documents for correctness, (2) verifying citations, Big-O claims, and baseline comparisons at scale, (3) producing independent review documents that can be cross-checked."
category: architecture
date: 2026-04-17
version: "1.4.0"
user-invocable: false
verification: verified-local
tags: []
history: arch-research-myrmidon-swarm-review.history
---

# Myrmidon Swarm: Parallel Architecture Research Review

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Review and validate 31 AI architecture research documents (research + summary pairs) for citation accuracy, Big-O correctness, baseline comparison validity, and implementation feasibility |
| **Outcome** | Successful — 31 review docs, 155 verification files, 2 synthesis reports, 1 final summary produced |
| **Verification** | verified-local |

## When to Use

- Reviewing a corpus of 10+ existing research documents for factual correctness
- Verifying that cited papers exist, summaries are faithful, and arXiv IDs are not fabricated
- Cross-checking Big-O complexity tables and Nx improvement claims against canonical baseline specs
- Finding missing literature that changes novelty classifications
- Producing independent review documents for a research corpus
- Generating research docs for new ideas that have no prior `research_*.md`/`summary_*.md` files, where each new idea needs full 5-role Myrmidon treatment alongside (or after) the existing corpus review
- Merging a reviewed corpus (review_*.md + summary_*.md + 5× verification_*.md per idea) into single-source research docs while simultaneously adding a new baseline and re-validating all merged docs

## Verified Workflow

### Quick Reference

```
Phase 0: Pre-flight baseline verification
  → Web-fetch authoritative config.json for each baseline model
  → Identify all errors in the shared context/prelude document
  → Inject canonical baselines verbatim into every agent prompt

Phase 1: 31 lead agents launched in parallel (one per idea)
  → Each lead spawns 5 sub-agents in parallel:
     a. Citation Verifier (WebFetch each paper; confirm existence/authors)
     b. Complexity Auditor (re-derive Big-O independently; check concrete byte calcs)
     c. Literature Gap Finder (rerun search queries + synonym variants)
     d. Comparison Validator (validate Nx claims, directional arrows)
     e. Feasibility Checker (hardware, training stability, framework support)
  → Each sub-agent emits verification_{id}_{role}.md

Phase 2: Lead agents synthesize → review_{id}_{name}.md
Phase 3a: Synthesis doc validator → review_synthesis_docs.md
Phase 3b: Coordinator → review_summary.md
```

### Detailed Steps

1. **Pre-flight baseline verification** — Before any agents run, web-fetch authoritative specs for every baseline model (e.g., HuggingFace config.json). Compare against any shared context document. If they disagree, the web-verified spec wins. Document all discrepancies as "inherited errors" and inject them into every agent prompt so sub-agents know which errors to attribute to the prelude vs. original author reasoning.

2. **Parallel lead agent launch** — Launch all N lead agents in a single message (one Agent tool call per idea). Each lead gets: canonical baselines + inherited error callouts + the research/summary doc pair for its idea.

3. **5 sub-agent roles per lead** — Each lead immediately spawns 5 sub-agents in parallel. Role assignments:
   - **Citation Verifier**: WebFetch every cited paper. Verdict per paper: YES / NO / PARTIALLY / COULD NOT VERIFY. Check author names, year, venue, and that the research doc's summary matches the actual abstract. Flag hallucinated arXiv IDs.
   - **Complexity Auditor**: Re-derive every Big-O independently. Recompute every concrete byte value (KV cache, weight memory) using canonical baseline specs. Surface hidden costs: router FLOPs O(d·E) for MoE, gradient memory 2× during training.
   - **Literature Gap Finder**: Run the pre-canned search queries from the original idea list plus 3–5 synonym variants. Compare against cited papers. Focus on post-cutoff papers, seminal overlooked work, and papers that would change the novelty classification.
   - **Comparison Validator**: Validate every Nx claim and every ↓/↑/= arrow in summary tables. Recompute using canonical baseline parameter values (not just symbolic O notation). Flag best-case-without-disclaimer claims.
   - **Feasibility Checker**: Hardware feasibility (custom kernels? Triton/CUDA?), training stability (routing collapse, expert collapse), framework support, cross-idea synergy claims (read the other idea's doc to confirm).

4. **Synthesis** — After all 5 sub-agent verification files land, lead agent synthesizes → review doc with 8 sections: citation verification, missing literature, Big-O verification, technical correctness, prior art check, verdict check, error summary, confidence scores. Assigns PASS / PASS WITH ISSUES / NEEDS REVISION / FAIL.

5. **Phase 3a synthesis doc validation** — One agent reads all synthesis artifacts (priority rankings, implementation specs, cross-reference matrices) and cross-checks each claim against the 31 reviews. Flags claims that rest on corrected Nx values or ideas with FAIL/NEEDS REVISION verdicts.

6. **Phase 3b coordinator** — One coordinator reads all 31 reviews + synthesis validation report. Produces: per-idea verdict table, aggregate stats, systemic error pattern analysis, revised priority ranking.

### Phase A: Research New Ideas (when ideas have no prior docs)

When adding N new ideas to an existing corpus that already has Phase 1–3 complete:

1. **Read the existing `SHARED_PRELUDE.md`** verbatim — inject into every new-idea lead agent prompt. New ideas get the same canonical baseline specs.

2. **Launch N new-idea lead agents in parallel** (one per idea). Each agent:
   - Spawns 5 sub-agents in parallel (same roles: Citation Verifier, Complexity Auditor, Literature Gap Finder, Comparison Validator, Feasibility Checker)
   - Produces `research_6_N_<slug>.md`, `summary_6_N_<slug>.md`, 5× `verification_6_N_<role>.md`, then `review_6_N_<slug>.md`
   - Follows the same 8-section review template as Phase 2 lead agents

3. **Critical prior art each new-idea agent MUST check** (inject these search terms explicitly):
   - N1 (in-arch AR loop with stop-token break): RWKW inference loops, Medusa/EAGLE speculative decoding trained-in, PonderNet, ACT (Adaptive Computation Time)
   - N2 (prefill/decode split): Splitwise (Patel 2023, arXiv:2311.18677), DistServe (Zhong 2024, arXiv:2401.09670), SARATHI-Serve chunked prefill (Agrawal 2023)
   - N3 (block-diffusion AR decoder): BD3-LM (arXiv:2406.15253), MDLM (Sahoo 2024, arXiv:2406.07524), LLaDA (Nie 2025, arXiv:2502.09992), Fast-dLLM (arXiv:2505.05175)
   - N4 (combined N1+N2+N3): cite all three base papers above; cross-synergy analysis required

4. **arXiv IDs must be WebFetch-verified** before citation — same rule as Phase 1.

5. **After Phase A completes**: new `research_6_N_*.md` files are equivalent to existing `research_1_*`–`research_5_*` files and can be included in the LaTeX paper on equal footing.

### Phase B: Per-Idea Merge + Myrmidon Re-Validation of Merged Docs

When the corpus has accumulated separate review_*.md, summary_*.md, and verification_*.md files per idea and you want to collapse them into a single authoritative research_*.md per idea (with optional new baseline addition):

**Pre-conditions:**
- All `review_X_Y.md` + `summary_X_Y.md` + `verification_X_Y_*.md` exist for each idea
- `SHARED_PRELUDE.md` extended with new baseline (e.g., Baseline C) before starting
- Outlier files identified (e.g., `scope_X_Y_*.md` to absorb into `research_X_Y.md`)

**Step B1: Extend SHARED_PRELUDE.md with new baseline**
- Web-fetch authoritative config.json for new baseline
- Add full spec block + per-token complexity + KV cache formulas at all reference contexts
- Add to KV cache comparison table
- Update Changelog section

**Step B2: One lead agent per idea (39 × parallel launch in 2 waves to avoid message size limits)**
- Each lead reads: `research_X_Y.md` + `summary_X_Y.md` + `review_X_Y.md` + all `verification_X_Y_*.md`
- Integrates review findings SILENTLY into prose (no "Review Findings" subsection)
- Integrates summary doc: Executive Summary subsection + Key Comparison Tables for ALL baselines (including new one)
- Absorbs any outlier scope files (e.g., `scope_4_7_*.md`) for its idea
- Converts all inline citations to `<Title>[N]: <description>` format
- Collects `<!-- CITATION MANIFEST -->` block at bottom of merged doc
- Applies systemic corrections silently (wrong KV formula, wrong vocab, wrong context)
- Spawns 5 sub-agents in parallel for validation of the merged doc
- Produces final merged `research_X_Y.md` (overwrite in-place)
- Produces `verification_merged_X_Y_{citations,complexity,literature,comparison,feasibility}.md`

**Step B3: Delete legacy docs (after all merges complete)**
- `rm summary_*.md review_*.md scope_*.md`
- `rm verification_*.md` (original, non-merged ones)
- Keep `verification_merged_*.md` as audit trail
- Delete audit trail after synthesis regen if desired

**Step B4: Regenerate synthesis docs from merged corpus**
- `cross_reference_matrix.md`, `priority_ranking.md`, `architecture_synthesis.md`, `implementation_spec_phase1.md`

### Phase C: Accuracy Review-and-Fix Pass (in-place, marker-free)

**When to use Phase C vs Phase B:**
- Phase B = merge + re-validate: collapses separate review/summary/verification files into unified `research_X_Y.md`; spawns 5 sub-agents per idea; adds a new baseline.
- Phase C = surgical fix pass: all 39 `research_X_Y.md` already exist (post-Phase-B); goal is to correct factual errors in-place without producing any new output files.

**Fix priority order (7 levels — work in this order):**
1. KV cache and FLOP values (wrong formula, wrong head count, wrong context window)
2. Wrong arXiv IDs (replace with WebFetch-verified IDs)
3. Claim mismatches (research doc says X, cited paper says Y)
4. Invalid table rows (rows that cannot be recomputed to within ±5% of stated value)
5. Wrong directional arrows in comparison tables (↓ vs ↑)
6. Missing prior art (add any citations that change novelty classification; no cap on new citations)
7. Training / synergy caveats (flag best-case-without-caveat claims)

**Two-wave launch (same limit as Phase B):**
- Wave 1: 17 lead agents — groups 1+2+3 (ideas 1.1–1.7, 2.1–2.2, 3.1–3.8)
- Wave 2: 22 lead agents — groups 4+5+6 (ideas 4.1–4.7, 5.1–5.10, 6.1–6.5)
- Do NOT launch all 39 in one message: confirmed runtime failure.

**Three citation manifest formats (leads must handle all three):**
- Format A: HTML comment per line — `<!-- [N] Title: ... -->`
- Format B: plain `## Citation Manifest` heading followed by numbered list
- Format C: `<!-- CITATION MANIFEST -->` header followed by a plain-text list outside the HTML comment block

**Fix discipline rules:**
- Change the minimum text necessary to make the value correct. No paragraph rewrites.
- No `[corrected: ...]` inline markers. No `## Corrections applied:` subsections added by the Phase C agent. No meta-commentary.
- Do not add a "Review Findings" or "Phase C Notes" subsection.
- **Verdicts are OUT OF SCOPE**: PURSUE / INVESTIGATE / DEPRIORITIZE / Final Verdict / Prior Art Classification are NOT touched in this pass; they will be addressed in a separate later phase.
- Pre-existing `## Corrections applied:` headers (from Phase B merge metadata) are legitimate — do not remove them.

**LoRA case taxonomy (for LoRA-based ideas such as 4.2, 4.3):**
- Case 1 — LoRA merged into W_base before inference: KV benefit = zero (full-rank W seen at runtime)
- Case 2 — W_core + A·B stored separately (both present in KV): ~1.5× worse KV than base model
- Case 3 — pure A·B adapter only (W_base discarded): ~2× fewer weight bytes, ~1.64× TPOT improvement

**SwiGLU ×3 factor (for MoE and expert-routing ideas):**
- SwiGLU has 3 weight matrices per expert: gate projection, up projection, down projection.
- Per-token per-layer expert FLOPs = 3×d×d_ff (not 2×d×d_ff).
- Always apply this factor when computing MoE active-expert FLOPs or total router + expert cost.
- Missing ×3 causes ~1.5× undercount; found in research_1_3 and others during Phase C.

### Phase D: Verdict Removal Pass

**When to use:** After Phase C (accuracy review-and-fix pass) is complete and before corpus publication. Phase D removes all verdict-related content from every `research_X_Y.md` file while preserving all technical content.

**What to remove (5 targets):**

1. `## Verdict` / `## Final Verdict` / `## Recommendation` section blocks — remove the header and all body text until the next `##` heading or EOF.
2. `**Prior Art Classification:** EXISTS/PARTIAL/NOVEL` lines — remove the entire line.
3. Standalone verdict-token lines — lines whose entire content is `**PURSUE**`, `**INVESTIGATE**`, `**DEPRIORITIZE**` (bold or bare) and nothing else. Do NOT remove mid-sentence uses of these words in technical argument.
4. Verdict-adjacent `- **Potential impact**: ...` and `- **Implementation effort**: ...` bullets — only when immediately adjacent (within the same block) to a verdict header or standalone token; not when appearing in independent implementation analysis.
5. Verdict-adjacent `**Confidence:** X/10` and `**Priority rank:** N` lines — only within verdict blocks; preserve any identical-looking lines that appear in independent scoring sections.

**What NOT to remove (5 preservation rules):**

1. Technical analysis, comparison tables, FLOPs/KV calculations — always preserve.
2. Literature review prose around a `**Prior Art Classification:**` line — only the status line itself is removed; surrounding analysis stays.
3. Mid-sentence uses of pursue / investigate / deprioritize embedded in technical argument — do not remove.
4. Citation manifest blocks (`<!-- CITATION MANIFEST -->` or `## Citation Manifest`).
5. `## Accuracy / Quality Tradeoff` sections and pre-existing `## Corrections applied:` metadata headers from Phase B merge — these are not verdict content; do not touch.

**Structural variation by group:**

- **Groups 1–4**: Verdict tokens appear as inline `**Verdict: PURSUE/INVESTIGATE/DEPRIORITIZE**` sentences embedded in the Executive Summary section — not as dedicated section headers. Use sentence-level extraction: find and remove only the verdict sentence, leaving surrounding Executive Summary prose intact.
- **Groups 5.1–5.8**: Verdict appears as `**Status: PURSUE/INVESTIGATE/PARTIAL** — ...` lines in the Executive Summary section. Remove the entire line.
- **Groups 5.9–5.10 and 4.x outliers**: Full `## 8–10. Verdict` or `## Verdict` section blocks running to EOF. Remove header + entire body.
- **Group 6**: Verdict tokens are embedded inline within `## Executive Summary` prose paragraphs (same treatment as groups 1–4). Some 6.x docs have `### Prior Art Classification` subsections that are verdict tables — remove the entire subsection including its table. Some 6.x docs have `## Assessment` sections with mixed technical content and verdict tokens: strip only the verdict tokens and classification status lines; preserve the surrounding technical prose (do not remove the whole section).

**Two-wave execution:** Same 17+22 wave structure as Phase C — launch 17 leads for groups 1–3, wait for completion, then 22 leads for groups 4–6. Confirmed: attempting all 39 in one message causes timeout.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using prelude/command baseline specs directly | Accepted SHARED_PRELUDE.md baseline numbers at face value | Prelude had 5 factual errors: wrong vocab (151,936→248,320 for A1/B), wrong context (32,768→262,144), wrong head_dim (128→256 for GatedAttn), wrong head counts for B global attention. These cascaded into all 31 research docs | Always web-fetch authoritative config.json before starting any quantitative analysis |
| Single-agent review | Tried reviewing multiple ideas sequentially | Context window exhaustion; cross-contamination between ideas | One lead agent per idea; no agent works on more than one idea |
| Agent self-approval stall | 4 agents invoked `/hephaestus:advise` internally, presented a plan, and waited for approval | Agents stalled indefinitely waiting for human approval in background context | Detect stalled agents by checking for verification files without corresponding review files; unblock by sending explicit approval via SendMessage |
| Trusting "68 GB KV at 32K" for A2 | SHARED_PRELUDE stated A2 (Qwen3-32B) KV cache = ~68 GB at 32K context | Wrong: used 64 Q-heads instead of 8 KV-heads in formula; ~8× overestimate. Correct: 64L × 2 × 8KV × 128hd × 32768tok × 2B = ~8.59 GB | Always verify KV cache formulas use KV head count not Q head count |
| N4 before N1/N2/N3 | Tried to research the combined idea before the three component ideas had research docs | N4 requires cross-references to N1, N2, N3 prior art and Big-O analysis; without them the N4 agent fabricates component details | Always research component ideas N1, N2, N3 fully before launching N4 agent |
| Trusting author complexity claims for new ideas | Accepted "O(n) per token" claim from a new idea's mechanism description without re-deriving | Author was counting attention heads as O(1); when DeltaNet state per head is O(d²), full per-token cost is O(d²) not O(n·d) | Complexity Auditor sub-agent must re-derive every Big-O for new ideas, same as for existing corpus |
| Processing all 39 ideas in a single agent message | One giant Agent call listing all 39 ideas | Context exhaustion before half the ideas complete | Split into waves of ~7 ideas per group; parallel agents per group are fine |
| Verification file role-name drift ignored | Assumed all ideas use the same verification file suffix pattern | Ideas 1.x–5.x use `{citations,comparison,complexity,feasibility,literature}`; ideas 6.x use `{citation_verifier,comparison_validator,complexity_auditor,feasibility_checker,literature_gap}` — glob-only approach missed 6.x files | Each lead agent must explicitly glob BOTH naming patterns before reading |
| All 39 leads in one message | Launched all in a single message with 39 Agent tool calls | Message too large for runtime | Wave approach: launch groups 1–3 first, then 4–6 after confirmation |
| Scope outlier handled by wrong agent | Tried to absorb `scope_4_7_*.md` in a general cleanup step | The scope file's content was context-dependent on idea 4.7 — only the 4.7 lead agent knew the right place to fold it in | Always assign outlier files to the lead agent for their idea |
| Adding `[corrected: ...]` markers during Phase C in-place fix pass | Using inline correction markers to trace changes made during Phase C | User explicitly opted out — markers create clutter in the final corpus and make the doc less readable | Phase C is marker-free: change the minimum text, no inline traces, no `## Corrections applied:` subsections added by the Phase C agent |
| Treating pre-existing `## Corrections applied:` as banned content | Agent flagged `## Corrections applied: See verification_merged_1_5_*.md files` as a banned subsection and attempted removal | It was a pre-existing Phase B merge metadata header, not added by the Phase C agent | Before flagging a section as "agent-added banned content", check git history or context — it may be a legitimate pre-existing artifact |
| Launching all 39 Phase C leads in one message | Single Agent call listing all 39 Phase C leads | 39 is too many for one message (same limit as Phase B) | Two-wave approach: launch 17 leads for groups 1–3, wait for completion, then launch 22 leads for groups 4–6 |
| Using H_q in attention FLOPs formula | Attention FLOPs computed as 4×d×H_q×s per layer | The formula is 4×d×s per layer total (not per head); H_q does not appear as a multiplier — prefill attention FLOPs = 2×s×d (QKV projection) + 2×s×d (attention matmul) = 4×s×d per layer | Complexity Auditor must re-derive attention FLOPs from first principles; H_kv applies only to KV cache size, not to total attention FLOPs |
| Using SwiGLU FLOPs = 2×d×d_ff | Treated SwiGLU the same as a standard two-matrix FFN (gate + down) | SwiGLU has 3 weight matrices per expert (gate, up, down): correct FLOPs = 3×d×d_ff not 2×d×d_ff; missing ×3 causes ~1.5× undercount | SwiGLU FLOPs = 3×d×d_ff per token per layer; apply to all MoE and expert-routing ideas that count per-expert FLOPs |
| Treating `## Corrections applied:` as banned content during Phase D | Agent flagged `## Corrections applied: See verification_merged_*.md files` as agent-added banned content and attempted removal | It was a pre-existing Phase B merge metadata header, not added by the Phase C or Phase D agent | Before flagging a section as "agent-added banned content", check file context or git history — it may be a legitimate pre-existing artifact |
| Removing whole `## Assessment` sections in group 6 docs during Phase D | Removed entire `## Assessment` section because it contained a verdict token | Group 6 `## Assessment` sections sometimes contain mixed technical content alongside verdict tokens; removing the whole section destroys technical analysis | For sections with mixed content: strip only verdict tokens and classification status lines; preserve surrounding technical prose |

## Results & Parameters

### Corpus Merge Parallelization — Verified Grouping (39 Ideas, 6 Groups)

| Wave | Groups | Ideas | Lead agents | Sub-agents |
|------|--------|-------|-------------|------------|
| 1 | 1, 2, 3 | 1.1–1.7, 2.1–2.2, 3.1–3.8 | 17 | 85 |
| 2 | 4, 5, 6 | 4.1–4.7, 5.1–5.10, 6.1–6.5 | 22 | 110 |

**Outlier file handling**: `scope_X_Y_*.md` → assigned to idea X.Y lead agent; absorbed into merged `research_X_Y.md`.

**Verification file naming drift** (two conventions — must handle both):
- Ideas 1.x–5.x: `verification_{id}_{citations|comparison|complexity|feasibility|literature}.md`
- Ideas 6.x: `verification_{id}_{citation_verifier|comparison_validator|complexity_auditor|feasibility_checker|literature_gap[_finder]}.md`

### Systemic Error Patterns Found (apply to any similar review)

1. **KV cache formula error**: `n_q` (query heads) used instead of `n_kv` (KV heads) → 8× overestimate for GQA models
2. **Context window mislabeling**: Concrete byte values computed at native context but labeled with a smaller context value
3. **Vocab propagation**: Shared vocab across model families confused; each baseline may have different vocab size
4. **Speedup figure context mismatch**: Long-context speedup figures (e.g., "3× at 65K context") incorrectly cited at short context (8K–32K) where MLP FLOPs dominate attention
5. **Citation discipline failures**: Anonymous keys ("Multiple authors"), missing §X.Y section references, post-cutoff papers without "unverified" flags

### Review Document Template (8 sections)

```markdown
## 1. Paper Citation Verification (YES/NO/PARTIALLY/COULD NOT VERIFY per paper)
## 2. Missing Literature (papers the review should have cited)
## 3. Big-O / Complexity Verification (table: original vs. corrected)
## 4. Technical Correctness (mechanism, feasibility, fairness)
## 5. Prior Art Classification Check (EXISTS/PARTIAL/NOVEL — confirmed or revised)
## 6. Verdict Check (PURSUE/INVESTIGATE/DEPRIORITIZE — confirmed or revised)
## 7. Error Summary (Critical / Minor / Suggestions)
## 8. Confidence Scores (literature, technical, comparison, overall — 1-10)
```

### Correction Pass (post-review)

After reviews complete, launch parallel surgical correction agents (one per group of 5–8 ideas). Each agent:
- Reads the review files for its assigned ideas
- Makes in-place edits to research/summary docs
- Adds `[corrected: ...]` inline notes so changes are traceable
- Never touches review_*.md or verification_*.md (read-only ground truth)

### New Idea Research — Verified arXiv IDs (2026-04-14)

These IDs were WebFetch-verified during the N1–N4 research pass:

| Idea | Key paper | arXiv ID | Verified |
|------|-----------|----------|---------|
| N1 (AR loop + stop token) | PonderNet | arXiv:2107.05407 | YES |
| N1 | EAGLE speculative decoding | arXiv:2401.15077 | YES |
| N2 (prefill/decode split) | Splitwise | arXiv:2311.18677 | YES |
| N2 | DistServe | arXiv:2401.09670 | YES |
| N3 (block diffusion AR) | BD3-LM | arXiv:2406.15253 | YES |
| N3 | MDLM | arXiv:2406.07524 | YES |
| N3 | LLaDA | arXiv:2502.09992 | YES |
| N3 | Fast-dLLM | arXiv:2505.05175 | YES |

### N1–N4 Final Verdicts

| Idea | Verdict | Rationale |
|------|---------|-----------|
| N1 (In-arch AR loop + stop token) | INVESTIGATE | Novel framing; prior art (PonderNet, Medusa) covers components but not the specific trained-in stop-token-as-architecture-gate |
| N2 (Prefill/decode split) | PURSUE | Splitwise and DistServe validate the operational benefit; architectural-level split (vs. system-level) is the novel angle |
| N3 (Block-diffusion AR decoder) | INVESTIGATE | BD3-LM and LLaDA are close prior art; the AR-across-blocks + diffusion-within-block combination at architecture level has novelty |
| N4 (Combined N1+N2+N3) | INVESTIGATE | Synergy benefit is plausible but compounding complexity; depends on N2 and N3 independently proving out first |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | 31 AI architecture ideas (sections 1–5 plus 4.7) | Qwen3.5-27B Hybrid, Qwen3-32B Dense, Qwen3.5-397B-A17B MoE baselines |
| ArchIdeas | 4 new ideas (N1–N4) added to existing 31-idea corpus | research_6_1 through research_6_4 produced by parallel Myrmidon swarms; all 4 included in final LaTeX paper |
| ArchIdeas | 39-idea corpus merge (Phase B) | review_*.md + summary_*.md + 5× verification_*.md merged into 39 unified research_*.md files; 195 merged verification files produced; synthesis docs regenerated |
| ArchIdeas | 39-idea corpus accuracy review-and-fix pass (Phase C) | In-place surgical fix pass on all 39 research_X_Y.md; no output files; verdicts out of scope. Baseline C (K2 Family / LLM360): L=80, d=8192, d_ff=28672, H_q=64, H_kv=8, head_dim=128, vocab=250112; K2-V2 ctx=524288, K2-Think-V2 ctx=262144; KV @ 32K≈10.0 GiB, @ 262K≈80.0 GiB, @ 524K≈160.0 GiB |
| ArchIdeas | 39-idea corpus verdict removal pass (Phase D) | Removed all verdict-related content (PURSUE/INVESTIGATE/DEPRIORITIZE tokens, Final Verdict sections, Prior Art Classification status lines, verdict-adjacent impact/effort/confidence bullets) from all 39 research_X_Y.md files; all technical content preserved; two-wave execution (17+22) |
