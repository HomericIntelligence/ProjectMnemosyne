---
name: checkpoint-save-guard-bug
description: Fix for --retry-errors not persisting checkpoint when only intermediate-state
  runs exist
category: debugging
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
# Checkpoint Save Guard Bug

| Field | Value |
|-------|-------|
| Date | 2026-03-13 |
| Objective | Fix `--retry-errors` not working for runs stuck in intermediate states |
| Outcome | Success - one-line fix, all 4774 tests pass |

## When to Use

- `--retry-errors` appears to do nothing when runs are stuck in intermediate states (e.g., `judge_prompt_built`, `replay_generated`, `config_committed`)
- Checkpoint file on disk does not reflect in-memory state changes after retry-errors reset
- Return value of a reset/count function is used as a save guard but only counts a subset of affected items

## Verified Workflow

1. Identified that `_reset_non_completed_runs()` returned count of only terminal (failed/rate_limited) resets
2. Callers at two sites gated `save_checkpoint()` on `if reset_count > 0:`
3. For intermediate-only cases, tier/subtest states were cascaded to `pending` in memory but `reset_count=0` meant checkpoint was never saved
4. Fix: moved `reset_count += 1` to count ALL non-completed runs (before the terminal-state check), not just terminal resets
5. Updated two test assertions to match new semantics (2->4, 0->4)

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Root cause pattern**: Function return value counts only a subset of affected items, but caller uses it as a "did anything change?" guard for persistence. The fix is to count all affected items, not just the subset that was mutated.

**Files changed**:
- `scripts/manage_experiment.py:351` - moved `reset_count += 1` before terminal-state check
- `scripts/manage_experiment.py:337` - updated docstring
- Two caller sites (lines 649 and 1038) required no changes - the guard `if reset_count > 0:` now works correctly

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1474 - dryrun3 intermediate state fix | 4774 tests pass, 76.45% unit coverage |
