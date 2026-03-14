---
name: checkpoint-disk-reconciliation
description: "Reconcile stale checkpoint states with on-disk artifacts after ProcessPool race conditions or interrupted runs. Use when: checkpoint shows intermediate states but disk has valid results, --retry-errors skips runs that completed on disk, or judge-failed runs need re-running."
category: debugging
date: 2026-03-13
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Checkpoint states become stale after ProcessPool race conditions or interrupted runs — runs that completed on disk still show intermediate states like `judge_prompt_built` or `dir_structure_created` in the checkpoint |
| **Root Cause** | ProcessPool workers each get a serialized (forked) copy of the checkpoint at fork time; concurrent saves can overwrite each other's state entries |
| **Solution** | Before retrying, scan on-disk artifacts to infer the true terminal state of each run and advance stale checkpoint entries forward |
| **Key Invariant** | Reconciliation only advances states — never regresses a more advanced checkpoint state |
| **Related Fix** | ProcessPool read-modify-write fix in `checkpoint.py` (commit 18f619b) prevents future races |

## When to Use

1. `--retry-errors` skips tests that should be re-run — checkpoint shows all runs at `worktree_cleaned` but some failed the judge
2. Experiment interrupted mid-run; checkpoint has intermediate states (`judge_prompt_built`, `dir_structure_created`, etc.) but `run_result.json` exists on disk
3. After restoring from backup: disk has results but checkpoint is stale
4. Multi-process/parallel tier execution produced conflicting checkpoint saves

## Verified Workflow

### Quick Reference

```python
# Disk inference priority (highest wins):
# run_result.json + report.md + no workspace/ → worktree_cleaned
# run_result.json + report.md                 → report_written
# run_result.json                             → run_finalized
# judge/result.json valid                     → judge_complete
# agent/result.json valid                     → agent_complete
# nothing                                     → leave as-is
```

### Step 1: Understand the stale state pattern

Stale checkpoint states arise from two distinct failure modes:

**Mode A — Intermediate states with valid on-disk results**:
- Checkpoint shows `judge_prompt_built`, `replay_generated`, etc.
- On disk: `run_result.json` + `report.md` exist (run completed)
- `--retry-errors` would resume from the intermediate state, re-running judge unnecessarily

**Mode B — Judge-failed runs at `worktree_cleaned`**:
- Checkpoint shows `worktree_cleaned` (run is "complete")
- `completed_runs` has `status: "failed"` (judge rejected the agent output)
- `--retry-errors` skips this run because it sees `worktree_cleaned`

### Step 2: Implement `_reconcile_checkpoint_with_disk()`

Add to `scripts/manage_experiment.py` after `_reset_non_completed_runs`:

