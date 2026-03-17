---
name: checkpoint-intermediate-state-resume
description: "Fixing checkpoint resume when runs are stuck in intermediate states or subtests are orphaned. Use when: experiment marked complete but runs not terminal, subtest_states without run_states, or ProcessPool checkpoint save races."
category: debugging
date: 2026-03-17
user-invocable: false
---

# Checkpoint Intermediate State Resume

## Overview

| Field | Value |
|-------|-------|
| Problem | Experiments marked "complete" with runs stuck in non-terminal states (e.g. `report_written`) or subtests marked `aggregated` with no `run_states` entries |
| Root Cause | (1) `reset_failed_states()` only handled `failed`/`interrupted` experiments, not `complete` ones with intermediate runs. (2) Checkpoint integrity: ProcessPool save race can lose run state transitions. |
| Solution | Extended `reset_failed_states()` to detect and reset intermediate runs and orphaned subtests in complete experiments |
| Impact | Fixed 3 stuck runs across 2 tests in a 47-test, 1196-run experiment |

## When to Use

- Experiment checkpoint shows `experiment_state=complete` but `analyze_dryrun3.py` reports intermediate runs
- `subtest_states` has entries marked `aggregated` or `runs_complete` with no corresponding `run_states` key
- Resume skips re-execution because experiment is already marked complete
- State machine log shows transitions (e.g. `checkpointed -> worktree_cleaned`) but checkpoint file has stale state

## Verified Workflow

### Quick Reference

```python
# Detect intermediate runs in complete experiments
tiers_with_intermediate = self._find_tiers_with_intermediate_runs()
if tiers_with_intermediate and experiment_state in COMPLETE_FAMILY:
    experiment_state = "tiers_running"
    for tier_id in tiers_with_intermediate:
        tier_states[tier_id] = "config_loaded"
        # Reset affected subtests to runs_in_progress

# Detect orphaned subtest_states
orphaned = self._find_orphaned_subtest_states()
if orphaned:
    for tier_id, sub_ids in orphaned.items():
        for sub_id in sub_ids:
            subtest_states[tier_id][sub_id] = "pending"
    experiment_state = "tiers_running"
```

### Step 1: Identify the Problem

Run the analysis script to detect stuck states:

```bash
pixi run python scripts/analyze_dryrun3.py --results-dir ~/dryrun3
```

Look for:
- `INTERMEDIATE: T3/04/run_01(report_written)` — runs stuck mid-pipeline
- `ORPHANED SUBTESTS: T0/02(subtest_state=aggregated, no run_states)` — checkpoint integrity issues

### Step 2: Classify Run States

| Category | Run State | Action on Resume | Example |
|----------|-----------|-----------------|---------|
| INFRA_ERROR | `failed`, `rate_limited` | Always reset to `pending` and retry | Crashed process, API rate limit |
| AGENT_FAILURE | `worktree_cleaned` + `judge_passed=false` | Never retry (valid data) | Agent didn't solve task |
| COMPLETE_PASS | `worktree_cleaned` + `judge_passed=true` | Never retry (valid data) | Agent solved task |
| INTERMEDIATE | Any non-terminal state (e.g. `report_written`) | Resume from current state | Interrupted mid-pipeline |

Terminal states: `worktree_cleaned`, `failed`, `rate_limited`

### Step 3: Fix Resume Logic

The fix requires three new detection methods:

1. **`_find_tiers_with_intermediate_runs()`** — Scans `run_states` for non-terminal, non-pending states. `PENDING` is excluded because those runs haven't started yet.

2. **`_find_orphaned_subtest_states()`** — Finds `aggregated`/`runs_complete` subtests with empty `run_states`.

3. **`_reset_intermediate_runs_in_complete_experiment()`** — Resets experiment from `complete` to `tiers_running`, affected tiers to `config_loaded`, and affected subtests to `runs_in_progress`.

### Step 4: Reduce Complexity

Extract each concern into its own method to stay under C901 complexity limit (10):

```python
# Shared helpers
_COMPLETE_FAMILY_STATES = ("complete", "tiers_complete", "reports_generated")
_COMPLETE_TIER_STATES = ("complete", "subtests_complete", "best_selected", "reports_generated")

def _reset_experiment_to_tiers_running(self): ...
def _reset_tier_to_config_loaded(self, tier_id): ...
def _reset_intermediate_runs_in_complete_experiment(self): ...
def _reset_orphaned_subtest_states(self): ...
def _reset_failed_and_interrupted(self): ...

# Main method becomes simple dispatch:
def reset_failed_states(self):
    self._reset_infra_error_runs()
    self._reset_intermediate_runs_in_complete_experiment()
    self._reset_orphaned_subtest_states()
    self._reset_failed_and_interrupted()
```

