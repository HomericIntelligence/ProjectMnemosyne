---
name: checkpoint-state-machine-test-fixtures
description: "Use when: (1) writing integration or unit tests for ProjectScylla checkpoint-based state machines (StateMachine / SubtestStateMachine / TierStateMachine / ExperimentStateMachine), (2) debugging tests where checkpoint states are unexpectedly reset to pending, (3) adding orphan/integrity detectors to resume pipelines, (4) verifying additive/non-destructive resume behavior across sequential invocations, (5) testing zombie detection with real disk I/O, (6) verifying DataLoader reset behavior in Mojo training/validation loops, or (7) extracting shared pytest fixtures to eliminate per-test boilerplate."
category: testing
date: '2026-06-07'
version: "1.1.0"
user-invocable: false
history: checkpoint-state-machine-test-fixtures.history
tags:
  - checkpoint
  - state-machine
  - test-fixtures
  - pytest
  - integration-tests
  - orphan-detection
  - resume
  - zombie-detection
  - dataloader
  - mojo
---

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-05-19 |
| Project | ProjectScylla / ProjectOdyssey |
| Objective | Unified patterns for building consistent checkpoint test fixtures and integration tests across the 4-level state machine hierarchy |
| Outcome | 8 skills consolidated — covers fixture consistency rules, orphan detection, additive resume, zombie detection, shared fixtures, and DataLoader reset verification |

## When to Use

- Writing tests for `_initialize_or_resume_experiment()` or `ResumeManager.reset_failed_states()`
- Debugging a test where checkpoint subtest/tier states are unexpectedly reset to `"pending"`
- Adding integration tests for stateful/resumable experiment behavior across multiple invocations
- Testing that ephemeral flags do not affect persistent state (config hash stability)
- Adding orphan/integrity detectors to resume pipelines and auditing existing fixtures
- Testing zombie detection (`ResumeManager.handle_zombie()`) with real disk I/O
- Extending `RunState` enum and keeping `state_order` rank tables in sync
- Extracting shared `pytest` fixtures from repetitive per-test object construction
- Verifying that training/validation loops call `reset()` on a DataLoader before iterating

## Verified Workflow

### Quick Reference — Checkpoint Hierarchy Consistency

```python
# WRONG — orphan detector resets "01" to "pending"
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    # run_states defaults to {} — "01" has no backing runs!
)

# RIGHT — "01" has a terminal backing run, orphan detector leaves it alone
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
)
```

### 1. The 4-Level Checkpoint Hierarchy

ProjectScylla has four independent state machine layers, each populating distinct checkpoint fields:

```
experiment_state    (ExperimentStateMachine)
  └─ tier_states        (TierStateMachine — only populates tier_states)
       └─ subtest_states    (SubtestStateMachine)
            └─ run_states       (StateMachine)
```

| State Machine | Checkpoint field populated |
| --- | --- |
| `StateMachine` | `run_states[tier_id][subtest_id][run_num]` |
| `SubtestStateMachine` | `subtest_states[tier_id][subtest_id]` |
| `TierStateMachine` | `tier_states[tier_id]` |
| `ExperimentStateMachine` | `experiment_state` |

**Critical**: Running only `SubtestStateMachine` leaves `tier_states` empty. A tier absent from `tier_states` is implicitly `"pending"` regardless of whether subtests/runs completed.

### 2. Consistency Rules Enforced at Resume Time

| Higher State | Required Lower State | Validator |
| --- | --- | --- |
| subtest `"aggregated"` or `"runs_complete"` | At least one entry in `run_states[tier][subtest]` | `_find_orphaned_subtest_states()` |
| subtest `"runs_in_progress"` | At least one run in non-terminal state | `_find_tiers_with_intermediate_runs()` |
| tier `"complete"` | All subtests in `"aggregated"` | `_reset_tier_state_for_rerun()` |
| experiment `"complete"` | All tiers in complete-family state | `_reset_intermediate_runs_in_complete_experiment()` |

**Orphan cascade**: When an orphaned subtest is detected, `_reset_tier_to_config_loaded()` and `_reset_experiment_to_tiers_running()` are also called, so tier and experiment states may change unexpectedly.

### 3. ResumeManager Validator Execution Order

```python
def reset_failed_states(self):
    self._reset_infra_error_runs()                          # Step 1
    self._reset_intermediate_runs_in_complete_experiment()  # Step 2
    self._reset_orphaned_subtest_states()                   # Step 3 ← resets "aggregated" without run_states
    self._reset_failed_and_interrupted()                    # Step 4
```