```python
def _reconcile_checkpoint_with_disk(checkpoint: Any, experiment_dir: Path) -> int:
    """Reconcile checkpoint run_states with on-disk artifacts.

    Scans filesystem and advances stale checkpoint states to match reality.
    Only moves states forward — never regresses a more advanced state.

    Returns:
        Number of run states corrected.
    """
    from scylla.e2e.agent_runner import _has_valid_agent_result
    from scylla.e2e.judge_runner import _has_valid_judge_result

    # State ordering for rank comparison
    _STATE_ORDER = [
        "pending", "dir_structure_created", "symlinks_applied",
        "baseline_captured", "replay_generated", "agent_complete",
        "diff_captured", "judge_pipeline_run", "judge_prompt_built",
        "judge_complete", "run_finalized", "report_written",
        "checkpointed", "worktree_cleaned",
    ]
    _STATE_RANK = {s: i for i, s in enumerate(_STATE_ORDER)}

    corrected = 0

    for tier_id, subtests in checkpoint.run_states.items():
        for subtest_id, runs in subtests.items():
            for run_num_str, current_state in list(runs.items()):
                run_num = int(run_num_str)
                run_dir = experiment_dir / tier_id / subtest_id / f"run_{run_num:02d}"

                if not run_dir.exists():
                    continue

                run_result_file = run_dir / "run_result.json"
                report_md = run_dir / "report.md"
                workspace_dir = run_dir / "workspace"

                inferred_state: str | None = None
                inferred_status: str | None = None

                if run_result_file.exists():
                    try:
                        import json as _json
                        run_result_data = _json.loads(run_result_file.read_text())
                        judge_passed = run_result_data.get("judge_passed", False)
                        inferred_status = "passed" if judge_passed else "failed"
                    except (OSError, ValueError, KeyError):
                        inferred_status = None

                    if report_md.exists() and not workspace_dir.exists():
                        inferred_state = "worktree_cleaned"
                    elif report_md.exists():
                        inferred_state = "report_written"
                    else:
                        inferred_state = "run_finalized"
                elif _has_valid_judge_result(run_dir):
                    inferred_state = "judge_complete"
                elif _has_valid_agent_result(run_dir):
                    inferred_state = "agent_complete"

                if inferred_state is None:
                    continue

                current_rank = _STATE_RANK.get(current_state, 0)
                inferred_rank = _STATE_RANK.get(inferred_state, 0)

                if inferred_rank > current_rank:
                    checkpoint.set_run_state(tier_id, subtest_id, run_num, inferred_state)
                    if inferred_status is not None:
                        checkpoint.mark_run_completed(
                            tier_id, subtest_id, run_num, status=inferred_status
                        )
                    corrected += 1

    return corrected
```

### Step 3: Extend `_reset_non_completed_runs()` for judge-failed runs

Add a check inside the `worktree_cleaned` continue block:

```python
for run_num_str, state in list(runs.items()):
    if state == "worktree_cleaned":
        # Also reset judge-failed worktree_cleaned runs
        run_status = checkpoint.get_run_status(tier_id, subtest_id, int(run_num_str))
        if run_status == "failed":
            runs[run_num_str] = "pending"
            checkpoint.unmark_run_completed(tier_id, subtest_id, int(run_num_str))
            affected_tiers.add(tier_id)
            affected_subtests.add((tier_id, subtest_id))
            reset_count += 1
        continue
    # ... existing logic for non-worktree_cleaned states
```

### Step 4: Extend `_checkpoint_has_retryable_runs()` for batch skip detection

```python
def _checkpoint_has_retryable_runs(checkpoint_path: Path) -> bool:
    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
        for subtests in data.get("run_states", {}).values():
            for runs in subtests.values():
                for state in runs.values():
                    if state != "worktree_cleaned":
                        return True
        # Also check for judge-failed runs (worktree_cleaned + failed status)
        for subtests in data.get("completed_runs", {}).values():
            for runs in subtests.values():
                for status in runs.values():
                    if status == "failed":
                        return True
    except Exception:
        pass
    return False
```

### Step 5: Integrate into `--retry-errors` paths

In both batch mode and single mode `--retry-errors` handlers:

```python
if args.retry_errors:
    _cp_path = _find_checkpoint_path(args.results_dir, experiment_id)
    if _cp_path is not None:
        _cp = _load_cp(_cp_path)
        _exp_dir = Path(_cp.experiment_dir)
        # Step 1: Reconcile checkpoint with disk state
        _reconcile_count = _reconcile_checkpoint_with_disk(_cp, _exp_dir)
        if _reconcile_count > 0:
            logger.info(f"Reconciled {_reconcile_count} run state(s) with disk")
        # Step 2: Reset non-completed and judge-failed runs
        _reset_count = _reset_non_completed_runs(_cp)
        if _reconcile_count > 0 or _reset_count > 0:
            _save_cp(_cp, _cp_path)
```

### Step 6: Write unit tests

Test the key invariants:

