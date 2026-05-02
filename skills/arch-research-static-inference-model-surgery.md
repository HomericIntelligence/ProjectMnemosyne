---
name: arch-research-static-inference-model-surgery
description: "Pattern for analyzing 'static at inference time' claims in architecture research. A frozen gate does NOT produce inference speedup — only physical model surgery (layer removal) does. Use when: (1) a research doc claims 'static at inference' speedup from frozen gates or gating decisions, (2) validating TPOT/TTFT claims for any idea where layers or operations are 'frozen' after training, (3) auditing whether 'no per-token overhead' is truly achievable from a frozen architectural decision."
category: architecture
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [static-inference, model-surgery, frozen-gates, residual-gating, layer-pruning, tpot, ttft, speedup-claim]
---

# Static-at-Inference Speedup Requires Model Surgery, Not Frozen Gates

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-13 |
| **Objective** | Clarify the implementation requirement for "static at inference time" speedup claims in architecture research about learned gating / layer pruning |
| **Outcome** | Operational pattern — identified and documented while reviewing idea 4.5 (Learned Residual Flow Control) in the ArchIdeas research series |
| **Verification** | verified-local — analysis from first principles, consistent with PyTorch execution model |

## When to Use

- A research document claims a mechanism is "static at inference time" and therefore has zero per-token overhead
- A document describes frozen gates, frozen routing weights, or frozen skip decisions as producing inference speedup
- Any idea where architectural decisions are learned during training and then "frozen" — and the document claims this produces a faster model at inference time
- Reviewing DenseFormer-style ideas (learned depth weights frozen post-training) vs hard-gate pruning ideas

**Key question to always ask:** "What exactly happens to the frozen gate VALUE at inference time?"

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end in CI. It is a checklist derived from first principles and verified locally against the inference execution model of PyTorch/JAX.

### Quick Reference

```
For any "static at inference" claim, determine which scenario applies:

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

### Detailed Steps

#### Step 1: Identify the Claimed Speedup Path

Read the document's §5 (Implementation) or inference section. Find the answer to:
1. After training, are gates soft (continuous) or hard (binary)?
2. What happens to the gate mechanism at inference: kept frozen, thresholded, or removed?
3. Does the document describe model surgery (deleting zero-gate layers)?

#### Step 2: Map Claim to Scenario

| What the document says | Which scenario | Real speedup? |
| ----------------------- | ---------------- | -------------- |
| "Gates are frozen after training" (no further detail) | Scenario A | NO — gates are frozen but layers still execute |
| "Zero-gate layers are skipped" | Scenario B | YES — conditional execution with static branch |
| "Layers with g < 0.5 are removed from the checkpoint" | Scenario C | YES — true model surgery |
| "Static, so no per-token overhead" WITHOUT specifying mechanism | AMBIGUOUS — flag for clarification | UNKNOWN until clarified |

#### Step 3: Pre-Norm Interaction Check

For models using Pre-LN (like Qwen3/3.5 with RMSNorm before sublayers):
```
Standard pre-norm: x_{i+1} = x_i + F_i(RMSNorm(x_i))
With soft gate:    x_{i+1} = x_i + g_i · F_i(RMSNorm(x_i))
```
If g_i = 0 but the code is not conditioned on it, RMSNorm runs and F_i runs — both are wasted.

**Model surgery resolves this completely** — the entire layer (norm + sublayer) is removed, so neither runs.

#### Step 4: Framework Feasibility Check

| Framework | Model surgery feasibility |
| ----------- | -------------------------- |
| PyTorch | `nn.ModuleList` can be filtered in-place. `torch.jit.script` or torch.compile() will compile the pruned model with no residual gate infrastructure. FEASIBLE. |
| JAX | `jax.lax.scan` over variable-length list requires refactoring; functional-style layer application over a filtered list works. FEASIBLE with effort. |
| HuggingFace Transformers | Most models use `nn.ModuleList` for layers; filtering is straightforward. Some models have hardcoded layer count in config — requires config update. FEASIBLE. |

#### Step 5: Residual Stream Reindexing

After removing layers [i1, i2, ...] from a 64-layer model:
- The remaining layers form a sequential list: `active_layers = [l for i,l in enumerate(model.layers) if gates[i] > 0.5]`
- Residual connections in standard sequential transformers chain through active layers naturally
- No explicit reindexing of skip connections needed for standard transformers
- **Exception**: If idea 4.4 (Skip List Layers) is also applied, skip connections are position-indexed and must be updated after 4.5 surgery

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Claiming speedup from frozen soft gates | Research doc stated "static at inference, therefore zero overhead" for frozen continuous gate values | Frozen gate is multiplied with layer output — the full layer still computes F_i(x) before the multiply | "Static" means the gate VALUE doesn't change; it does NOT mean the computation is eliminated |
| Conditional execution with per-token gates | Prior work like GateSkip uses dynamic (per-token) gates with conditional execution | Per-token conditional causes SIMD divergence on GPU — different tokens take different branches | Dynamic gates cannot use efficient static branching; only truly static (same for all tokens) gates allow branch prediction optimization |
| Forgetting that pre-norm still runs | Implementation skipped the sublayer but kept the RMSNorm running | RMSNorm cost is ~O(d) per token per layer — small but not zero | Model surgery must remove the entire layer block (norm + attention/MLP), not just the sublayer computation |
| Assuming DenseFormer-style savings | Research doc conflated DenseFormer's frozen DWA weights with hard-zero gate inference | DenseFormer freezes learned AGGREGATION weights (still blends all past representations) — no layer is eliminated, and throughput is actually 22% WORSE than baseline | Frozen learned weights ≠ frozen skip decisions; aggregation weights run at every token regardless of value |

## Results & Parameters

### Implementation Recipe (PyTorch)

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

### Expected Speedup at p=0.75 (25% pruning), batch=1

```
TPOT: 0.75× baseline (bandwidth-bound; weight bytes ∝ active layers)
TTFT: ~0.75× baseline (MLP-dominated at s≤8K; compute ∝ active layers)

Note: Speedup is exactly proportional to p only under model surgery.
Under frozen soft gates (Scenario A): no speedup.
Under frozen hard gates with conditional execution (Scenario B): speedup minus branch overhead
  (static branch on GPU ≈ zero overhead since all tokens take same path).
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

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas research | Idea 4.5 (Learned Residual Flow Control) review, sub-agent B complexity audit | `/home/mvillmow/Random/ArchIdeas/research/verification_4_5_complexity.md` §B.2 |
