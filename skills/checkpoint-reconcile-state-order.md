---
name: checkpoint-reconcile-state-order
description: 'Fix stale checkpoint run states by reconciling with on-disk artifacts.
  Use when: adding RunState enum values, testing checkpoint reconcile edge cases,
  or debugging silent rank-comparison failures.'
category: testing
date: 2026-03-14
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | `_reconcile_checkpoint_with_disk()` uses a `state_order` rank list. States missing from the list get rank=0 (same as `pending`), so `inferred_rank > current_rank` is `0 > 0 = False` — the state never advances. No error is raised. |
| **Root Cause** | `state_order` was not kept in sync with the `RunState` enum. Three states were missing: `worktree_created`, `config_committed`, `prompt_written`. |
| **Fix** | Add all non-terminal `RunState` values in sequential order. Add a regression-guard test that asserts every non-terminal state appears in the function source. |
| **Project** | ProjectScylla — `scripts/manage_experiment.py` + `tests/unit/e2e/test_manage_experiment_run.py` |

## When to Use

- You are extending a state machine and adding new `RunState` (or equivalent) enum values
- A reconcile/recovery function uses a rank list (`state_order = [...]`) to compare states
- Runs are "stuck" at an intermediate state despite on-disk artifacts being present
- You need edge-case test coverage for: corrupted JSON, missing fields, mixed terminal/non-terminal states
- CI fails with `assert 'passed' is None` or similar — checkpoint auto-syncs status on `set_run_state`

## Verified Workflow

### Quick Reference

```python
# The pattern to watch for:
state_order = [
    "pending",
    "dir_structure_created",
    # ← missing states here get rank=0, silently fail rank comparison
    "symlinks_applied",
    ...
]
state_rank = {s: i for i, s in enumerate(state_order)}
# current_rank = state_rank.get(current_state, 0)  ← "get with default 0" hides the gap
```

### Step 1 — Identify Missing States

Compare `state_order` list against the `RunState` enum (or equivalent):

```python
# scylla/e2e/models.py RunState sequential order:
# PENDING → DIR_STRUCTURE_CREATED → WORKTREE_CREATED → SYMLINKS_APPLIED
# → CONFIG_COMMITTED → BASELINE_CAPTURED → PROMPT_WRITTEN → REPLAY_GENERATED
# → AGENT_COMPLETE → DIFF_CAPTURED → JUDGE_PIPELINE_RUN → JUDGE_PROMPT_BUILT
# → JUDGE_COMPLETE → RUN_FINALIZED → REPORT_WRITTEN → CHECKPOINTED
# → WORKTREE_CLEANED
# Terminal: FAILED | RATE_LIMITED (exclude from state_order)
```

Check: does `state_order` contain ALL non-terminal values?

### Step 2 — Fix `state_order`

Add missing states in correct sequential position:

```python
state_order = [
    "pending",
    "dir_structure_created",
    "worktree_created",        # ← was missing
    "symlinks_applied",
    "config_committed",        # ← was missing
    "baseline_captured",
    "prompt_written",          # ← was missing
    "replay_generated",
    "agent_complete",
    "diff_captured",
    "judge_pipeline_run",
    "judge_prompt_built",
    "judge_complete",
    "run_finalized",
    "report_written",
    "checkpointed",
    "worktree_cleaned",
]
```

### Step 3 — Add Regression Guard Test

Use `inspect.getsource()` to assert all non-terminal states appear in the function:

```python
def test_reconcile_state_order_covers_all_run_states(self) -> None:
    """All non-terminal RunState values must appear in state_rank (regression guard)."""
    import inspect
    import manage_experiment
    from scylla.e2e.models import RunState

    source = inspect.getsource(manage_experiment._reconcile_checkpoint_with_disk)
    terminal_states = {RunState.FAILED.value, RunState.RATE_LIMITED.value}
    non_terminal = {s.value for s in RunState if s.value not in terminal_states}

    for state_value in non_terminal:
        assert state_value in source, (
            f"RunState '{state_value}' is missing from _reconcile_checkpoint_with_disk "
            f"state_order — add it in the correct sequential position."
        )
```

### Step 4 — Edge-Case Tests

#### Corrupted JSON — state advances, status defaults to "passed"

```python
def test_reconcile_corrupted_run_result_json(self, tmp_path):
    (run_dir / "run_result.json").write_text("{ not valid json !!!")
    (run_dir / "report.md").write_text("# Report")
    # checkpoint at intermediate state
    corrected = _reconcile_checkpoint_with_disk(checkpoint, exp_dir)
    assert corrected == 1
    assert checkpoint.run_states["T0"]["00"]["1"] == "worktree_cleaned"
    # set_run_state("worktree_cleaned") auto-calls mark_run_completed("passed")
    # because inferred_status=None (JSON parse failed) → no override
    assert checkpoint.get_run_status("T0", "00", 1) == "passed"
```