```python
def test_reconcile_advances_stale_state(tmp_path):
    """Stale intermediate state advances to worktree_cleaned when artifacts exist."""
    run_dir = tmp_path / "exp" / "T0" / "00" / "run_01"
    run_dir.mkdir(parents=True)
    (run_dir / "run_result.json").write_text('{"judge_passed": true, "cost_usd": 0.01}')
    (run_dir / "report.md").write_text("# Report")

    checkpoint = E2ECheckpoint(
        run_states={"T0": {"00": {"1": "judge_prompt_built"}}}, ...
    )
    corrected = _reconcile_checkpoint_with_disk(checkpoint, tmp_path / "exp")

    assert corrected == 1
    assert checkpoint.run_states["T0"]["00"]["1"] == "worktree_cleaned"
    assert checkpoint.get_run_status("T0", "00", 1) == "passed"

def test_reconcile_does_not_regress_advanced_state(tmp_path):
    """State already more advanced than disk evidence is not regressed."""
    # Only agent result exists, but checkpoint is at judge_complete
    # → no change (0 corrected)

def test_reset_resets_judge_failed_worktree_cleaned(tmp_path):
    """worktree_cleaned + completed_runs failed → reset to pending."""

def test_checkpoint_has_retryable_runs_true_for_judge_failed(tmp_path):
    """All run_states worktree_cleaned + some completed_runs failed → True."""
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Only reset `failed`/`rate_limited` run states | Original `_reset_non_completed_runs` skipped `worktree_cleaned` entirely | Judge-failed runs at `worktree_cleaned` were never re-run | Must also check `completed_runs` status, not just run state |
| Only fix `_checkpoint_has_retryable_runs` for batch skip | Updated skip detection but not the actual reset logic | Batch would enter retry but `_reset_non_completed_runs` still skipped judge-failed runs | Both detection AND reset must handle judge-failed pattern |
| Reconcile by resetting all non-`worktree_cleaned` states to `pending` | Simple reset without reading disk first | Would re-run agent from scratch on runs where judge already completed | Must infer state from disk artifacts to resume at the right point |
| Read `run_result.json` with `judge_passed` only | Used field directly without error handling | Some `run_result.json` files have malformed JSON or missing `judge_passed` | Always wrap in try/except; default `inferred_status = None` if parse fails |

## Results & Parameters

### Dryrun3 Impact (what triggered this)
- 47 tests, 8 with stale checkpoint states (test-001/002/003/004/012/013/014/028)
- test-001/002/003: All 103 `run_result.json` exist on disk, but 13/14/35 stale intermediate states in checkpoint
- T0/12 and T6/01: Judge-failed runs at `worktree_cleaned` that needed re-running

### State inference priority (disk artifacts)

| Disk Artifacts Present | Inferred State |
|------------------------|----------------|
| `run_result.json` + `report.md` + no `workspace/` | `worktree_cleaned` |
| `run_result.json` + `report.md` + `workspace/` present | `report_written` |
| `run_result.json` only | `run_finalized` |
| `judge/result.json` valid (no `run_result.json`) | `judge_complete` |
| `agent/result.json` valid (no `judge/result.json`) | `agent_complete` |
| Nothing | leave as-is |

### Run directory structure
```
experiment_dir/
  {tier_id}/          # e.g., T0, T1, T6
    {subtest_id}/     # e.g., 00, 01 (or 00-empty for named subtests)
      run_{NN:02d}/   # e.g., run_01, run_02, run_03
        run_result.json
        report.md
        report.json
        workspace/    # deleted at worktree_cleaned stage
        agent/
          result.json
          stderr.log
          stdout.log
        judge/
          result.json
```

### Key checkpoint fields

```python
# run_states: fine-grained state machine position
checkpoint.run_states["T0"]["00"]["1"]  # e.g., "judge_prompt_built"

# completed_runs: pass/fail status (used by skip detection)
checkpoint.completed_runs["T0"]["00"][1]  # "passed", "failed", or "agent_complete"

# Methods
checkpoint.set_run_state(tier_id, subtest_id, run_num, state)
checkpoint.mark_run_completed(tier_id, subtest_id, run_num, status="passed")
checkpoint.unmark_run_completed(tier_id, subtest_id, run_num)
checkpoint.get_run_status(tier_id, subtest_id, run_num)  # returns str | None
```

### PR reference
- ProjectScylla PR #1480: `feat(retry-errors): reconcile checkpoint with disk state before retrying`
