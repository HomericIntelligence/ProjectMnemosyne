---
name: research-corpus-inline-derivation-standard
description: "Standard for tagging analytically-derived numeric claims in research corpus documents. Use when: (1) writing or reviewing research docs with numeric claims not backed by a paper, (2) auditing derivation tags for completeness, (3) deciding how to format a first-principles calculation in a table cell or prose."
category: documentation
date: 2026-04-18
version: "1.1.0"
user-invocable: false
verification: verified-local
history: research-corpus-inline-derivation-standard.history
tags: [research, corpus, derivation, citation, inline, numeric, documentation, annotation]
---

# Research Corpus Inline Derivation Standard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-18 (v1.1.0), 2026-04-17 (v1.0.0) |
| **Objective** | Define the required format for tagging analytically-derived numeric claims in AI architecture research corpus documents |
| **Outcome** | Standard established during 39-file corpus audit; user explicitly rejected bare labels and confirmed inline computation format. Confirmed again in follow-up remediation pass. |
| **Verification** | verified-local |
| **History** | [changelog](./research-corpus-inline-derivation-standard.history) |

## When to Use

- Writing a numeric value (memory size, TPOT, bandwidth, parameter count) that comes from a formula, not a cited paper
- Reviewing existing research docs for derivation tag completeness
- Adding a Notes cell to a comparison table where the value is analytically computed
- Any time you would write `[derived from first principles]` — instead, show the computation
- A table has a block-level note like "All calculations derived from first principles using canonical head dimensions from SHARED_PRELUDE.md" with no per-row derivations — this is also the antipattern

## Verified Workflow

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bare `[derived from first principles]` tag | Added the tag to numeric claims with no further detail | User explicitly rejected: "bare tags are useless to a reader — they signal 'trust me' without showing the work" | Always show the actual computation; the tag alone carries zero information |
| `[derived from first principles — no direct experimental citation]` | Extended label explaining why there's no citation | Still no verifiable arithmetic; just a longer "trust me" | The explanation of why there's no citation is irrelevant — what matters is showing the derivation |
| Deferring arithmetic to a notes.md file | Wrote `[derived — see notes.md §3.2]` | Reader must switch files to verify; breaks the audit flow | Inline derivations must be self-contained; the reader should never have to leave the file |
| Using variable names without substitution | Wrote `n_layers × n_heads × head_dim × seq × bytes` | Reader can't verify without looking up each variable | Substitute actual values in the formula so the arithmetic is checkable on the spot |
| Block-level derivation disclaimer at table top | Wrote "All calculations derived from first principles using canonical head dimensions from SHARED_PRELUDE.md" above the table | Reader still must redo the math for each row; the block note is a collective "trust me" at table scope rather than row scope | Same rule applies at block scope: every derived value needs its own inline computation, not a shared disclaimer |

## Results & Parameters

### Canonical format

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

### Real examples from the ArchIdeas corpus

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

### When to cite a paper instead

Use `[Author et al., Year] — p.N, §X.Y` when:
- The value comes from a measurement in an experiment (throughput, accuracy, latency)
- The value is a design choice from a specific model architecture (e.g., n_heads=8 from Qwen3-32B spec)
- The formula itself is from a paper (e.g., the KIVI quantization error bound formula)

Use `[derived: ...]` when:
- The value follows mechanically from known constants (dimensions, bytes per dtype, sequence length)
- The value is a ratio or improvement computed from two other values
- The arithmetic is straightforward enough that a reader can verify it in under 30 seconds

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ArchIdeas corpus | 39-file audit, Phase C + D | Apr 2026 — user rejected bare tags mid-session, standard applied to multiple files during the audit |
| ArchIdeas corpus | Follow-up quality remediation pass | Apr 2026 — found and fixed block-level disclaimer antipattern in research_5_4_linked_attention.md; added per-baseline KV cache derivation |
