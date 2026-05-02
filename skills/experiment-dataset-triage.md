---
name: experiment-dataset-triage
description: "Triage experiment datasets for paper readiness by analyzing checkpoint states, detecting inconsistencies, and planning phased resume. Use when: assessing experiment completion, diagnosing stale checkpoints, or planning phased --until execution."
category: evaluation
date: 2026-03-21
version: "1.0.0"
user-invocable: false
---

## Overview

| Field | Value |
| ------- | ------- |
| **Objective** | Assess experiment dataset completion status for paper inclusion |
| **Context** | ProjectScylla e2e experiments with v3.1 checkpoints across T0-T6 tiers |
| **Complexity** | Medium — requires understanding 4-level state hierarchy |
| **Key Risk** | Checkpoint states can be misleading (tiers marked "complete" with unfinished runs) |

## When to Use

- You need to determine which experiments in a results directory are paper-ready
- You suspect checkpoint state inconsistencies (e.g., `experiment_state=complete` but runs stuck at `agent_complete`)
- You need to plan a phased resume strategy to complete partially-done experiments
- You're comparing old vs new experiment runs and deciding whether to merge or discard

## Verified Workflow

### Quick Reference

```bash
# Scan all checkpoints in a results directory
for dir in ~/fullruns/<dataset>/*/; do
  python3 -c "
import json
with open('$dir/checkpoint.json') as f:
    cp = json.load(f)
print('$(basename $dir)')
print('  state:', cp['experiment_state'])
print('  tiers:', {t: s for t, s in cp.get('tier_states', {}).items()})
rs = cp.get('run_states', {})
for tier in sorted(rs):
    counts = {}
    for sub in rs[tier]:
        for rnum, state in rs[tier][sub].items():
            counts[state] = counts.get(state, 0) + 1
    print(f'  {tier}: {counts}')
"
done
```

### Step 1: Inventory all experiment directories

Group by test number (e.g., `test-001`) since multiple timestamp directories may exist per test from resume attempts. The most recent directory (by timestamp prefix) is what `_find_checkpoint_path()` will discover.

### Step 2: Classify checkpoint health

For each checkpoint, check for these patterns:

| Pattern | Meaning | Action |
| --------- | --------- | -------- |
| `experiment_state=complete`, all runs `worktree_cleaned` | Truly complete | Paper-ready |
| `experiment_state=complete`, runs at `agent_complete` | **Stale/inconsistent** | Needs resume — `_reset_non_completed_runs()` will fix |
| `experiment_state=complete`, runs at `replay_generated` | **Never executed** | Checkpoint states are fake — needs full execution |
| `experiment_state=tiers_running`, mix of states | Interrupted mid-run | Resumable with same command |
| `experiment_state=interrupted` | Graceful shutdown | Resumable |

### Step 3: Check config compatibility before merging

If old and new experiment directories exist for the same test:

```python
# Compare config hashes and run counts
old_cp = json.load(open(old_dir + '/checkpoint.json'))
new_cp = json.load(open(new_dir + '/checkpoint.json'))

# Different config_hash = different configurations — DO NOT MERGE
print(old_cp.get('config_hash'), new_cp.get('config_hash'))

# Different runs/subtest = incompatible data structures
old_runs_per = len(next(iter(next(iter(old_cp['run_states'].values())).values())))
new_runs_per = len(next(iter(next(iter(new_cp['run_states'].values())).values())))
```

**Rule**: If config hashes differ OR runs-per-subtest differ, data cannot be merged. Keep the newer run and delete the old.

### Step 4: Plan phased execution

For large datasets, use phased `--until` to control resource usage:

```bash
# Phase 1: Agent execution (CPU/API intensive, high parallelism OK)
pixi run python scripts/manage_experiment.py run \
  --threads 5 --until agent_complete [COMMON_ARGS]

# Phase 2: Diff capture (disk I/O, lower parallelism)
pixi run python scripts/manage_experiment.py run \
  --threads 2 --until diff_captured [COMMON_ARGS]

# Phase 3: Judging + finalization (API calls, high parallelism OK)
pixi run python scripts/manage_experiment.py run \
  --threads 5 [COMMON_ARGS]
```

### Step 5: Verify completion

After each phase, re-scan checkpoints to confirm progress. Watch for runs stuck in intermediate states.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Merge old 1-run data into new 3-run experiment | Copy run artifacts from old dirs to new, update checkpoint | Config hashes differed, runs-per-subtest incompatible (1 vs 3-5), would corrupt statistics | Always check config_hash and runs-per-subtest before attempting merge |
| Trust `experiment_state=complete` at face value | Assumed complete experiments were paper-ready | 12 experiments showed complete state but all runs were at `replay_generated` (never executed) | Always verify run_states — tier/experiment states can be misleading |
| Trust `tier_states=complete` with `subtest_states=runs_in_progress` | Assumed subtests in `runs_in_progress` were actively running | Subtests were actually stuck — the tier completion was premature | Cross-reference all 4 levels of state hierarchy (experiment → tier → subtest → run) |
| Use `--parallel` CLI flag | Tried `--parallel 2` to control parallelism | Flag doesn't exist in manage_experiment.py CLI | Only `--threads` controls batch parallelism |

## Results & Parameters

### Checkpoint State Hierarchy

```
ExperimentState: initializing → dir_created → repo_cloned → tiers_running → complete
  TierState: pending → config_loaded → subtests_running → complete
    SubtestState: pending → runs_in_progress → runs_complete → aggregated
      RunState: pending → ... → agent_complete → ... → worktree_cleaned
```

### Key Files

- `checkpoint.json` — v3.1 format with experiment_state, tier_states, subtest_states, run_states
- `run_result.json` — per-run results (exists only in completed runs)
- `batch_summary.json` — batch-level completion tracking

### Resume Discovery

`_find_checkpoint_path()` in `manage_experiment.py` uses glob pattern `*-{experiment_id}` in the results directory, returning the most recent match by directory name sort. The checkpoint stores `experiment_dir` as an absolute path.

### Batch Skip Logic

The batch runner skips tests where:
1. `batch_summary.json` shows `status=success`
2. Checkpoint has no retryable runs (all `worktree_cleaned`)
3. `--max-subtests` doesn't require expansion

Tests with `status=error` or non-completed runs are always re-run.

### Phased Execution Template

```bash
COMMON_ARGS=(
  --judge-model opus-4.6
  --add-judge sonnet-4.6
  --add-judge haiku-4.5
  --results-dir ~/fullruns/<dataset>/
  --tiers T0 T1 T2 T3 T4 T5 T6
  --runs 5
  --max-subtests 50
  --config tests/fixtures/tests/
  --model haiku-4.5
  --tests test-001 test-002 test-003
)

# Phase 1: agents (5 threads)
pixi run python scripts/manage_experiment.py run \
  --threads 5 --until agent_complete "${COMMON_ARGS[@]}"

# Phase 2: diffs (2 threads)
pixi run python scripts/manage_experiment.py run \
  --threads 2 --until diff_captured "${COMMON_ARGS[@]}"

# Phase 3: complete (5 threads)
pixi run python scripts/manage_experiment.py run \
  --threads 5 "${COMMON_ARGS[@]}"
```
