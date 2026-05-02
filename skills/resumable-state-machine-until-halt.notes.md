# Notes: Resumable State Machine --until Halt Semantics

## Session Context

- **Date**: 2026-02-25
- **Project**: ProjectScylla
- **Branch**: `1067-additive-cli-args-checkpoint`
- **PRs**: #1106 (additive CLI args), #1107 (--until fix + in_progress display)

## Problem Description

Two related bugs discovered from a real run log:

### Bug 1: `--until` Failure Cascade

Run log showed:
```
[T1/01] runs_in_progress -> runs_complete: All runs finished
[T1/01/run_01] replay_generated -> agent_complete: Execute Claude CLI agent
[ERROR] Run T1/01/run_01 failed in state replay_generated
[ERROR] Tier T1 failed
```

**Root cause**: `--until replay_generated` stopped runs at that state. SubtestSM advanced
PENDING → RUNS_IN_PROGRESS (first call to `_run_loop_and_save_manifest`). Then advanced
RUNS_IN_PROGRESS → RUNS_COMPLETE (second call). The second call tried to advance runs from
`replay_generated → agent_complete` which failed.

**Deeper root cause in `advance()`**:
```
1. current_state = PENDING
2. transition = PENDING → RUNS_IN_PROGRESS
3. action() called (_run_loop_and_save_manifest for PENDING)
4. _run_loop runs, stops runs at replay_generated
5. UntilHaltError raised from within action()
6. set_subtest_state() NEVER called (exception propagated past it)
7. State stays at PENDING
8. advance_to_completion catches UntilHaltError — state still PENDING
```

On next resume, the whole cycle repeats: PENDING action runs again, `_run_loop` tries
to re-execute `replay_generated → agent_complete`, which fails.

### Bug 2: CLI Args Lost on Config Reload

When resuming, `_load_checkpoint_and_config()` replaces `self.config` with the saved
`experiment.json`. This loses:
- `--tiers` (which tiers to run this invocation)
- `--until-*` flags
- `--max-subtests`

Previously, tier-merge only happened inside `if experiment_state in ("failed", "interrupted")`.
A previously-complete experiment would exit immediately even if new tiers were requested.

## Files Modified

| File | Change |
| ------ | -------- |
| `scylla/e2e/subtest_state_machine.py` | `UntilHaltError` class; `advance()` catches it, transitions state, re-raises |
| `scylla/e2e/subtest_executor.py` | Skip runs at `until_run_state`; raise `UntilHaltError` when non-terminal runs remain |
| `scylla/e2e/runner.py` | 4-step resume: capture ephemeral→load→restore ephemeral→merge tiers+detect incomplete |
| `scylla/e2e/checkpoint.py` | `tiers_to_run` excluded from config hash |
| `scripts/manage_experiment.py` | `_find_checkpoint_path()`, `_derive_run_result()`, `--retry-errors` tier scoping |

## Test Patterns

### Testing `UntilHaltError` state after sentinel

```python
def test_until_halt_error_leaves_subtest_in_runs_in_progress(ssm, checkpoint, checkpoint_path):
    from scylla.e2e.subtest_state_machine import UntilHaltError

    def action_that_raises_until_halt() -> None:
        raise UntilHaltError("--until stopped runs at replay_generated")

    actions = {SubtestState.PENDING: action_that_raises_until_halt}
    result = ssm.advance_to_completion(TIER_ID, SUBTEST_ID, actions)

    # Key assertion: state is RUNS_IN_PROGRESS, not PENDING or FAILED
    assert result == SubtestState.RUNS_IN_PROGRESS
    assert ssm.get_state(TIER_ID, SUBTEST_ID) == SubtestState.RUNS_IN_PROGRESS
    assert not ssm.is_complete(TIER_ID, SUBTEST_ID)
```

### Testing non-sentinel exceptions still mark FAILED

```python
def test_non_until_halt_exception_still_marks_failed(ssm, checkpoint, checkpoint_path):
    def action_that_crashes() -> None:
        raise RuntimeError("unexpected failure")

    with pytest.raises(RuntimeError):
        ssm.advance_to_completion(TIER_ID, SUBTEST_ID, {SubtestState.PENDING: action_that_crashes})

    assert ssm.get_state(TIER_ID, SUBTEST_ID) == SubtestState.FAILED
```

### Testing `_derive_run_result` for `in_progress`

```python
def test_derive_run_result_returns_in_progress_for_mid_sequence_state():
    mock_cp = MagicMock()
    mock_cp.get_run_status.return_value = None  # not in completed_runs
    result = _derive_run_result(mock_cp, "T0", "00", 1, "replay_generated")
    assert result == "in_progress"
```

## Mypy Gotcha: Unused `type: ignore` After Fix

The tests originally had `# type: ignore[arg-type]` on `advance_to_completion()` calls
because the `actions` dict type was incompatible. After the `advance()` fix made the type
signatures compatible, these became "unused-ignore" mypy errors. Remove them when the
underlying incompatibility is fixed.

## Timestamp-Prefixed Checkpoint Discovery

Runner creates dirs as `{timestamp}-{experiment_id}` (e.g., `2026-02-25T06-12-39-test-001`).
`manage_experiment.py --from` and `--retry-errors` were using bare `experiment_id` paths.

Fix pattern:
```python
def _find_checkpoint_path(results_dir: Path, experiment_id: str) -> Path | None:
    pattern = f"*-{experiment_id}"
    matching_dirs = sorted(
        [d for d in results_dir.glob(pattern) if d.is_dir()],
        key=lambda d: d.name, reverse=True,
    )
    for exp_dir in matching_dirs:
        cp = exp_dir / "checkpoint.json"
        if cp.exists():
            return cp
    return None
```

Test fixtures that use bare paths (`results_dir / experiment_id`) must be updated to
use timestamp-prefixed dirs (`results_dir / "2024-01-01T00-00-00-{experiment_id}"`).
