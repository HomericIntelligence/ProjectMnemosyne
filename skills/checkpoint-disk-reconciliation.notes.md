# Session Notes: checkpoint-disk-reconciliation

## Date
2026-03-13

## Project
ProjectScylla — AI agent testing and optimization framework

## Problem Statement

The dryrun3 experiment had stale checkpoint states caused by the ProcessPool checkpoint race condition (fixed in commit 18f619b). Runs that completed on disk (all `run_result.json` files exist) had intermediate checkpoint states like `judge_prompt_built`, `dir_structure_created`, or `pending`. When `--retry-errors` ran, it only reset `failed`/`rate_limited` run states — it didn't notice that:
1. A run at `judge_prompt_built` in the checkpoint actually has `run_result.json` on disk
2. A run at `worktree_cleaned` with `completed_runs=failed` needs re-running (judge failed)

## Root Cause (ProcessPool Race)

When running tiers in parallel with ProcessPoolExecutor:
- Each worker gets a **serialized (forked) copy** of the checkpoint at fork time
- Worker B's save could overwrite Worker A's new states (B's copy didn't know about A's entries)
- Main process TierStateMachine/ExperimentStateMachine saved stale `self.checkpoint`, erasing subprocess writes

Fix was in `checkpoint.py`: `save_checkpoint()` now does read-modify-write under `_checkpoint_write_lock`.

## Dryrun3 Status at Time of Fix

- **47 tests**, all have at least one successful completion directory
- **8 tests** have stale checkpoint states (test-001/002/003/004/012/013/014/028)
- test-001/002/003: All 103 `run_result.json` exist on disk, but 13/14/35 stale intermediate states
- **T0/12 and T6/01**: Judge-failed runs at `worktree_cleaned` — these need re-running

## Implementation Plan Followed

### Files Modified
- `scripts/manage_experiment.py` — all changes

### Functions Added/Modified
1. `_reconcile_checkpoint_with_disk()` — NEW — scans disk, advances stale states
2. `_reset_non_completed_runs()` — MODIFIED — second pass for judge-failed `worktree_cleaned` runs
3. `_checkpoint_has_retryable_runs()` — MODIFIED — checks `completed_runs` for `failed` entries
4. Batch mode `--retry-errors` handler — MODIFIED — calls reconcile before reset
5. Single mode `--retry-errors` handler — MODIFIED — calls reconcile before reset

### Test Results
- 6 new unit tests added to `tests/unit/e2e/test_manage_experiment_run.py`
- All 4795 tests pass (4687 unit + 108 integration)
- Coverage: 76.62% (above 75% unit floor)

## Key Design Decisions

1. **Only advance, never regress**: If checkpoint is at `judge_complete` but disk only has `agent/result.json`, keep `judge_complete`. The disk may be stale (e.g., partially cleaned workspace).

2. **Read `judge_passed` from `run_result.json`**: This determines whether to set `completed_runs` status to `"passed"` or `"failed"`. Default to `None` if parse fails.

3. **State ordering array**: Used a `_STATE_RANK` dict for O(1) rank lookup rather than nested conditionals. Makes it easy to add new states.

4. **`workspace/` directory absence = worktree cleaned**: The final stage deletes the workspace directory. If `run_result.json` + `report.md` exist but `workspace/` is gone → `worktree_cleaned`.

5. **Both batch and single mode**: The reconcile+reset sequence is identical — copy-paste rather than extracting a shared helper (YAGNI).

## What NOT to Do

- Don't reset all non-`worktree_cleaned` states to `pending` without reading disk — this restarts agent execution unnecessarily
- Don't skip the `completed_runs` check in `_checkpoint_has_retryable_runs` — batch mode will incorrectly skip tests with judge-failed runs
- Don't save checkpoint if both `reconcile_count` and `reset_count` are 0 — avoid spurious writes