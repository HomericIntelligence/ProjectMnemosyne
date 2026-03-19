# CLI Visualize Subcommand — Raw Notes

## Session: 2026-02-24

### Context

ProjectScylla's `scripts/manage_experiment.py` had only `run` and `repair` subcommands.
There was no way to inspect experiment state from the CLI without manually reading checkpoint JSON files.

### Key Files Modified

| File | Change |
|------|--------|
| `scripts/manage_experiment.py` | Added ~270 lines: helper functions, format renderers, `cmd_visualize()`, parser registration |
| `tests/unit/e2e/test_manage_experiment.py` | Added `TestCmdVisualize` class with 16 tests |

### Checkpoint Structure (v3.1)

```json
{
  "version": "3.1",
  "experiment_id": "test-017",
  "experiment_state": "complete",
  "tier_states": {"T0": "complete", "T1": "complete"},
  "subtest_states": {"T0": {"00": "aggregated"}},
  "run_states": {"T0": {"00": {"1": "worktree_cleaned"}}},
  "completed_runs": {"T0": {"00": {"1": "passed"}}},
  "started_at": "2026-02-23T18:56:10+00:00",
  "last_updated_at": "2026-02-23T19:20:33+00:00",
  "pid": 12345
}
```

### Sample Tree Output

```
Experiment: test-017 [complete]
  +-- T0 [complete]
  |    \-- 00 [aggregated]
  |        \-- run_01 [worktree_cleaned] -> passed
  +-- T1 [complete]
  |    \-- 01 [aggregated]
  |        \-- run_01 [worktree_cleaned] -> passed
  \-- T6 [complete]
       \-- 01 [aggregated]
           \-- run_01 [worktree_cleaned] -> failed
```

### Sample `--states-only` Batch Output

```
EXP              TIER  SUBTEST      RUN  STATE
-------------------------------------------------------
test-017         T0    00           1    worktree_cleaned
test-017         T1    01           1    worktree_cleaned
test-021         T0    00           1    failed
test-038         T0    00           1    diff_captured
```

### Pre-commit Hook Requirements

- ruff format (auto-fixes formatting)
- ruff check (E501 line length 100, N806 uppercase in function)
- mypy type checking
- All hooks must pass before push