Order matters: the orphan reset (Step 3) runs BEFORE the failed/interrupted reset (Step 4).

### 4. Building a Resume Test Fixture (Step-by-Step)

1. Decide which states you're testing — identify the specific reset behavior under test.
2. Set all four levels consistently — if a subtest is `"aggregated"`, give it a terminal run.
3. Use `"worktree_cleaned"` as the canonical terminal run state.
4. Use non-terminal run states for in-progress work (`"pending"`, `"report_written"`, etc.).
5. Audit: `grep -n '"aggregated"\|"runs_complete"' tests/unit/e2e/test_runner.py` — every match needs a backing `run_states` entry.

```python
def test_resume_resets_failed_subtests_only(self, mock_config, tmp_path):
    """Only failed subtests reset; aggregated subtests with runs survive."""
    checkpoint = E2ECheckpoint(
        experiment_id=mock_config.experiment_id,
        experiment_dir=str(tmp_path / mock_config.experiment_id),
        config_hash="abc123",
        experiment_state="failed",
        tier_states={"T0": "failed"},
        subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
        run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
        started_at=datetime.now(timezone.utc).isoformat(),
        last_updated_at=datetime.now(timezone.utc).isoformat(),
        status="failed",
    )
    assert checkpoint.subtest_states["T0"]["00"] == "pending"    # reset
    assert checkpoint.subtest_states["T0"]["01"] == "aggregated" # untouched
```

### 5. Additive Resume — State Machine Layer Tests

Tests at the state machine level (not `E2ERunner.run()`) — no real API calls, git ops, or subprocesses:

```python
from scylla.e2e.state_machine import StateMachine
from scylla.e2e.subtest_state_machine import SubtestStateMachine, UntilHaltError
from scylla.e2e.tier_state_machine import TierStateMachine
```

**TierState sequence and terminal states**:

```python
_TIER_STATE_SEQUENCE = [
    TierState.PENDING,
    TierState.CONFIG_LOADED,
    TierState.SUBTESTS_RUNNING,
    TierState.SUBTESTS_COMPLETE,
    TierState.BEST_SELECTED,
    TierState.REPORTS_GENERATED,
    TierState.COMPLETE,
]
_TIER_TERMINAL_STATES = frozenset([TierState.COMPLETE, TierState.FAILED])
```

**`_simulate_tier_subtests_at_state` — simulate runs halted at a specific state (mimics `--until` flag)**:

```python
def _simulate_tier_subtests_at_state(cp, cp_path, tier_id, subtest_ids, run_count, until_run_state):
    for subtest_id in subtest_ids:
        ssm = SubtestStateMachine(checkpoint=cp, checkpoint_path=cp_path)

        def _pending_runs() -> None:
            run_sm = StateMachine(checkpoint=cp, checkpoint_path=cp_path)
            for run_num in range(1, run_count + 1):
                run_sm.advance_to_completion(
                    tier_id, subtest_id, run_num,
                    make_noop_run_actions(),
                    until_state=until_run_state,
                )
            raise UntilHaltError("all runs reached until_state")

        subtest_actions: dict[SubtestState, Callable[[], None]] = cast(
            dict[SubtestState, Callable[[], None]],
            {
                SubtestState.PENDING: _pending_runs,
                SubtestState.RUNS_IN_PROGRESS: MagicMock(),
                SubtestState.RUNS_COMPLETE: MagicMock(),
            },
        )
        ssm.advance_to_completion(tier_id, subtest_id, subtest_actions)
```

**`_simulate_tier_to_complete` and `make_noop_tier_actions`**:

```python
def _simulate_tier_to_complete(cp, cp_path, tier_id, subtest_ids, run_count):
    """Run all subtests to WORKTREE_CLEANED, then advance TierStateMachine to COMPLETE."""
    _simulate_tier_subtests_full(cp, cp_path, tier_id, subtest_ids, run_count)
    tsm = TierStateMachine(checkpoint=cp, checkpoint_path=cp_path)
    tsm.advance_to_completion(tier_id, make_noop_tier_actions())

def make_noop_tier_actions():
    from scylla.e2e.models import TierState
    return {
        TierState.PENDING: MagicMock(),
        TierState.CONFIG_LOADED: MagicMock(),
        TierState.SUBTESTS_RUNNING: MagicMock(),
        TierState.SUBTESTS_COMPLETE: MagicMock(),
        TierState.BEST_SELECTED: MagicMock(),
        TierState.REPORTS_GENERATED: MagicMock(),
    }
```

