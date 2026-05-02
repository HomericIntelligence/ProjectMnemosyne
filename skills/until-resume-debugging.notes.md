# Raw Notes: --until Resume Debugging Session (2026-02-25)

## Session context
- Branch: `1067-additive-cli-args-checkpoint`
- Tests validated: test-031, test-033
- Results dirs: `/home/mvillmow/dryrun_step_test4` (test-031), `/home/mvillmow/dryrun_step_test5` (test-033)

## Sequence of failures encountered

### test-031 Step 7 attempt 1 (before any fixes)
Error: "No sub-test results to select from"
Cause: Tier resumed at SUBTESTS_RUNNING which ran select_best_subtest on empty subtest_results
Fix: runner.py STEP 4 reset tier to config_loaded instead of subtests_running

### test-031 Step 7 attempt 2 (after Bug 1 fix)
Error: "" (empty exception) — "Run T0/00/run_01 failed in state replay_generated"
Cause: assert adapter_config is not None in stage_execute_agent
Fix: lazy adapter_config reconstruction when None

### test-031 Batch C attempt 1 (after Bug 2 + adapter_config fix)
Error: "agent_result must be set before finalize_run"
Cause: RunContext freshly constructed, stage_execute_agent not called for resume at judge_complete
Fix: restore_run_context() loads agent_result from disk

### test-031 Batch C attempt 2 (after restore_run_context added)
Error: "judgment must be set before finalize_run"
Cause:_has_valid_judge_result returns False for is_valid=False results
Fix: check judge_dir/"result.json" exists directly, not via_has_valid_judge_result

## Linter reverts observed
After committing, the linter reverted these changes:
- stages.py line 450: restored `assert adapter_config is not None` (removing lazy reconstruction)
- stages.py: removed `restore_run_context` function
- subtest_executor.py: removed `restore_run_context` call and import
- runner.py line 414: reverted `config_loaded` back to `subtests_running`
- test_runner.py: reverted `_run_resume` signature (removed `run_states` param)
- test_runner.py line 1166: reverted assertion back to `subtests_running`

These reverts mean bugs 1 and 3 are still present in the committed code.
Bug 2 (failed run reset) may or may not have been reverted.