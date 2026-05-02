# Raw Notes: resume-from-failed-experiment

## Session Details

- **Date**: 2026-02-25
- **Project**: ProjectScylla
- **Branch**: `fix-resume-from-failed-experiment`
- **PRs**: #1104 (merged), #1105 (merged)

## Original Failing Command

```bash
pixi run python scripts/manage_experiment.py run \
  --config tests/fixtures/tests/test-001 --runs 1 --max-subtests 1 \
  --until replay_generated --results-dir ~/dryrun3 -v --retry-errors
```

**Symptom**: Experiment exits with "Experiment complete" in <1 second. Only T0 runs (already
complete), T1 never starts.

## Checkpoint State That Triggered Bug

```json
{
  "experiment_state": "failed",
  "tier_states": {"T0": "complete"},
  "subtest_states": {"T0": {"00": "aggregated"}},
  "run_states": {"T0": {"00": {"1": "failed"}}}
}
```

`experiment.json` had `tiers_to_run: ['T0']` (original run was T0-only).

## Investigation Log

1. Checked `advance_to_completion()` — `while not self.is_complete()` exits immediately for
   FAILED state
2. Checked `_run_batch()` — `--retry-errors` consumed here only (batch_summary.json filter)
3. Checked `cmd_run()` — `--retry-errors` not consumed in single mode path
4. Found `_load_checkpoint_and_config()` replaces `self.config` entirely with saved `experiment.json`
5. Confirmed saved `experiment.json` has `tiers_to_run: ['T0']` — T1 never in scope

## Files Changed

### `scylla/e2e/runner.py` (PR #1104, #1105)

- `_initialize_or_resume_experiment()`: Added `_cli_tiers = list(self.config.tiers_to_run)`
  before load, then terminal state reset block + tier merge block after load
- Key lines: ~313 (`_cli_tiers` capture), ~327-367 (reset + merge block)

### `scripts/manage_experiment.py` (PR #1104)

- Updated `--retry-errors` help text to mention both modes
- Added single-mode block after `--from` block (~line 886-904)

### `tests/unit/e2e/test_runner.py` (PR #1104, #1105)

- `TestInitializeOrResumeExperimentFailedReset` class with 6 tests
- Key pattern: mock `_load_checkpoint_and_config` via `patch.object` + `fake_load` side_effect
  to bypass config hash validation

### `tests/unit/e2e/test_manage_experiment.py` (PR #1104)

- `TestRetryErrorsInSingleMode` class with 2 tests
- Key pattern: patch `scylla.e2e.checkpoint.reset_runs_for_from_state` (NOT `manage_experiment.*`)

## Test Execution

```bash
# Run new tests
pixi run python -m pytest tests/unit/e2e/test_runner.py::TestInitializeOrResumeExperimentFailedReset -v
pixi run python -m pytest tests/unit/e2e/test_manage_experiment.py::TestRetryErrorsInSingleMode -v

# Full suite
pixi run python -m pytest tests/unit/e2e/test_runner.py tests/unit/e2e/test_manage_experiment.py -v
# Result: 136 passed (no regressions)
```

## Errors Encountered During Implementation

### 1. `AttributeError: module 'scylla.e2e.runner' does not have the attribute 'is_zombie'`

- **Cause**: `is_zombie` imported locally inside function block, not at module level
- **Fix**: Patch `scylla.e2e.health.is_zombie` instead

### 2. `AttributeError: module 'manage_experiment' does not have the attribute 'reset_runs_for_from_state'`

- **Cause**: `reset_runs_for_from_state` imported locally inside `if args.retry_errors:` block
- **Fix**: Patch `scylla.e2e.checkpoint.reset_runs_for_from_state`

### 3. Tests asserting `experiment_state == 'tiers_running'` but got `'initializing'`

- **Cause**: `_load_checkpoint_and_config()` raises ValueError (config hash mismatch, no
  `experiment.json` on disk), outer try/except falls through to `_create_fresh_experiment()`
- **Fix**: Mock `_load_checkpoint_and_config` with `patch.object` to inject checkpoint directly,
  set `runner.checkpoint` and `runner.experiment_dir` in side_effect

### 4. Ruff E501 line too long on help text and test docstring

- `--retry-errors` help text: shortened to fit 100 char limit
- Test docstring with `status_filter=['failed']`: removed the brackets/quotes

### 5. Ruff D401 "First line of docstring should be in imperative mood"

- `"""Helper: create runner...` → `"""Create runner and run...`

## Verification of Fix (Manual Smoke Test)

Expected log after all three fixes applied, resuming the dryrun3 FAILED checkpoint:

```
Resetting experiment state from 'failed' to 'tiers_running' for re-execution
Adding CLI-specified tiers to retry run: ['T1']
Starting tier T0
[T0 runs/skips completed runs]
Starting tier T1
[T1 executes]
Experiment complete
```

## Architectural Notes

### Why `tiers_to_run` can be extended on FAILED resume (not strict hash violation)

The config hash is validated on resume to prevent silent config drift. However, when we
detect a FAILED terminal state and reset it, we're intentionally expanding the run scope.
By re-computing the hash after extending `tiers_to_run` and saving both `experiment.json`
and the checkpoint, the hash stays consistent for any future resume of this checkpoint.

### Why only FAILED/INTERRUPTED trigger the tier merge (not complete)

A `complete` experiment should be idempotent — re-running it should be a no-op or start fresh.
Only terminal-but-retryable states (FAILED, INTERRUPTED) warrant state reset + tier extension.
