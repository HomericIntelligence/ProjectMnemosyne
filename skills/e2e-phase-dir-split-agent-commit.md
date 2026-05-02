---
name: e2e-phase-dir-split-agent-commit
description: "Split E2E run directories into in_progress/ and completed/ phases with atomic promotion, agent git commit, and off-peak scheduling. Use when: (1) agent crashes or interrupted runs pollute results with phantom 0.0 scores, (2) judging must be isolated from in-flight runs, (3) rm -rf in_progress/ must be safe for clean restart, (4) Stage 3 ENOENT on promote after multi-stage execution."
category: architecture
date: 2026-03-28
version: "1.1.0"
user-invocable: false
verification: verified-ci
tags:
  - e2e
  - directory-structure
  - state-machine
  - agent-commit
  - off-peak
  - phase-split
  - run-lifecycle
  - debugging
  - idempotency
---

# E2E Phase Directory Split + Agent Commit + Off-Peak Scheduling

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Prevent agent crashes and interrupted runs from polluting pass_rate stats; isolate judging from in-flight work; enable clean restarts |
| **Outcome** | ✅ Operational — PRs #1738, #1739, and #1748 merged |
| **Verification** | verified-ci |
| **Project** | ProjectScylla |
| **PRs** | [#1738](https://github.com/HomericIntelligence/ProjectScylla/pull/1738), [#1739](https://github.com/HomericIntelligence/ProjectScylla/pull/1739), [#1748](https://github.com/HomericIntelligence/ProjectScylla/pull/1748) |

## When to Use

- Agent crashes create empty workspaces — judge scores 0.0, dragging down pass_rate
- Worktree cleanup loses all agent work (git diff captures nothing)
- You need to restart a failed experiment without losing already-judged results
- Judging and reporting must only operate on completed, stable run data
- You want off-peak API scheduling to avoid rate limits during peak hours
- Stage 3 ENOENT on promote after multi-stage execution (`_reset_non_completed_runs()` incorrectly resets `promoted_to_completed` runs, causing `stage_promote_to_completed()` to fail with `[Errno 2] No such file or directory`)

## Verified Workflow

### Quick Reference

```python
# paths.py additions (centralized routing)
IN_PROGRESS_DIR = "in_progress"
COMPLETED_DIR = "completed"

def get_tier_dir(experiment_dir, tier_id, *, completed=False):
    phase = COMPLETED_DIR if completed else IN_PROGRESS_DIR
    return experiment_dir / phase / tier_id

def get_run_dir(experiment_dir, tier_id, subtest_id, run_num, *, completed=False):
    return get_subtest_dir(..., completed=completed) / f"run_{run_num:02d}"

def get_experiment_dir_from_run(run_dir):
    """4 levels up: run → subtest → tier → phase → experiment"""
    return run_dir.parent.parent.parent.parent

def promote_run_to_completed(experiment_dir, tier_id, subtest_id, run_num):
    src = get_run_dir(..., completed=False)
    dst = get_run_dir(..., completed=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    # v1.1.0: Idempotency guard — if source already moved, return existing dst
    if not src.exists() and dst.exists():
        return dst
    shutil.move(str(src), str(dst))
    # Copy (not move) pipeline_baseline.json so siblings can also use it
    baseline = src.parent / "pipeline_baseline.json"
    if baseline.exists():
        shutil.copy2(baseline, dst.parent / "pipeline_baseline.json")
    return dst
```

```python
# New RunStates (models.py)
AGENT_CHANGES_COMMITTED = "agent_changes_committed"
PROMOTED_TO_COMPLETED = "promoted_to_completed"

# ExperimentConfig addition
off_peak: bool = False
```

```python
# New stage functions (stages.py)

def stage_commit_agent_changes(ctx):
    """AGENT_COMPLETE → AGENT_CHANGES_COMMITTED"""
    # Detect infrastructure failure: exit_code=-1 AND zero tokens
    if (ctx.agent_result and ctx.agent_result.exit_code == -1
            and ctx.agent_result.token_stats.input_tokens == 0
            and ctx.agent_result.token_stats.output_tokens == 0):
        failed_dir = ctx.run_dir.parent / ".failed" / ctx.run_dir.name
        failed_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ctx.run_dir), str(failed_dir))
        raise RuntimeError(f"Infrastructure failure — run archived to {failed_dir}")
    if ctx.workspace and ctx.workspace.exists():
        subprocess.run(["git", "add", "-A"], cwd=ctx.workspace, check=True)
        subprocess.run(["git", "commit", "-m", "[scylla] Agent changes"], cwd=ctx.workspace)

def stage_promote_to_completed(ctx):
    """DIFF_CAPTURED → PROMOTED_TO_COMPLETED"""
    experiment_dir = get_experiment_dir_from_run(ctx.run_dir)
    new_run_dir = promote_run_to_completed(experiment_dir, ...)
    ctx.run_dir = new_run_dir
    ctx.workspace = new_run_dir / "workspace"
```

```python
# scheduling.py (new module)
PEAK_START_UTC = 12   # 8AM EDT (conservative)
PEAK_END_UTC = 19     # 3PM EDT / 2PM EST

def is_peak_hours():
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Weekend
        return False
    return PEAK_START_UTC <= now.hour < PEAK_END_UTC

def wait_for_off_peak(check_interval_seconds=300):
    while is_peak_hours():
        time.sleep(check_interval_seconds)
```

### Detailed Steps

1. **Add `IN_PROGRESS_DIR`/`COMPLETED_DIR` constants to `paths.py`** with `get_tier_dir(completed=False)` routing
2. **Add new RunStates** `AGENT_CHANGES_COMMITTED` and `PROMOTED_TO_COMPLETED` to `models.py`
3. **Add transitions** in `state_machine.py`:
   - `AGENT_COMPLETE → AGENT_CHANGES_COMMITTED`
   - `DIFF_CAPTURED → PROMOTED_TO_COMPLETED`
4. **Add stage functions** `stage_commit_agent_changes` and `stage_promote_to_completed` to `stages.py`
5. **Create `in_progress/` and `completed/`** in `experiment_setup_manager.py` at init time
6. **Update all path construction sites** to use `get_tier_dir/get_subtest_dir/get_run_dir` with correct `completed=` value
7. **Create `scheduling.py`** with `is_peak_hours()` and `wait_for_off_peak()`
8. **Add `--off-peak` flag** to CLI; gate each subtest in `parallel_executor.py` on `wait_for_off_peak()`
9. **Fix `llm_judge._get_patchfile`** — guard for missing workspace, add `_get_committed_diff(HEAD~1..HEAD)` fallback
10. **Update all consuming modules** (regenerate, rehydrate, analysis/loader, experiment_result_writer) to read/write from `completed/`
11. **Add `_STATES_PAST_AGENT_COMPLETE`** updates in `resume_manager.py` for new states

### Directory Structure After Implementation

```
experiment_dir/
  checkpoint.json
  in_progress/          # PENDING → DIFF_CAPTURED (safe to rm -rf for restart)
    T0/00/run_01/
      workspace/        # agent works here
  completed/            # PROMOTED_TO_COMPLETED onward
    T0/00/run_01/
      agent/
      judge/
      run_result.json   # written during judging
    T0/best_subtest.json
    T0/result.json
```

### State Flow

```
PENDING → ... → AGENT_COMPLETE
       → AGENT_CHANGES_COMMITTED   (git commit in workspace)
       → FAILURE_CLEARED
       → DIFF_CAPTURED
       → PROMOTED_TO_COMPLETED     (shutil.move to completed/)
       → JUDGE_PIPELINE_RUN → ...
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Initial PR merged without auditing all path construction sites | 17 bypass violations found post-merge in tier_manager, parallel_tier_runner, regenerate, manage_experiment | Always grep `experiment_dir / tier_id` pattern before merging a directory structure change |
| 2 | `tier_action_builder.py` had `elif` fallback loading `best_subtest.json` from `in_progress/` | `best_subtest.json` is written to `completed/` — fallback returned wrong/empty data for T5 | Remove stale fallbacks entirely; don't add fallback paths that point to the wrong phase |
| 3 | `promote_run_to_completed` used `shutil.move` for `pipeline_baseline.json` | First run's baseline would be gone after promotion; sibling runs in the same subtest need it too | Use `shutil.copy2` for the baseline (copy not move) so siblings can also be promoted |
| 4 | Committed CONDITIONAL GO before adding missing tests | `_get_patchfile` committed-diff fallback had no test; `test_stage_promote.py` didn't exist as separate file | Run strict audit before marking implementation complete; create test files for every new stage |
| 5 | `resume_manager._STATES_PAST_AGENT_COMPLETE` not updated | New states `AGENT_CHANGES_COMMITTED` and `PROMOTED_TO_COMPLETED` not included — resume into these states would skip agent result validation | Whenever new RunStates are added, grep for all frozensets/lists of RunState values and update them |
| 6 | `_reset_non_completed_runs()` only treated `worktree_cleaned` as terminal in its skip list | `promoted_to_completed` runs were reset to `pending`, forcing re-execution of `stage_promote_to_completed()` on runs whose `in_progress/` directory was already moved to `completed/` — ENOENT crash | Any state representing "data safely persisted" must be added to the reset skip list; treat `promoted_to_completed` as terminal alongside `worktree_cleaned` |
| 7 | `promote_run_to_completed()` had no idempotency guard — `shutil.move()` on a missing source crashes | When source `in_progress/` path is already moved but state was reset, `shutil.move()` raises `FileNotFoundError` instead of recognizing the destination already exists | Add defense-in-depth: `if not src.exists() and dst.exists(): return dst` before `shutil.move()` |
| 8 | "Reset 357 non-completed run(s) for retry" log message looked normal but was the smoking gun | 357 out of 360 total runs being reset means almost everything was reset — the number should have been close to 0 for a Stage 3 resume, not close to total | When diagnosing multi-stage failures, compare reset count against total run count; a reset count near total indicates the skip list is incomplete |

## Results & Parameters

### Pre-Merge Audit Command

Run this before merging any directory-structure PR to catch bypass violations:

```bash
# Find all sites that construct paths directly without paths.py
grep -rn "experiment_dir / \|experiment_dir/" src/scylla/e2e/ scripts/ \
  | grep -v "paths.py" \
  | grep -v "# noqa" \
  | grep -v "__pycache__"
```

Expected output: zero hits (all path construction routed through `paths.py`).

### Test Coverage Requirements

For any phase-split implementation, require tests for:
1. `stage_commit_agent_changes` — infra failure detection, normal commit, missing workspace
2. `stage_promote_to_completed` — directory move, ctx.run_dir update, baseline promotion
3. `scheduling.is_peak_hours` — weekday peak, weekend, boundary minutes
4. `_get_patchfile` — missing workspace guard, committed-diff fallback, no-changes sentinel
5. `--off-peak` CLI flag wiring (flag=True sets `config.off_peak=True`)
6. All existing path construction tests updated to use `completed/` prefix

### State Machine Additions Template

```python
# models.py
class RunState(str, Enum):
    # ... existing states ...
    AGENT_CHANGES_COMMITTED = "agent_changes_committed"   # After AGENT_COMPLETE
    PROMOTED_TO_COMPLETED = "promoted_to_completed"       # After DIFF_CAPTURED

# Update _STATES_PAST_AGENT_COMPLETE in resume_manager.py
_STATES_PAST_AGENT_COMPLETE = frozenset({
    RunState.AGENT_COMPLETE.value,
    RunState.AGENT_CHANGES_COMMITTED.value,   # ADD
    RunState.DIFF_CAPTURED.value,
    RunState.PROMOTED_TO_COMPLETED.value,     # ADD
    # ... rest of states ...
})
```

### Reset Skip List (v1.1.0)

In `_reset_non_completed_runs()` (`scripts/manage_experiment.py`), the skip set must include all
states where run data has been safely persisted to `completed/`:

```python
# manage_experiment.py — _reset_non_completed_runs()
_SKIP_STATES = ("worktree_cleaned", "promoted_to_completed")
# Any run in these states has already moved data to completed/
# and MUST NOT be reset to pending
```

**Diagnostic**: If the "Reset N non-completed run(s) for retry" log shows N close to total
run count, the skip list is missing a terminal state.

### Clean Restart Procedure

```bash
# Safe — no judged data is in in_progress/
rm -rf experiment_dir/in_progress/

# Resume from checkpoint (will restart all non-promoted runs)
python scripts/manage_experiment.py run --config test-dir --from agent_complete
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PRs #1738/#1739 — haiku-2 production run prep | 5439 tests, 78.44% coverage |
| ProjectScylla | PR #1748 — fix `_reset_non_completed_runs()` + idempotent promote guard | 89 tests pass locally, verified-local |
