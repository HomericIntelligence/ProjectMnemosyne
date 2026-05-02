# Session Notes: always-retry-infra-failures

## Date
2026-03-14

## Repository
HomericIntelligence/ProjectScylla

## Context
ProjectScylla is an AI agent testing framework. It runs experiments with multiple tiers (T0-T6),
subtests, and runs. Experiment state is persisted in checkpoint.json with a 4-level state machine:
experiment → tier → subtest → run.

The `--retry-errors` flag had failed to work correctly across multiple attempts. The goal was to
remove it entirely and replace with always-on behavior.

## Bugs Fixed

### Bug 1: _checkpoint_has_retryable_runs() second pass (manage_experiment.py:319-324)
The function had a second loop over `completed_runs` that returned True if any entry was "failed".
But `completed_runs["failed"]` means judge_passed=False (bad grade) — a VALID result, not an
infra crash. This caused the batch runner to re-queue tests that had completed with low scores,
wasting compute and corrupting results.

Fix: Delete the entire second pass over completed_runs.

### Bug 2: _reset_non_completed_runs() worktree_cleaned second-pass (manage_experiment.py:354-363)
When resetting runs for retry, there was a block that checked worktree_cleaned runs and reset them
if their completed_runs status was "failed". This conflated the two meanings of "failed" again —
get_run_status() returns completed_runs status, so "failed" = bad grade, not infra crash.

Fix: Replace the entire worktree_cleaned block with `continue`. Completed runs (any grade) are never reset.

### Bug 3: Retry gated behind --retry-errors flag
The reconcile+reset logic in run_one_test() (batch mode) and cmd_run() (single mode) was wrapped
in `if args.retry_errors:`. This meant infra failures were silently skipped by default.

Fix: Remove the flag entirely; make both blocks unconditional.

## Key Invariant (confirmed from full code read)
- `run_states="FAILED"` → ALWAYS an unhandled exception (infra crash) → retry
- `run_states="RATE_LIMITED"` → ALWAYS a RateLimitError → retry
- `run_states="WORKTREE_CLEANED"` → ALWAYS completed (workspace removed) → never retry
- `run_states="WORKTREE_CLEANED"` + `completed_runs="failed"` → bad judge grade → valid result, NEVER retry

## Changes Made
- Removed --retry-errors from argument parser
- Fixed _checkpoint_has_retryable_runs(): removed completed_runs second pass
- Fixed _reset_non_completed_runs(): replaced worktree_cleaned block with continue
- Made batch skip logic unconditional (lines 816-822)
- Made run_one_test() reconcile+reset unconditional (lines 748-774)
- Made single-test mode reconcile+reset unconditional (~line 1151)
- Updated tests in test_manage_experiment_run.py and test_manage_experiment_cli.py

## Test Results
- 4761 tests passing
- 78.3% unit coverage (above 75% threshold)
- Pre-commit hooks passed
- PR #1491 created with auto-merge enabled
