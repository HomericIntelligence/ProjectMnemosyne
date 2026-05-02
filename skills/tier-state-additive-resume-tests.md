---
name: tier-state-additive-resume-tests
description: "Skill: TierStateMachine-Level Additive Resume Tests"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: TierStateMachine-Level Additive Resume Tests

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-03 |
| Project | ProjectScylla |
| Objective | Add TierStateMachine-level tests verifying tier_states is additive across multi-invocation resumes |
| Outcome | Success — 5/5 new tests pass, full suite 3804 passed |
| Issue | HomericIntelligence/ProjectScylla#1153 |
| PR | HomericIntelligence/ProjectScylla#1338 |

## When to Use

Use this skill when:
- Adding tests that verify `tier_states` population via `TierStateMachine`
- Verifying that completed tier states are preserved (not downgraded) when new tiers are added
- Testing TierStateMachine's `advance_to_completion()` with `until_state` parameter
- Extending the `TestAdditiveResume` / `TestAdditiveResumeTierStates` class pattern

**Precursor skill**: See `additive-resume-integration-tests` for run/subtest-level additive resume
testing patterns (SubtestStateMachine, StateMachine layers).

## Key Architectural Insight: tier_states is TierStateMachine-only

The 4-level state machine hierarchy populates different checkpoint fields independently:

| State Machine | Checkpoint field populated |
| --- | --- |
| `StateMachine` | `run_states[tier_id][subtest_id][run_num]` |
| `SubtestStateMachine` | `subtest_states[tier_id][subtest_id]` |
| **`TierStateMachine`** | **`tier_states[tier_id]`** |
| `ExperimentStateMachine` | `experiment_state` |

**Critical**: Running only `SubtestStateMachine` does NOT populate `tier_states`. A tier is
implicitly `"pending"` if it has no entry in `tier_states`, regardless of whether subtests/runs
have completed. `tier_states` entries only appear after `TierStateMachine.advance()` is called.

## Verified Workflow

### Helper: Drive a tier to full COMPLETE state via TierStateMachine

```python
from scylla.e2e.tier_state_machine import TierStateMachine

def _simulate_tier_to_complete(
    cp: E2ECheckpoint,
    cp_path: Path,
    tier_id: str,
    subtest_ids: list[str],
    run_count: int,
) -> None:
    """Run all subtests to WORKTREE_CLEANED, then advance TierStateMachine to COMPLETE."""
    _simulate_tier_subtests_full(cp, cp_path, tier_id, subtest_ids, run_count)

    tsm = TierStateMachine(checkpoint=cp, checkpoint_path=cp_path)
    tier_actions = make_noop_tier_actions()
    tsm.advance_to_completion(tier_id, tier_actions)
```

### Helper: make_noop_tier_actions

```python
from scylla.e2e.models import TierState
from unittest.mock import MagicMock

def make_noop_tier_actions() -> dict[TierState, Callable[[], None]]:
    return {
        TierState.PENDING: MagicMock(),
        TierState.CONFIG_LOADED: MagicMock(),
        TierState.SUBTESTS_RUNNING: MagicMock(),
        TierState.SUBTESTS_COMPLETE: MagicMock(),
        TierState.BEST_SELECTED: MagicMock(),
        TierState.REPORTS_GENERATED: MagicMock(),
    }
```

### Pattern: Assert tier_states after additive resume

```python
# After T0 reaches COMPLETE
_simulate_tier_to_complete(cp, cp_path, "T0", ["00"], runs=3)
cp = load_checkpoint(cp_path)
assert cp.tier_states.get("T0") == TierState.COMPLETE.value

# Load fresh from disk, add T1 partial runs (no TierStateMachine advance)
cp = load_checkpoint(cp_path)
_simulate_tier_subtests_at_state(cp, cp_path, "T1", ["00"], runs=3, RunState.REPLAY_GENERATED)
cp_after = load_checkpoint(cp_path)

# T0 must remain "complete" — never downgraded by adding T1
assert cp_after.tier_states.get("T0") == TierState.COMPLETE.value
# T1 absent from tier_states (TierStateMachine not advanced for T1)
assert "T1" not in cp_after.tier_states
```

### Pattern: Tier halted mid-way via until_state is preserved

```python
# Advance T0 only to SUBTESTS_RUNNING (not COMPLETE)
tsm = TierStateMachine(checkpoint=cp, checkpoint_path=cp_path)
tsm.advance_to_completion(
    "T0",
    make_noop_tier_actions(),
    until_state=TierState.SUBTESTS_RUNNING,
)
cp = load_checkpoint(cp_path)
assert cp.tier_states.get("T0") == TierState.SUBTESTS_RUNNING.value

# After adding T1 partial runs, T0 must not revert to "pending"
cp = load_checkpoint(cp_path)
_simulate_tier_subtests_at_state(cp, cp_path, "T1", ["00"], 3, RunState.REPLAY_GENERATED)
cp_after = load_checkpoint(cp_path)
assert cp_after.tier_states.get("T0") == TierState.SUBTESTS_RUNNING.value  # preserved
```

### Pattern: Structural guarantee — only explicitly run tiers in tier_states

```python
_simulate_tier_to_complete(cp, cp_path, "T0", ["00"], 3)
cp = load_checkpoint(cp_path)

assert "T0" in cp.tier_states
assert cp.tier_states["T0"] == TierState.COMPLETE.value
assert len(cp.tier_states) == 1  # No phantom entries for T1, T2, etc.
```

### validate_checkpoint_states — verify tier_states inline

```python
from tests.integration.e2e.conftest import validate_checkpoint_states

validate_checkpoint_states(
    cp_path,
    expected_tier_states={"T0": "complete", "T1": "complete"},
    no_failed_states=True,
)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test class added

`TestAdditiveResumeTierStates` in `tests/integration/e2e/test_additive_resume.py`:

| Test | Scenario |
| ------ | --------- |
| `test_t0_complete_then_add_t1_preserves_t0_tier_state` | T0→COMPLETE, then T1 partial |
| `test_two_tiers_complete_then_add_third_preserves_both` | T0+T1→COMPLETE, then T2 partial |
| `test_complete_tier_tier_state_additive_across_three_invocations` | 3 sequential invocations |
| `test_until_tier_state_partial_completion_preserved` | T0 halted at SUBTESTS_RUNNING |
| `test_tier_states_dict_structure_after_full_completion` | Structural guarantee |

### TierState sequence (from tier_state_machine.py)

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

### Test runner command

```bash
pixi run python -m pytest tests/integration/e2e/test_additive_resume.py \
    -v -k "TestAdditiveResumeTierStates"
```
