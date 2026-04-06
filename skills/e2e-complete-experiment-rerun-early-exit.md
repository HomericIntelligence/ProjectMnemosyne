---
name: e2e-complete-experiment-rerun-early-exit
description: "Early-exit when re-running an already-complete E2E experiment to avoid expensive rehydrate (rglob scan of hundreds of run_result.json files) that can hang or OOM on low-memory systems"
category: debugging
date: 2026-04-05
version: 1.0.0
user-invocable: false
---
# E2E Complete Experiment Rerun Early Exit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Project** | ProjectScylla |
| **Objective** | Prevent expensive filesystem rehydrate when re-running an already-complete experiment |
| **Outcome** | Added 6-line early-exit guard in runner.py; 4903 tests passing |
| **Impact** | High - eliminates 3.5 min rehydrate per experiment; prevents OOM on low-memory systems (3130MB) |
| **PR** | ProjectScylla PR #1751 |
| **Verification** | verified-local |

## When to Use This Skill

Use this skill when:

1. **Re-running a completed experiment** takes minutes instead of returning immediately
2. **Runner hangs or OOMs** on low-memory systems when experiment_state is already COMPLETE
3. **`rglob("run_result.json")` scans hundreds of files** causing slow rehydrate on re-run
4. **State machine returns no transitions** but code falls through to expensive IO path
5. **Debugging "fall-through" bugs** in the experiment runner where terminal states are not handled

**Key Indicator**: Experiment checkpoint shows `experiment_state: complete` but `manage_experiment.py run` still takes minutes and loads every `run_result.json` from disk.

## Root Cause

In `src/scylla/e2e/runner.py:run()`, when `experiment_state` is already `complete` and the state machine produces no transitions:

1. State machine correctly does nothing (no work needed)
2. `_last_experiment_result` remains `None` (no action populated it)
3. Code falls through to `load_experiment_tier_results()` which calls `scan_run_results()`
4. `scan_run_results()` uses `rglob("run_result.json")` over 360+ files
5. Each file is opened, parsed, and loaded into memory
6. On test-003 with 3130MB RAM, this never completed

## Verified Workflow

### 1. Diagnose the Problem

```bash
# Check if experiment is already complete
python3 -c "
import json
cp = json.load(open('<experiment>/checkpoint.json'))
print('experiment_state:', cp.get('experiment_state'))
print('tier_states:', cp.get('tier_states', {}))
"

# Count run_result.json files that would be scanned
find <experiment>/ -name "run_result.json" | wc -l
# If >100 and experiment_state=complete, this is the bug
```

### 2. The Fix Pattern

The fix adds an early-exit check after the state machine returns, before the expensive rehydrate path.

**Key insight**: `_current_exp_state` is captured from the checkpoint BEFORE state machine entry (line 657-660 in runner.py). This existing variable is the perfect discriminator.

```python
# After state machine completes, before rehydrate path:
if (
    _current_exp_state == ExperimentState.COMPLETE
    and _last_experiment_result is None
):
    # Already complete, no new work done - skip expensive rehydrate
    return _aggregate_results(tier_results, start_time)
```

**Why this works**:
- `_current_exp_state` was captured from checkpoint before any transitions
- `_last_experiment_result is None` confirms no action populated new results
- `_aggregate_results(tier_results, start_time)` returns a truthy `ExperimentResult`
- The caller (`manage_experiment.py`) only checks `if results:` for truthiness

### 3. Write Tests

```python
def test_run_already_complete_experiment_returns_immediately(
    wired_runner, tmp_path
):
    """Re-running a COMPLETE experiment must NOT trigger rehydrate."""
    runner = wired_runner
    # Set experiment state to COMPLETE in checkpoint
    runner._current_exp_state = ExperimentState.COMPLETE
    runner._last_experiment_result = None

    result = runner.run()

    assert result is not None  # Returns truthy ExperimentResult
    # Verify load_experiment_tier_results was NOT called
```

### 4. Verify

```bash
pixi run python -m pytest tests/unit/e2e/test_runner.py -v -k "already_complete"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct early-exit approach worked | N/A | The `_current_exp_state` variable was already available |

## Traps and Pitfalls

### 1. `_TERMINAL_STATES` is Deceptively Narrow

The `_TERMINAL_STATES` set contains only 3 states: `worktree_cleaned`, `failed`, `rate_limited`. Notably, `promoted_to_completed` is NOT in `_TERMINAL_STATES` but IS a valid stage endpoint. Don't rely on `_TERMINAL_STATES` to detect "done" experiments.

### 2. `load_experiment_tier_results` is O(N) and Memory-Hungry

`load_experiment_tier_results` -> `scan_run_results` -> `rglob("run_result.json")` loads every result file into memory. With 360+ files, this is:
- 3.5 minutes on a normal system
- OOM/hang on systems with < 4GB RAM

### 3. Recurring Pattern: Fall-Through on Complete State

This is the same class of bug fixed in commit 21f09b1 (`manage_experiment.py` not handling `promoted_to_completed` on Stage 3 resume). When adding new terminal-like states or completion paths, audit ALL code paths that check experiment completion:
- `runner.py:run()` - main run loop
- `manage_experiment.py` - experiment management
- `resume_manager.py` - resume logic

### 4. Caller Only Checks Truthiness

`manage_experiment.py` checks `if results:` not `if results.has_data()`. An empty `ExperimentResult` from `_aggregate_results({}, start_time)` is truthy and works correctly.

## Code Locations (ProjectScylla)

| File | Change |
|------|--------|
| `src/scylla/e2e/runner.py` | 6-line early-exit guard after state machine |
| `tests/unit/e2e/test_runner.py` | 62 lines - test for early-exit behavior |

## Related Skills

- `debugging/skill-resume-checkpoint-bugs` - Related checkpoint/resume bugs in the same codebase
- `evaluation/verify-e2e-experiment-completion` - Verifying experiment completion state
- `optimization/e2e-resource-exhaustion` - Resource exhaustion during E2E runs
- `evaluation/skill-preserve-workspaces-on-e2e-experiment-re-runs` - Re-run behavior

## Tags

`debugging` `early-exit` `performance` `oom` `rehydrate` `rglob` `experiment-state` `state-machine` `fall-through` `e2e-runner` `checkpoint`
