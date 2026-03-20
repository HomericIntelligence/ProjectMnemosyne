---
name: resume-from-failed-experiment
description: "Fix resume-from-FAILED experiment in E2E state machine framework \u2014\
  \ three compounding bugs where terminal states cause immediate exit, --retry-errors\
  \ is silently ignored in single mode, and saved tiers_to_run overrides CLI tiers\
  \ on resume"
category: evaluation
date: 2026-02-25
version: 1.0.0
user-invocable: false
---
# Resume-from-FAILED Experiment: Three Compounding Bugs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Project** | ProjectScylla |
| **Objective** | Fix `--retry-errors` in single mode resuming a FAILED experiment that runs only old tiers and then exits immediately |
| **Outcome** | ✅ Three distinct bugs identified and fixed across two PRs (#1104, #1105) |
| **Impact** | High — FAILED experiments can now be resumed and extended with additional tiers without `--from` workaround |

## When to Use This Skill

Use this skill when:

1. **Resuming a checkpoint with `experiment_state=failed`** causes immediate "Experiment complete" with no tiers running
2. **`--retry-errors` flag has no effect** in single-test mode (only works in batch mode)
3. **Only original tiers run** on resume, even when CLI specifies additional tiers (e.g. saved `T0` but CLI wants `T0 T1`)
4. **Diagnosing why a failed experiment doesn't retry** despite explicit retry flags

**Triggers**:
- Log shows: `"Experiment complete"` immediately after loading FAILED checkpoint
- `experiment_state=failed` in checkpoint.json, run exits in <1 second
- T1-T6 never appear in logs despite being in `--tiers` or default
- `--retry-errors` in single mode produces no reset behavior

## Verified Workflow

### Root Cause Analysis

Three compounding bugs — each necessary for the symptom to appear:

#### Bug 1: FAILED is a terminal state — ESM exits immediately

`ExperimentStateMachine.advance_to_completion()` checks `while not self.is_complete()` on the
first iteration. `FAILED` is in `_EXPERIMENT_TERMINAL_STATES`, so the loop body never executes.

```python
# scylla/e2e/experiment_state_machine.py
_EXPERIMENT_TERMINAL_STATES: frozenset[ExperimentState] = frozenset(
    [ExperimentState.COMPLETE, ExperimentState.INTERRUPTED, ExperimentState.FAILED]
)

# advance_to_completion() — immediately exits if state is FAILED
while not self.is_complete():   # <-- exits here for FAILED
    new_state = self.advance(actions)
```

#### Bug 2: `--retry-errors` is batch-only, silently a no-op in single mode

`--retry-errors` is only consumed in `_run_batch()` where it filters `batch_summary.json`.
In `cmd_run()` single mode, the flag is parsed but never acted upon — no checkpoint reset
occurs.

#### Bug 3: Saved `experiment.json` overrides CLI `tiers_to_run` completely

When resuming, `_load_checkpoint_and_config()` loads `experiment.json` verbatim:
```python
self.config = ExperimentConfig.load(saved_config_path)  # CLI config completely replaced
```
If the original run had `tiers_to_run: ['T0']`, the loaded config also has only T0 — the
CLI's `--tiers T0 T1` default is silently ignored.

### Fix 1: Reset terminal experiment state on resume (`scylla/e2e/runner.py`)

In `_initialize_or_resume_experiment()`, after zombie detection, detect FAILED/INTERRUPTED and
reset to allow re-entry:

```python
# Capture CLI tiers BEFORE _load_checkpoint_and_config overwrites self.config
_cli_tiers = list(self.config.tiers_to_run)

# ... load checkpoint (overwrites self.config) ...

# Reset terminal experiment states for re-execution
if self.checkpoint and self.checkpoint.experiment_state in ("failed", "interrupted"):
    logger.info(
        f"Resetting experiment state from '{self.checkpoint.experiment_state}'"
        " to 'tiers_running' for re-execution"
    )
    self.checkpoint.experiment_state = "tiers_running"
    # Reset failed tier states so they can be retried
    for tier_id, tier_state in self.checkpoint.tier_states.items():
        if tier_state == "failed":
            self.checkpoint.tier_states[tier_id] = "pending"
    # Reset failed subtest states
    for tier_id in self.checkpoint.subtest_states:
        for subtest_id, sub_state in self.checkpoint.subtest_states[tier_id].items():
            if sub_state == "failed":
                self.checkpoint.subtest_states[tier_id][subtest_id] = "pending"

    # Merge CLI tiers into the loaded config (Bug 3 fix)
    existing_tier_ids = {t.value for t in self.config.tiers_to_run}
    new_tiers = [t for t in _cli_tiers if t.value not in existing_tier_ids]
    if new_tiers:
        tier_names = [t.value for t in new_tiers]
        logger.info(f"Adding CLI-specified tiers to retry run: {tier_names}")
        self.config = self.config.model_copy(
            update={"tiers_to_run": self.config.tiers_to_run + new_tiers}
        )
        # Persist updated config and config_hash for consistency
        self._save_config()
        self.checkpoint.config_hash = compute_config_hash(self.config)

    save_checkpoint(self.checkpoint, checkpoint_path)
```

**Key**: `_cli_tiers` must be captured BEFORE `_load_checkpoint_and_config()` is called, as
that method overwrites `self.config` entirely.

### Fix 2: `--retry-errors` in single mode (`scripts/manage_experiment.py`)

After the existing `--from` block in `cmd_run()`, add:

```python
# Handle --retry-errors in single mode: reset failed runs to pending
if args.retry_errors and not (from_run_state or from_tier_state or from_experiment_state):
    from scylla.e2e.checkpoint import (
        load_checkpoint,
        reset_runs_for_from_state,
        save_checkpoint,
    )

    checkpoint_path = args.results_dir / experiment_id / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = load_checkpoint(checkpoint_path)
        reset_count = reset_runs_for_from_state(
            checkpoint,
            from_state="pending",
            status_filter=["failed"],
        )
        if reset_count > 0:
            save_checkpoint(checkpoint, checkpoint_path)
            logger.info(f"--retry-errors: reset {reset_count} failed run(s) for retry")
```

**Note**: Only trigger when `--from` is NOT also specified (avoid double-reset).

### Verification

Expected log output after fix when resuming FAILED experiment with new tiers:
```
Resetting experiment state from 'failed' to 'tiers_running' for re-execution
Adding CLI-specified tiers to retry run: ['T1']
Starting tier T0
Starting tier T1
```

### Workaround (no code change required)

The existing `--from` flag already handles this correctly:
```bash
pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-001 --runs 1 --max-subtests 1 \
  --from replay_generated --filter-status failed \
  --until replay_generated --results-dir ~/dryrun3 -v
```

`--from` calls `reset_runs_for_from_state()` which resets FAILED runs to PENDING and cascades
to subtest/tier/experiment states.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### PRs

- PR #1104: Fix 1 (runner.py terminal state reset) + Fix 2 (--retry-errors single mode) — merged
- PR #1105: Fix 3 (CLI tier merging into saved config) — merged

### Checkpoint JSON structure after fix

```json
{
  "experiment_state": "tiers_running",
  "tier_states": {"T0": "pending", "T1": "pending"},
  "subtest_states": {"T0": {"00": "pending"}}
}
```

### Test patterns

**Mocking `_load_checkpoint_and_config` for terminal state tests**:
```python
def fake_load(path: Path) -> tuple[Any, Path]:
    runner.checkpoint = checkpoint  # inject directly
    runner.experiment_dir = exp_dir
    return checkpoint, exp_dir

with patch.object(runner, "_load_checkpoint_and_config", side_effect=fake_load):
    runner._initialize_or_resume_experiment()
```

**Integration test for tier merge** (real filesystem, no mock of load):
```python
# Create saved config with only T0
saved_config = ExperimentConfig(..., tiers_to_run=[TierID.T0])
saved_config.save(config_dir / "experiment.json")

# Create runner with CLI config T0+T1
cli_config = ExperimentConfig(..., tiers_to_run=[TierID.T0, TierID.T1])
runner = E2ERunner(cli_config, ...)

# After _initialize_or_resume_experiment, T1 must be in tiers_to_run
tier_ids = {t.value for t in runner.config.tiers_to_run}
assert "T1" in tier_ids
```

### Key architectural facts

- `ExperimentConfig.tiers_to_run` IS included in `config_hash` (static field)
- `until_run_state`, `from_run_state`, `filter_*` are NOT in `config_hash` (ephemeral)
- `_load_checkpoint_and_config()` completely replaces `self.config` with saved `experiment.json`
- `compute_config_hash()` must be re-called after updating `tiers_to_run` to keep checkpoint consistent
- `reset_runs_for_from_state(from_state="pending", status_filter=["failed"])` resets runs
  in `failed` state and cascades to subtest/tier/experiment states

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PRs #1104, #1105 (2026-02-25) | [notes.md](../../references/notes.md) |

## Related Skills

- `e2e-checkpoint-resume` — v1 checkpoint/resume with rate limit handling (earlier system)
- `e2e-framework-crash-recovery-bugs` — resume assertion errors when states are past PENDING
- `state-machine-wiring` — `advance_to_completion` loop and terminal state behavior
- `manage-experiment-audit` — `--from` args silently ignored in batch mode (similar pattern)
