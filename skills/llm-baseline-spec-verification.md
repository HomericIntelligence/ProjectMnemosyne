---
name: llm-baseline-spec-verification
description: "Verify LLM baseline model specs from authoritative sources before any quantitative analysis. Use when: (1) starting any research/review task that involves computing KV cache sizes, FLOPs, or memory bandwidth for specific models, (2) using a shared context document with model specs, (3) comparing multiple LLM baselines quantitatively."
category: architecture
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# LLM Baseline Spec Verification

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-13 |
| **Objective** | Establish ground-truth baseline specs before quantitative AI architecture analysis |
| **Outcome** | Found 5 errors in SHARED_PRELUDE.md baseline specs; corrected specs cascaded into 31 research docs and 4 synthesis documents |
| **Verification** | verified-local |

## When to Use

- Starting any task with quantitative claims about specific LLM models (KV cache, FLOPs, memory)
- Using a shared context/prelude document that specifies model architectures
- Comparing multiple LLM baselines in research or review documents
- Identifying which numeric errors are "inherited from prelude" vs. "original author error"

## Verified Workflow

### Quick Reference

```bash
# For Qwen/HuggingFace models -- fetch authoritative config directly
curl -s "https://huggingface.co/Qwen/<model-name>/raw/main/config.json" | python3 -m json.tool

# Key fields to verify:
# - num_hidden_layers (L)
# - hidden_size (d)
# - intermediate_size (d_ff)
# - num_attention_heads (Q heads)
# - num_key_value_heads (KV heads -- use THIS for KV cache formulas, not Q heads!)
# - head_dim (or compute as hidden_size / num_attention_heads)
# - vocab_size
# - max_position_embeddings (native context window)
# - For hybrid models: full_attention_interval, attn_type_list
```

### Detailed Steps

1. **Fetch config.json** for each baseline model from the authoritative source (HuggingFace model hub). Do not trust any intermediary document (shared prelude, command text, prior conversation) until verified against the config.

2. **Extract the 6 critical fields** for KV cache and FLOPs calculations:
   - `num_hidden_layers` (L)
   - `hidden_size` (d)
   - `intermediate_size` (d_ff)
   - `num_key_value_heads` (H_kv -- **use this for KV cache, not Q heads**)
   - `head_dim` (or derive as `hidden_size / num_attention_heads`)
   - `vocab_size`
   - `max_position_embeddings`

3. **For hybrid models** (DeltaNet, Mamba, SSM hybrids), also check:
   - `full_attention_interval` or `attn_type_list` -- which layers are full-attention vs. linear
   - Head counts for each layer type may differ (e.g., DeltaNet V-heads vs. GatedAttn Q/KV heads)

4. **Compute KV cache formula** using verified values:
   ```
   KV_cache = L x 2 x H_kv x head_dim x seq_len x bytes_per_element
   ```
   Where `bytes_per_element = 2` for BF16/FP16. For hybrid models with only partial full-attention layers, multiply by the fraction that use full attention.

5. **Compare against the shared context document**. For each discrepancy, document:
   - What the shared doc says
   - What the authoritative config says
   - Which downstream calculations are affected
   - The magnitude of the error (e.g., "8x overestimate")

6. **Inject canonical specs verbatim** into all agent prompts as "use these, override any prelude values."

### KV Cache Formula Reference

```
# Standard dense transformer (e.g., Qwen3-32B):
KV = L x 2 x H_kv x head_dim x S x 2 bytes

# Hybrid (e.g., Qwen3.5-27B, only every 4th layer is full-attn):
KV = (L/4) x 2 x H_kv x head_dim x S x 2 bytes
# Note: H_kv and head_dim may differ between full-attn and linear-attn layers

# Sparse MoE hybrid (e.g., Qwen3.5-397B, 15/60 global-attn layers):
KV = 15 x 2 x H_kv x head_dim x S x 2 bytes
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting SHARED_PRELUDE.md baseline specs | Used context document's model specs directly without verification | Prelude had 5 errors including vocab 151,936 instead of 248,320 for A1/B, context 32,768 instead of 262,144 for A1/B, GatedAttn head_dim 128 instead of 256, wrong global attention head counts for Baseline B | Always fetch config.json before trusting any secondary spec source |
| Using Q heads for KV cache | Computed KV cache as `L x 2 x H_q x head_dim x S x 2` | GQA models have H_kv << H_q; Qwen3-32B has 64 Q heads but only 8 KV heads, producing 8x overestimate | Always use `num_key_value_heads` (H_kv) in KV cache formula, never `num_attention_heads` |
| Using uniform context across a model family | Assumed all models in a family share the same context window | Qwen3-32B uses 40,960 native context; Qwen3.5-27B uses 262,144; the 397B MoE also uses 262,144 | Check max_position_embeddings per model even within the same family |
| Applying long-context speedup figures to short context | Cited "3x throughput improvement" at short context | Figure came from 65K context (a~0.08 attention fraction) where attention dominates; at 32K context a~0.25, MLP dominates and speedup is ~1.18x | Always verify the context length at which a speedup figure was measured; recalculate for the target context |

## Results & Parameters

### Qwen3/Qwen3.5 Family Verified Specs (2026-04-13)

| Model | L | d | d_ff | H_q | H_kv | head_dim | Vocab | Native ctx |
|-------|---|---|------|-----|-------|----------|-------|------------|
| Qwen3.5-27B (Hybrid) | 64 | 5120 | 17408 | 24 (full-attn) | 4 (full-attn) | 256 | 248,320 | 262,144 |
| -- DeltaNet layers | -- | -- | -- | 16 QK-heads | 48 V-heads | 128 | -- | -- |
| Qwen3-32B (Dense) | 64 | 5120 | 25600 | 64 | 8 | 128 | 151,936 | 40,960 |
| Qwen3.5-397B-A17B (MoE) | 60 | 4096 | -- | 32 (global) | 2 (global) | 256 | 248,320 | 262,144 |
| -- DeltaNet layers | -- | -- | -- | 16 QK-heads | 64 V-heads | 128 | -- | -- |
| -- MoE config | -- | -- | -- | 512 experts | k=11 active | -- | -- | -- |

### KV Cache at Reference Context Lengths

| Model | 32K ctx | 40K ctx | 262K ctx |
|-------|---------|---------|---------|
| Qwen3-32B (full KV) | ~8.59 GB | ~10.49 GB | ~68.7 GB |
| Qwen3.5-27B (16/64 full-attn layers) | ~2.15 GB | ~2.63 GB | ~17.2 GB |
| Qwen3.5-397B (15/60 global-attn layers) | ~1.0 GB | ~1.22 GB | ~8.0 GB |

Source: config.json from HuggingFace model hub + direct formula application.

### Common Errors to Check

```
ERROR: "~68 GB KV at 32K context" for Qwen3-32B
CORRECT: ~8.59 GB (used 8 KV heads, not 64 Q heads)

ERROR: vocab_size=151,936 for Qwen3.5-27B or 397B-A17B
CORRECT: 248,320

ERROR: context=32,768 for Qwen3.5-27B or 397B-A17B
CORRECT: 262,144

ERROR: GatedAttn head_dim=128 for Qwen3.5-27B or 397B-A17B
CORRECT: head_dim=256 for full-attention layers

ERROR: Baseline B global attention 64Q/4KV
CORRECT: 32Q/2KV, head_dim=256
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ArchIdeas | Reviewing 31 AI architecture research documents | 3 baselines: Qwen3.5-27B Hybrid, Qwen3-32B Dense, Qwen3.5-397B-A17B MoE |
