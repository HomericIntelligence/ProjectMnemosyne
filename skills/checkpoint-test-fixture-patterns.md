---
name: checkpoint-test-fixture-patterns
description: 'Patterns for building consistent checkpoint test fixtures with hierarchical
  state. Use when: writing tests for resume/retry logic, debugging orphan detector
  resets, or setting up checkpoint state for state machine tests.'
category: testing
date: 2026-03-17
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | Test fixtures for checkpoint-based resume logic silently break when they set higher-level state (e.g., subtest "aggregated") without providing the lower-level backing state (e.g., run_states entries) that integrity validators expect |
| **Solution** | Always populate all four checkpoint hierarchy levels consistently: experiment_state → tier_states → subtest_states → run_states |
| **Key Insight** | Runtime validators (orphan detectors, intermediate-run scanners) run during resume and will correct inconsistent fixtures — causing "correct code, broken test" failures |
| **Scope** | ProjectScylla `scylla/e2e/resume_manager.py`, `scylla/e2e/checkpoint.py`, `tests/unit/e2e/test_runner.py` |

## When to Use

- Writing new tests for `_initialize_or_resume_experiment()` or `ResumeManager.reset_failed_states()`
- Debugging a test where checkpoint subtest/tier states are unexpectedly reset to "pending"
- Setting up `E2ECheckpoint` fixtures for state machine transition tests
- Adding new checkpoint integrity validators that inspect cross-level consistency

## Verified Workflow

### Quick Reference

```python
# WRONG — orphan detector will reset "01" to "pending"
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    # run_states defaults to {} — "01" has no backing runs!
)

# RIGHT — "01" has a backing run, orphan detector leaves it alone
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
)
```

### Checkpoint Hierarchy Rules

The E2ECheckpoint has a 4-level hierarchy. Each level's state implies constraints on levels below:

```
experiment_state  (1 value)
  └─ tier_states      (per tier: T0, T1, ...)
       └─ subtest_states  (per subtest: 00, 01, ...)
            └─ run_states      (per run: 1, 2, 3, ...)
```

**Consistency rules enforced at resume time:**

| Higher State | Required Lower State | Validator |
| ------------- | --------------------- | ----------- |
| subtest "aggregated" or "runs_complete" | At least one entry in `run_states[tier][subtest]` | `_find_orphaned_subtest_states()` |
| subtest "runs_in_progress" | At least one run in non-terminal state | `_find_tiers_with_intermediate_runs()` |
| tier "complete" | All subtests in "aggregated" | `_reset_tier_state_for_rerun()` |
| experiment "complete" | All tiers in complete-family state | `_reset_intermediate_runs_in_complete_experiment()` |

### Step-by-Step: Building a Resume Test Fixture

1. **Decide which states you're testing** — identify the specific reset behavior under test
2. **Set all four levels consistently** — if a subtest is "aggregated", give it a terminal run
3. **Use terminal run states for completed work** — `"worktree_cleaned"` is the canonical terminal state
4. **Use non-terminal run states for in-progress work** — `"pending"`, `"report_written"`, etc.
5. **Verify the test asserts the right thing** — if testing that failed subtests reset, ensure non-failed subtests have backing state so they don't also reset

### Common Terminal vs Non-Terminal Run States

```python
TERMINAL_STATES = {"worktree_cleaned"}  # Run is fully done
RETRYABLE_STATES = {"failed", "rate_limited"}  # Reset to pending on resume
INTERMEDIATE_STATES = {"report_written", "judge_pipeline_run", ...}  # Mid-pipeline
```

### Full Example: Testing Failed-Subtest Reset

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
        # Critical: "01" needs backing run_states
        run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
        started_at=datetime.now(timezone.utc).isoformat(),
        last_updated_at=datetime.now(timezone.utc).isoformat(),
        status="failed",
    )
    # ... run resume ...
    assert checkpoint.subtest_states["T0"]["00"] == "pending"      # reset
    assert checkpoint.subtest_states["T0"]["01"] == "aggregated"   # untouched
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Minimal fixture with subtest_states only | Set `subtest_states={"T0": {"00": "failed", "01": "aggregated"}}` without run_states | `_find_orphaned_subtest_states()` detected "01" as orphaned (aggregated with no backing runs) and correctly reset it to "pending" | Fixtures must be cross-level consistent — higher-state assertions require lower-state backing data |
| Using `_run_resume` helper for complex fixtures | Used the shared helper which only accepts subtest_states/tier_states kwargs | Helper creates checkpoint with `run_states={}` — no way to inject run_states | For tests needing run_states, inline the checkpoint creation instead of using the shared helper |

## Results & Parameters

### Fix Applied

```python
# File: tests/unit/e2e/test_runner.py
# Test: TestInitializeOrResumeExperimentFailedReset
#       ::test_resume_failed_experiment_resets_failed_subtest_states_to_pending

# Before (FAILING): used _run_resume helper, no run_states
# After (PASSING): inlined checkpoint creation with run_states for subtest "01"
```

### Validators in ResumeManager.reset_failed_states()

Execution order matters — validators run in this sequence:
1. `_reset_infra_error_runs()` — failed/rate_limited runs → pending
2. `_reset_intermediate_runs_in_complete_experiment()` — complete experiments with stuck runs
3. `_reset_orphaned_subtest_states()` — aggregated subtests without run_states → pending
4. `_reset_failed_and_interrupted()` — failed/interrupted experiment/tier/subtest → pending/tiers_running

### Test Results

```
Before fix: 1 failed (assert 'pending' == 'aggregated')
After fix:  2637 passed, 1 skipped
```
