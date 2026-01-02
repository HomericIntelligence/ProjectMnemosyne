---
name: tier-ablation-testing
description: "Run comprehensive tier ablation studies across AI agent architectures (T0-T6) with ~114 sub-tests"
category: evaluation
source: ProjectScylla
date: 2026-01-02
---

# Tier Ablation Testing

Run comprehensive tier ablation studies across 7 evaluation tiers (T0-T6) with ~114 sub-tests for AI agent architecture evaluation.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-01-02 | Run comprehensive tier ablation study across T0-T6 with ~114 sub-tests | Successfully validated tier infrastructure, discovered and fixed CLI argument limit bug in T6 |

## When to Use

- (1) Setting up multi-tier ablation experiments for AI agent evaluation
- (2) Running E2E validation across all capability tiers (T0-T6)
- (3) Debugging issues with large configuration combinations (T5/T6)
- (4) Understanding the tier structure and sub-test organization
- (5) Need to compare agent performance across different capability levels

## Verified Workflow

### 1. Tier Structure (T0-T6)

| Tier | Name | Sub-tests | Description |
|------|------|-----------|-------------|
| T0 | Prompts | 24 | System prompt ablation (empty -> full CLAUDE.md) |
| T1 | Skills | 10 | Skill category ablation |
| T2 | Tooling | 15 | Tool categories + MCP servers |
| T3 | Delegation | 41 | Agent ablation (non-orchestrators) |
| T4 | Hierarchy | 7 | Orchestrator ablation |
| T5 | Hybrid | 15 | Best combinations + permutations |
| T6 | Super | 1 | Everything enabled at maximum capability |

### 2. Running E2E Experiments

```bash
pixi run python scripts/run_e2e_experiment.py \
    --repo https://github.com/octocat/Hello-World \
    --commit 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d \
    --prompt tests/fixtures/tests/test-001/prompt.md \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 T1 T2 T3 T4 T5 T6 \
    --runs 1 \
    --experiment-id <experiment-name> \
    --timeout 1200 \
    -v 2>&1 | tee results/e2e-$(date +%Y%m%d-%H%M%S).log
```

### 3. Results Directory Structure

```
results/YYYY-MM-DDTHH-MM-SS-<experiment-id>/
├── config/experiment.json       # Experiment configuration
├── tiers/
│   ├── T0/
│   │   ├── 00/run_01/logs/     # Sub-test 00 results
│   │   │   ├── judgment.json   # LLM judge evaluation
│   │   │   ├── report.md       # Per-run markdown report
│   │   │   └── command_log.json
│   │   ├── 01/run_01/logs/
│   │   └── ...
│   ├── T1/ through T6/
│   └── best_subtest.json       # Winner selection per tier
├── summary/
│   ├── result.json             # Overall experiment results
│   └── tier_comparison.json    # Cross-tier metrics
└── report.md                   # Final markdown report
```

### 4. Key Files for Sub-Test Configuration

```
tests/fixtures/tests/test-001/t{N}/NN-name/
├── config.yaml                  # Sub-test metadata
├── CLAUDE.md                    # Optional: System prompt override
└── .claude/                     # Optional: Skills, agents, plugins
    ├── skills/
    ├── agents/
    └── plugins/
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Pass evaluation context as CLI arg | `[Errno 7] Argument list too long` for T6 | Write to temp file, use `-p` flag instead |
| Direct `evaluation_context` in cmd | OS command line limit (~128KB) exceeded | Large prompts must use file-based passing |
| T6 with all configs combined | Context size explodes with full CLAUDE.md + skills + agents | Always test highest tier combinations early |

## Results & Parameters

### Sample T0 Judgment (00-empty sub-test)

```json
{
  "score": 0.92,
  "passed": true,
  "grade": "A",
  "criteria_scores": {
    "correctness": {"score": 1.0},
    "completeness": {"score": 1.0},
    "code_structure": {"score": 1.0}
  }
}
```

### T6 Result (after fix)

```
T6: PASS (score: 0.700, cost: $0.4037)
```

### CLI Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--tiers` | T0 T1 | Tiers to run |
| `--runs` | 10 | Runs per sub-test |
| `--timeout` | 3600 | Timeout per run (seconds) |
| `--parallel` | 4 | Max parallel sub-tests |
| `--judge-model` | claude-opus-4-5 | Model for LLM judging |

## Related Skills

- `complex-agent-eval-task` - Setting up complex evaluation tasks
