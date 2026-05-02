---
name: skill-e2e-state-machine-bugs
description: Fix --until off-by-one in advance_to_completion() loops and disconnected terminal signal handlers in manage_experiment.py
category: debugging
date: 2026-02-24
version: 1.0.0
user-invocable: false
---
# Skill: E2E State Machine Bugs

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-02-24 |
| **Objective** | Fix `--until` flag executing one extra transition and Ctrl+C having no effect |
| **Outcome** | ✅ Both bugs fixed; 154 unit tests pass; PR #1102 merged |
| **Files Modified** | `scylla/e2e/state_machine.py`, `experiment_state_machine.py`, `tier_state_machine.py`, `subtest_state_machine.py`, `scripts/manage_experiment.py` |
| **Root Cause** | `advance_to_completion()` checked pre-advance state; `terminal_guard()` called with no args |

## When to Use This Skill

Use when:
- `--until <state>` runs one extra transition beyond the target state (agent executes when it shouldn't)
- Ctrl+C / SIGTERM does nothing during a long-running experiment
- Graceful shutdown log message never appears despite signal handlers existing in the codebase
- `terminal_guard()` is called but signals appear unhandled
- A state machine loop checks state before calling `advance()` then breaks — this pattern is always off-by-one

**Trigger signals**:
- `--until replay_generated` still runs the agent
- `is_shutdown_requested()` always returns `False`
- `terminal_guard()` exists but `install_signal_handlers()` is never called

## Critical Concept: State Naming Convention

In this codebase, **state names represent what has just been completed**, not what is about to happen.
The action registered FOR a state runs WHILE IN that state to produce the NEXT state.

```
State             | Meaning (what's done)          | Action when IN this state
------------------|-------------------------------|---------------------------
PROMPT_WRITTEN    | task_prompt.md written         | stage_generate_replay()
REPLAY_GENERATED  | replay script generated        | stage_execute_agent()  ← runs agent!
AGENT_COMPLETE    | agent executed, outputs saved  | stage_capture_diff()
```

This means `--until replay_generated` should stop AFTER `stage_generate_replay()` runs
(transitioning INTO `REPLAY_GENERATED`) but BEFORE `stage_execute_agent()` runs.

## Bug 1: `--until` Off-By-One

### Pattern (all 4 state machines)

```python
# BUGGY — checks pre-advance state:
while not self.is_complete(...):
    current = self.get_state(...)   # captures state BEFORE advance
    self.advance(...)               # runs action, transitions to new state
    if current == until_state:      # fires too late — action already ran
        break

# CORRECT — checks post-advance state:
while not self.is_complete(...):
    new_state = self.advance(...)   # runs action, transitions to new state
    if new_state == until_state:    # fires immediately after reaching target
        break
```

### Semantics clarification

The `--until` flag has **inclusive** semantics:
- The action that transitions INTO `until_state` **IS** executed
- No further transitions run
- Checkpoint is left at `until_state` for future resume

### Files affected (same pattern in all 4)

| File | Method |
| ------ | -------- |
| `scylla/e2e/state_machine.py` | `StateMachine.advance_to_completion()` |
| `scylla/e2e/experiment_state_machine.py` | `ExperimentStateMachine.advance_to_completion()` |
| `scylla/e2e/tier_state_machine.py` | `TierStateMachine.advance_to_completion()` |
| `scylla/e2e/subtest_state_machine.py` | `SubtestStateMachine.advance_to_completion()` |

## Bug 2: Disconnected Signal Handlers

### Root cause

`terminal_guard(shutdown_fn=None)` only installs signal handlers when `shutdown_fn is not None`.
Both call sites in `manage_experiment.py` called it with no arguments:

```python
# BUGGY — shutdown_fn defaults to None, no signal handlers installed:
with terminal_guard():
    results = run_experiment(...)

# CORRECT — pass the shutdown function:
from scylla.e2e.runner import request_shutdown
with terminal_guard(request_shutdown):
    results = run_experiment(...)
```

Both call sites must be fixed: batch mode (`_run_batch`) and single-test mode (`cmd_run`).

## Verified Workflow

1. Grep for `advance_to_completion` loops — look for pattern `current = self.get_state()` followed by `self.advance()` followed by `if current == until_state`
2. Replace with `new_state = self.advance()` and `if new_state == until_state`
3. Update docstrings: "inclusive — the action that transitions INTO until_state IS executed"
4. Grep for `terminal_guard()` with no arguments
5. Add `from <package>.runner import request_shutdown` to the local import block
6. Change `terminal_guard()` → `terminal_guard(request_shutdown)` at each call site
7. Update tests: `until_state=X` stops with checkpoint at `X`, action that PRODUCED `X` ran, action registered for `X` did NOT run

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Test Pattern for `until_state`

```python
# Test inclusive semantics correctly:
def test_stops_at_until_state(self, sm):
    actions_called = []
    def make_action(state):
        def action(): actions_called.append(state)
        return action

    actions = {s: make_action(s) for s in RunState if not is_terminal_state(s)}
    final = sm.advance_to_completion("T0", "sub", 1, actions,
                                      until_state=RunState.AGENT_COMPLETE)

    assert final == RunState.AGENT_COMPLETE          # stopped AT target
    assert RunState.REPLAY_GENERATED in actions_called  # action that PRODUCED target ran
    assert RunState.AGENT_COMPLETE not in actions_called  # action FOR target did NOT run
    assert RunState.DIFF_CAPTURED not in actions_called   # nothing after target ran
```

Key insight: `REPLAY_GENERATED` action (not `AGENT_COMPLETE` action) is what produces
`AGENT_COMPLETE` state. Check the action one step BEFORE the target state, not the target itself.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1102 | [notes.md](../../references/notes.md) |
