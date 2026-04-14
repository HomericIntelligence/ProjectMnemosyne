---
name: arch-research-doc-lora-review-pattern
description: "Myrmidon swarm review pattern for AI architecture research documents covering low-rank parameterization, complexity analysis, citation verification, and inference benefit claims. Use when: (1) reviewing research/summary docs for ideas involving weight factorization or LoRA-style parameterization, (2) validating Big-O complexity tables in transformer architecture research, (3) auditing inference speedup claims (merged vs unmerged, compute-bound vs bandwidth-bound), (4) verifying that training and inference benefit claims are internally consistent across cases."
category: architecture
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [arch-research, lora, low-rank, complexity-audit, citation-verification, inference, myrmidon, swarm-review]
---

# Architecture Research Doc Review: LoRA / Low-Rank Parameterization Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Parallel Myrmidon swarm review of AI architecture research document for idea 4.3 (LoRA Everywhere) — 5 specialist agents covering citations, complexity, literature gaps, comparison validation, and feasibility |
| **Outcome** | Operational — produced 5 verification files and final review document with 2 material complexity errors corrected, 1 suspect citation flagged, 1 critical missing competitor (Monarch matrices) identified, and TTFT direction error fixed |
| **Verification** | verified-local — review documents produced and internally consistent; no CI involved |

## When to Use

- Reviewing any research or summary document that involves low-rank factorization of weight matrices (LoRA, matrix decomposition, rank-r parameterization)
- Validating claims about inference speedup from weight factorization — especially "merged vs unmerged" distinctions
- Auditing complexity tables in transformer architecture papers or internal research docs
- Any document that uses GaLore, CoLA, WeLore, or similar citations as evidence for training or inference benefits
- When a research doc presents multiple parameterization cases (e.g., W = W_core + A·B vs W = A·B) without cleanly labeling which claim applies to which case

**Trigger phrases**: "LoRA everywhere", "low-rank pre-training", "native LoRA parameterization", "W = W_core + A·B", "merged vs unmerged inference", "rank-r factorization pre-training"

**Red flags that require this skill's checklist**:
- Document claims both TTFT penalty AND throughput improvement for the same "unmerged" path
- Document cites GaLore's optimizer state reduction to support LoRA weight parameter reduction (different mechanisms)
- Document cites dLoRA (course PDF) as evidence of inference overhead
- "Unmerged" rows in tables don't specify whether W_core is present or absent
- Training cost claim assumes optimizer savings without checking whether W_core is also being trained

## Verified Workflow

> **Note:** This is a review methodology checklist, not executable code. Verified locally on the LoRA Everywhere (4.3) research document review session.

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

### Detailed Steps

#### Step 1: Identify the Parameterization Cases (Before Any Analysis)

For any W = W_core + A·B document, ALWAYS distinguish three cases before analyzing any claim:

| Case | Formula | W_core | Expected Benefit |
|------|---------|--------|-----------------|
| Case 1: Merged | W_full = W_core + A·B materialized | Any | ZERO inference benefit — identical to dense |
| Case 2: Unmerged, W_core present | x·W_core + (x·A)·B | Present | 1.5× MORE bandwidth and FLOPs than dense — a regression |
| Case 3: Unmerged, W_core absent | (x·A)·B only | Absent | 2× fewer weight bytes, ~1.64× TPOT improvement |

**Every claim in the document must specify which case it applies to.** If it doesn't, that is a red flag.

#### Step 2: Complexity Table Audit Checklist

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

#### Step 3: Citation Verification Checklist

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

#### Step 4: Literature Gap Checklist

For any low-rank parameterization research doc, check whether these are cited:

- [ ] **Monarch matrices** (Dao et al., 2022, NeurIPS, arXiv 2204.00595) — structured factorization competitor, O(d log d) params vs O(dr) for LoRA; achieves higher expressiveness at similar compression
- [ ] **Scale laws for low-rank pre-training** — does quality gap grow or shrink with scale?
- [ ] **LoRA-GA** (gradient-aligned initialization) — addresses A·B initialization for pre-training
- [ ] **Sheared LLaMA** (Xia et al., 2023) — competing paradigm: train dense then compress, vs train compressed
- [ ] **FWSVD** (Fisher-weighted SVD) — post-hoc compression baseline for comparison

#### Step 5: Inference Regime Disambiguation

**ALWAYS verify which inference regime each speedup claim applies to:**

