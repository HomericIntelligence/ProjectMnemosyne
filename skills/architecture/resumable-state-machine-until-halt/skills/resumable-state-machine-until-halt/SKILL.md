---
name: resumable-state-machine-until-halt
description: "Fix --until semantics in resumable state machines: sentinel exception that transitions state before stopping, additive CLI tier merging, ephemeral CLI arg preservation. Use when advance() leaves subtest/tier stuck at prior state because sentinel exception fires before the state update."
category: architecture
date: 2026-02-25
user-invocable: false
---

# Resumable State Machine: --until Halt Semantics

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-25 |
| Branch | `1067-additive-cli-args-checkpoint` |
| Objective | Fix `--until` re-execution bug; additive CLI tiers; `in_progress` run display |
| Outcome | SUCCESS — 3108 tests pass, 78.27% coverage, all hooks pass |

## When to Use

- A state machine's `advance()` method updates checkpoint state **after** executing the action
- You have a sentinel exception (`UntilHaltError`) raised from inside an action to signal "stop here"
- After raising the sentinel, the subtest/tier is stuck in the **from_state** instead of **to_state**
- You want `--until` to stop cleanly but leave state resumable (not FAILED)
- CLI `--tiers` / `--until` flags must survive a config reload from checkpoint on resume
- Previously-complete work should be detected and skipped; new work should be added additively

## The Core Bug: Sentinel Exception Before State Update

In a typical state machine `advance()`:

```python
action = actions.get(current_state)
if action is not None:
    action()                          # ← sentinel raised HERE
    # ...
# State update — NEVER REACHED when exception propagates
self.checkpoint.set_state(transition.to_state.value)
save_checkpoint(...)
```

When `UntilHaltError` is raised from the PENDING action, `set_state` is never called.
The subtest stays at PENDING, not RUNS_IN_PROGRESS. On the next resume, the action
runs again, causing re-execution and potential failure cascades.

## Verified Workflow

### 1. Define `UntilHaltError` in the state machine module (not the executor)

To avoid circular imports, put the sentinel class in the same module as the state machine:

```python
# scylla/e2e/subtest_state_machine.py
class UntilHaltError(Exception):
    """Sentinel raised when --until stops run execution before runs reach a terminal state.

    SubtestStateMachine.advance_to_completion catches this and leaves the subtest
    in RUNS_IN_PROGRESS (preserving state for future resume) without marking FAILED.
    """
```

In the executor (which imports from the state machine), use a lazy import:

```python
# scylla/e2e/subtest_executor.py
def _run_loop_and_save_manifest(self, ...):
    ...
    from scylla.e2e.subtest_state_machine import UntilHaltError
    raise UntilHaltError(f"--until stopped runs at {until_run_state.value}")
```

### 2. Catch `UntilHaltError` in `advance()` and STILL perform the state transition

The key fix: catch the sentinel, do the state update, then re-raise:

```python
def advance(self, tier_id, subtest_id, actions):
    current = self.get_state(tier_id, subtest_id)
    transition = get_next_subtest_transition(current)  # e.g. PENDING → RUNS_IN_PROGRESS

    halt_error: UntilHaltError | None = None
    action = actions.get(current)
    if action is not None:
        _t0 = time.monotonic()
        try:
            action()
        except UntilHaltError as _e:
            # Still transition the state so we land in RUNS_IN_PROGRESS (resumable)
            # rather than staying at PENDING.
            halt_error = _e
        _elapsed = time.monotonic() - _t0
        logger.info(f"[{tier_id}/{subtest_id}] {current.value} -> {transition.to_state.value}: ...")

    # Update state (even if UntilHaltError was raised)
    self.checkpoint.set_subtest_state(tier_id, subtest_id, transition.to_state.value)
    save_checkpoint(self.checkpoint, self.checkpoint_path)

    if halt_error is not None:
        raise halt_error   # re-raise so advance_to_completion can stop the loop

    return transition.to_state
```

### 3. Catch `UntilHaltError` in `advance_to_completion()` to stop without FAILED

