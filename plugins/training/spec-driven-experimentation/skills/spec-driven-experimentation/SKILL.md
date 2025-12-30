---
name: spec-driven-experimentation
description: "TECHSPEC.md pattern for structured ML experiments"
category: training
source: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
date: 2025-12-29
---

# Spec-Driven Experimentation

Structure ML experiments with TECHSPEC.md before running them.

## Overview

| Item | Details |
|------|---------|
| Date | 2025-12-29 |
| Objective | Define experiment goals and success criteria before training |
| Outcome | Reduced wasted compute, clearer experiment interpretation |
| Source | Sionic AI HuggingFace blog |

## When to Use

- Planning hyperparameter sweeps
- Defining success criteria before expensive training runs
- Budget-constrained experiment design
- Architecture ablation studies
- When you want Claude to understand *why* each experiment exists

## Verified Workflow

### 1. Create TECHSPEC.md Before Experiments

```markdown
# TECHSPEC: Addition Task Parameter Scaling

## Objective
Determine minimum viable model size for integer addition (0-999).

## Hypotheses
1. Wider models beat deeper for local operations (addition is positional)
2. RoPE theta values matter less for short sequences
3. d_proj=32 causes information bottleneck

## Parameter Ranges
| Parameter | Values | Priority |
|-----------|--------|----------|
| params | [253K, 500K, 1M, 2M, 3.2M] | High |
| depth | [2, 4, 6, 8] | High |
| d_model | [64, 128, 256, 512] | High |
| RoPE theta | [10, 30, 100, 500, 10000] | Medium |
| batch_size | [512, 1024, 2048, 4096] | Low |

## Success Criteria
| Scenario | Exact Match | Notes |
|----------|-------------|-------|
| Best case | >95% | Full accuracy |
| Realistic | 85-95% | Acceptable |
| Minimum viable | >70% | Worth investigating |
| Failure | <50% | Abandon approach |

## Budget Constraints
- Max GPU hours: 24
- Max experiments: 50
- Priority: depth/width ablation > RoPE sweep

## Context for Claude
This continues Phase 1 baseline work. Prior finding: 3.18M params achieved 91.5%.
Focus on finding minimum viable size while maintaining >70% accuracy.
```

### 2. Run /advise with TECHSPEC Context

Before running experiments, `/advise` pulls from the spec AND existing skills:

```
User: /advise I'm running the addition task experiments from TECHSPEC.md
Claude: Found 2 related skills...
- colbert-parameter-search: RoPE theta sweep [10, 30, 100, 500, 10000]
  - Key finding: d_proj=32 causes information loss → use 64+
- addition-baseline: 3.18M params achieved 91.5%

Recommendation: Start with depth/width ablation at fixed 1M params.
Skip RoPE sweep initially (prior work shows theta=100 works for short seq).
```

### 3. Generate Controlled Ablation from Spec

Claude can generate experiment configs directly from the spec:

```python
# Auto-generated from TECHSPEC: width/depth ablation at 1M params
experiments = [
    {"d_model": 512, "depth": 2, "params": "~1M"},   # Wide-shallow
    {"d_model": 256, "depth": 4, "params": "~1M"},   # Balanced
    {"d_model": 128, "depth": 8, "params": "~1M"},   # Narrow-deep
    {"d_model": 384, "depth": 3, "params": "~1M"},   # Intermediate
]
```

### 4. Capture Results Back to Skills Registry

After experiments, `/retrospective` saves findings with TECHSPEC reference:

```markdown
## Results vs TECHSPEC Predictions
| Hypothesis | Confirmed? | Evidence |
|------------|------------|----------|
| Wider > deeper for addition | YES | 512x2 beat 128x8 by 15% |
| RoPE theta insensitive | YES | <2% variance across sweep |
| d_proj=32 bottleneck | YES | 32 → 64 gave +8% accuracy |
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Tiny model (32d-2L, 77K params) | Flatlined at ~0% accuracy | Minimum viable for addition is ~253K params |
| Standard RoPE implementation | RuntimeError: dimension mismatch [32] vs [16] | Need `torch.cat((freqs, freqs), dim=-1)` to duplicate freqs |
| d_proj=32 in attention | Performance drop of 8% | Use d_proj=64+ to avoid information bottleneck |
| No upfront success criteria | Couldn't tell if 75% was good or bad | Define best/realistic/fail thresholds in TECHSPEC |
| Unscoped parameter ranges | 200+ experiments, ran out of budget | Prioritize parameters, set max experiments |
| Missing context for Claude | Claude didn't know why experiments mattered | Add "Context for Claude" section |
| Running all params at once | Wasted compute on low-priority sweeps | Priority column + staged execution |
| No hypothesis | Just grid search, no insight | Hypothesis-first design |

## Results & Parameters

```yaml
# TECHSPEC Template
techspec_sections:
  - objective: "What are we trying to learn?"
  - hypotheses: "What do we predict and why?"
  - parameter_ranges: "What to sweep, with priorities"
  - success_criteria: "Best/realistic/fail thresholds"
  - budget_constraints: "GPU hours, max experiments"
  - context_for_claude: "Why this matters, prior work"

