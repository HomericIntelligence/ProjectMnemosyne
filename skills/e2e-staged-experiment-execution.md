---
name: e2e-staged-experiment-execution
description: "Run E2E experiments in 3 stages with controlled concurrency: Stage 1 (agent execution, --until agent_complete), Stage 2 (commit+diff+promote, --until promoted_to_completed), Stage 3 (judging+finalization, no --until). Use when: (1) you need to split agent work from judging for cost control, (2) judges must only read from completed/ directory, (3) you want independent concurrency limits per phase."
category: evaluation
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - e2e
  - experiment
  - staged-execution
  - concurrency
  - judging
  - checkpoint
  - cli-flags
  - off-peak
---

# E2E Staged Experiment Execution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Go/NoGo assessment for haiku paper experiment; verify E2E infrastructure supports 3-stage execution with 3 runs x 3 judges, agent commit capture, and judge diff visibility |
| **Outcome** | GO — repo audit scored A- (91%), infrastructure verified, 3-stage runner script created |
| **Verification** | verified-ci |
| **Project** | ProjectScylla |
| **Repo Audit** | 91% (A-) across 15 dimensions; 5,306 tests passing, 78.24% coverage |

## When to Use

- You are planning a multi-stage E2E experiment (agent execution separate from judging)
- You need different concurrency limits for agent work vs commit/promote vs judging
- Judges must only read from `completed/` directory (not `in_progress/`)
- You want off-peak scheduling for expensive API-bound stages
- You need to understand the correct CLI flags for `manage_experiment.py`
- You are building a shell script to orchestrate a full experiment run

## Verified Workflow

### Quick Reference

```bash
# Stage 1: Agent execution (high concurrency, off-peak)
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 10 \
  --until agent_complete \
  --off-peak

# Stage 2: Commit + Diff + Promote (low concurrency, sequential)
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 2 \
  --until promoted_to_completed

# Stage 3: Judging + Finalization (moderate concurrency, off-peak)
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 5 \
  --judge-model claude-sonnet-4-20250514 \
  --add-judge claude-haiku-4-20250414 \
  --add-judge claude-opus-4-20250514 \
  --off-peak
```

### Key CLI Flags

| Flag | Purpose | Notes |
|------|---------|-------|
| `--until agent_complete` | Stop after agent execution | Runs stay in `in_progress/` |
| `--until promoted_to_completed` | Stop after commit+diff+promote | Runs move to `completed/` |
| (no `--until`) | Run to completion including judging | Full pipeline |
| `--max-concurrent-agents N` | Per-test concurrency limit | Use for single-config runs |
| `--threads N` | Batch mode parallelism | Use for `--batch` runs only |
| `--judge-model MODEL` | Primary judge model | Singular, not `--judge-models` |
| `--add-judge MODEL` | Additional judge (repeatable) | Use multiple times for multi-judge |
| `--off-peak` | Wait for off-peak hours before each subtest | Avoids rate limits during peak |

### Critical: No `--from` Needed Between Stages

Checkpoint auto-resumes between stages. The `--from` flag is NOT needed:

```bash
# CORRECT: just re-run with new --until
python scripts/manage_experiment.py run --config "$DIR" --until agent_complete
python scripts/manage_experiment.py run --config "$DIR" --until promoted_to_completed
python scripts/manage_experiment.py run --config "$DIR"

# WRONG: don't add --from between stages
python scripts/manage_experiment.py run --config "$DIR" --from agent_complete --until promoted_to_completed
```

### Critical: Auth Uses `claude` CLI, Not ANTHROPIC_API_KEY

Agents run via the `claude` CLI which has its own authentication. Do NOT check for `ANTHROPIC_API_KEY` in pre-flight scripts:

```bash
# WRONG
[ -z "$ANTHROPIC_API_KEY" ] && echo "Missing API key" && exit 1

# CORRECT — verify claude CLI auth
claude --version >/dev/null 2>&1 || { echo "claude CLI not found"; exit 1; }
```

### Detailed Steps

1. **Pre-flight checks**: Verify `claude` CLI is available, experiment directory exists, config YAML is valid
2. **Stage 1 — Agent Execution**: Run with `--until agent_complete --off-peak --max-concurrent-agents 10`
   - All runs stay in `in_progress/` directory
   - High concurrency is safe because agents are independent
3. **Stage 2 — Commit + Diff + Promote**: Run with `--until promoted_to_completed --max-concurrent-agents 2`
   - Low concurrency because git operations on worktrees are I/O-bound
   - Runs are moved from `in_progress/` to `completed/` via `promote_run_to_completed()`
   - Must use `promoted_to_completed` NOT `diff_captured` as the `--until` target
