---
name: arch-research-doc-lora-review-pattern
description: "Myrmidon swarm review pattern for AI architecture research documents covering low-rank parameterization, layer pruning/residual gating, complexity analysis, citation verification, and inference benefit claims. Use when: (1) reviewing research/summary docs for ideas involving weight factorization or LoRA-style parameterization, (2) reviewing ideas involving learned layer skipping, residual gating, or static-at-inference pruning, (3) validating Big-O complexity tables in transformer architecture research, (4) auditing inference speedup claims (merged vs unmerged, frozen gates vs model surgery, compute-bound vs bandwidth-bound), (5) verifying that training and inference benefit claims are internally consistent across cases."
category: architecture
date: 2026-04-13
version: "1.1.0"
user-invocable: false
verification: verified-local
history: arch-research-doc-lora-review-pattern.history
tags: [arch-research, lora, low-rank, complexity-audit, citation-verification, inference, myrmidon, swarm-review, layer-pruning, residual-gating, static-inference]
---

# Architecture Research Doc Review: LoRA / Low-Rank + Layer Pruning / Residual Gating Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-13 |
| **Objective** | Parallel Myrmidon swarm review of AI architecture research documents for ideas involving (a) low-rank parameterization or (b) layer pruning / residual gating |
| **Outcome** | Operational — verified on idea 4.3 (LoRA Everywhere) and idea 4.5 (Learned Residual Flow Control), producing 5 verification files + final review per idea |
| **Verification** | verified-local — review documents produced and internally consistent; no CI involved |
| **History** | [changelog](./arch-research-doc-lora-review-pattern.history) |

## When to Use

**LoRA / Low-Rank variant:**
- Reviewing any research or summary document that involves low-rank factorization of weight matrices (LoRA, matrix decomposition, rank-r parameterization)
- Validating claims about inference speedup from weight factorization — especially "merged vs unmerged" distinctions
- Any document that uses GaLore, CoLA, WeLore, or similar citations as evidence for training or inference benefits

**Layer Pruning / Residual Gating variant:**
- Reviewing any research or summary document that involves learned gates on residual streams, layer-level pruning, or "static at inference" skip decisions
- Validating TTFT/TPOT claims for layer pruning ideas (ShortGPT, GateSkip, Mixture of Depths)
- Any document that claims "static at inference time" speedup from frozen gates
- Any document describing synergy between layer-pruning ideas (e.g., idea 4.4 Skip List Layers + idea 4.5 Learned Residual Flow)

**Red flags that require this skill's checklist (LoRA):**
- Document claims both TTFT penalty AND throughput improvement for the same "unmerged" path
- Document cites GaLore's optimizer state reduction to support LoRA weight parameter reduction (different mechanisms)
- Document cites dLoRA (course PDF) as evidence of inference overhead
- "Unmerged" rows in tables don't specify whether W_core is present or absent
- Training cost claim assumes optimizer savings without checking whether W_core is also being trained

**Red flags that require this skill's checklist (Layer Pruning):**
- Document claims "static at inference" speedup from frozen gates without specifying model surgery
- Document attributes 1.05–1.15× training overhead to scalar gates (correct range is ~1.00×; that range belongs to Hyper-Connections SHC matrix expansion)
- Document lacks a citation for Mixture of Depths [Raposo et al., 2024, arXiv:2404.02258]
- Document cites "Frankle and Carlin" instead of "Frankle and Carbin" (Lottery Ticket Hypothesis)
- Document claims idea 4.4 (Skip List Layers) and idea 4.5 (Residual Flow) "combine well" without noting order-dependency
- Any 2026 arXiv ID without a "URL not verified" marker

## Verified Workflow

> **Note:** This is a review methodology checklist, not executable code. Verified locally on idea 4.3 (LoRA Everywhere) and idea 4.5 (Learned Residual Flow Control) review sessions.

### Quick Reference

```
Five-agent parallel review:
  A — Citation Verifier    → verification_<id>_citations.md
  B — Complexity Auditor   → verification_<id>_complexity.md
  C — Literature Gap Finder → verification_<id>_literature.md
  D — Comparison Validator → verification_<id>_comparison.md
  E — Feasibility Checker  → verification_<id>_feasibility.md
  F — Synthesizer (Wave 2) → review_<id>_<name>.md
```

### Detailed Steps — LoRA / Low-Rank Variant

#### Step 1: Identify the Parameterization Cases (Before Any Analysis)

For any W = W_core + A·B document, ALWAYS distinguish three cases before analyzing any claim:

