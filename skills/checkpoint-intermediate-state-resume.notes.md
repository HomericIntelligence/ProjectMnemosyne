# Session Notes: Checkpoint Intermediate State Resume

## Date: 2026-03-17

## Context

Dryrun3 experiment with 47 tests (~1,196 runs) was at NOGO status with 3 issues:
1. test-003: 2 runs stuck at `report_written` (T3/03/run_01, T3/04/run_01)
2. test-014: Missing T0/02 — subtest_state=`aggregated` but no run_states entry
3. User wanted to remove `--retry-errors` flag and always retry infra failures automatically

## Root Causes

### test-003: Intermediate runs in complete experiment
- `reset_failed_states()` had an early return: `if experiment_state not in ("failed", "interrupted"): return`
- This skipped complete experiments entirely, even when they had non-terminal runs
- The retry script had its own reset logic that advanced the runs in memory
- But the ProcessPool checkpoint save race meant the on-disk checkpoint wasn't updated

### test-014: Orphaned subtest_state
- T0/02 had `subtest_state=aggregated` in checkpoint but no entry in `run_states.T0.02`
- This was a checkpoint integrity issue from a prior ProcessPool race (subtest aggregated without completing its runs)
- The analysis script didn't detect this mismatch

## Changes Made

### resume_manager.py
- Added `_find_tiers_with_intermediate_runs()` — detects non-terminal, non-pending run states
- Added `_find_orphaned_subtest_states()` — detects aggregated subtests without run_states
- Added `_reset_intermediate_runs_in_complete_experiment()` — resets complete experiments with intermediate runs
- Added `_reset_orphaned_subtest_states()` — resets orphaned subtests to pending
- Refactored `reset_failed_states()` into 5 extracted methods to stay under C901 complexity limit
- Used class-level constants `_COMPLETE_FAMILY_STATES` and `_COMPLETE_TIER_STATES`

### analyze_dryrun3.py
- Added `check_orphaned_subtest_states()` function
- Added orphaned subtests to analysis results, report output, and Go/NoGo criteria
- Added to `tests_needing_work` filter

### test_resume_manager.py
- 12 new tests across 3 test classes
- Fixed 2 existing tests that had `aggregated` subtests without `run_states` (new orphan detection caught them)

## Key Observations

1. ProcessPool checkpoint save race is a recurring issue — the fix in commit 18f619b uses read-modify-write under `_checkpoint_write_lock`, but it can still lose transitions in edge cases
2. The state machine log is NOT authoritative for on-disk state — always verify the checkpoint file
3. `run_result.json` on disk IS authoritative for run completion — if it exists, the run completed regardless of checkpoint state
4. C901 complexity limit (10) is enforced by pre-commit — always extract methods early
5. SIM102 rule requires combining nested if statements with `and`