4. **Stage 3 — Judging + Finalization**: Run with no `--until` flag, `--off-peak --max-concurrent-agents 5`
   - Judges read from `completed/` directory only
   - Multi-judge setup via `--judge-model` (primary) + `--add-judge` (repeatable)
   - Moderate concurrency to avoid API rate limits
5. **Post-run**: Check `tier_states` in checkpoint (not just `experiment_state`) for partial failures

### Concurrency Guidelines

| Stage | Recommended `--max-concurrent-agents` | Rationale |
|-------|---------------------------------------|-----------|
| 1 — Agent Execution | 10 | Agents are independent; parallelism speeds up total time |
| 2 — Commit + Promote | 2 | Git/IO-bound; low concurrency avoids contention |
| 3 — Judging | 5 | API-bound; moderate to avoid rate limits |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Used `--until diff_captured` for Stage 2 | Runs stay in `in_progress/` at `diff_captured` state; judges only read from `completed/` directory so they never see the runs | Must use `--until promoted_to_completed` to move runs into `completed/` before judging |
| 2 | Pre-flight check for `ANTHROPIC_API_KEY` env var | Agents run via `claude` CLI which has its own auth (OAuth/API key configured in `~/.claude/`); `ANTHROPIC_API_KEY` is not used | Check `claude --version` instead of `ANTHROPIC_API_KEY` in pre-flight scripts |
| 3 | Used `--judge-models` (plural) flag | CLI uses `--judge-model` (singular) for primary judge + `--add-judge` (repeatable) for additional judges | Always check `manage_experiment.py --help` for exact flag names; plural form does not exist |
| 4 | Added `--from agent_complete` between Stage 1 and Stage 2 | Checkpoint auto-resumes from where each run left off; `--from` is for manual override, not normal stage transitions | Omit `--from` between stages; the checkpoint system handles resume automatically |

## Results & Parameters

### 3-Stage Experiment Runner Template

```bash
#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT_DIR="${1:?Usage: $0 <experiment-dir>}"
LOG_DIR="$EXPERIMENT_DIR/logs"
mkdir -p "$LOG_DIR"

# Pre-flight
command -v claude >/dev/null 2>&1 || { echo "ERROR: claude CLI not found"; exit 1; }
[ -d "$EXPERIMENT_DIR" ] || { echo "ERROR: $EXPERIMENT_DIR not found"; exit 1; }

echo "=== Stage 1: Agent Execution ==="
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 10 \
  --until agent_complete \
  --off-peak \
  2>&1 | tee "$LOG_DIR/stage1.log"

echo "=== Stage 2: Commit + Diff + Promote ==="
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 2 \
  --until promoted_to_completed \
  2>&1 | tee "$LOG_DIR/stage2.log"

echo "=== Stage 3: Judging + Finalization ==="
python scripts/manage_experiment.py run \
  --config "$EXPERIMENT_DIR" \
  --max-concurrent-agents 5 \
  --judge-model claude-sonnet-4-20250514 \
  --add-judge claude-haiku-4-20250414 \
  --add-judge claude-opus-4-20250514 \
  --off-peak \
  2>&1 | tee "$LOG_DIR/stage3.log"

echo "=== Experiment Complete ==="
echo "Check tier_states in $EXPERIMENT_DIR/checkpoint.json for partial failures"
```

### Partial Failure Check

After experiment completion, always inspect tier states:

```bash
python -c "
import json, sys
cp = json.load(open('$EXPERIMENT_DIR/checkpoint.json'))
states = cp.get('tier_states', {})
for tid, st in sorted(states.items()):
    status = '  PASS' if st == 'complete' else '  FAIL'
    print(f'{status}  {tid}: {st}')
failed = [t for t, s in states.items() if s != 'complete']
if failed:
    print(f'\nWARNING: {len(failed)} tier(s) failed: {failed}')
    sys.exit(1)
"
```

### Repo Audit Dimensions (for Go/NoGo)

Before running an experiment, audit the repo across these key dimensions:

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| Test Coverage | High | >= 75% combined src + scripts |
| CI Green | High | All checks pass on main |
| E2E Framework | High | State machine, stages, paths all operational |
| Checkpoint Resume | Medium | Auto-resume works between stages |
| Judge Pipeline | High | Judges read from completed/ only |
| Off-Peak Scheduling | Low | --off-peak flag wired correctly |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Go/NoGo for haiku paper experiment | 5,306 tests, 78.24% coverage, A- (91%) audit score |