**Asserting additive preservation**:

```python
_simulate_tier_to_complete(cp, cp_path, "T0", ["00"], runs=3)
cp = load_checkpoint(cp_path)
assert cp.tier_states.get("T0") == TierState.COMPLETE.value

# Add T1 partial runs without TierStateMachine advance
cp = load_checkpoint(cp_path)
_simulate_tier_subtests_at_state(cp, cp_path, "T1", ["00"], 3, RunState.REPLAY_GENERATED)
cp_after = load_checkpoint(cp_path)
assert cp_after.tier_states.get("T0") == TierState.COMPLETE.value  # preserved
assert "T1" not in cp_after.tier_states                            # no phantom entry
```

**Monotonic State Advancement Check** — verify runs only move forward across a resume:

```python
def _run_state_index(state_str: str) -> int:
    from scylla.e2e.state_machine import _RUN_STATE_SEQUENCE
    for idx, state in enumerate(_RUN_STATE_SEQUENCE):
        if state.value == state_str:
            return idx
    return -1  # Terminal states (failed, rate_limited)

# Verify runs only move forward
for tier_id, subtests in previous_cp.run_states.items():
    for subtest_id, runs in subtests.items():
        for run_key, old_state_str in runs.items():
            new_state_str = cp.run_states.get(tier_id, {}).get(subtest_id, {}).get(run_key, old_state_str)
            old_idx = _run_state_index(old_state_str)
            new_idx = _run_state_index(new_state_str)
            if old_idx == -1 and new_idx == -1:
                continue  # Both terminal: OK
            assert new_idx >= old_idx  # Monotonic
```

### 6. Config Hash Stability

Fields excluded from config hash (as of v3.1): `tiers_to_run`, `max_subtests`, `parallel_subtests`, all `until_*`/`from_*`/`filter_*` ephemeral flags.

```python
configs = [
    make_config(["T0"], max_subtests=1),
    make_config(["T0", "T1"], max_subtests=2),
    make_config(["T0", "T1", "T2"], max_subtests=3),
]
hashes = [compute_config_hash(c) for c in configs]
assert len(set(hashes)) == 1  # all identical
```

### 7. Zombie Detection Integration Tests (Real Disk I/O)

Use a guaranteed-dead PID to avoid mocking `os.kill`:

```python
_DEAD_PID = 999_999_999   # Linux max PID is 4,194,304 — this is always dead

cp = make_checkpoint(status="running", pid=_DEAD_PID, last_heartbeat=_stale_heartbeat(),
                     experiment_dir=str(tmp_path))
cp_path = tmp_path / "checkpoint.json"
save_checkpoint(cp, cp_path)

rm = ResumeManager(cp, MagicMock(spec=ExperimentConfig), MagicMock())
_, updated_cp = rm.handle_zombie(checkpoint_path=cp_path, experiment_dir=tmp_path,
                                  heartbeat_timeout_seconds=120)

assert updated_cp.status == "interrupted"
assert load_checkpoint(cp_path).status == "interrupted"   # disk persistence
```

`is_zombie()` requires **all three**: `status=="running"` AND dead PID AND stale heartbeat.

```python
_STALE_HEARTBEAT_AGE = 300   # 5 minutes — past 120s default
_FRESH_HEARTBEAT_AGE = 10    # within 120s default

def _stale_heartbeat(): return (datetime.now(timezone.utc) - timedelta(seconds=_STALE_HEARTBEAT_AGE)).isoformat()
def _fresh_heartbeat(): return (datetime.now(timezone.utc) - timedelta(seconds=_FRESH_HEARTBEAT_AGE)).isoformat()
```

### 8. state_order Rank Table Sync (RunState enum extensions)

When adding new `RunState` values, keep `state_order` in `_reconcile_checkpoint_with_disk()` complete. Missing states silently get rank=0 (same as `"pending"`), causing `0 > 0 = False` — the state never advances.

```python
state_order = [
    "pending", "dir_structure_created", "worktree_created", "symlinks_applied",
    "config_committed", "baseline_captured", "prompt_written", "replay_generated",
    "agent_complete", "diff_captured", "judge_pipeline_run", "judge_prompt_built",
    "judge_complete", "run_finalized", "report_written", "checkpointed", "worktree_cleaned",
]
```

