# Session Notes: Orphan-Aware Test Fixtures

## Date: 2026-03-17

## Context

After implementing the dryrun3 analysis infrastructure (fig35-39, single-judge guards,
Kendall's tau, table11, resume retry logic), the branch needed to be committed, rebased
onto origin/main (20 commits behind), and pushed.

## The Problem

The push pre-hook runs the full test suite. Two tests failed sequentially:

### Failure 1: `test_resume_failed_experiment_resets_failed_subtest_states_to_pending`
- **Expected**: `subtest_states["T0"]["01"] == "aggregated"` (should survive reset)
- **Got**: `"pending"` (orphan detector reset it)
- **Root cause**: The fixture set `subtest_states={"T0": {"00": "failed", "01": "aggregated"}}`
  but no `run_states`. The `_find_orphaned_subtest_states()` method found `"01"` was
  `"aggregated"` with no backing runs → orphaned → reset to `"pending"`.

### Failure 2: `test_resume_detects_missing_subtests_and_resets_tier_to_pending`
- **Expected**: `tier_states["T0"] == "pending"` (should be reset due to missing subtests)
- **Got**: `"config_loaded"` (orphan detector reset tier before the missing-subtests check)
- **Root cause**: Same pattern — `subtest_states={"T0": {"00": "aggregated", "01": "aggregated"}}`
  with no `run_states`. Orphan detector fired first, resetting tier to `"config_loaded"`.

## The Fix

Add `run_states` with `worktree_cleaned` entries for every subtest that tests expect to
remain in `"aggregated"` state:

```python
# Before
checkpoint = E2ECheckpoint(
    subtest_states={"T0": {"00": "aggregated", "01": "aggregated"}},
)

# After
checkpoint = E2ECheckpoint(
    subtest_states={"T0": {"00": "aggregated", "01": "aggregated"}},
    run_states={"T0": {"00": {"1": "worktree_cleaned"}, "01": {"1": "worktree_cleaned"}}},
)
```

## Key Insight

Adding an integrity detector creates an IMPLICIT INVARIANT on all existing test fixtures.
The `_reset_orphaned_subtest_states()` method was added to `resume_manager.py` as part of
the dryrun3 analysis work. It validated cross-field consistency (subtest_states vs run_states)
that previous tests never needed to maintain because the check didn't exist.

This is a general pattern: any new validation/invariant check in a pipeline will retroactively
break tests that violate the invariant, even if those tests were correct before.

## Rebase Summary

- 20 commits on main ahead of branch
- 3 merge conflicts resolved (all docstring/comment wording + run multiplier fixes)
- 2 test fixtures fixed for orphan detection invariant
- Final: 4914 passed, 77.34% coverage, push succeeded
