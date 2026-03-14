---
name: always-retry-infra-failures
description: "Fix retry logic bugs where a flag-gated retry conflates infra crashes with bad-grade results, discarding valid judge results. Use when: removing a retry flag to make behavior unconditional, fixing state machine reset logic that incorrectly resets completed runs, or debugging checkpoint semantics with multiple terminal state meanings."
category: debugging
date: 2026-03-14
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `--retry-errors` flag incorrectly retried bad-grade runs (valid results) AND gated all retry behavior behind a flag |
| **Root cause** | Three bugs: (1) second pass over `completed_runs` used `"failed"` ambiguously, (2) `worktree_cleaned` second-pass discarded valid judge results, (3) all retry logic was flag-gated |
| **Fix** | Remove flag; make retry unconditional; distinguish `run_states="failed"` (infra crash) from `completed_runs="failed"` (bad grade) |
| **Language** | Python 3.10+ |
| **Files changed** | `scripts/manage_experiment.py`, `tests/unit/e2e/test_manage_experiment_run.py`, `tests/unit/e2e/test_manage_experiment_cli.py` |

## When to Use

Apply this skill when:

1. A feature flag controls retry/resume behavior that should always run
2. Reset logic is incorrectly resetting completed runs (bad scores, not crashes)
3. A state machine has terminal states with multiple meanings that are being conflated
4. Test failures show valid results being overwritten on retry

## Verified Workflow

### Quick Reference

```
Bug 1: _checkpoint_has_retryable_runs() second pass
  completed_runs["failed"] = bad grade (NOT a crash) → delete second pass

Bug 2: _reset_non_completed_runs() worktree_cleaned block
  run_states="worktree_cleaned" + completed_runs="failed" = valid result → never reset
  Fix: replace block with `continue`

Bug 3: Retry gated behind --retry-errors flag
  Fix: remove flag, make reconcile+reset run unconditionally

The invariant:
  run_states="FAILED"          → infra crash → always reset to pending
  run_states="WORKTREE_CLEANED" → completed (any grade) → never reset
```

### Step 1: Identify the state model invariants

Before fixing, read the full state machine to establish invariants:

- `run_states` = pipeline execution state (e.g. `FAILED`, `RATE_LIMITED`, `WORKTREE_CLEANED`)
- `completed_runs` = backward-compat field set by finalization stage (`"passed"`, `"failed"`, `"agent_complete"`)
- **Critical invariant**: `run_states="FAILED"` is ALWAYS an infra crash (unhandled exception)
- **Critical invariant**: `run_states="WORKTREE_CLEANED"` + `completed_runs="failed"` is ALWAYS a bad judge grade, NEVER an infra crash

### Step 2: Fix `_checkpoint_has_retryable_runs()`

Delete the second pass over `completed_runs` — `"failed"` there means bad grade, not retryable:

```python
# BEFORE (buggy): falsely triggers retry for bad-grade runs
def _checkpoint_has_retryable_runs(checkpoint_path):
    ...
    for subtests in data.get("run_states", {}).values():
        for runs in subtests.values():
            for state in runs.values():
                if state != "worktree_cleaned":
                    return True
    # DELETE THIS ENTIRE BLOCK:
    for subtests in data.get("completed_runs", {}).values():
        for runs in subtests.values():
            for status in runs.values():
                if status == "failed":   # "failed" here = bad grade, NOT crash
                    return True
    return False

# AFTER (correct): only run_states non-worktree_cleaned = retryable
def _checkpoint_has_retryable_runs(checkpoint_path):
    """Return True if checkpoint contains any non-completed runs (infra failures or
    mid-pipeline crashes). Runs in worktree_cleaned state (even with bad grades) are
    NOT considered retryable."""
    ...
    for subtests in data.get("run_states", {}).values():
        for runs in subtests.values():
            for state in runs.values():
                if state != "worktree_cleaned":
                    return True
    return False
```

### Step 3: Fix `_reset_non_completed_runs()`

Delete the `worktree_cleaned` second-pass block that discards valid results:

```python
# BEFORE (buggy): resets bad-grade runs to pending, erasing valid results
for run_num_str, state in list(runs.items()):
    if state == "worktree_cleaned":
        run_status = checkpoint.get_run_status(tier_id, subtest_id, int(run_num_str))
        if run_status == "failed":      # "failed" here = bad grade
            runs[run_num_str] = "pending"   # BUG: discards valid judge result
            checkpoint.unmark_run_completed(...)
            ...
        continue
    ...

# AFTER (correct): simple skip — completed runs (any grade) are never reset
for run_num_str, state in list(runs.items()):
    if state == "worktree_cleaned":
        continue  # Completed run (passed or bad grade) — never reset
    ...
```