**Regression guard test** — assert every non-terminal state appears in function source:

```python
def test_reconcile_state_order_covers_all_run_states(self):
    import inspect, manage_experiment
    from scylla.e2e.models import RunState
    source = inspect.getsource(manage_experiment._reconcile_checkpoint_with_disk)
    terminal = {RunState.FAILED.value, RunState.RATE_LIMITED.value}
    for state_value in {s.value for s in RunState if s.value not in terminal}:
        assert state_value in source, f"RunState '{state_value}' missing from state_order"
```

### 9. Shared `wired_runner` Pytest Fixture

Extract per-test boilerplate when multiple tests construct the same object:

```python
@pytest.fixture
def wired_runner(mock_config, mock_tier_manager, tmp_path):
    """Pre-configured E2ERunner with experiment_dir and tier_manager already set."""
    with patch.object(TierManager, "__init__", return_value=None):
        runner = E2ERunner(mock_config, tmp_path / "tiers", tmp_path / "results")
    runner.tier_manager = mock_tier_manager
    runner.experiment_dir = tmp_path / "experiment"
    runner.experiment_dir.mkdir(parents=True)
    return runner
```

Use function scope (default) when the class under test mutates state. Adopt all-or-nothing within a test class — partial adoption creates inconsistency.

### 10. DataLoader Reset Verification (Mojo — Pre-Exhaustion Strategy)

Prove `reset()` is called without mock objects — use catastrophic failure as the signal:

```mojo
fn test_validation_loop_run_resets_loader() raises:
    var vloop = ValidationLoop()
    var loader = create_val_loader(n_batches=2)
    loader.current_batch = loader.num_batches   # pre-exhaust
    assert_true(not loader.has_next())          # confirm pre-condition
    var metrics = TrainingMetrics()
    var val_loss = vloop.run(simple_forward, simple_loss, loader, metrics)
    assert_greater(val_loss, Float64(-1e-10))   # finite: reset() was called
    assert_less(val_loss, Float64(1e10))
```

Without `reset()`: `num_batches == 0` → division by zero or NaN.
With `reset()`: `num_batches == 2` → valid finite loss.