### Step 5: Handle Checkpoint Save Race

If the state machine advanced runs in memory but the checkpoint file wasn't saved (ProcessPool race), verify completion from artifacts:

```bash
# Check if run_result.json exists (confirms run completed)
python3 -c "
import json
from pathlib import Path
base = Path('~/dryrun3/EXPERIMENT_DIR')
for sub in ['03', '04']:
    rr = base / 'T3' / sub / 'run_01' / 'run_result.json'
    if rr.exists():
        data = json.load(open(rr))
        print(f'T3/{sub}: judge_passed={data[\"judge_passed\"]}')
"
```

If artifacts confirm completion, manually patch the checkpoint:

```python
cp['run_states']['T3']['03']['1'] = 'worktree_cleaned'
cp['subtest_states']['T3']['03'] = 'aggregated'
```

### Step 6: Update Analysis Script

Add checkpoint integrity validation to `analyze_dryrun3.py`:

```python
def check_orphaned_subtest_states(cp):
    """Find subtest_states with no corresponding run_states."""
    orphaned = []
    for tier_id, subtests in cp.get("subtest_states", {}).items():
        for sub_id, sub_state in subtests.items():
            if sub_state in ("aggregated", "runs_complete"):
                runs = cp.get("run_states", {}).get(tier_id, {}).get(sub_id, {})
                if not runs:
                    orphaned.append((tier_id, sub_id, sub_state))
    return orphaned
```

Add to Go/NoGo criteria so orphaned subtests block the GO verdict.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial `reset_failed_states()` only handling `failed`/`interrupted` | Only reset experiment states `failed`/`interrupted` to `tiers_running` | `complete` experiments with intermediate runs were skipped entirely — the guard clause returned early | Must also check for intermediate runs when experiment is in `complete`-family states |
| Monolithic `reset_failed_states()` with inline intermediate/orphan detection | Added all logic directly into `reset_failed_states()` | C901 complexity exceeded limit (19 > 10), SIM102 nested-if lint failure | Extract each concern into its own method; use shared helper constants for state sets |
| Existing tests with `aggregated` subtests but no `run_states` | Tests assumed orphaned subtests were valid (untouched by reset) | New orphan detection correctly reset them, breaking the old assertions | Add `run_states` entries to test fixtures when subtests are `aggregated` |
| Relying on state machine log as proof of completion | Log showed `checkpointed -> worktree_cleaned` transition | Checkpoint file on disk still had `report_written` — ProcessPool save race | Always verify the on-disk checkpoint file, not just in-memory state machine logs; verify from artifact files (`run_result.json`) |

## Results & Parameters

### Final Experiment Status

```
Tests: 47 | Complete: 47
Active runs: 1196 | Complete: 1196 | Incomplete: 0 | Missing: 0
  PASS=719 | AGENT_FAILURE=477
Overall pass rate: 60.1%
Per-tier: T0:60%, T1:52%, T2:58%, T3:65%, T4:61%, T5:67%, T6:36%
Verdict: GO
```

### Files Modified

| File | Change |
|------|--------|
| `scylla/e2e/resume_manager.py` | Added `_find_tiers_with_intermediate_runs()`, `_find_orphaned_subtest_states()`, `_reset_intermediate_runs_in_complete_experiment()`, `_reset_orphaned_subtest_states()`, `_reset_failed_and_interrupted()` |
| `scripts/analyze_dryrun3.py` | Added `check_orphaned_subtest_states()`, added orphaned subtests to Go/NoGo criteria and report |
| `tests/unit/e2e/test_resume_manager.py` | Added 12 tests, fixed 2 existing tests with missing `run_states` fixtures |

### Key Configuration

```bash
# Resume always retries infra failures, never retries agent/judge failures
# No --retry-errors flag needed — behavior is unconditional
pixi run python scripts/manage_experiment.py run \
    --config tests/fixtures/tests/test-XXX \
    --results-dir ~/dryrun3 \
    --threads 2 --parallel 1 \
    --model claude-haiku-4-5-20251001 \
    --judge-model claude-haiku-4-5-20251001 -v
```
