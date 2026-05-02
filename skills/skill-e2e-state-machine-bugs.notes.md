# Raw Notes: E2E State Machine Bugs

## Session Context

- **Date**: 2026-02-24
- **Project**: ProjectScylla
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1102
- **Branch**: `fix-until-flag-and-signal-handlers`

## The Confusion About Semantics

This session had significant back-and-forth about "inclusive" vs "exclusive" semantics.
The confusion arose because the fix was described in the original plan as "move the check before advance()"
which produces exclusive semantics, but the user wanted inclusive semantics.

The correct fix turned out to be a third option: check `new_state = self.advance()` (post-advance).

**Semantic definitions in this codebase**:
- **Exclusive**: Stop when you see `until_state` as current; don't execute its action. Checkpoint = `until_state`.
- **Inclusive**: Execute the action that produces `until_state`; stop immediately after. Checkpoint = `until_state`.
- **Original buggy code**: Check `current == until_state` after advance — fires one iteration too late.

The key insight is that inclusive and exclusive both leave the checkpoint at `until_state`, but
inclusive means the action that transitioned INTO that state already ran, while exclusive means it hasn't.

## State Naming Convention (Critical)

The state sequence from `scylla/e2e/models.py`:
```
PENDING → DIR_STRUCTURE_CREATED → WORKTREE_CREATED → SYMLINKS_APPLIED
→ CONFIG_COMMITTED → BASELINE_CAPTURED → PROMPT_WRITTEN → REPLAY_GENERATED
→ AGENT_COMPLETE → DIFF_CAPTURED → JUDGE_PIPELINE_RUN → JUDGE_PROMPT_BUILT
→ JUDGE_COMPLETE → RUN_FINALIZED → REPORT_WRITTEN → CHECKPOINTED → WORKTREE_CLEANED
```

The action registered for state X runs WHILE IN state X to produce state X+1.
From `scylla/e2e/stages.py`:
```
PROMPT_WRITTEN       -> stage_generate_replay()   # produces REPLAY_GENERATED
REPLAY_GENERATED     -> stage_execute_agent()     # produces AGENT_COMPLETE  ← runs agent!
AGENT_COMPLETE       -> stage_capture_diff()      # produces DIFF_CAPTURED
```

## Files Changed

### `scylla/e2e/state_machine.py`
```python
# Before:
current = self.get_state(tier_id, subtest_id, run_num)
self.advance(tier_id, subtest_id, run_num, actions)
if until_state is not None and current == until_state:
    break

# After:
new_state = self.advance(tier_id, subtest_id, run_num, actions)
if until_state is not None and new_state == until_state:
    break
```

Same pattern in `experiment_state_machine.py`, `tier_state_machine.py`, `subtest_state_machine.py`.

### `scripts/manage_experiment.py`
```python
# Before (both call sites):
from scylla.e2e.runner import run_experiment
with terminal_guard():

# After (both call sites):
from scylla.e2e.runner import request_shutdown, run_experiment
with terminal_guard(request_shutdown):
```

## Test Count

- 154 unit tests pass across 4 test files
- Pre-commit hooks: ruff-format reformatted 1 file on first commit attempt; clean on second
