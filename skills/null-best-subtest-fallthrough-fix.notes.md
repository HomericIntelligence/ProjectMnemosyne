# Session Notes — null-best-subtest-fallthrough-fix

## Date
2026-03-13

## Context
ProjectScylla dryrun3 experiment set (~47 tests) had T5 subtests consistently
failing with "Cannot build merged baseline: all required tiers failed (T1)" even
though T1 showed as `complete` in the checkpoint. This was blocking dryrun3
completion for test-001, test-002, test-003, test-012, test-014.

## Investigation Path

1. User provided a plan identifying 3 root causes:
   - Bug 1: `build_merged_baseline` doesn't fall through to `best_subtest.json`
   - Bug 2: `_reset_non_completed_runs` counting (already fixed in f77126a0)
2. Read `scylla/e2e/tier_manager.py` around `build_merged_baseline()` (lines 692-760)
3. Confirmed the `elif` at line 726 was the culprit

## Exact Diff

```python
# BEFORE (lines 721-729)
best_subtest_id = None
if result_file.exists():
    with open(result_file) as f:
        tier_result = json.load(f)
    best_subtest_id = tier_result.get("best_subtest")
elif best_subtest_file.exists():
    with open(best_subtest_file) as f:
        selection = json.load(f)
    best_subtest_id = selection.get("winning_subtest")

# AFTER
best_subtest_id = None
if result_file.exists():
    with open(result_file) as f:
        tier_result = json.load(f)
    best_subtest_id = tier_result.get("best_subtest")

if not best_subtest_id and best_subtest_file.exists():
    with open(best_subtest_file) as f:
        selection = json.load(f)
    best_subtest_id = selection.get("winning_subtest")
```

## Test Results
- 4681 unit tests pass
- 76.58% unit coverage (above 75% threshold)
- pre-commit: all hooks passed
- PR #1476 created, auto-merge enabled

## Why result.json Had null best_subtest
During re-runs of dryrun3, the `--retry-errors` flow resets runs to pending and
re-executes them. The tier report is regenerated early in the process with empty
data (before aggregation completes), writing `result.json` with `best_subtest: null`.
The `best_subtest.json` file (written during the original run) retains the
correct `winning_subtest` value. The `elif` silently skipped it.