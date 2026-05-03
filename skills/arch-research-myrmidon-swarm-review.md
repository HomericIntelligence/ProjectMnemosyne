---
name: arch-research-myrmidon-swarm-review
description: "Parallel AI architecture research review using Myrmidon Swarm pattern: 1 lead agent per idea + 5 parallel sub-agents (citation verifier, complexity auditor, literature gap finder, comparison validator, feasibility checker) + coordinator. Use when: (1) reviewing a corpus of 10+ research documents for correctness, (2) verifying citations, Big-O claims, and baseline comparisons at scale, (3) producing independent review documents that can be cross-checked, (4) reviewing ideas involving weight factorization or LoRA-style parameterization, (5) reviewing ideas involving learned layer skipping, residual gating, or static-at-inference pruning, (6) auditing inference speedup claims (merged vs unmerged, frozen gates vs model surgery, compute-bound vs bandwidth-bound), (7) verifying that training and inference benefit claims are internally consistent across cases."
category: architecture
date: 2026-04-17
version: "2.0.0"
user-invocable: false
verification: verified-local
tags: [arch-research, lora, low-rank, complexity-audit, citation-verification, inference, myrmidon, swarm-review, layer-pruning, residual-gating, static-inference]
history: arch-research-myrmidon-swarm-review.history
---

# Myrmidon Swarm: Parallel Architecture Research Review

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-13 |
| **Objective** | Review and validate 31 AI architecture research documents (research + summary pairs) for citation accuracy, Big-O correctness, baseline comparison validity, and implementation feasibility |
| **Outcome** | Successful — 31 review docs, 155 verification files, 2 synthesis reports, 1 final summary produced. Absorbed arch-research-doc-lora-review-pattern + arch-research-static-inference-model-surgery on 2026-05-03 |
| **Verification** | verified-local |
| **Absorbed** | arch-research-doc-lora-review-pattern (v1.1.0), arch-research-static-inference-model-surgery (v1.0.0) on 2026-05-03 |

## When to Use

- Reviewing a corpus of 10+ existing research documents for factual correctness
- Verifying that cited papers exist, summaries are faithful, and arXiv IDs are not fabricated
- Cross-checking Big-O complexity tables and Nx improvement claims against canonical baseline specs
- Finding missing literature that changes novelty classifications
- Producing independent review documents for a research corpus
- Generating research docs for new ideas that have no prior `research_*.md`/`summary_*.md` files, where each new idea needs full 5-role Myrmidon treatment alongside (or after) the existing corpus review
- Merging a reviewed corpus (review_*.md + summary_*.md + 5× verification_*.md per idea) into single-source research docs while simultaneously adding a new baseline and re-validating all merged docs
- Reviewing any research or summary document that involves low-rank factorization of weight matrices (LoRA, matrix decomposition, rank-r parameterization)
- Validating claims about inference speedup from weight factorization — especially "merged vs unmerged" distinctions
- Any document that uses GaLore, CoLA, WeLore, or similar citations as evidence for training or inference benefits
- Reviewing any research or summary document that involves learned gates on residual streams, layer-level pruning, or "static at inference" skip decisions
- Validating TTFT/TPOT claims for layer pruning ideas (ShortGPT, GateSkip, Mixture of Depths)
- Any document that claims "static at inference time" speedup from frozen gates
- Any document describing synergy between layer-pruning ideas (e.g., idea 4.4 Skip List Layers + idea 4.5 Learned Residual Flow)
- A research document claims a mechanism is "static at inference time" and therefore has zero per-token overhead
- A document describes frozen gates, frozen routing weights, or frozen skip decisions as producing inference speedup
- Any idea where architectural decisions are learned during training and then "frozen" — and the document claims this produces a faster model at inference time
- Reviewing DenseFormer-style ideas (learned depth weights frozen post-training) vs hard-gate pruning ideas

**Red flags requiring the LoRA checklist:**
- Document claims both TTFT penalty AND throughput improvement for the same "unmerged" path
- Document cites GaLore's optimizer state reduction to support LoRA weight parameter reduction (different mechanisms)
- Document cites dLoRA (course PDF) as evidence of inference overhead
- "Unmerged" rows in tables don't specify whether W_core is present or absent
- Training cost claim assumes optimizer savings without checking whether W_core is also being trained

