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
| No upfront success criteria | Couldn't tell if 75% was good or bad | Define best/realistic/fail thresholds |
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

From the blog:

**Phase 1 Baselines:**
- Upper bound (3.18M): 91.5% exact match
- Minimum viable question: How small can we go?
- Scaling law discovered: 40x params = 98x improvement

**Phase 2 Width/Depth Ablation:**
- Hypothesis: "Addition is local, doesn't need depth"
- Generated: 6 width/depth pairs at identical param counts
- Result: Wide-shallow confirmed better for positional ops

## References

- Source blog: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Spec-driven development: Reduces 1000+ experiments/day to targeted runs
- Key insight: "Claude reads the spec and understands *why* each experiment exists"