### Step 4: Make retry unconditional (remove the flag)

Remove the `--retry-errors` argument from the parser and all `if args.retry_errors:` guards:

```python
# BEFORE: gated behind flag
parser.add_argument("--retry-errors", action="store_true", ...)

# In run_one_test():
if args.retry_errors:
    _cp_path = _find_checkpoint_path(...)
    if _cp_path is not None:
        ...reconcile...
        ...reset...

# AFTER: unconditional
# (no --retry-errors argument)

# In run_one_test():
_cp_path = _find_checkpoint_path(...)
if _cp_path is not None:
    ...reconcile...
    ...reset...
```

Apply the same pattern to:
- Batch skip logic (`for test_id, r in last_by_test.items()`)
- Single-test mode reconcile+reset block

### Step 5: Update tests

Update tests in three files:

1. `test_manage_experiment_cli.py`: Remove `test_run_accepts_retry_errors` test and `assert not args.retry_errors` from defaults test
2. `test_manage_experiment_run.py`: Rename classes (`TestRetryErrorsInBatch` → `TestRetryInfraFailuresInBatch`), remove `--retry-errors` from all `parse_args` calls, fix the bad-grade retryable test (was `True`, now `False`), fix the bad-grade reset test (was expecting reset, now not)

Key new tests to add:
```python
def test_checkpoint_has_retryable_runs_false_for_worktree_cleaned_bad_grade():
    # run_states=worktree_cleaned + completed_runs=failed → False
    assert _checkpoint_has_retryable_runs(cp) is False

def test_reset_does_not_touch_bad_grade_worktree_cleaned():
    # reset_count=0, state stays worktree_cleaned, grade stays "failed"
    reset_count = _reset_non_completed_runs(checkpoint)
    assert reset_count == 0
    assert checkpoint.run_states["T0"]["00"]["1"] == "worktree_cleaned"

def test_batch_skips_test_with_only_bad_grades():
    # All worktree_cleaned + bad grades → test NOT re-queued
    assert "test-001" not in executed_ids

def test_batch_reruns_test_with_failed_run_state():
    # Any FAILED run_state → test IS re-queued
    assert "test-001" in executed_ids
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Previous `--retry-errors` implementations | Added flag to make retry opt-in, with second pass over `completed_runs` to catch judge failures | `completed_runs="failed"` means bad grade (valid result), not an infra crash — the flag was retrying valid completed runs | Always distinguish state machine terminal states: `run_states` vs `completed_runs` encode different semantics |
| Keeping `worktree_cleaned` second-pass | Tried to reset only some `worktree_cleaned` runs (those with bad grades) | Valid results were being discarded; also broke the invariant that `worktree_cleaned` = completed | Once a run reaches `worktree_cleaned`, it is done regardless of grade — never reset it |
| Flag-gated unconditional behavior | Kept retry behind `--retry-errors` flag as default-off | Infrastructure failures were silently skipped when flag was absent, causing wasted runs and misleading "completed" status | Infra failures should always be retried — there is no valid reason to preserve a FAILED run state |

## Results & Parameters

**PR**: `HomericIntelligence/ProjectScylla#1491`
**Issue**: `HomericIntelligence/ProjectScylla#1490`
**Branch**: `1490-always-retry-infra-failures`

### Files changed

| File | Change |
|------|--------|
| `scripts/manage_experiment.py` | Remove `--retry-errors` arg; fix `_checkpoint_has_retryable_runs`; fix `_reset_non_completed_runs`; make batch + single-test retry unconditional |
| `tests/unit/e2e/test_manage_experiment_run.py` | Rename classes, remove flag from tests, fix bad-grade test expectations, add new unit tests |
| `tests/unit/e2e/test_manage_experiment_cli.py` | Remove `test_run_accepts_retry_errors` and `retry_errors` default assertion |

### State machine semantics (ProjectScylla-specific)

```
run_states values:
  "failed"           → unhandled exception (infra crash) → ALWAYS retry
  "rate_limited"     → RateLimitError → ALWAYS retry
  "worktree_cleaned" → pipeline completed (workspace removed) → NEVER retry
  <intermediate>     → crashed mid-pipeline → cascade tier/subtest to pending, resume from state

completed_runs values:
  "passed"          → judge_passed=True → valid result
  "failed"          → judge_passed=False (BAD GRADE) → valid result, NEVER retry
  "agent_complete"  → agent ran, judge never ran → treat as in-progress
```

### Test coverage after fix

- Unit coverage: 78.3% (above 75% threshold)
- Tests: 4761 passing
- Key assertions: `worktree_cleaned + bad grade → retryable=False`, `FAILED run_state → reset to pending`