```python
def advance_to_completion(self, tier_id, subtest_id, actions, until_state=None):
    try:
        while not self.is_complete(tier_id, subtest_id):
            new_state = self.advance(tier_id, subtest_id, actions)
            if until_state is not None and new_state == until_state:
                break
    except UntilHaltError as e:
        # --until stopped runs before they reached a terminal state.
        # Leave the subtest in RUNS_IN_PROGRESS so it can be resumed later.
        # Do NOT mark as FAILED — this is intentional early termination.
        logger.info(f"[{tier_id}/{subtest_id}] {e}")
    except Exception:
        self.checkpoint.set_subtest_state(tier_id, subtest_id, SubtestState.FAILED.value)
        save_checkpoint(self.checkpoint, self.checkpoint_path)
        raise

    return self.get_state(tier_id, subtest_id)
```

### 4. Skip runs already at `until_run_state` in the run loop

Prevents re-execution on resume when `_run_loop_and_save_manifest` is called again:

```python
def _run_loop(self, ...):
    for run_num in range(1, runs_per_subtest + 1):
        if sm and self.config.until_run_state is not None:
            current_run_state = sm.get_state(tier_id.value, subtest.id, run_num)
            if current_run_state == self.config.until_run_state:
                continue  # already at --until state, skip
        # ... execute run
```

### 5. Raise `UntilHaltError` after `_run_loop` when non-terminal runs remain

```python
def _run_loop_and_save_manifest(self, tier_id, subtest, ...):
    self._run_loop(tier_id, subtest, ...)
    self._save_manifest(...)

    if self.config.until_run_state is not None and ssm is not None:
        from scylla.e2e.models import RunState
        from scylla.e2e.state_machine import is_terminal_state
        from scylla.e2e.subtest_state_machine import UntilHaltError

        run_map = ssm.checkpoint.run_states.get(tier_id.value, {}).get(subtest.id, {})
        any_non_terminal = any(
            not is_terminal_state(RunState(s))
            for s in run_map.values()
            if s in {e.value for e in RunState}
        )
        if any_non_terminal:
            raise UntilHaltError(
                f"--until stopped runs before terminal state in "
                f"{tier_id.value}/{subtest.id}"
            )
```

### 6. Restore ephemeral CLI args after config reload from checkpoint

Config reload overwrites `self.config`. Capture CLI-only fields before and re-apply after:

```python
def _initialize_or_resume_experiment(self):
    # STEP 1: Capture CLI tiers and ephemeral args before overwrite
    _cli_tiers = list(self.config.tiers_to_run)
    _cli_ephemeral = {
        "until_run_state": self.config.until_run_state,
        "until_tier_state": self.config.until_tier_state,
        "until_experiment_state": self.config.until_experiment_state,
        "max_subtests": self.config.max_subtests,
    }

    # STEP 2: Load checkpoint + config (overwrites self.config)
    _load_checkpoint_and_config(...)

    # Restore ephemeral args (only if non-None, so saved config wins when CLI omits)
    non_none_ephemeral = {k: v for k, v in _cli_ephemeral.items() if v is not None}
    if non_none_ephemeral:
        self.config = self.config.model_copy(update=non_none_ephemeral)
```

### 7. Merge CLI tiers additively and detect tiers needing execution

Move tier-merge OUT of the `failed/interrupted` block so it fires for all checkpoint states:

```python
    # STEP 4: Merge CLI tiers + detect incomplete runs
    existing_tier_ids = {t.value for t in self.config.tiers_to_run}
    new_tiers = [t for t in _cli_tiers if t.value not in existing_tier_ids]
    if new_tiers:
        self.config = self.config.model_copy(
            update={"tiers_to_run": self.config.tiers_to_run + new_tiers}
        )
        self._save_config()
        self.checkpoint.config_hash = compute_config_hash(self.config)

    needs_execution = self._check_tiers_need_execution(_cli_tiers)

    if needs_execution and self.checkpoint.experiment_state in (
        "complete", "tiers_complete", "reports_generated"
    ):
        self.checkpoint.experiment_state = "tiers_running"
        for tier_id_str in needs_execution:
            existing_tier_state = self.checkpoint.tier_states.get(tier_id_str)
            if existing_tier_state in ("complete", "subtests_complete", ...):
                self.checkpoint.tier_states[tier_id_str] = "subtests_running"
                for sub_id, sub_state in self.checkpoint.subtest_states.get(tier_id_str, {}).items():
                    if sub_state == "aggregated":
                        if self._subtest_has_incomplete_runs(tier_id_str, sub_id):
                            self.checkpoint.subtest_states[tier_id_str][sub_id] = "runs_in_progress"
```

