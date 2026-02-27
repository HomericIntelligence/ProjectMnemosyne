# Raw Session Notes: manage-experiment-audit (2026-02-24)

## Source
ProjectScylla, branch: consolidate-run-command
Commit: 068dbc4

## Files Changed
- scripts/manage_experiment.py (+68/-0 net, --from wiring + filter_judge_slot doc)
- tests/unit/e2e/test_manage_experiment.py (+605 lines, 13 new tests)
- scripts/README.md (rewritten, removed stale subcommand docs)
- scripts/run_e2e_batch.py (deleted, 1166 lines)

## Test Count
Before: 34 tests
After: 47 tests (+13)

## Pre-commit Issues Encountered
1. ruff-format auto-fixed formatting in manage_experiment.py (f-string in log statement)
2. E501 line too long in docstring → shortened from 102 to 98 chars

## Patch Target Resolution
The most confusing part was determining the correct patch target for run_experiment.
cmd_run does `from scylla.e2e.runner import run_experiment` inside the function.
Tested: `patch("scylla.e2e.runner.run_experiment")` → works ✓
Tested: `patch("manage_experiment.run_experiment")` → fails (AttributeError) ✗

## 2026-02-27: docker-ci-dead-step-cleanup (ProjectScylla #1114)

Session resolved a CI workflow referencing a non-existent test directory.

Key insight: When a CI step tests Docker integration and requires API keys,
Option B (remove + ADR) is almost always the right choice over Option A
(implement heavyweight integration tests in standard PR CI).

The pre-commit hook that runs all tests before `git push` caught any regressions:
3185 tests, 78.36% coverage, push succeeded.