# Experiment lifecycle
workflow:
  1. Write TECHSPEC.md
  2. Run /advise to check prior work
  3. Generate experiments from spec
  4. Execute priority-ordered
  5. /retrospective to save findings
  6. Update TECHSPEC with results

# Anti-patterns
avoid:
  - Grid search without hypotheses
  - Missing success thresholds
  - Unbounded parameter ranges
  - No priority ordering
  - Orphaned experiments (no context)
```

## Real Example: Addition Task

Complete reference from Sionic AI blog with verified results and configurations.

### Task Specification

| Property | Value |
|----------|-------|
| Task | Integer addition (0-999 + 0-999) |
| Tokenization | Base-100 (each digit 0-99 is one token) |
| Sequence length | 32 tokens max |
| Dataset | 100K train / 10K eval |
| Hardware | NVIDIA A100-SXM4-80GB |
| Runtime | 24 GPU hours total (Phase 1 + 2) |

### Phase 1: Baseline Size Scaling

**Objective**: Determine minimum viable model size for integer addition.

**TECHSPEC.md Excerpt:**
```markdown
## Hypotheses
1. Smaller models can learn addition (local operation)
2. Performance degrades gracefully with param count
3. Minimum viable: ~250K params

## Parameter Grid
| Name | d_model | depth | params | Priority |
|------|---------|-------|--------|----------|
| Upper | 256 | 6 | 3.18M | Baseline |
| Middle | 192 | 4 | 1.4M | High |
| Lower | 64 | 3 | 253K | High |
| Tiny | 32 | 2 | 77K | Test floor |

## Success Criteria
- Best case: >95% exact match
- Minimum viable: >70% exact match
- Failure: <50% exact match
```

**Phase 1 Results:**

| Model | d_model | depth | Params | Exact Match | Outcome |
|-------|---------|-------|--------|-------------|---------|
| Upper | 256 | 6 | 3.18M | **91.5%** | Best case achieved |
| Middle | 192 | 4 | 1.4M | **79.31%** | Above minimum viable |
| Lower | 64 | 3 | 253K | **37.6%** | Below threshold |
| Tiny | 32 | 2 | 77K | **~0%** | Complete failure |

**Key Finding**: 40x parameter reduction (3.18M → 77K) = 98x performance drop (91.5% → ~0%). Minimum viable size is ~250K params.

### Phase 2: Width vs Depth Ablation

**Objective**: Test hypothesis that addition (positional operation) benefits more from width than depth.

**TECHSPEC.md Excerpt:**
```markdown
## Hypothesis
Addition is a local, positional operation. Wide-shallow models should
outperform narrow-deep at identical parameter counts.

## Parameter-Matched Pairs
Target: ~1M params each
| Config | d_model | depth | Params | Rationale |
|--------|---------|-------|--------|-----------|
| Wide-shallow | 512 | 2 | ~1.05M | Test max width |
| Narrow-deep | 128 | 8 | ~1.02M | Test max depth |
| Balanced | 256 | 4 | ~1.31M | Control |

## Prediction
Wide-shallow > Balanced > Narrow-deep for positional ops
```

**Phase 2 Results:**

| Config | d_model | depth | Params | Exact Match | Hypothesis |
|--------|---------|-------|--------|-------------|------------|
| Wide-shallow | 512 | 2 | 1.05M | **87.2%** | ✓ Confirmed |
| Balanced | 256 | 4 | 1.31M | **79.31%** | ✓ Middle |
| Narrow-deep | 128 | 8 | 1.02M | **71.8%** | ✓ Weakest |

**Key Finding**: Width matters more than depth for positional operations. 512d-2L outperformed 128d-8L by 15.4 percentage points at identical parameter budget.

### Critical Implementation Details

**RoPE Configuration** (from blog debugging section):
```yaml
# For sequences <32 tokens
rope_theta: 100  # Lower than default 10000
rope_scaling: null

# Bug fix required:
# Standard RoPE outputs [seq_len, head_dim/2]
# Attention expects [seq_len, head_dim]
# Solution in apply_rotary_pos_emb:
freqs = torch.cat((freqs, freqs), dim=-1)  # Duplicate to match head_dim
freqs = freqs.unsqueeze(0).unsqueeze(0)    # [1, 1, seq, dim]
```

**Training Configuration**:
```yaml
batch_size: 512  # Higher for small models, 256 for 3M+
learning_rate: 1e-4
max_steps: 10000
eval_every: 500
early_stopping: true  # Stop if eval loss plateaus for 3 evals
```

**Tokenization** (Base-100):
```python
# Each digit 0-99 becomes one token
# Example: 123 + 456 = 579
# Tokens: [1, 23, PAD, +, 4, 56, PAD, =, 5, 79, PAD]
# Max seq: 32 tokens (handles 999 + 999 = 1998)
```

### Scaling Laws Observed

```
Parameter Count → Exact Match Accuracy
3.18M → 91.5%
1.4M  → 79.31%
1.05M → 87.2% (wide-shallow advantage)
253K  → 37.6%
77K   → ~0%

Inflection point: ~250K params (where performance crosses 50%)
Minimum viable: ~1M params (for >70% accuracy)
Production target: ~3M params (for >90% accuracy)
```

## References

- Source blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Spec-driven development: Reduces 1000+ experiments/day to targeted runs
- Key insight: "Claude reads the spec and understands *why* each experiment exists"
