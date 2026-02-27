# Skill: Integration Tests for Additive Resume Behavior

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-27 |
| Project | ProjectScylla |
| Objective | Add integration tests validating additive resume across sequential --tiers/--max-subtests/--until invocations |
| Outcome | Success — 16/16 tests pass, full suite 3201 passed, 78.36% coverage |
| Issue | HomericIntelligence/ProjectScylla#1111 |
| PR | HomericIntelligence/ProjectScylla#1149 |

## When to Use

Use this skill when:
- Adding integration tests for stateful/resumable experiment behavior
- Testing checkpoint state machine progression across multiple invocations
- Validating additive/non-destructive behavior (new tiers/subtests don't reset existing ones)
- Testing that ephemeral flags don't affect persistent state (config hash stability)

## Key Architectural Insight: State Machine Layers

ProjectScylla has a 4-level state machine hierarchy:
- **StateMachine** — run-level (RunState: PENDING → WORKTREE_CLEANED)
- **SubtestStateMachine** — subtest-level (SubtestState: PENDING → AGGREGATED)
- **TierStateMachine** — tier-level (TierState: PENDING → COMPLETE)
- **ExperimentStateMachine** — experiment-level (ExperimentState: INITIALIZING → COMPLETE)

**Important**: Each layer independently populates different checkpoint fields:
- `run_states` ← populated by `StateMachine`
- `subtest_states` ← populated by `SubtestStateMachine`
- `tier_states` ← populated by `TierStateMachine` ONLY
- If you only run `SubtestStateMachine`, `tier_states` stays empty (implicitly "pending")

## Verified Workflow

### Test Architecture Pattern

Tests at the state machine level (not `E2ERunner.run()`) — no real API calls, git ops, or subprocesses:

```python
from scylla.e2e.state_machine import StateMachine
from scylla.e2e.subtest_state_machine import SubtestStateMachine, UntilHaltError
from scylla.e2e.tier_state_machine import TierStateMachine

# Simulate runs halted at a specific state (mimics --until flag)
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

### Config Hash Stability Verification

```python
from scylla.e2e.checkpoint import compute_config_hash

# All these produce the same hash:
configs = [
    make_config(["T0"], max_subtests=1, until_run_state=RunState.REPLAY_GENERATED),
    make_config(["T0", "T1"], max_subtests=2, until_run_state=RunState.REPLAY_GENERATED),
    make_config(["T0", "T1", "T2"], max_subtests=3),
    make_config(["T0", "T1", "T2", "T3"], max_subtests=1),
]
hashes = [compute_config_hash(c) for c in configs]
assert len(set(hashes)) == 1  # All identical
```

Fields excluded from config hash (as of v3.1):
- `tiers_to_run` — additive across resumes
- `max_subtests` — development/testing only
- `parallel_subtests` — parallelization setting only
- All `until_*`, `from_*`, `filter_*` ephemeral flags

### Monotonic State Advancement Check

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

## Failed Attempts

### 1. `assert "T1" in cp.tier_states` — Wrong assertion target

**Problem**: Asserting `tier_states` contains a new tier after `SubtestStateMachine` only.

**Root cause**: `tier_states` is only populated when `TierStateMachine.advance_to_completion()` runs. SubtestStateMachine only updates `subtest_states` and (via StateMachine) `run_states`.

**Fix**: Assert on `run_states` instead:
```python
# WRONG:
assert "T1" in cp_after.tier_states

# CORRECT:
assert "T1" in cp_after.run_states, "T1 runs not found in checkpoint"
```

### 2. Mypy error: `dict[SubtestState, object]` for mixed MagicMock + Callable dict

**Problem**: Mixing `MagicMock()` with regular callables in a dict causes mypy to widen the value type to `object`.

**Fix**: Use `cast()` to explicitly type the dict:
```python
from typing import cast
from collections.abc import Callable
from unittest.mock import MagicMock

subtest_actions: dict[SubtestState, Callable[[], None]] = cast(
    dict[SubtestState, Callable[[], None]],
    {
        SubtestState.PENDING: my_callable,
        SubtestState.RUNS_IN_PROGRESS: MagicMock(),
        SubtestState.RUNS_COMPLETE: MagicMock(),
    },
)
```

### 3. Mypy variable name shadowing across for-loops

**Problem**: Reusing variable names (`tier_id`, `subtests`, `state`) across multiple for-loops in the same function scope causes mypy to infer conflicting types.

**Root cause**: In the monotonic check, `subtests` is `dict[str, dict[str, str]]` (from `run_states`). Then in the no-failed check, another loop uses `subtests` bound to `dict[str, str]` (from `subtest_states`) — mypy sees conflicting type assignments.

**Fix**: Use unique variable names for each for-loop scope:
```python
# Monotonic check (run_states iteration):
for tier_id, subtests in previous_cp.run_states.items():  # subtests: dict[str, dict[str, str]]
    ...

# No-failed check (subtest_states iteration) — use different names:
for t_id, sub_map in cp.subtest_states.items():  # sub_map: dict[str, str]
    for sub_id, sub_state in sub_map.items():
        assert sub_state != "failed"
```

## Results & Parameters

### Test counts
- 4 TestConfigHashStability tests
- 4 TestAdditiveResume tests (4-stage progression)
- 8 TestAdditiveResumeInvariants tests (parametrized + fine-grained)
- Total: **16 integration tests**

### Key constants
```python
_RUNS = 3        # runs_per_subtest (constant across all stages)
_EXPERIMENT_ID = "additive-resume-test"
_FIXTURE_DIR = Path("tests/fixtures/tests/test-001")
```

### Minimal ExperimentConfig for testing
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

### pytestmark
```python
pytestmark = pytest.mark.integration
# Run with: pixi run python -m pytest tests/integration/ -v -m integration
```
