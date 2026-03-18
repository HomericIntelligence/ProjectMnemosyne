---
name: orphan-aware-test-fixtures
description: "Patterns for fixing test fixtures that break when checkpoint integrity detectors are added. Use when: adding orphan detection to resume pipelines, or when aggregated states get unexpectedly reset."
category: testing
date: 2026-03-17
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Adding `_reset_orphaned_subtest_states()` to the resume pipeline created a new invariant: subtest states in `aggregated`/`runs_complete` must have backing `run_states`, or they get reset to `pending`. Existing tests that set `subtest_states` without `run_states` broke silently — the orphan detector correctly reset them. |
| **Solution** | Add `run_states` entries with `worktree_cleaned` for any test fixture subtest in `aggregated` or `runs_complete` state |
| **Key Insight** | Integrity detectors create implicit invariants on test fixtures. When you add a detector that validates cross-field consistency (e.g., subtest_states must have backing run_states), ALL existing fixtures that set those fields must be updated. |
| **Scope** | `tests/unit/e2e/test_runner.py` — `TestInitializeOrResumeExperimentFailedReset` and `TestInitializeOrResumeExperimentMaxSubtests` |

## When to Use

- Adding an orphan/integrity detector to a resume or state machine pipeline
- Debugging tests where checkpoint states get unexpectedly reset to `pending`
- Rebasing branches that add new checkpoint invariants onto branches with existing test fixtures
- Seeing `assert 'pending' == 'aggregated'` or `assert 'config_loaded' == 'pending'` failures in resume tests

## Verified Workflow

### Quick Reference

```python
# BEFORE (broken — orphan detector resets "01" to "pending"):
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    # No run_states → "01" is orphaned → reset to pending
)

# AFTER (fixed — "01" has backing run_states):
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
)
```

### Step-by-Step: Diagnosing Orphan-Related Test Failures

1. **Identify the symptom**: Test asserts a subtest state is `"aggregated"` or `"runs_complete"` but gets `"pending"` instead.

2. **Check if an orphan detector exists**: Search for `_find_orphaned_subtest_states` or similar cross-field validation in the resume pipeline.

3. **Trace the execution order**: In `reset_failed_states()`, the orphan reset runs BEFORE the failed/interrupted reset:
   ```python
   def reset_failed_states(self):
       self._reset_infra_error_runs()           # Step 1
       self._reset_intermediate_runs_in_complete_experiment()  # Step 2
       self._reset_orphaned_subtest_states()     # Step 3 ← resets "aggregated" without run_states
       self._reset_failed_and_interrupted()      # Step 4
   ```

4. **Fix**: Add `run_states` entries for every subtest that the test expects to remain in `aggregated` or `runs_complete` state. Use `"worktree_cleaned"` as the terminal run state.

5. **Audit**: `grep` for `"aggregated"` and `"runs_complete"` across all test fixtures:
   ```bash
   grep -n '"aggregated"\|"runs_complete"' tests/unit/e2e/test_runner.py
   ```
   For each match, verify there's a corresponding `run_states` entry.

### Cascade Effects

The orphan detector also calls `_reset_tier_to_config_loaded()` and `_reset_experiment_to_tiers_running()`, which can change tier and experiment states as side effects:

| Orphan detected | Tier state changes to | Experiment state changes to |
|---|---|---|
| Any subtest orphaned | `config_loaded` (if was complete-family) | `tiers_running` (if was complete-family) |

This means a test expecting `tier_states["T0"] == "pending"` might get `"config_loaded"` instead if the orphan detector fires first.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| First push after rebase | Rebased onto main, resolved 3 merge conflicts, pushed | `test_resume_failed_experiment_resets_failed_subtest_states_to_pending` failed — `"aggregated"` subtest without `run_states` was orphan-detected | Adding integrity detectors creates implicit invariants on ALL fixtures that touch the validated fields |
| Second push after fixing one test | Fixed the first failing test, pushed | `test_resume_detects_missing_subtests_and_resets_tier_to_pending` failed — same root cause in different test class | Must audit ALL test fixtures for the pattern, not just the first failure; use `grep '"aggregated"'` across the entire file |

## Results & Parameters

### Fix Pattern

```python
# For every subtest in "aggregated" state in a test fixture,
# add a terminal run_states entry:
run_states={"T0": {"00": {"1": "worktree_cleaned"}, "01": {"1": "worktree_cleaned"}}}
```

### Audit Command

```bash
# Find all test fixtures with aggregated/runs_complete without run_states
grep -n '"aggregated"\|"runs_complete"' tests/unit/e2e/test_runner.py
```

### Test Results

```
Before fix: 2 failures (2637 passed, 1 failed; then 2648 passed, 1 failed)
After fix: 4914 passed, 2 skipped, 77.34% coverage
Push: succeeded with --force-with-lease (rebased branch)
```
