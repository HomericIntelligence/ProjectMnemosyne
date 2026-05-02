# Notes: state-machine-interrupt-handling

## Session Context

- **Date**: 2026-02-27
- **Project**: ProjectScylla
- **Branch**: `fix-resume-issues-triple-bug`
- **PR**: [#1109](https://github.com/HomericIntelligence/ProjectScylla/pull/1109)
- **Commit**: `787dfb4`

## What Happened

During a 4-stage incremental resume test, Stage 4 was run without `--until` to let experiments
complete end-to-end. This required the agent (Claude Code CLI) to actually execute. When the user
hit Ctrl+C to interrupt:

1. OS sent SIGINT to the process group
2. The agent subprocess (`bash replay.sh`) was killed
3. `subprocess.run()` in `stage_execute_agent` returned with `returncode=-2` (no exception)
4. `stage_execute_agent` treated it as a completed run, set `ctx.agent_result`, `ctx.agent_ran = True`
5. `StateMachine.advance()` updated checkpoint: `REPLAY_GENERATED → AGENT_COMPLETE`
6. On next resume, runs were at `AGENT_COMPLETE` with empty/broken agent output
7. The judge stage then ran on broken output, producing meaningless results
8. Even worse, in a previous crash the runs had been left at `FAILED` (terminal), which meant
   the next resume computed 0% pass rate and completed in 0.1s

## The Related Bug (also fixed this session): Failed Tier Reset

**Separate from Ctrl+C**: When resuming and some runs were `FAILED` (terminal), the tier was
being reset to `SUBTESTS_RUNNING` instead of `CONFIG_LOADED`.

`SUBTESTS_RUNNING` = "select best subtest" phase — requires aggregated results from all subtests.
`CONFIG_LOADED` = "start subtest execution" phase — correctly re-enters the run loop.

Fix in `runner.py` STEP 4 resume logic:
```python
# Before fix:
self.checkpoint.tier_states[tier_id_str] = "subtests_running"  # WRONG

# After fix:
_any_incomplete = any(
    self._subtest_has_incomplete_runs(tier_id_str, sub_id)
    for sub_id in self.checkpoint.subtest_states.get(tier_id_str, {})
)
if _any_incomplete:
    self.checkpoint.tier_states[tier_id_str] = "config_loaded"  # CORRECT
    # Also reset relevant subtests back to runs_in_progress
```

## Checkpoint State After Ctrl+C Fix (Stage 4 final)

```json
{
  "experiment_state": "complete",
  "tier_states": { "T0": "complete", "T1": "complete", "T2": "complete", "T3": "complete" },
  "subtest_states": {
    "T0": { "00": "aggregated", "01": "runs_in_progress", "02": "runs_in_progress" },
    "T1": { "01": "aggregated", "02": "runs_in_progress", "03": "runs_in_progress" },
    "T2": { "02": "runs_in_progress", "01": "aggregated", "03": "runs_in_progress" },
    "T3": { "01": "aggregated" }
  },
  "run_states": {
    "T0": {
      "00": { "1": "worktree_cleaned", "2": "worktree_cleaned", "3": "worktree_cleaned" },
      "01": { "1": "replay_generated", ... },
      "02": { "1": "replay_generated", ... }
    }
  }
}
```

Subtests 01/02 (from earlier `--max-subtests` expansion) stayed at `replay_generated` — outside
the `--max-subtests 1` scope of Stage 4.

## File Locations (ProjectScylla)

| File | Role |
| ------ | ------ |
| `scylla/e2e/runner.py` | `ShutdownInterruptedError` class + `is_shutdown_requested()` |
| `scylla/e2e/stages.py` | `stage_execute_agent()` — shutdown check after `subprocess.run()` |
| `scylla/e2e/state_machine.py` | Run-level SM — `except ShutdownInterruptedError` before `except Exception` |
| `scylla/e2e/subtest_state_machine.py` | Subtest-level SM — re-raise without FAILED |
| `scylla/e2e/tier_state_machine.py` | Tier-level SM — reset to `CONFIG_LOADED` on interrupt |
| `scylla/e2e/experiment_state_machine.py` | Experiment-level SM — mark `INTERRUPTED` |
| `scylla/e2e/parallel_executor.py` | `_run_subtest_in_process_safe` — re-raise; `as_completed` loop — re-raise |

## Test Files Added

```
tests/unit/e2e/test_state_machine.py        — test_advance_to_completion_shutdown_interrupted_does_not_mark_failed
tests/unit/e2e/test_subtest_state_machine.py — test_shutdown_interrupted_does_not_mark_failed
tests/unit/e2e/test_tier_state_machine.py   — test_shutdown_interrupted_resets_tier_to_config_loaded
tests/unit/e2e/test_experiment_state_machine.py — test_shutdown_interrupted_marks_experiment_interrupted_not_failed
```

## Related Skills

- `architecture/resumable-state-machine-until-halt` — the `UntilHaltError` sentinel pattern
  (same principle: sentinel exception that avoids FAILED; this skill extends it to OS signals)
- `architecture/e2e-resume-refactor` — broader context on the 4-level state machine hierarchy