---
name: e2e-resume-restore-run-context
description: "Fix _restore_run_context() missing run_result and judgment loading on resume past RUN_FINALIZED/JUDGE_COMPLETE. Use when: (1) Phase 3 resume crashes with 'run_result must be set before write_report', (2) checkpoint shows runs at run_finalized/report_written but ctx fields are None on resume."
category: debugging
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - e2e
  - resume
  - checkpoint
  - state-machine
  - judge
---

# E2E Resume: Restore RunContext Fields Past Judge States

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix Phase 3 (judging) resume crash where `stage_write_report()` fails with "run_result must be set before write_report" |
| **Outcome** | Successful — added judgment + run_result loading to `_restore_run_context()`, plus cleanup script for stale experiment data |

## When to Use

- Resume from a state past `JUDGE_COMPLETE` or `RUN_FINALIZED` crashes with missing `ctx.run_result` or `ctx.judgment`
- Phase 3 retry after partial judge execution leaves stale artifacts (judge dirs, run_result.json, reports)
- Multi-phase experiment execution (`--until agent_complete` then `--until diff_captured` then full run) where later phases skip earlier stages
- Checkpoint shows runs at `run_finalized` or `report_written` but `stage_write_report()` fails on resume

## Verified Workflow

### Quick Reference

```python
# In _restore_run_context() (subtest_executor.py), after judge_prompt loading:

# Load judgment for states past JUDGE_COMPLETE
if is_at_or_past_state(run_state, RunState.JUDGE_COMPLETE) and ctx.judgment is None:
    from scylla.e2e.judge_runner import _has_valid_judge_result, _load_judge_result
    from scylla.e2e.paths import get_judge_dir
    judge_dir = get_judge_dir(ctx.run_dir)
    if _has_valid_judge_result(ctx.run_dir):
        ctx.judgment = _load_judge_result(judge_dir)

# Load run_result for states past RUN_FINALIZED
if is_at_or_past_state(run_state, RunState.RUN_FINALIZED) and ctx.run_result is None:
    run_result_path = ctx.run_dir / "run_result.json"
    if run_result_path.exists():
        ctx.run_result = _load_run_result(run_result_path)
```

```python
# _load_run_result helper — filter extra keys before model_validate
def _load_run_result(run_result_path: Path) -> Any:
    from scylla.e2e.models import E2ERunResult
    data = json.loads(run_result_path.read_text())
    known_fields = set(E2ERunResult.model_fields.keys())
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return E2ERunResult.model_validate(filtered)
```

### Detailed Steps

1. **Identify the gap**: `_restore_run_context()` loaded `agent_result` (past AGENT_COMPLETE) and `judge_prompt` (past JUDGE_PROMPT_BUILT) but NOT `judgment` or `run_result` for later states.

2. **Understand the resume paths**: `stage_capture_diff()` (stages.py:730-746) loads judgment when replaying through DIFF_CAPTURED, but runs resuming **past** DIFF_CAPTURED skip that stage entirely. `_restore_run_context()` is the only restore point for those runs.

3. **Handle Pydantic model constraints**: `E2ERunResult` has `ConfigDict(frozen=True)` without `extra="ignore"`. The on-disk `run_result.json` contains extra keys (`process_metrics`, `progress_tracking`, `changes`) added by `stage_finalize_run()`. Must filter to known fields before `model_validate()`.

4. **Cleanup stale experiment data**: After partial Phase 3 execution, cleanup script must:
   - Delete: `judge/` dirs, `run_result.json`, `report.md`, `report.json` at run level
   - Delete: report files at subtest/tier/experiment levels
   - Reset checkpoint: run_states → `diff_captured`, clear `completed_runs`, subtest_states → `runs_in_progress`, tier_states → `config_loaded`, experiment_state → `tiers_running`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct `E2ERunResult.model_validate(data)` | Load run_result.json directly into Pydantic model | `ConfigDict(frozen=True)` without `extra="ignore"` rejects extra keys (`process_metrics`, `progress_tracking`, `changes`) | Always check Pydantic model config before deserialization; `stage_finalize_run()` adds extra keys beyond the model schema |

## Results & Parameters

### Key Files

| File | Role |
|------|------|
| `scylla/e2e/subtest_executor.py:115-197` | `_restore_run_context()` — the only place RunContext fields are restored on resume |
| `scylla/e2e/stage_finalization.py:447-483` | `stage_write_report()` — requires `ctx.run_result`, `ctx.agent_result`, `ctx.judgment` |
| `scylla/e2e/stage_finalization.py:316-444` | `stage_finalize_run()` — creates `E2ERunResult`, writes `run_result.json` |
| `scylla/e2e/stages.py:709-746` | `stage_capture_diff()` — loads judgment on replay through DIFF_CAPTURED (not past it) |
| `scylla/e2e/models.py:85-120` | `RunState` enum — sequential states from PENDING to WORKTREE_CLEANED |

### Run State Machine (Judge Phase)

```
DIFF_CAPTURED → JUDGE_PIPELINE_RUN → JUDGE_PROMPT_BUILT → JUDGE_COMPLETE
    → RUN_FINALIZED → REPORT_WRITTEN → CHECKPOINTED → WORKTREE_CLEANED
```

### Restore Coverage Matrix

| Field | Loaded By | For States Past |
|-------|-----------|-----------------|
| `ctx.agent_result` | `_restore_run_context()` | `AGENT_COMPLETE` |
| `ctx.judge_prompt` | `_restore_run_context()` | `JUDGE_PROMPT_BUILT` |
| `ctx.judgment` | `_restore_run_context()` (NEW) | `JUDGE_COMPLETE` |
| `ctx.run_result` | `_restore_run_context()` (NEW) | `RUN_FINALIZED` |
| `ctx.judgment` | `stage_capture_diff()` | `DIFF_CAPTURED` (replay only, agent not re-run) |

### Cleanup Script Pattern

```python
# Reset states past judge phase back to diff_captured
JUDGE_AND_BEYOND = {"judge_pipeline_run", "judge_prompt_built", "judge_complete",
                     "run_finalized", "report_written", "checkpointed", "worktree_cleaned"}

# For each run in checkpoint:
if state in JUDGE_AND_BEYOND or state == "failed":
    runs[run_num_str] = "diff_captured"

# Clear completed_runs (contains judge pass/fail status)
cp["completed_runs"] = {}

# Reset subtest/tier/experiment states
# subtest: aggregated/failed → runs_in_progress
# tier: complete/failed/etc → config_loaded
# experiment: → tiers_running
```

### Haiku-2 Cleanup Stats

| Metric | Count |
|--------|-------|
| Judge dirs deleted | 46 |
| Run files deleted | 1,469 |
| Subtest files deleted | 959 |
| Tier files deleted | 161 |
| Experiment files deleted | 23 |
| Run states reset | 713 |
| Completed runs cleared | 2,408 |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | haiku-2 experiment Phase 3 resume failure | PR #1546, 7 tests cleaned, 1597 unit tests pass |
