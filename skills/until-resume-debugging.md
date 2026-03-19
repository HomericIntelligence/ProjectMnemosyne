---
name: until-resume-debugging
description: Debugging and fixing --until checkpoint resume bugs in the E2E state
  machine pipeline; use when investigating resume errors like 'No sub-test results
  to select from' or 'agent_result must be set'
category: testing
date: '2026-02-25'
version: 1.0.0
user-invocable: true
tags:
- e2e
- checkpoint
- resume
- state-machine
- until
- debugging
- runner
- stages
---
# Skill: --until Checkpoint Resume Debugging

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-25 |
| Objective | Validate --until sequential stepping via live E2E test; find and fix resume bugs |
| Outcome | 3 bugs found and fixed; stepping works cleanly end-to-end for test-031 and test-033 |
| Tests affected | `scylla/e2e/runner.py`, `scylla/e2e/stages.py`, `scylla/e2e/subtest_executor.py` |

## When to Use

Use this skill when:
- Implementing or debugging `--until`/`--from` checkpoint stepping in the E2E runner
- Resuming mid-pipeline after a crash leaves stale checkpoint states
- Investigating "No sub-test results to select from" or "agent_result must be set" errors
- Running live E2E validation of sequential `--until` steps

## Context: TierState Naming Confusion

**Critical**: `TierState.SUBTESTS_RUNNING` does NOT mean "subtests are running". It means "subtests have finished, now select best". The actual subtest execution happens in the action for `CONFIG_LOADED → SUBTESTS_RUNNING`. When resetting a tier for re-execution, always reset to `config_loaded`, never to `subtests_running`.

```
CONFIG_LOADED     → SUBTESTS_RUNNING   # action: run_tier_subtests_parallel() ← actual execution here
SUBTESTS_RUNNING  → SUBTESTS_COMPLETE  # action: select_best_subtest()
```

## Verified Workflow: Live E2E --until Stepping

Base command pattern (use a fresh --results-dir each time):
```bash
BASE="pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-NNN --runs 1 --max-subtests 1 \
  --filter-subtest 00 --tiers T0 --results-dir /home/mvillmow/dryrun_step_testN \
  --skip-judge-validation -v --threads 1 --model haiku --judge-model haiku"

# Batch A: fresh start through all free pre-agent stages
$BASE --fresh --until replay_generated

# Step 7: agent execution (costs ~$0.01 haiku)
$BASE --until agent_complete

# Batch B: post-agent free stages through judge prompt
$BASE --until judge_prompt_built

# Step 11: judge execution (costs ~$0.01 haiku)
$BASE --until judge_complete

# Batch C: finalize, report, checkpoint, clean
$BASE --until worktree_cleaned

# Step 16: final completion (no --until)
$BASE
```

### Checkpoint validation after each step

```python
import json
with open('/path/to/checkpoint.json') as f:
    cp = json.load(f)

# Critical regression check: subtest must stay runs_in_progress until worktree_cleaned
assert cp['subtest_states']['T0']['00'] == 'runs_in_progress'  # steps 0-14
assert cp['run_states']['T0']['00']['1'] == '<expected_state>'
```

### Expected state progression

| Step | run_state | subtest_state | Notes |
|------|-----------|---------------|-------|
| Batch A | `replay_generated` | `runs_in_progress` | ✓ regression check |
| Step 7 | `agent_complete` | `runs_in_progress` | ✓ regression check |
| Batch B | `judge_prompt_built` | `runs_in_progress` | ✓ regression check |
| Step 11 | `judge_complete` | `runs_in_progress` | ✓ regression check |
| Batch C | `worktree_cleaned` | `aggregated` | terminal — subtest aggregates |
| Step 16 | `worktree_cleaned` | `aggregated` | no-op, already complete |

## Bug 1: Tier Reset to Wrong State (runner.py STEP 4)

**Symptom**: "No sub-test results to select from" on second `--until` invocation.

**Root cause**: STEP 4 (`_initialize_or_resume_experiment`) reset tiers to `subtests_running` instead of `config_loaded`. Since `SUBTESTS_RUNNING` maps to the "select best subtest" action (not "run subtests"), `subtest_results` was empty when selection ran.

**Fix** (`scylla/e2e/runner.py`):
```python
# WRONG — subtests_running = "select best", not "run subtests"
self.checkpoint.tier_states[tier_id_str] = "subtests_running"

# CORRECT — config_loaded triggers action_config_loaded which runs subtests
self.checkpoint.tier_states[tier_id_str] = "config_loaded"
```
Also add `"subtests_running"` to the set of trigger states that get reset.

**Note**: The linter reverted `config_loaded` back to `subtests_running` after this fix was committed. If you see this bug resurface, check whether runner.py line ~414 has `"subtests_running"` or `"config_loaded"`.

## Bug 2: Failed Run States Not Reset on Crash (runner.py STEP 3)