**Key insight**: `set_run_state("worktree_cleaned")` auto-syncs `completed_runs` to `"passed"` (backward compat). If `inferred_status is None`, this default is NOT overridden. So corrupted JSON → status = `"passed"`, NOT `None`.

#### Missing `judge_passed` field — status = "failed" (default False)

```python
def test_reconcile_missing_judge_passed_field(self, tmp_path):
    (run_dir / "run_result.json").write_text(json.dumps({"cost_usd": 0.05}))
    (run_dir / "report.md").write_text("# Report")
    corrected = _reconcile_checkpoint_with_disk(checkpoint, exp_dir)
    assert corrected == 1
    assert checkpoint.run_states["T0"]["00"]["1"] == "worktree_cleaned"
    # .get("judge_passed", False) → False → inferred_status="failed"
    # mark_run_completed(..., "failed") overrides the "passed" default
    assert checkpoint.get_run_status("T0", "00", 1) == "failed"
```

#### `worktree_created` rank — run advances to `agent_complete`

```python
def test_reconcile_worktree_created_state_gets_correct_rank(self, tmp_path):
    # agent/result.json exists on disk
    checkpoint.run_states = {"T0": {"00": {"1": "worktree_created"}}}
    corrected = _reconcile_checkpoint_with_disk(checkpoint, exp_dir)
    assert corrected == 1
    assert checkpoint.run_states["T0"]["00"]["1"] == "agent_complete"
    # Before fix: worktree_created rank=0, agent_complete rank>0, 0 > 0 = False → no advance
    # After fix: worktree_created rank=2, agent_complete rank=8, 8 > 2 = True → advances
```

#### Mixed `failed` + `rate_limited` + `worktree_cleaned`

```python
def test_reset_interleaved_rate_limited_and_failed(self, tmp_path):
    checkpoint.run_states = {"T0": {"00": {"1": "failed", "2": "rate_limited", "3": "worktree_cleaned"}}}
    checkpoint.completed_runs = {"T0": {"00": {3: "passed"}}}  # int key, not str
    _reset_non_completed_runs(checkpoint)
    assert checkpoint.run_states["T0"]["00"]["1"] == "pending"
    assert checkpoint.run_states["T0"]["00"]["2"] == "pending"
    assert checkpoint.run_states["T0"]["00"]["3"] == "worktree_cleaned"
    assert checkpoint.get_run_status("T0", "00", 3) == "passed"
```

**Note**: `completed_runs` inner keys are `int`, not `str`. Mypy will catch `{"3": "passed"}` — use `{3: "passed"}`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assert `get_run_status() is None` after corrupted JSON | Expected that no `mark_run_completed` call → `None` status | `set_run_state("worktree_cleaned")` auto-calls `mark_run_completed("passed")` as backward-compat sync | Always check if `set_run_state` has side-effects on `completed_runs` before asserting status |
| `completed_runs={"T0": {"00": {"3": "passed"}}}` (str key) | Used string `"3"` as inner dict key | `E2ECheckpoint` declares `completed_runs: dict[str, dict[str, dict[int, str]]]` — inner key is `int` | Mypy error: `Dict entry 0 has incompatible type "str": "str"; expected "int": "str"` |
| Assumed `json.JSONDecodeError` not caught by `except (OSError, ValueError, KeyError)` | Thought the except block wouldn't fire | `json.JSONDecodeError` IS a subclass of `ValueError` — it is caught; the issue was the `set_run_state` side-effect | Verify the inheritance chain before assuming exception handling gaps |

## Results & Parameters

### PR Created

- **Branch**: `reconcile-checkpoint-retry-errors`
- **PR**: `HomericIntelligence/ProjectScylla#1485`
- **Files changed**: `scripts/manage_experiment.py` (+3 lines), `tests/unit/e2e/test_manage_experiment_run.py` (+176 lines)
- **Tests added**: 5 edge-case tests in `TestRetryErrorsInBatch`
- **Test suite**: 4861 passed, 78.36% coverage

### `E2ECheckpoint.set_run_state` Auto-Sync Behavior

```python
# States that auto-call mark_run_completed("passed") if no prior status:
terminal_complete = {
    "run_complete",      # v3.0 compat
    "run_finalized",     # v3.1
    "report_written",    # v3.1
    "checkpointed",
    "worktree_cleaned",
}
# Logic: preserves existing "passed"/"failed", defaults to "passed"
existing = self.get_run_status(tier_id, subtest_id, run_num)
compat_status = existing if existing in ("passed", "failed") else "passed"
self.mark_run_completed(tier_id, subtest_id, run_num, status=compat_status)
```

This means: if you call `set_run_state("worktree_cleaned")` before `mark_run_completed(..., "failed")`, the final status is `"failed"` (override wins). But if `inferred_status is None`, no override occurs and status stays `"passed"`.
