# Skill: Fix `--until` Resume Bug — Runs Past Target State Not Skipped

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-25 |
| Category | debugging |
| Objective | Fix crash when resuming with `--until` on runs already past the target state |
| Outcome | Success — 3172 tests pass, no regressions |
| Project | ProjectScylla |

## When to Use

Apply this pattern when:
- A state machine has an `--until TARGET_STATE` early-stop feature
- The state machine can be resumed from a checkpoint
- Runs may have progressed **past** the target state before resumption
- An equality check (`==`) is used to detect "already at the target" — this misses "already past it"

Symptoms of the bug:
- Crash with "X must be set before Y" during resume
- Context/data not restored from disk because the run was expected to be at an earlier state
- Only manifests on resume when runs are past the `--until` target, not on fresh runs

## Verified Workflow

### 1. Audit All `--until` Check Sites

Search for every place that checks `current_state == until_state` or equivalent:

```python
# BAD: misses runs already past the target
if current_run_state == self.config.until_run_state:
    continue  # skip

# BAD: in-loop break misses runs already past target
if until_state is not None and new_state == until_state:
    break
```

### 2. Add an Index Map for O(1) Ordering

At module load time, precompute the index of each state in the normal sequence:

```python
# In state_machine.py, after _RUN_STATE_SEQUENCE definition:
_RUN_STATE_INDEX: dict[RunState, int] = {
    state: idx for idx, state in enumerate(_RUN_STATE_SEQUENCE)
}

def is_at_or_past_state(current: RunState, target: RunState) -> bool:
    """Return True if current is at or past target in the run sequence.

    States not in the normal sequence (FAILED, RATE_LIMITED) return False.
    """
    cur_idx = _RUN_STATE_INDEX.get(current)
    tgt_idx = _RUN_STATE_INDEX.get(target)
    if cur_idx is None or tgt_idx is None:
        return False
    return cur_idx >= tgt_idx
```

**Key insight**: Using `.get()` returning `None` for non-sequence states (FAILED, RATE_LIMITED) naturally handles the "not in sequence = don't skip" semantic — no explicit special-casing needed.

### 3. Add Early-Return Guard in `advance_to_completion()`

Before the `while` loop, add:

```python
def advance_to_completion(self, tier_id, subtest_id, run_num, actions, until_state=None):
    # Early return if already at or past the --until target state
    if until_state is not None:
        current = self.get_state(tier_id, subtest_id, run_num)
        if is_at_or_past_state(current, until_state):
            logger.info(
                f"[{tier_id}/{subtest_id}/run_{run_num:02d}] "
                f"Already at or past --until target state: {until_state.value} "
                f"(current: {current.value})"
            )
            return current

    # ... existing while loop ...
```

This guard is critical: without it, a run at `diff_captured` with `until_state=replay_generated` enters the while loop, calls `advance()` from `diff_captured`, and crashes because context (agent_result, etc.) was never restored.

### 4. Fix the Pre-Loop Skip Check

```python
# Before (exact equality — misses past states):
if current_run_state == self.config.until_run_state:
    logger.debug(f"Skipping ... already at --until state: ...")
    continue

# After (ordering check — catches past states too):
from scylla.e2e.state_machine import is_at_or_past_state
if is_at_or_past_state(current_run_state, self.config.until_run_state):
    logger.debug(
        f"Skipping ... already at or past --until state: "
        f"{self.config.until_run_state.value} "
        f"(current: {current_run_state.value})"
    )
    continue
```

### 5. Write the Regression Test

Create an integration test that pre-seeds a checkpoint with a run **past** the target:

```python
def test_until_skips_run_already_past_target(self, tmp_path: Path) -> None:
    cp = make_checkpoint(
        run_states={"T0": {"00": {"1": RunState.DIFF_CAPTURED.value}}},
    )
    cp_path = tmp_path / "checkpoint.json"
    save_checkpoint(cp, cp_path)

    sm = _build_run_sm(cp, cp_path)
    actions_called: list[RunState] = []

    def tracking_action(state: RunState) -> Callable[[], None]:
        def _action() -> None:
            actions_called.append(state)
        return _action

    actions = {s: tracking_action(s) for s in RunState if not is_terminal_state(s)}

    # Resume with --until replay_generated on a run already at diff_captured (past the target)
    final = sm.advance_to_completion(
        "T0", "00", 1, actions, until_state=RunState.REPLAY_GENERATED
    )

    assert final == RunState.DIFF_CAPTURED  # unchanged
    assert actions_called == []              # nothing ran
```

## Failed Attempts

None — the plan was clear and implementation went directly to the correct solution.

However, two pre-commit issues were encountered:

### Pre-commit: E501 Line Too Long in f-string

```python
# FAILED (line > 100 chars):
logger.debug(
    f"Skipping run ... "
    f"— already at or past --until state: {self.config.until_run_state.value} "
    f"(current: {current_run_state.value})"
)

# FIXED (split f-string):
logger.debug(
    f"Skipping run ... "
    f"— already at or past --until state: "
    f"{self.config.until_run_state.value} "
    f"(current: {current_run_state.value})"
)
```

### Pre-commit: Missing Return Type on Inner Helper

```python
# FAILED (mypy error: Function is missing a return type annotation):
def tracking_action(state: RunState):
    def _action() -> None:
        actions_called.append(state)
    return _action

# FIXED:
def tracking_action(state: RunState) -> Callable[[], None]:
    def _action() -> None:
        actions_called.append(state)
    return _action
```

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `scylla/e2e/state_machine.py` | Add `_RUN_STATE_INDEX`, `is_at_or_past_state()`, early-return guard in `advance_to_completion()` |
| `scylla/e2e/subtest_executor.py` | Change `==` to `is_at_or_past_state()` in pre-loop skip check |
| `tests/unit/e2e/test_state_machine.py` | 6 tests for `is_at_or_past_state` + 1 for early-return guard |
| `tests/integration/e2e/test_until_from_stepping.py` | 1 regression test for skip-past-target behavior |

### Test Results

- 3172 tests pass
- Coverage: 78.29% (threshold: 75%)
- Pre-commit: all hooks pass

### Key Design Decisions

1. **Why `_RUN_STATE_INDEX` at module load?** Avoids repeated O(n) `list.index()` calls in hot paths. The sequence is static so precomputing is safe.

2. **Why does `is_at_or_past_state` return `False` for FAILED/RATE_LIMITED?** These are terminal states outside the normal sequence. A run that is FAILED or RATE_LIMITED should not be skipped by the `--until` logic — it is already terminal and handled separately by `is_complete()`.

3. **Why add the early-return guard AND fix the pre-loop check?** Defense in depth. The pre-loop check in `subtest_executor.py` is the first line of defense (avoids even building `RunContext`). The early-return in `advance_to_completion()` is the second (handles any caller that bypasses the pre-loop check).