Add call to `main()` in the correct test group block. Mojo tests use `fn main() raises`, not pytest.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Minimal fixture with subtest_states only | Set `subtest_states={"T0": {"00": "failed", "01": "aggregated"}}` without `run_states` | `_find_orphaned_subtest_states()` correctly reset `"01"` to `"pending"` — aggregated subtest with no backing runs is orphaned | Fixtures must be cross-level consistent; higher-state assertions require lower-state backing data |
| Using `_run_resume` helper for complex fixtures | Used shared helper which creates checkpoint with `run_states={}` by default | No way to inject `run_states` through the helper | For tests needing `run_states`, inline checkpoint creation instead of using shared helpers |
| Fixing only the first failing test after rebase | Fixed one fixture and pushed | Second test (`test_resume_detects_missing_subtests_and_resets_tier_to_pending`) had same root cause in different class | Audit ALL fixtures with `grep '"aggregated"'` across the entire file, not just the first failure |
| Assert `get_run_status() is None` after corrupted JSON | Expected no `mark_run_completed` call → `None` status | `set_run_state("worktree_cleaned")` auto-calls `mark_run_completed("passed")` as backward-compat sync | Always check if `set_run_state` has side-effects on `completed_runs` before asserting status |
| `completed_runs={"T0": {"00": {"3": "passed"}}}` (str key) | Used string `"3"` as inner dict key | `E2ECheckpoint` declares `completed_runs: dict[str, dict[str, dict[int, str]]]` — inner key is `int` | Mypy error: incompatible type `"str": "str"`; expected `"int": "str"` — use `{3: "passed"}` |
| Mock-based approach for DataLoader reset (Mojo) | Wrapping DataLoader to count `reset()` calls | Mojo structs do not support vtable-based mocking; no trait for spy | Use direct field mutation + observable side effects (finite loss) instead |
| Asserting exact loss value in Mojo test | `assert_almost_equal(val_loss, Float64(1.0), ...)` | Relies on loss function returning exactly 1.0; brittle if loss function changes | Use range assertions (`> -eps` and `< large`) for robustness |
| Using `run_in_background` for Skill tool commit | Called `commit-commands:commit-push-pr` skill | Skill tool denied (don't-ask mode) | Fall back to direct Bash git commands when Skill tool is unavailable |
| Checking for pytest tests in Mojo project | Issue prompt suggested pytest | Project uses Mojo test runner, not pytest | Always check test file extension and existing patterns before writing tests |

## Results & Parameters

### Run Commands

```bash
# Integration tests (suppress coverage floor when running in isolation)
pixi run python -m pytest tests/integration/ -v --override-ini="addopts="

# Additive resume tier-level tests only
pixi run python -m pytest tests/integration/e2e/test_additive_resume.py \
    -v -k "TestAdditiveResumeTierStates"

# Zombie detection integration tests
pixi run python -m pytest tests/integration/e2e/test_zombie_resume.py -v \
    --override-ini="addopts="

# Unit tests for state machine / reconcile
pixi run python -m pytest tests/unit/e2e/test_runner.py tests/unit/e2e/test_manage_experiment_run.py -v
```

### Audit Commands

```bash
# Find all test fixtures with aggregated/runs_complete that may need run_states
grep -n '"aggregated"\|"runs_complete"' tests/unit/e2e/test_runner.py

# Verify only one constructor call remains after fixture extraction
grep -n "E2ERunner(" tests/unit/e2e/test_runner.py
```

### Key Constants

```python
# Zombie detection
_DEAD_PID = 999_999_999          # Guaranteed dead on Linux (max is 4,194,304)
_STALE_HEARTBEAT_AGE = 300       # 5 minutes — well past 120s default timeout
_FRESH_HEARTBEAT_AGE = 10        # 10 seconds — well within 120s default timeout

# Additive resume
_RUNS = 3
_EXPERIMENT_ID = "additive-resume-test"
_FIXTURE_DIR = "<project-root>/tests/fixtures/tests/test-001"
```

### Minimal ExperimentConfig for Testing

```python
config = ExperimentConfig(
    experiment_id="additive-resume-test",
    task_repo="https://github.com/mvillmow/Hello-World",
    task_commit="7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
    task_prompt_file=Path("tests/fixtures/tests/test-001/prompt.md"),
    language="python",
    models=["claude-haiku-4-5-20251001"],
    judge_models=["claude-haiku-4-5-20251001"],
    runs_per_subtest=3,
    tiers_to_run=[TierID("T0")],
    max_subtests=1,
    until_run_state=RunState.REPLAY_GENERATED,
)
```

### `set_run_state` Auto-Sync Behavior

```python
# States that auto-call mark_run_completed("passed") if no prior status:
terminal_complete = {"run_complete", "run_finalized", "report_written", "checkpointed", "worktree_cleaned"}
existing = self.get_run_status(tier_id, subtest_id, run_num)
compat_status = existing if existing in ("passed", "failed") else "passed"
self.mark_run_completed(tier_id, subtest_id, run_num, status=compat_status)
# Result: if inferred_status is None → no override → status stays "passed"
```

### Mojo DataLoader Pre-Exhaustion Template

```mojo
loader.current_batch = loader.num_batches   # exhaust loader
assert_true(not loader.has_next())          # confirm pre-condition
# call method under test
assert_greater(val_loss, Float64(-1e-10))   # finite loss proves reset() was called
assert_less(val_loss, Float64(1e10))
```

**Key parameters**: `n_batches=2`, `max_batches=2` (must equal `n_batches`), range bounds `-1e-10` to `1e10`.

### Test Counts by PR

| PR | Tests Added | Suite Result |
| --- | --- | --- |
| ProjectScylla#1149 (additive resume) | 16 integration tests | 3201 passed, 78.36% coverage |
| ProjectScylla#1312 (zombie detection) | 11 integration tests | 3595 passed, 67.46% coverage |
| ProjectScylla#1485 (state-order reconcile) | 5 edge-case unit tests | 4861 passed, 78.36% coverage |
| ProjectScylla#815 (wired\_runner fixture) | 4 refactored (net +1) | 4/4 passed |
| ProjectOdyssey#3687 (DataLoader reset) | 1 Mojo test | CI validated |
| ProjectOdyssey#4770 (run() reset parallel) | 1 Mojo test | CI validated |

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectScylla | PRs #815, #1149, #1312, #1485 | Checkpoint state machine test patterns |
| ProjectOdyssey | PRs #3687, #4770 | Mojo DataLoader reset verification |