| Regime | Characteristic | Who benefits |
|--------|---------------|-------------|
| Batch=1 decode | Bandwidth-bound — TPOT proportional to bytes loaded | Case 3 (pure A·B): ~1.64× faster |
| Large-batch decode | Compute-bound — TPOT proportional to FLOPs | No benefit (FLOPs same or higher) |
| Prefill (any batch) | Compute-bound — TTFT proportional to FLOPs | Case 3 (pure A·B): ~2× faster |
| Multi-request serving | Mixed — dLoRA's measurement regime | Case 2 (W_core+A·B): +38.9% overhead |

**The dLoRA 38.9% overhead and CoLA 1.64× speedup are BOTH CORRECT — they measure different cases in different regimes. Never apply one to the context of the other.**

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treating "unmerged" as a single case | Research doc had a single "unmerged" row covering all three cases | TTFT and TPOT values were contradictory (one showed penalty, other showed speedup) | Always split into Case 1/2/3 before populating any table |
| Using GaLore optimizer savings to quantify LoRA Everywhere training benefit | Doc cited GaLore Table 1 (65.5%) to support LoRA Everywhere (50%) | Different mechanisms: GaLore reduces gradient states; LoRA reduces weight parameters | Cite separately; note that GaLore 65.5% beats LoRA Everywhere 50% for optimizer state alone |
| Applying dLoRA 38.9% to TPOT (batch=1 decode) | Complexity table used 38.9% overhead as TPOT estimate | dLoRA measures compute-bound multi-request; TPOT at batch=1 is bandwidth-bound | dLoRA measurement is only valid for Case 2 in compute-bound serving |
| Assuming TTFT is penalized for the case with inference benefit | Summary doc said "1.5× slower TTFT" for all unmerged cases | Pure A·B (Case 3) actually has 2× FASTER TTFT (half the FLOPs) | The TTFT penalty only applies to Case 2 (W_core present), which has no deployment value |
| Not distinguishing whether W_core is trained or frozen | Training cost claim assumed 50% optimizer savings | If W_core is also trained from scratch, optimizer memory is 1.5× MORE than dense | Explicitly state: optimizer savings ONLY if W_core is frozen or absent |

## Results & Parameters

### FLOPs Reference at r=d/4

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

### Bandwidth Reference at r=d/4, bf16

```
Dense: d² × 2 bytes per matrix per token
Case 2: (d² + d²/4 + d²/4) × 2 = 1.5d² × 2  ← 1.5× MORE
Case 3: (d²/4 + d²/4) × 2 = d²/2 × 2          ← 2× FEWER

CoLA empirical (≤7B): 1.64× throughput (not 2× due to non-GEMM ops ≈18% of time)
  1/(0.18 + 0.82/2) ≈ 1.64×  ✓
```

### Optimizer State Reference

```
Dense Adam: 2 × d² per matrix = 2d²
Case 3 (pure A·B, only A+B tracked): 2 × d²/2 = d²  ← 50% reduction ✓
Case 2 (W_core + A + B all tracked): 2 × 1.5d² = 3d²  ← 50% MORE than dense ✗
Case 1 (W_core frozen, A+B tracked): 2 × d²/2 = d²    ← 50% reduction ✓ (fine-tuning only)
```

### Non-Uniform Rank Allocation (WeLore-informed, for quality parity)

```
Q/K projections:    r ≈ 0.05–0.1 × d  (tolerate ≥90% rank reduction)
V projection:       r ≈ 0.4 × d        (resists compression)
MLP up/gate:        r ≈ 0.2–0.25 × d
MLP down:           r ≈ 0.4 × d        (resists compression)

Effective avg r ≈ 0.25 × d  (similar to CoLA's r=d/4 overall, but non-uniform per type)
```

### Go/No-Go Ablation Design

```
Four 1B-parameter training runs on same data:
  1. Dense baseline
  2. CoLA (A·B + σ, uniform r=d/4)       ← quality reference
  3. Linear A·B, uniform r=d/4            ← pessimistic test
  4. Linear A·B, non-uniform WeLore-rank  ← primary hypothesis

Pass criterion: Model 4 PPL within 2% of Model 1 (dense)
Compute cost: ~1–2 A100-weeks
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas research | Myrmidon swarm review of idea 4.3 (LoRA Everywhere), 5 parallel sub-agents | `/home/mvillmow/Random/ArchIdeas/research/review_4_3_lora_everywhere.md` |