**Red flags requiring the Layer Pruning checklist:**
- Document claims "static at inference" speedup from frozen gates without specifying model surgery
- Document attributes 1.05–1.15× training overhead to scalar gates (correct range is ~1.00×; that range belongs to Hyper-Connections SHC matrix expansion)
- Document lacks a citation for Mixture of Depths [Raposo et al., 2024, arXiv:2404.02258]
- Document cites "Frankle and Carlin" instead of "Frankle and Carbin" (Lottery Ticket Hypothesis)
- Document claims idea 4.4 (Skip List Layers) and idea 4.5 (Residual Flow) "combine well" without noting order-dependency
- Any 2026 arXiv ID without a "URL not verified" marker

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

### LoRA / Low-Rank Parameterization Review Checklist

> **Note:** Verified locally on idea 4.3 (LoRA Everywhere) review session.

#### LoRA Quick Reference

```
Five-agent parallel review:
  A — Citation Verifier    → verification_<id>_citations.md
  B — Complexity Auditor   → verification_<id>_complexity.md
  C — Literature Gap Finder → verification_<id>_literature.md
  D — Comparison Validator → verification_<id>_comparison.md
  E — Feasibility Checker  → verification_<id>_feasibility.md
  F — Synthesizer (Wave 2) → review_<id>_<name>.md
```

#### LoRA Step 1: Identify the Parameterization Cases (Before Any Analysis)

For any W = W_core + A·B document, ALWAYS distinguish three cases before analyzing any claim:

| Case | Formula | W_core | Expected Benefit |
|------|---------|--------|-----------------|
| Case 1: Merged | W_full = W_core + A·B materialized | Any | ZERO inference benefit — identical to dense |
| Case 2: Unmerged, W_core present | x·W_core + (x·A)·B | Present | 1.5× MORE bandwidth and FLOPs than dense — a regression |
| Case 3: Unmerged, W_core absent | (x·A)·B only | Absent | 2× fewer weight bytes, ~1.64× TPOT improvement |

**Every claim in the document must specify which case it applies to.** If it doesn't, that is a red flag.

#### LoRA Step 2: Complexity Table Audit Checklist

For each row in any complexity or benefit table, verify:

- [ ] **TTFT (prefill)**:
  - Case 1 (merged): identical to dense ✓
  - Case 2 (W_core + A·B): 1.5× MORE FLOPs at r=d/4 (FLOPs = 3d² vs 2d²) ← slower
  - Case 3 (pure A·B): 0.5× FLOPs at r=d/4 (FLOPs = d² vs 2d²) ← **2× FASTER, NOT slower**

- [ ] **TPOT (batch=1 decode)**:
  - Case 1 (merged): identical to dense ✓
  - Case 2 (W_core + A·B): 1.5× MORE bytes loaded (d² + d²/2 = 1.5d² vs d²) ← slower
  - Case 3 (pure A·B): 0.5× bytes loaded (d²/2 vs d²) ← **~1.64× faster per CoLA** ✓

- [ ] **Weight memory**:
  - Cases 1 and 2: identical to or worse than dense (W_core present)
  - Case 3 only: 2× reduction at r=d/4 ✓

- [ ] **Training optimizer state**:
  - If W_core is also trained: 1.5× MORE optimizer memory than dense (d² + 2·d²/4·2 = 1.5× Adam states)
  - If W_core is frozen or absent (pure A·B): 50% reduction ✓

#### LoRA Step 3: Citation Verification Checklist

For any document citing papers about LoRA or low-rank training, verify:

