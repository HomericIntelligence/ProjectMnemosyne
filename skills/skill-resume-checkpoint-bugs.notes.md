# Raw Notes: Resume Checkpoint Bugs (2026-02-26)

## PR
https://github.com/HomericIntelligence/ProjectScylla/pull/1109

## Bug Analysis

### Issue 3 was the cheapest fix (5 lines)
The uppercase `"INTERRUPTED"` bug was invisible because the pre-existing test
`test_sets_experiment_state_to_interrupted` was asserting the buggy value `"INTERRUPTED"`.
Lesson: when a test documents behavior that seems wrong, check if it's documenting a bug.

### Issue 2 had 4 reinforcing bugs
Each fix was necessary but not sufficient:
1. Clearing `max_subtests` on resume lets new runs get all subtests
2. But `_check_tiers_need_execution` still returned empty set
3. Add subtest detection to `_check_tiers_need_execution`
4. But tier resets to `subtests_running` which skips `action_pending`
5. Reset to `pending` to force `action_pending` re-run

### Issue 1 required a semantic change
The user explicitly confirmed this was the desired behavior change (not a bug in the
original design). Moving baseline to experiment level required a new method, a new
call site, and updating stage_capture_baseline's load order.

## Technical Notes

### Why use ctx.experiment_dir instead of path arithmetic
The `RunContext` dataclass has `experiment_dir: Path | None` field. Using it directly
is cleaner and correct. Path arithmetic (`run_dir.parent.parent.parent`) assumes a
fixed directory depth that tests don't replicate.

### TierState "pending" vs "subtests_running" for reset
- `"subtests_running"` maps to `TierState.SUBTESTS_RUNNING` which triggers
  `action_config_loaded()` -> `run_tier_subtests_parallel()`. This action uses
  `tier_ctx.tier_config` set at pre-population time (limited to old max_subtests).
- `"pending"` maps to `TierState.PENDING` which triggers `action_pending()` ->
  loads tier config fresh with current `max_subtests`. Correct choice for expansion.

### Idempotent baseline capture
The `pipeline_baseline.json` existence check makes `_capture_experiment_baseline`
safe to call on resume. `action_dir_created` runs at the DIR_CREATED state, which
on resume is replayed from the beginning of the DIR_CREATED action.

## Ephemeral vs Persistent CLI Fields

Fields that mean "for this run only" (like `--until-*`) should only override if non-None.
Fields that mean "scope limit" (like `--max-subtests`) need special handling:
- `None` should clear the saved value (no limit)
- A value should override the saved value

This distinction matters because:
- `--until` omitted on resume means "use saved target" (continue to same target)
- `--max-subtests` omitted on resume means "run all subtests" (no limit = expand)

## Files Modified in ProjectScylla PR #1109
- `scylla/e2e/runner.py:316-333` - Ephemeral CLI field handling (STEP 2)
- `scylla/e2e/runner.py:441-524` - `_check_tiers_need_execution()`
- `scylla/e2e/runner.py:405-454` - Tier state reset logic
- `scylla/e2e/runner.py:589-628` - `_capture_experiment_baseline()`
- `scylla/e2e/runner.py:551,561` - `_handle_experiment_interrupt()` INTERRUPTED fix
- `scylla/e2e/stages.py:269-310` - `stage_capture_baseline()` load order
- `tests/unit/e2e/test_runner.py` - INTERRUPTED test update + 2 new tests
- `tests/unit/e2e/test_stages.py` - Baseline tests split into experiment-level + backward-compat