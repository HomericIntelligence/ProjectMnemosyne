# Raw Notes: batch-retry-errors-checkpoint-reset

## Session Context

- **Date**: 2026-03-06
- **Branch**: `retry-errors-per-run-checkpoint-reset`
- **PR**: HomericIntelligence/ProjectScylla#1451
- **Files changed**: `scripts/manage_experiment.py`, `tests/unit/e2e/test_manage_experiment_run.py`

## Problem Statement

Batch mode `--retry-errors` consulted only `batch_summary.json` to decide which tests to re-run.
Tests with `status=success` at the batch level were skipped even if their internal checkpoints
contained `failed` or `rate_limited` runs.

Real-world examples from dryrun3:
- test-001: T5/02/1=`failed`, T6/01=`failed`, T0 runs stuck at `judge_prompt_built`
- test-003: T0/06,07=`failed`, T5/02,04,11-15=`failed`, T3/11,12=`failed`
- test-002: T3/08=`failed` subtest, T5/13-15=`failed`

## Key Code Locations (ProjectScylla)

```
scripts/manage_experiment.py
  _find_checkpoint_path()         line ~279  — globs *-{experiment_id} dirs
  _checkpoint_has_retryable_runs() line ~307  — NEW: fast JSON scan
  _reset_terminal_runs()          line ~323  — NEW: resets failed+rate_limited runs
  _run_batch() → completed_ids    line ~676  — PATCHED: checks checkpoint for success tests
  run_one_test() → retry reset    line ~625  — NEW: resets checkpoint before run_experiment()
  cmd_run() → single-mode reset   line ~1017 — PATCHED: uses _reset_terminal_runs()

tests/unit/e2e/test_manage_experiment_run.py
  TestRetryErrorsInBatch          line ~1297 — 3 new tests added
  TestRetryErrorsInSingleMode     line ~2857 — 2 existing tests updated
```

## Why `reset_runs_for_from_state()` Was Wrong for This Use Case

```python
# Old single-mode code
reset_runs_for_from_state(checkpoint, from_state="pending", status_filter=["failed"])
```

Inside `reset_runs_for_from_state`, `status_filter` is applied via `get_run_status()` which
reads from `completed_runs` dict. `rate_limited` runs are never recorded in `completed_runs`
(only `passed`/`failed`/`agent_complete` go there). So `rate_limited` runs had `get_run_status()
→ None` and were excluded by the filter check.

The fix: iterate `run_states` directly, which tracks ALL states including `rate_limited`.

## Cascade Logic for `_reset_terminal_runs()`

When a run is reset:
1. `run_states[tier][subtest][run_num] = "pending"` — direct mutation
2. `checkpoint.unmark_run_completed(tier, subtest, run_num)` — removes from `completed_runs`
3. `checkpoint.set_subtest_state(tier, subtest, "pending")` — cascade up
4. `checkpoint.set_tier_state(tier, "pending")` — cascade up
5. `checkpoint.experiment_state = "tiers_running"` — experiment-level reset

This matches the cascade in `reset_runs_for_from_state()` exactly.

## Interrupted Runs (Non-Issue)

Runs stuck mid-way (e.g. `replay_generated`, `judge_prompt_built`) do NOT need reset.
`ResumeManager.merge_cli_tiers_and_reset_incomplete()` inside `run_experiment()` already
resumes them from their current state. `_checkpoint_has_retryable_runs()` intentionally
does NOT detect interrupted states — only terminal `failed`/`rate_limited`.

## Test Count

- Before: 4455 unit tests
- After: 4563 tests (pre-push hook ran all tests including integration)
- Coverage: 75.80% combined (above 75% threshold)

## Pre-commit Issues Encountered

1. `ruff-format` split `from scylla.e2e.checkpoint import (load_checkpoint as _load_cp, save_checkpoint as _save_cp)` into two separate import blocks — cosmetic, no action needed
2. Mypy: `dict[str, dict]` → fix to `dict[str, dict[str, Any]]`
3. E501: docstring "Tests that --retry-errors in single mode..." exceeded 100 chars → shortened
