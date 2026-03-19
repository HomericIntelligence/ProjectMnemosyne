---
name: manage-experiment-audit
description: "Skill: manage-experiment-audit"
category: uncategorized
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: manage-experiment-audit

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-24 |
| Project | ProjectScylla |
| Objective | Audit and fix manage_experiment.py CLI surface, --from logic, batch mode dispatch, and test coverage |
| Outcome | Bug fixed, 13 new tests, stale artifacts cleaned, docs updated |
| Commit | 068dbc4 on branch consolidate-run-command |

## When to Use

Use this skill when:
- Auditing a unified CLI script that wraps complex batch + single-mode logic
- Debugging why `--from` or filter args seem to have no effect in batch mode
- Writing tests for functions that use local imports (`from X import Y` inside function body)
- Encountering `TestFixture.from_directory` failures in test setup
- Reviewing `manage_experiment.py run` for missing arg wiring

## The Core Bug Pattern: --from Silently Ignored in Batch Mode

### Root Cause
`_run_batch → run_one_test()` only wired `--until*` args to `ExperimentConfig`. The `--from*` and `--filter-*` args were missing, AND the checkpoint reset block was entirely absent from the batch code path.

### Pattern to Check (Audit Checklist)
When a CLI has both a single-test path and a batch path, verify BOTH paths wire ALL relevant args:

```python
# WRONG: batch run_one_test missing --from wiring
config = ExperimentConfig(
    ...
    until_run_state=until_run_state,
    # MISSING: from_run_state, filter_tiers, etc.
)
# MISSING: checkpoint reset block

# CORRECT: full wiring
config = ExperimentConfig(
    ...
    until_run_state=until_run_state,
    from_run_state=from_run_state,
    from_tier_state=from_tier_state,
    from_experiment_state=from_experiment_state,
    filter_tiers=args.filter_tier,
    filter_subtests=args.filter_subtest,
    filter_runs=args.filter_run,
    filter_statuses=args.filter_status,
    filter_judge_slots=args.filter_judge_slot,
)
if from_run_state or from_tier_state or from_experiment_state:
    checkpoint_path = results_dir / experiment_id / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = load_checkpoint(checkpoint_path)
        reset_count = 0
        if from_run_state:
            reset_count += reset_runs_for_from_state(checkpoint, from_run_state.value, ...)
        if from_tier_state:
            reset_count += reset_tiers_for_from_state(checkpoint, from_tier_state.value, ...)
        if from_experiment_state:
            reset_count += reset_experiment_for_from_state(checkpoint, from_experiment_state.value)
        save_checkpoint(checkpoint, checkpoint_path)
```

## Mock Patching for Local Imports

### Problem
`cmd_run` imports `run_experiment` *inside* the function body:
```python
def cmd_run(args):
    from scylla.e2e.runner import run_experiment  # local import
    ...
    results = run_experiment(...)
```

### What Works
```python
# Patch the module attribute — import re-executes at call time, picks up the mock
with patch("scylla.e2e.runner.run_experiment", side_effect=mock_fn):
    cmd_run(args)
```

### What Fails
```python
# WRONG: manage_experiment.run_experiment doesn't exist at module level
with patch("manage_experiment.run_experiment", ...):  # AttributeError
    cmd_run(args)
```

### Rule
For locally-imported names, patch the **source module** (`X.Y`), not the importer (`importer.Y`).
This works because the `from X import Y` statement inside the function executes fresh each call,
looking up `Y` from the already-patched `X`.

## Test Fixture Gotchas for run_one_test()

### TestFixture.from_directory raises if prompt.md missing
```python
# run_one_test tries TestFixture.from_directory(test_dir) first
# If prompt.md doesn't exist → raises exception → falls back to raw yaml
# Always create prompt.md in test directories:
(test_dir / "prompt.md").write_text("test prompt")
```

### Correct yaml keys for run_one_test fallback
```python
# WRONG: TestFixture field names
test_yaml = {"source_repo": "...", "source_hash": "..."}  # → task_repo=None → error

# CORRECT: keys that run_one_test reads from raw yaml
test_yaml = {
    "task_repo": "https://github.com/test/repo",
    "task_commit": "abc123",
    "experiment_id": "test-exp",
    "timeout_seconds": 3600,
    "language": "python",
}
```

### Non-existent config path: mock run_experiment to return None
```python
# WRONG: raising FileNotFoundError propagates uncaught
def mock_run(config, tiers_dir, results_dir, fresh):
    raise FileNotFoundError(...)  # propagates out of cmd_run

# CORRECT: return falsy to trigger "if results:" → return 1
with patch("scylla.e2e.runner.run_experiment", return_value=None):
    result = cmd_run(args)
assert result == 1  # cmd_run returns 1 when results is falsy
```

## Incomplete Feature: --filter-judge-slot

`--filter-judge-slot` is parsed and stored on `ExperimentConfig.filter_judge_slots` but
`reset_runs_for_from_state()` has **no `judge_slot_filter` parameter**. The filter has no effect.

Document with explicit test:
```python
def test_filter_judge_slot_has_no_effect(...):
    # verify judge_slot_filter NOT in reset function kwargs
    assert "judge_slot_filter" not in reset_kwargs_captured[0]
```

Update CLI help to warn:
```python
parser.add_argument(
    "--filter-judge-slot",
    ...
    help="... NOTE: judge-slot-level filtering is not yet implemented; "
         "this argument is accepted but has no effect.",
)
```

## Audit Checklist for Unified CLI Scripts

When auditing a CLI that has both single-mode and batch-mode paths:

1. **Arg parity**: Does batch path wire ALL args that single path wires?
2. **Reset logic parity**: Does batch path perform checkpoint reset when `--from` is set?
3. **Error handling**: Does `--from` with missing checkpoint warn/fail gracefully in batch?
4. **Stale artifacts**: Are there old scripts superseded by the new unified CLI?
5. **Stale docs**: Does README still document removed subcommands?
6. **Incomplete features**: Are there args that are parsed but never consumed downstream?

## Verified Test Pattern: --from with existing checkpoint

```python
def test_from_with_checkpoint_calls_reset_and_run(self, tmp_path):
    results_dir = tmp_path / "results"
    experiment_id = "test-exp"
    # Create checkpoint at expected path
    checkpoint_dir = results_dir / experiment_id
    checkpoint_dir.mkdir(parents=True)
    checkpoint_path = checkpoint_dir / "checkpoint.json"
    checkpoint_path.write_text(json.dumps({...minimal checkpoint...}))

    reset_calls = []
    run_calls = []

    def mock_reset_runs(checkpoint, from_state, **kwargs):
        reset_calls.append(("runs", from_state, kwargs))
        return 1

    with (
        patch("scylla.e2e.model_validation.validate_model", return_value=True),
        patch("scylla.e2e.checkpoint.reset_runs_for_from_state", side_effect=mock_reset_runs),
        patch("scylla.e2e.checkpoint.reset_tiers_for_from_state", return_value=0),
        patch("scylla.e2e.checkpoint.reset_experiment_for_from_state", return_value=0),
        patch("scylla.e2e.runner.run_experiment", return_value={"T0": {}}),
    ):
        result = cmd_run(args)

    assert result == 0
    assert len(reset_calls) == 1
    assert reset_calls[0][1] == "replay_generated"
    assert len(run_calls) == 1  # NOTE: run_calls not wired above — use run_calls.append in mock
```