**Symptom**: After a crash leaves `run_states.T0.00.1=failed`, next resume skips the run (it's terminal) and aggregates with zero results.

**Root cause**: STEP 3 (experiment_state=failed handler) reset failed tiers → `pending` and failed subtests → `pending`, but did NOT reset failed run states. The run stayed `failed` (terminal), so the subtest executor skipped it.

**Fix** (`scylla/e2e/runner.py`):
```python
# Add after subtest reset in STEP 3:
# Reset failed run states so they are retried from scratch
for tier_id in self.checkpoint.run_states:
    for subtest_id in self.checkpoint.run_states[tier_id]:
        for run_id, run_state in self.checkpoint.run_states[tier_id][subtest_id].items():
            if run_state == "failed":
                self.checkpoint.run_states[tier_id][subtest_id][run_id] = "pending"
```

## Bug 3: RunContext Not Restored on Mid-Sequence Resume (stages.py, subtest_executor.py)

**Symptom**: "agent_result must be set before finalize_run" or "judgment must be set before finalize_run" when resuming from `judge_complete`. Also: assert on `adapter_config is not None` when resuming from `replay_generated`.

**Root cause**: `RunContext` is freshly constructed per-run. When resuming at `judge_complete`, the stages that populate `ctx.agent_result` (stage_execute_agent) and `ctx.judgment` (stage_capture_diff / stage_execute_judge) are skipped. Also, `stage_execute_agent` asserted `adapter_config is not None` but `stage_generate_replay` wasn't called when resuming from `replay_generated`.

**Fix 1** — lazy `adapter_config` reconstruction (`scylla/e2e/stages.py`):
```python
# In stage_execute_agent, replace assert with:
if adapter_config is None:
    from scylla.adapters.base import AdapterConfig
    adapter_config = AdapterConfig(
        model=ctx.config.models[0],
        prompt_file=ctx.run_dir / "task_prompt.md",
        workspace=ctx.workspace,
        output_dir=agent_dir,
        timeout=ctx.config.timeout_seconds,
    )
    ctx.adapter_config = adapter_config
```

**Fix 2** — `restore_run_context()` function (`scylla/e2e/stages.py`):
```python
def restore_run_context(ctx: RunContext, current_state: RunState) -> None:
    """Load persisted agent_result and judgment from disk when resuming mid-sequence."""
    from scylla.e2e.agent_runner import _has_valid_agent_result, _load_agent_result
    from scylla.e2e.judge_runner import _load_judge_result

    agent_dir = get_agent_dir(ctx.run_dir)
    judge_dir = get_judge_dir(ctx.run_dir)

    _NEEDS_AGENT_RESULT = {DIFF_CAPTURED, JUDGE_PIPELINE_RUN, JUDGE_PROMPT_BUILT,
                           JUDGE_COMPLETE, RUN_FINALIZED, REPORT_WRITTEN,
                           CHECKPOINTED, WORKTREE_CLEANED}
    _NEEDS_JUDGMENT = {JUDGE_COMPLETE, RUN_FINALIZED, REPORT_WRITTEN,
                       CHECKPOINTED, WORKTREE_CLEANED}

    if ctx.agent_result is None and current_state in _NEEDS_AGENT_RESULT:
        if _has_valid_agent_result(ctx.run_dir):
            ctx.agent_result = _load_agent_result(agent_dir)
            ctx.agent_ran = False

    if ctx.judgment is None and current_state in _NEEDS_JUDGMENT:
        judge_result_file = judge_dir / "result.json"
        if judge_result_file.exists():
            # Load even if is_valid=False — needed for finalize/report
            ctx.judgment = _load_judge_result(judge_dir)
```

**Fix 3** — call `restore_run_context` after RunContext construction (`scylla/e2e/subtest_executor.py`):
```python
# After ctx = RunContext(...), before build_actions_dict:
from scylla.e2e.stages import restore_run_context
from scylla.e2e.models import RunState as _RS
if sm:
    _current = sm.get_state(tier_id.value, subtest.id, run_num)
    if _current != _RS.PENDING:
        restore_run_context(ctx, _current)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | What To Do Instead |
|---------|----------------|---------------|--------------------|
| Crash recovery by patching checkpoint to `failed` | Manually patched checkpoint JSON to `experiment_state=failed` so STEP 3 would trigger when bug left checkpoint in bad state (`experiment_state=complete` but `run_states=failed`) | Worked as a one-time recovery but is a manual workaround | Should not be needed once bugs 1-3 are fixed; apply the proper code fixes |
| Using `--fresh` to restart after failed resume | Restarted the full run with `--fresh` flag to recover from a failed resume | `--fresh` destroys all previously-computed stages (worktree, baseline, replay.sh), wasting time and computation | Patch the checkpoint to `failed` state and let STEP 3 handle recovery |
| Loading judge result only if `is_valid=True` | `restore_run_context` checked `_has_valid_judge_result()` before loading the judge result | `_has_valid_judge_result()` returns `False` for `is_valid=False` results (zero-score consensus from failed judges), causing "judgment must be set" errors even when `judge/result.json` existed | Check for file existence directly, bypassing the validity check |

## Key Files

| File | Role |
|------|------|
| `scylla/e2e/runner.py` | STEP 3 (failed reset) and STEP 4 (incomplete run re-entry) |
| `scylla/e2e/stages.py` | `stage_execute_agent`, `stage_finalize_run`, `restore_run_context()` |
| `scylla/e2e/subtest_executor.py` | RunContext creation + `restore_run_context` call |
| `scylla/e2e/tier_state_machine.py` | TierState enum and transition registry |
| `scylla/e2e/state_machine.py` | RunState enum and `advance_to_completion()` |
| `tests/unit/e2e/test_runner.py` | `TestInitializeOrResumeExperimentFailedReset` class |

## Notes

- The linter reverted several changes in `runner.py`, `stages.py`, `subtest_executor.py`, and `test_runner.py` after the bugs were fixed (reverting `config_loaded` → `subtests_running`, removing `restore_run_context`, etc.). Always verify the current state of these files before assuming bugs are fixed.
- Judge prompt is empty when `--skip-judge-validation` is used with haiku and the agent produces no output — this is expected; the system falls back to zero-score consensus and continues normally.
- `worktree_cleaned` is the last RunState; when `--until worktree_cleaned` is used, the run is terminal so the subtest correctly advances to `aggregated` (not `runs_in_progress`).