### 8. Exclude `tiers_to_run` from config hash

Prevents hash mismatches when tiers change between invocations:

```python
# scylla/e2e/checkpoint.py — compute_config_hash()
config_dict = self.config.model_dump()
config_dict.pop("tiers_to_run", None)  # Tiers are additive across resumes
```

### 9. Add `in_progress` as a third run display status

For runs stopped mid-sequence by `--until`:

```python
_RUN_TERMINAL_STATES = frozenset({"worktree_cleaned", "failed", "rate_limited"})

def _derive_run_result(checkpoint, tier_id, subtest_id, run_num_int, run_state_raw) -> str:
    stored: str | None = checkpoint.get_run_status(tier_id, subtest_id, run_num_int)
    if stored is not None:
        return stored                        # pass / fail / agent_complete
    if run_state_raw in ("pending", ""):
        return ""                            # not started
    if run_state_raw in _RUN_TERMINAL_STATES:
        return run_state_raw                 # terminal non-pass state
    return "in_progress"                     # mid-sequence (e.g. replay_generated)
```

## Failed Attempts (Critical)

| Attempt | Why It Failed | Fix |
|---------|---------------|-----|
| Define `UntilHaltError` in `subtest_executor.py` | Circular import: `subtest_executor` imports `subtest_state_machine`, which would need to import `subtest_executor` | Define in `subtest_state_machine.py`; use lazy import in `subtest_executor.py` |
| Test expects `RUNS_IN_PROGRESS` after `UntilHaltError` from PENDING action | `advance()` updates state AFTER `action()` returns; exception prevents the update; state stays at PENDING | Fix `advance()` to catch `UntilHaltError`, still update state, re-raise |
| Tier-merge only inside `if experiment_state in ("failed", "interrupted")` | CLI tiers not merged when experiment was previously `"complete"` | Move tier-merge outside the failed/interrupted block |
| Remove `# type: ignore[arg-type]` before testing | After fix, mypy no longer needs the suppression; leaving it causes `unused-ignore` mypy error | Remove suppressions after fix |
| `--retry-errors` resets ALL failed runs globally | User only wants retries scoped to CLI-requested tiers | Pass `tier_filter=cli_tiers` to `reset_runs_for_from_state()` |
| Bare `results_dir / experiment_id` path for `--from` | Runner creates timestamp-prefixed dirs (`2026-02-25T06-12-39-test-001`); bare path never matches | Use `_find_checkpoint_path(results_dir, experiment_id)` with `*-{experiment_id}` glob |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Tests | 3108 passed |
| Coverage | 78.27% (threshold: 75%) |
| Pre-commit | All hooks pass |
| New tests added | 14 (UntilHaltError×3, DeriveRunResult×5, FindCheckpointPath×3, RetryScoped×1, Runner×3) |
| Files modified | 5 (runner.py, checkpoint.py, subtest_state_machine.py, subtest_executor.py, manage_experiment.py) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1107 — additive CLI args + --until fix | [notes.md](../references/notes.md) |

## Key Invariants

1. **Sentinel exception must transition state**: Any sentinel that signals "stop here but don't fail" must trigger the state update before propagating — otherwise the machine is stuck in the prior state and will re-execute on resume.
2. **Ephemeral fields = fields excluded from config hash**: Only fields not persisted to `experiment.json` should be restored from CLI; persistent fields (`runs_per_subtest`, `model`) must stay from saved config.
3. **Additive means merge, not replace**: New tiers go into `tiers_to_run`; already-complete tiers are detected and skipped by `_check_tiers_need_execution()`.
4. **Skip-already-at logic prevents re-execution**: In the run loop, check if a run is already at `until_run_state` before executing it.
