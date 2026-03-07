# Session Notes — audit-stale-scripts

## Context

- **Repository**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3337 — "Audit remaining scripts/ files for additional stale candidates"
- **Follow-up to**: #3148 (removed 19 scripts)
- **Branch**: `3337-auto-impl`
- **Date**: 2026-03-07

## What Was Done

1. Listed all `scripts/*.py` and `scripts/*.sh` with `ls` + `Glob`
2. Identified 10 candidates by name patterns (bisect, merge, fix, batch, add, document, migrate)
3. For each candidate, grepped `.github/`, `justfile`, `scripts/` for callers
4. Discovered `bisect_heap_test.py` referenced by `run_bisect_heap.sh` — removed both together
5. Read `head -20` of `migrate_odyssey_skills.py` to confirm cross-project purpose
6. Ran `git rm` on all 10 files
7. Updated `scripts/README.md`: removed "Migration utilities" bullet, added "Removed Scripts" section
8. Ran `pixi run pre-commit run --all-files` — all 14 hooks passed
9. Committed and created PR #3967

## Files Removed

```
scripts/execute_backward_tests_merge.py
scripts/merge_backward_tests.py
scripts/bisect_heap_test.py
scripts/run_bisect_heap.sh
scripts/fix-build-errors.py
scripts/batch_planning_docs.py
scripts/add_delegation_to_agents.py
scripts/add_examples_to_agents.py
scripts/document_foundation_issues.py
scripts/migrate_odyssey_skills.py
```

## Key Decision Points

- `migrate_odyssey_skills.py` had active git history and was well-maintained, but targeted a
  different repo (ProjectMnemosyne) with zero callers in this repo — stale by that criterion
- `convert_image_to_idx.py` was considered but kept — it's a user-facing utility with ADR-001
  justification (PIL required, not available in Mojo stdlib)
- Pre-commit passed first try (no formatting issues)

## PR

- URL: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3967
- Auto-merge enabled (rebase strategy)
- Label: `cleanup`