| Case | Formula | W_core | Expected Benefit |
| ------ | --------- | -------- | ----------------- |
| Case 1: Merged | W_full = W_core + A·B materialized | Any | ZERO inference benefit — identical to dense |
| Case 2: Unmerged, W_core present | x·W_core + (x·A)·B | Present | 1.5× MORE bandwidth and FLOPs than dense — a regression |
| Case 3: Unmerged, W_core absent | (x·A)·B only | Absent | 2× fewer weight bytes, ~1.64× TPOT improvement |

**Every claim in the document must specify which case it applies to.** If it doesn't, that is a red flag.

#### Step 2: Complexity Table Audit Checklist (LoRA)

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

#### Step 3: Citation Verification Checklist (LoRA)

For any document citing papers about LoRA or low-rank training, verify:

| Citation | What to Check |
| ---------- | -------------- |
| GaLore (Zhao et al., 2024) | Verify: reduces GRADIENT optimizer states; weights remain full-rank. Do NOT use to support weight parameter reduction in LoRA Everywhere. |
| CoLA (Liu et al., 2025) | Verify: has nonlinearity σ between A and B. Claims are valid only at ≤7B. EMNLP 2025 venue is plausible. |
| WeLore (Wei et al., 2025) | Verify: post-training compression study (not pre-training). Uniform 50% rank → PPL 1836.62; non-uniform → 11.87 for LLaMA-2 7B. |
| dLoRA (Princeton course PDF) | Flag as grey literature (non-peer-reviewed course syllabus). The 38.9% overhead measures W_core+A·B compute-bound — NOT pure A·B bandwidth-bound. Do not cross-apply. |
| GaLore 2 (Su et al., 2025) | Treat as SUSPECT: vague author list, modest claimed improvement (~6% memory reduction vs GaLore 1's 65.5%), possible Llama 7B/8B inconsistency. |
| SLTrain (Cichocki et al., 2024) | Verify: low-rank alone fails at pre-training; needs sparse correction. Analogous to W_core in idea 4.3 serving as full-rank anchor. |
| Flora (Hao et al., 2024) | Key insight: fixed A·B (no rotation) is inferior to full-rank training. W_core or nonlinearity serves same role as Flora's rotation. |

#### Step 4: Literature Gap Checklist (LoRA)

For any low-rank parameterization research doc, check whether these are cited:

- [ ] **Monarch matrices** (Dao et al., 2022, NeurIPS, arXiv 2204.00595) — structured factorization competitor, O(d log d) params vs O(dr) for LoRA; achieves higher expressiveness at similar compression
- [ ] **Scale laws for low-rank pre-training** — does quality gap grow or shrink with scale?
- [ ] **LoRA-GA** (gradient-aligned initialization) — addresses A·B initialization for pre-training
- [ ] **Sheared LLaMA** (Xia et al., 2023) — competing paradigm: train dense then compress, vs train compressed
- [ ] **FWSVD** (Fisher-weighted SVD) — post-hoc compression baseline for comparison

#### Step 5: Inference Regime Disambiguation (LoRA)

**ALWAYS verify which inference regime each speedup claim applies to:**

| Regime | Characteristic | Who benefits |
| -------- | --------------- | ------------- |
| Batch=1 decode | Bandwidth-bound — TPOT proportional to bytes loaded | Case 3 (pure A·B): ~1.64× faster |
| Large-batch decode | Compute-bound — TPOT proportional to FLOPs | No benefit (FLOPs same or higher) |
| Prefill (any batch) | Compute-bound — TTFT proportional to FLOPs | Case 3 (pure A·B): ~2× faster |
| Multi-request serving | Mixed — dLoRA's measurement regime | Case 2 (W_core+A·B): +38.9% overhead |

**The dLoRA 38.9% overhead and CoLA 1.64× speedup are BOTH CORRECT — they measure different cases in different regimes. Never apply one to the context of the other.**

---

### Detailed Steps — Layer Pruning / Residual Gating Variant

#### Step 1: "Static at Inference" Implementation Path Audit

**CRITICAL**: Documents claiming "static at inference time" speedup MUST specify the implementation path. There are two paths; only one delivers the claimed speedup:

| Path | Description | Inference speedup? |
| ------ | ------------- | ------------------- |
| Frozen soft gates | Gates g_i ∈ (0,1) frozen after training; layer still computes F_i(x) then multiplies by g_i | **NONE** — layer executes fully; only one scalar multiply saved |
| Model surgery | After training, identify zero-gate layers (g_i < 0.5), physically remove them from model graph, reindex | **REAL** — identical to a model originally designed with L·p layers; zero per-token overhead |

**The inference speedup claim is ONLY valid when model surgery is performed.** Flag any document that claims speedup from frozen gates without specifying surgery.

#### Step 2: TTFT/TPOT Claim Verification (Layer Pruning)

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

**Red flag**: Document attributes different TTFT/TPOT ratios to different baseline models without noting that the same p=0.75 applies to all — if ratios differ, check whether different p values are assumed.

#### Step 3: Training Overhead Verification (Layer Pruning)

**Gate type → training overhead mapping:**

| Gate type | Extra FLOPs per forward pass | Training overhead |
| ----------- | ------------------------------ | ------------------- |
| Scalar gate per layer (L scalars) | L × batch_size × seq_len scalar ops | ~1.00× (negligible — <0.01% of baseline) |
| Vector gate per layer (L × d vectors) | L × d × batch_size × seq_len scalar ops | ~1.00× (still negligible vs d·d_ff matmuls) |
| Hyper-Connections SHC (n × d expansion matrix) | n × d² per layer | 1.05–1.15× (measurable overhead) |

**Do NOT attribute the 1.05–1.15× Hyper-Connections SHC overhead to scalar or vector gates.**
> Source: **[Zhu et al., 2024]** — §"Static Hyper-Connections (SHC)" (arXiv:2409.19606)
> Scalar gate training overhead: **[derived from first principles]** — 64 gates × 2048 seq_len = 131K scalar FLOPs vs ~10^15 baseline = 10^-10 fraction.

#### Step 4: Citation Checklist (Layer Pruning)

For any document about learned layer skipping, residual gating, or static pruning, verify:

| Citation | What to Check |
| ---------- | -------------- |
| Mixture of Depths (Raposo et al., 2024, arXiv:2404.02258) | **CRITICAL MISSING CHECK** — MoD is the closest prior art for learned skip decisions at scale. If not cited, flag as significant gap. Note: MoD is DYNAMIC (per-token); idea 4.5 is STATIC — this distinction preserves PARTIAL novelty. |
| LayerDrop (Fan et al., 2020, arXiv:1909.11556) | Foundational work on training transformers to be robust to layer dropping. If not cited, flag as important gap. Note: LayerDrop is RANDOM (not learned); idea 4.5 learns the optimal static pattern. |
| ShortGPT (Men et al., 2024, arXiv:2403.03853) | Block Influence (BI) metric proves 24–27% of layers are redundant. Quality claims: LLaMA 2-7B: 27.1% pruned MMLU 45.39→43.96 (−3.2%); LLaMA 2-13B: 24.6% pruned MMLU 55.00→54.69 (−0.6%). Verify math: 45.39→43.96 = −1.43 abs = −3.15% relative ✓ |
| GateSkip (Laitenberger et al., 2024, arXiv:2510.13876) | Validates learned gating principle with adaptive regularization. Correct table refs: Table 1 (1B quality), Table 6 (8B quality), Table 10 (throughput). |
| Frankle and Carbin, 2019 (ICLR, arXiv:1803.03635) | **AUTHOR NAME CHECK** — Correct name is "Carbin" not "Carlin". Second author is Michael Carbin (MIT CSAIL). This misspelling recurs in multiple docs. |
| Any arXiv ID from 2026 | Flag as HIGH RISK — must verify URL resolves. Add "URL not verified" marker if not fetched. |

#### Step 5: 4.4 + 4.5 Composition Audit

When a layer-pruning document claims synergy with Skip List Layers (idea 4.4):

**The composition is ORDER-DEPENDENT:**

| Order | Composability | Notes |
| ------- | -------------- | ------- |
| 4.5 first (determine survivors), then 4.4 (apply skip topology to survivors) | CLEAN — 4.4 operates on the pruned architecture with known layer count | Requires sequential training |
| 4.4 first (set skip intervals), then 4.5 (prune) | BROKEN — pruning a layer that is an anchor for a 4.4 skip connection breaks the topology | Skip intervals must be recomputed after pruning |
| Joint training | COMPLEX — 4.4 skip connections may help gradient flow past near-zero gates; possible positive interaction but requires careful design | Not cleanly validated |

**"Combines well with 4.4" claims should be qualified as "combines well if 4.5 gating is applied first."**

#### Step 6: Baseline Formula Audit (Layer Pruning)

Check the complexity tables against these known issues:

| Formula | Common Error | Correct |
| --------- | ------------- | --------- |
| Weight memory | O(p·L·d·d_ff + L·d) — missing attention weights | O(p·L·(d·d_ff + d²) + L·d) |
| Bandwidth (A1 hybrid) | O(p·L·(d²+s·d_kv/4)) — missing MLP loading | O(p·L·(d²+d·d_ff+s·d_kv/4)) |
| Baseline B compute | O(L·(d²+k·d·d_e)) — missing global-attn term | O(L·(d²+s·d/4+k·d·d_e)) for B's 25% global-attn layers |
| Context window heading | "32K tokens" for A1/B | A1 and B: 262,144; A2: 40,960 |

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Treating "unmerged" as a single case (LoRA) | Research doc had a single "unmerged" row covering all three cases | TTFT and TPOT values were contradictory (one showed penalty, other showed speedup) | Always split into Case 1/2/3 before populating any table |
| Using GaLore optimizer savings to quantify LoRA Everywhere training benefit | Doc cited GaLore Table 1 (65.5%) to support LoRA Everywhere (50%) | Different mechanisms: GaLore reduces gradient states; LoRA reduces weight parameters | Cite separately; note that GaLore 65.5% beats LoRA Everywhere 50% for optimizer state alone |
| Applying dLoRA 38.9% to TPOT (batch=1 decode) | Complexity table used 38.9% overhead as TPOT estimate | dLoRA measures compute-bound multi-request; TPOT at batch=1 is bandwidth-bound | dLoRA measurement is only valid for Case 2 in compute-bound serving |
| Assuming TTFT is penalized for the case with inference benefit (LoRA) | Summary doc said "1.5× slower TTFT" for all unmerged cases | Pure A·B (Case 3) actually has 2× FASTER TTFT (half the FLOPs) | The TTFT penalty only applies to Case 2 (W_core present), which has no deployment value |
| Not distinguishing whether W_core is trained or frozen | Training cost claim assumed 50% optimizer savings | If W_core is also trained from scratch, optimizer memory is 1.5× MORE than dense | Explicitly state: optimizer savings ONLY if W_core is frozen or absent |
| Claiming "static at inference" speedup from frozen soft gates (Layer Pruning) | Research doc described frozen gates as achieving inference speedup | Frozen soft gates still execute the full layer computation; only model surgery (physical layer removal) produces real speedup | Always distinguish: frozen gates = no speedup; model surgery = speedup |
| Attributing 1.05–1.15× training overhead to scalar gates (Layer Pruning) | Doc cited Hyper-Connections SHC overhead range for scalar gate overhead | SHC uses n × d expansion matrix (~10M extra FLOPs/layer); scalar gates add ~64 scalar ops total | 1.05–1.15× is correct for SHC; scalar gates are ~1.00× (< 0.01% overhead) |
| Missing Mixture of Depths as critical prior art (Layer Pruning) | Literature review omitted MoD despite it being the closest related work for learned layer skipping | MoD demonstrates per-token hard binary skip decisions at 6B+ scale; without it, novelty claim is incomplete | Always check for MoD [Raposo et al., 2024, arXiv:2404.02258] as first citation for any "learned layer skip" idea |
| Misspelling Lottery Ticket author name (Layer Pruning) | "Frankle and Carlin" appeared in multiple docs | Correct name is Michael Carbin (MIT CSAIL), not "Carlin" | Add to citation checklist: always verify second author of LTH = Carbin |
| Claiming 4.4 + 4.5 "combine well" without qualification (Layer Pruning) | Research doc stated both ideas synergize without noting composition order | 4.4 first → 4.5 second breaks skip-interval anchor points; composition is order-dependent | Qualify: "combines well if 4.5 gating (layer selection) is applied before 4.4 (connectivity topology)" |

## Results & Parameters

### FLOPs Reference at r=d/4 (LoRA variant)

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

### Bandwidth Reference at r=d/4, bf16 (LoRA variant)

```
Dense: d² × 2 bytes per matrix per token
Case 2: (d² + d²/4 + d²/4) × 2 = 1.5d² × 2  ← 1.5× MORE
Case 3: (d²/4 + d²/4) × 2 = d²/2 × 2          ← 2× FEWER

CoLA empirical (≤7B): 1.64× throughput (not 2× due to non-GEMM ops ≈18% of time)
  1/(0.18 + 0.82/2) ≈ 1.64×  ✓
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
| ArchIdeas research | Myrmidon swarm review of idea 4.3 (LoRA Everywhere), 5 parallel sub-agents | `/home/mvillmow/Random/ArchIdeas/research/review_4_3_lora_everywhere.md` |
| ArchIdeas research | Myrmidon swarm review of idea 4.5 (Learned Residual Flow Control), 5 parallel sub-agents | `/home/mvillmow/Random/ArchIdeas/research/review_4_5_learned_residual_flow.md` |