| Citation | What to Check |
|----------|--------------|
| GaLore (Zhao et al., 2024) | Verify: reduces GRADIENT optimizer states; weights remain full-rank. Do NOT use to support weight parameter reduction in LoRA Everywhere. |
| CoLA (Liu et al., 2025) | Verify: has nonlinearity σ between A and B. Claims are valid only at ≤7B. EMNLP 2025 venue is plausible. |
| WeLore (Wei et al., 2025) | Verify: post-training compression study (not pre-training). Uniform 50% rank → PPL 1836.62; non-uniform → 11.87 for LLaMA-2 7B. |
| dLoRA (Princeton course PDF) | Flag as grey literature (non-peer-reviewed course syllabus). The 38.9% overhead measures W_core+A·B compute-bound — NOT pure A·B bandwidth-bound. Do not cross-apply. |
| GaLore 2 (Su et al., 2025) | Treat as SUSPECT: vague author list, modest claimed improvement (~6% memory reduction vs GaLore 1's 65.5%), possible Llama 7B/8B inconsistency. |
| SLTrain (Cichocki et al., 2024) | Verify: low-rank alone fails at pre-training; needs sparse correction. Analogous to W_core in idea 4.3 serving as full-rank anchor. |
| Flora (Hao et al., 2024) | Key insight: fixed A·B (no rotation) is inferior to full-rank training. W_core or nonlinearity serves same role as Flora's rotation. |

#### LoRA Step 4: Literature Gap Checklist

For any low-rank parameterization research doc, check whether these are cited:

- [ ] **Monarch matrices** (Dao et al., 2022, NeurIPS, arXiv 2204.00595) — structured factorization competitor, O(d log d) params vs O(dr) for LoRA; achieves higher expressiveness at similar compression
- [ ] **Scale laws for low-rank pre-training** — does quality gap grow or shrink with scale?
- [ ] **LoRA-GA** (gradient-aligned initialization) — addresses A·B initialization for pre-training
- [ ] **Sheared LLaMA** (Xia et al., 2023) — competing paradigm: train dense then compress, vs train compressed
- [ ] **FWSVD** (Fisher-weighted SVD) — post-hoc compression baseline for comparison

#### LoRA Step 5: Inference Regime Disambiguation

**ALWAYS verify which inference regime each speedup claim applies to:**

| Regime | Characteristic | Who benefits |
|--------|---------------|-------------|
| Batch=1 decode | Bandwidth-bound — TPOT proportional to bytes loaded | Case 3 (pure A·B): ~1.64× faster |
| Large-batch decode | Compute-bound — TPOT proportional to FLOPs | No benefit (FLOPs same or higher) |
| Prefill (any batch) | Compute-bound — TTFT proportional to FLOPs | Case 3 (pure A·B): ~2× faster |
| Multi-request serving | Mixed — dLoRA's measurement regime | Case 2 (W_core+A·B): +38.9% overhead |

**The dLoRA 38.9% overhead and CoLA 1.64× speedup are BOTH CORRECT — they measure different cases in different regimes. Never apply one to the context of the other.**

---

### Layer Pruning / Residual Gating Review Checklist

> **Note:** Verified locally on idea 4.5 (Learned Residual Flow Control) review session.

#### Layer Pruning Step 1: "Static at Inference" Implementation Path Audit

**CRITICAL**: Documents claiming "static at inference time" speedup MUST specify the implementation path. There are two paths; only one delivers the claimed speedup:

| Path | Description | Inference speedup? |
|------|-------------|-------------------|
| Frozen soft gates | Gates g_i ∈ (0,1) frozen after training; layer still computes F_i(x) then multiplies by g_i | **NONE** — layer executes fully; only one scalar multiply saved |
| Model surgery | After training, identify zero-gate layers (g_i < 0.5), physically remove them from model graph, reindex | **REAL** — identical to a model originally designed with L·p layers; zero per-token overhead |

**The inference speedup claim is ONLY valid when model surgery is performed.** Flag any document that claims speedup from frozen gates without specifying surgery.

For any "static at inference" claim, also determine which scenario applies:

```
Scenario A: Frozen soft gate g_i ∈ (0,1)
  → Layer still computes F_i(x) then multiplies by g_i
  → NO compute savings (full layer executes)
  → Only one scalar multiply saved — negligible

Scenario B: Frozen hard-zero gate g_i = 0
  WITH conditional execution: if gate[i]: x = x + F_i(RMSNorm(x))
  → STATIC gate means all tokens take same branch → no GPU divergence
  → Speedup achieved but requires conditional logic in forward pass

Scenario C: Model surgery (post-training layer removal)
  → Remove layers with g_i < 0.5 from model graph entirely
  → Re-index remaining layers
  → Result: standard N·p-layer transformer, no gate infrastructure
  → TRUE zero overhead — identical to model designed with N·p layers from scratch
```

| What the document says | Which scenario | Real speedup? |
|-----------------------|----------------|--------------|
| "Gates are frozen after training" (no further detail) | Scenario A | NO — gates are frozen but layers still execute |
| "Zero-gate layers are skipped" | Scenario B | YES — conditional execution with static branch |
| "Layers with g < 0.5 are removed from the checkpoint" | Scenario C | YES — true model surgery |
| "Static, so no per-token overhead" WITHOUT specifying mechanism | AMBIGUOUS — flag for clarification | UNKNOWN until clarified |

For models using Pre-LN (like Qwen3/3.5 with RMSNorm before sublayers):
```
Standard pre-norm: x_{i+1} = x_i + F_i(RMSNorm(x_i))
With soft gate:    x_{i+1} = x_i + g_i · F_i(RMSNorm(x_i))
```
If g_i = 0 but the code is not conditioned on it, RMSNorm runs and F_i runs — both are wasted. **Model surgery resolves this completely** — the entire layer (norm + sublayer) is removed, so neither runs.

**Framework feasibility:**

| Framework | Model surgery feasibility |
|-----------|--------------------------|
| PyTorch | `nn.ModuleList` can be filtered in-place. `torch.jit.script` or torch.compile() will compile the pruned model with no residual gate infrastructure. FEASIBLE. |
| JAX | `jax.lax.scan` over variable-length list requires refactoring; functional-style layer application over a filtered list works. FEASIBLE with effort. |
| HuggingFace Transformers | Most models use `nn.ModuleList` for layers; filtering is straightforward. Some models have hardcoded layer count in config — requires config update. FEASIBLE. |

**Residual stream reindexing:** After removing layers from a standard sequential transformer, `active_layers = [l for i,l in enumerate(model.layers) if gates[i] > 0.5]` — no explicit reindexing needed. **Exception**: If idea 4.4 (Skip List Layers) is also applied, skip connections are position-indexed and must be updated after surgery.

#### Layer Pruning Step 2: TTFT/TPOT Claim Verification

For p = fraction of layers active after pruning (e.g., p=0.75 means 25% pruned):

**TTFT (~0.75× for p=0.75)**: CORRECT when:
- Pruning is uniform across layer types (both attention and MLP layers pruned)
- MLP FLOPs dominate at the sequence length being analyzed
- At s=8K for A1 (d_ff=17408): MLP fraction ≈ 90% of total FLOPs → uniform pruning gives ≈ 0.75× TTFT ✓
- At s=8K for A2 (d_ff=25600): MLP fraction ≈ 85% → pruning gives ≈ 0.75× TTFT ✓

**TPOT (~0.75× for p=0.75)**: CORRECT when:
- Batch=1 (bandwidth-bound)
- Active weight bytes scale as p × baseline
- KV cache access for pruned attention layers also reduces proportionally

#### Layer Pruning Step 3: Training Overhead Verification

**Gate type → training overhead mapping:**

| Gate type | Extra FLOPs per forward pass | Training overhead |
|-----------|------------------------------|-------------------|
| Scalar gate per layer (L scalars) | L × batch_size × seq_len scalar ops | ~1.00× (negligible — <0.01% of baseline) |
| Vector gate per layer (L × d vectors) | L × d × batch_size × seq_len scalar ops | ~1.00× (still negligible vs d·d_ff matmuls) |
| Hyper-Connections SHC (n × d expansion matrix) | n × d² per layer | 1.05–1.15× (measurable overhead) |

**Do NOT attribute the 1.05–1.15× Hyper-Connections SHC overhead to scalar or vector gates.**
> Source: **[Zhu et al., 2024]** — §"Static Hyper-Connections (SHC)" (arXiv:2409.19606)

#### Layer Pruning Step 4: Citation Checklist

For any document about learned layer skipping, residual gating, or static pruning, verify:

| Citation | What to Check |
|----------|--------------|
| Mixture of Depths (Raposo et al., 2024, arXiv:2404.02258) | **CRITICAL MISSING CHECK** — MoD is the closest prior art for learned skip decisions at scale. If not cited, flag as significant gap. Note: MoD is DYNAMIC (per-token); idea 4.5 is STATIC — this distinction preserves PARTIAL novelty. |
| LayerDrop (Fan et al., 2020, arXiv:1909.11556) | Foundational work on training transformers to be robust to layer dropping. If not cited, flag as important gap. Note: LayerDrop is RANDOM (not learned); idea 4.5 learns the optimal static pattern. |
| ShortGPT (Men et al., 2024, arXiv:2403.03853) | Block Influence (BI) metric proves 24–27% of layers are redundant. Quality claims: LLaMA 2-7B: 27.1% pruned MMLU 45.39→43.96 (−3.2%); LLaMA 2-13B: 24.6% pruned MMLU 55.00→54.69 (−0.6%). Verify math: 45.39→43.96 = −1.43 abs = −3.15% relative ✓ |
| GateSkip (Laitenberger et al., 2024, arXiv:2510.13876) | Validates learned gating principle with adaptive regularization. Correct table refs: Table 1 (1B quality), Table 6 (8B quality), Table 10 (throughput). |
| Frankle and Carbin, 2019 (ICLR, arXiv:1803.03635) | **AUTHOR NAME CHECK** — Correct name is "Carbin" not "Carlin". Second author is Michael Carbin (MIT CSAIL). This misspelling recurs in multiple docs. |
| Any arXiv ID from 2026 | Flag as HIGH RISK — must verify URL resolves. Add "URL not verified" marker if not fetched. |

#### Layer Pruning Step 5: 4.4 + 4.5 Composition Audit

When a layer-pruning document claims synergy with Skip List Layers (idea 4.4):

**The composition is ORDER-DEPENDENT:**

| Order | Composability | Notes |
|-------|--------------|-------|
| 4.5 first (determine survivors), then 4.4 (apply skip topology to survivors) | CLEAN — 4.4 operates on the pruned architecture with known layer count | Requires sequential training |
| 4.4 first (set skip intervals), then 4.5 (prune) | BROKEN — pruning a layer that is an anchor for a 4.4 skip connection breaks the topology | Skip intervals must be recomputed after pruning |
| Joint training | COMPLEX — 4.4 skip connections may help gradient flow past near-zero gates; possible positive interaction but requires careful design | Not cleanly validated |

**"Combines well with 4.4" claims should be qualified as "combines well if 4.5 gating is applied first."**

#### Layer Pruning Step 6: Baseline Formula Audit

Check the complexity tables against these known issues:

| Formula | Common Error | Correct |
|---------|-------------|---------|
| Weight memory | O(p·L·d·d_ff + L·d) — missing attention weights | O(p·L·(d·d_ff + d²) + L·d) |
| Bandwidth (A1 hybrid) | O(p·L·(d²+s·d_kv/4)) — missing MLP loading | O(p·L·(d²+d·d_ff+s·d_kv/4)) |
| Baseline B compute | O(L·(d²+k·d·d_e)) — missing global-attn term | O(L·(d²+s·d/4+k·d·d_e)) for B's 25% global-attn layers |
| Context window heading | "32K tokens" for A1/B | A1 and B: 262,144; A2: 40,960 |

---

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
| --------- | ---------------- | --------------- | ---------------- |
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
| Treating "unmerged" as a single case (LoRA) | Research doc had a single "unmerged" row covering all three cases | TTFT and TPOT values were contradictory (one showed penalty, other showed speedup) | Always split into Case 1/2/3 before populating any table |
| Using GaLore optimizer savings to quantify LoRA Everywhere training benefit | Doc cited GaLore Table 1 (65.5%) to support LoRA Everywhere (50%) | Different mechanisms: GaLore reduces gradient states; LoRA reduces weight parameters | Cite separately; note that GaLore 65.5% beats LoRA Everywhere 50% for optimizer state alone |
| Applying dLoRA 38.9% to TPOT (batch=1 decode) | Complexity table used 38.9% overhead as TPOT estimate | dLoRA measures compute-bound multi-request; TPOT at batch=1 is bandwidth-bound | dLoRA measurement is only valid for Case 2 in compute-bound serving |
| Assuming TTFT is penalized for the case with inference benefit (LoRA) | Summary doc said "1.5× slower TTFT" for all unmerged cases | Pure A·B (Case 3) actually has 2× FASTER TTFT (half the FLOPs) | The TTFT penalty only applies to Case 2 (W_core present), which has no deployment value |
| Not distinguishing whether W_core is trained or frozen | Training cost claim assumed 50% optimizer savings | If W_core is also trained from scratch, optimizer memory is 1.5× MORE than dense | Explicitly state: optimizer savings ONLY if W_core is frozen or absent |
| Claiming "static at inference" speedup from frozen soft gates (Layer Pruning / static-inference) | Research doc described frozen gates OR stated "static at inference, therefore zero overhead" for frozen continuous gate values | Frozen soft gates still execute the full layer computation (gate value is frozen, but F_i(x) still runs before the multiply); only model surgery (physical layer removal) produces real speedup | Always distinguish: frozen gate VALUE ≠ eliminated computation; model surgery (Scenario C) required for real speedup |
| Conditional execution with per-token gates | Prior work like GateSkip uses dynamic (per-token) gates with conditional execution | Per-token conditional causes SIMD divergence on GPU — different tokens take different branches | Dynamic gates cannot use efficient static branching; only truly static (same for all tokens) gates allow branch prediction optimization |
| Forgetting that pre-norm still runs under frozen soft gates | Implementation skipped the sublayer but kept the RMSNorm running | RMSNorm cost is ~O(d) per token per layer — small but not zero | Model surgery must remove the entire layer block (norm + attention/MLP), not just the sublayer computation |
| Assuming DenseFormer-style savings | Research doc conflated DenseFormer's frozen DWA weights with hard-zero gate inference | DenseFormer freezes learned AGGREGATION weights (still blends all past representations) — no layer is eliminated, and throughput is actually 22% WORSE than baseline | Frozen learned weights ≠ frozen skip decisions; aggregation weights run at every token regardless of value |
| Attributing 1.05–1.15× training overhead to scalar gates (Layer Pruning) | Doc cited Hyper-Connections SHC overhead range for scalar gate overhead | SHC uses n × d expansion matrix (~10M extra FLOPs/layer); scalar gates add ~64 scalar ops total | 1.05–1.15× is correct for SHC; scalar gates are ~1.00× (< 0.01% overhead) |
| Missing Mixture of Depths as critical prior art (Layer Pruning) | Literature review omitted MoD despite it being the closest related work for learned layer skipping | MoD demonstrates per-token hard binary skip decisions at 6B+ scale; without it, novelty claim is incomplete | Always check for MoD [Raposo et al., 2024, arXiv:2404.02258] as first citation for any "learned layer skip" idea |
| Misspelling Lottery Ticket author name (Layer Pruning) | "Frankle and Carlin" appeared in multiple docs | Correct name is Michael Carbin (MIT CSAIL), not "Carlin" | Add to citation checklist: always verify second author of LTH = Carbin |
| Claiming 4.4 + 4.5 "combine well" without qualification (Layer Pruning) | Research doc stated both ideas synergize without noting composition order | 4.4 first → 4.5 second breaks skip-interval anchor points; composition is order-dependent | Qualify: "combines well if 4.5 gating (layer selection) is applied before 4.4 (connectivity topology)" |

## Results & Parameters

### Corpus Merge Parallelization — Verified Grouping (39 Ideas, 6 Groups)

| Wave | Groups | Ideas | Lead agents | Sub-agents |
| ------ | -------- | ------- | ------------- | ------------ |
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
| ------ | ----------- | ---------- | --------- |
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
| ------ | --------- | ----------- |
| N1 (In-arch AR loop + stop token) | INVESTIGATE | Novel framing; prior art (PonderNet, Medusa) covers components but not the specific trained-in stop-token-as-architecture-gate |
| N2 (Prefill/decode split) | PURSUE | Splitwise and DistServe validate the operational benefit; architectural-level split (vs. system-level) is the novel angle |
| N3 (Block-diffusion AR decoder) | INVESTIGATE | BD3-LM and LLaDA are close prior art; the AR-across-blocks + diffusion-within-block combination at architecture level has novelty |
| N4 (Combined N1+N2+N3) | INVESTIGATE | Synergy benefit is plausible but compounding complexity; depends on N2 and N3 independently proving out first |

### LoRA FLOPs Reference at r=d/4

```
Dense matmul (d×d): FLOPs = 2d² per token

Case 2 (W_core + A·B unmerged):
  W_core: 2d²
  A (d×r): 2dr = 2d²/4 = d²/2
  B (r×d): 2rd = d²/2
  Total: 2d² + d² = 3d²  ← 1.5× MORE than dense

Case 3 (pure A·B unmerged):
  A (d×r): 2dr = d²/2
  B (r×d): 2rd = d²/2
  Total: d²  ← 0.5× of dense (2× FASTER)

Training FLOPs (forward + backward, Case 3):
  ≈ 3d² per matmul vs dense ≈ 6d²  ← ~0.5× training FLOPs
```

### LoRA Bandwidth Reference at r=d/4, bf16

```
Dense: d² × 2 bytes per matrix per token
Case 2: (d² + d²/4 + d²/4) × 2 = 1.5d² × 2  ← 1.5× MORE
Case 3: (d²/4 + d²/4) × 2 = d²/2 × 2          ← 2× FEWER

CoLA empirical (≤7B): 1.64× throughput (not 2× due to non-GEMM ops ≈18% of time)
  1/(0.18 + 0.82/2) ≈ 1.64×  ✓
```

### Layer Pruning Reference Figures (at p=0.75, 25% pruning)

```
TTFT reduction:
  A1 at 8K context: MLP fraction ≈ 90% → TTFT ≈ 0.75× baseline ✓
  A2 at 8K context: MLP fraction ≈ 85% → TTFT ≈ 0.75× baseline ✓
  Caveat: only when full layers (both attn + MLP) are pruned uniformly

TPOT reduction (batch=1):
  Active weight bytes → p × baseline bytes → TPOT ≈ p = 0.75× ✓

Quality degradation references (ShortGPT post-hoc, without fine-tune):
  LLaMA 2-7B: 27.1% pruned, MMLU 45.39→43.96 (−3.2% relative)
  LLaMA 2-13B: 24.6% pruned, MMLU 55.00→54.69 (−0.6% relative)

GateSkip quality retention (dynamic gates, with calibration):
  Llama-3.1-8B at 25% savings: >90% baseline accuracy ✓
  Llama-3.2-1B at 25% savings: 26.8%→19.8% (sharp cliff at small scale)

TPOT/TTFT under static scenarios:
  Scenario A (frozen soft gates): no speedup
  Scenario B (frozen hard gates + conditional execution): speedup minus branch overhead
    (static branch on GPU ≈ zero overhead since all tokens take same path)
  Scenario C (model surgery): speedup exactly proportional to p
```

### Expected Speedup at p=0.75 (25% pruning), batch=1

```
TPOT: 0.75× baseline (bandwidth-bound; weight bytes ∝ active layers)
TTFT: ~0.75× baseline (MLP-dominated at s≤8K; compute ∝ active layers)

Note: Speedup is exactly proportional to p only under model surgery.
Under frozen soft gates (Scenario A): no speedup.
Under frozen hard gates with conditional execution (Scenario B): speedup minus branch overhead
  (static branch on GPU ≈ zero overhead since all tokens take same path).
```

### Scalar Gate Training Overhead Reference

```
Extra FLOPs from scalar gates (L=64, batch=1, s=2048):
  Gate multiplies: 64 × 2048 = 131,072 scalar FLOPs
  Baseline A2 MLP FLOPs: 64 × 6 × 5120 × 25600 × 2048 ≈ 10^15 FLOPs
  Overhead fraction: 131K / 10^15 ≈ 1.3 × 10^-10 → effectively 1.00×

For comparison: Hyper-Connections SHC (n=4 expansion):
  Per layer: n × d^2 = 4 × 5120^2 ≈ 105M extra FLOPs per layer
  Over 64 layers: 6.7B extra FLOPs
  Overhead: 6.7B / 10^15 × 64 ≈ 10^-4 per layer → ~1.05-1.15× total ✓
```

### Model Surgery Implementation Recipe (PyTorch)

```python
# After training with soft scalar gates
import torch
import torch.nn as nn

# Step 1: Extract gate values
gate_values = {i: torch.sigmoid(model.gate_logits[i]).item()
               for i in range(len(model.layers))}

# Step 2: Identify layers to keep
threshold = 0.5
active_indices = [i for i, g in gate_values.items() if g >= threshold]
pruned_indices = [i for i, g in gate_values.items() if g < threshold]
p_active = len(active_indices) / len(model.layers)

print(f"Keeping {len(active_indices)}/{len(model.layers)} layers (p={p_active:.2f})")
print(f"Pruned layers: {pruned_indices}")

# Step 3: Model surgery
model.layers = nn.ModuleList([model.layers[i] for i in active_indices])

# Step 4: Remove gate infrastructure
if hasattr(model, 'gate_logits'):
    del model.gate_logits

# Step 5: Save pruned model
torch.save(model.state_dict(), f"model_p{p_active:.2f}.pt")

# Inference: identical to a model designed with len(active_indices) layers
# Zero per-token overhead, zero branching, zero gate compute
```

### Soft Gate Training Recipe (Standard)

```python
# Initialize gate logits to -2 (sigmoid(-2) ≈ 0.12)
# Gates start mostly passing-through, then regularization pushes toward 0 or 1
gate_logits = nn.Parameter(torch.full((num_layers,), -2.0))

# Adaptive L1 sparsity loss
def gate_loss(logits, target_sparsity=0.25, lambda_max=0.01):
    gates = torch.sigmoid(logits)
    active_fraction = gates.mean()
    lambda_t = lambda_max * max(0, active_fraction - (1 - target_sparsity))
    return lambda_t * gates.sum()

# Training loop addition:
L_total = L_task + gate_loss(gate_logits)
```

### Go/No-Go Ablation Design (Layer Pruning variant)

```
Four 1B–3B scale training runs on same data (50B tokens):
  1. Dense baseline
  2. ShortGPT BI post-hoc pruning at 25%, no recovery fine-tune
  3. ShortGPT BI post-hoc pruning at 25%, with 5% recovery fine-tune
  4. Soft-gate training (p_target=0.75) → threshold → model surgery

Pass criterion: Model 4 quality within 2% of Model 1 (dense) at same inference cost
Key question: Does gate-aware training (Model 4) outperform post-hoc pruning (Model 3)?
Compute cost: ~4 A100-weeks
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas | 31 AI architecture ideas (sections 1–5 plus 4.7) | Qwen3.5-27B Hybrid, Qwen3-32B Dense, Qwen3.5-397B-A17B MoE baselines |
| ArchIdeas | 4 new ideas (N1–N4) added to existing 31-idea corpus | research_6_1 through research_6_4 produced by parallel Myrmidon swarms; all 4 included in final LaTeX paper |
| ArchIdeas | 39-idea corpus merge (Phase B) | review_*.md + summary_*.md + 5× verification_*.md merged into 39 unified research_*.md files; 195 merged verification files produced; synthesis docs regenerated |
| ArchIdeas | 39-idea corpus accuracy review-and-fix pass (Phase C) | In-place surgical fix pass on all 39 research_X_Y.md; no output files; verdicts out of scope. Baseline C (K2 Family / LLM360): L=80, d=8192, d_ff=28672, H_q=64, H_kv=8, head_dim=128, vocab=250112; K2-V2 ctx=524288, K2-Think-V2 ctx=262144; KV @ 32K≈10.0 GiB, @ 262K≈80.0 GiB, @ 524K≈160.0 GiB |
| ArchIdeas | 39-idea corpus verdict removal pass (Phase D) | Removed all verdict-related content (PURSUE/INVESTIGATE/DEPRIORITIZE tokens, Final Verdict sections, Prior Art Classification status lines, verdict-adjacent impact/effort/confidence bullets) from all 39 research_X_Y.md files; all technical content preserved; two-wave execution (17+22) |
| ArchIdeas research | Myrmidon swarm review of idea 4.3 (LoRA Everywhere), 5 parallel sub-agents | `/home/mvillmow/Random/ArchIdeas/research/review_4_3_lora_everywhere.md` |
| ArchIdeas research | Myrmidon swarm review of idea 4.5 (Learned Residual Flow Control), 5 parallel sub-agents | `/home/mvillmow/Random/ArchIdeas/research/review_4_5_learned_residual_flow.md` |
| ArchIdeas research | Idea 4.5 (Learned Residual Flow Control) review, sub-agent B complexity audit — static-at-inference model surgery pattern | `/home/mvillmow/Random/ArchIdeas/research/verification_4_5_complexity.md` §B.2 |
