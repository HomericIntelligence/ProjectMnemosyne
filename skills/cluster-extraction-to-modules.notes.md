# Implementation Notes: cluster-extraction-to-modules

## Session Context

- **Date**: 2026-03-05
- **Project**: ProjectScylla
- **Issue**: #1395 — Continue decomposition: runner.py and implementer.py (1,220+ lines)
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/1444
- **Branch**: `1395-auto-impl`

## Target File

`scylla/automation/implementer.py` — 1,221 lines before, 837 lines after

The file contained `IssueImplementer`, a class implementing GitHub issues in parallel using
Claude Code. It mixed 4 concerns:

1. **Core orchestration** — `run()`, `_implement_all()`, `_implement_issue()`, state management
2. **Retrospective lifecycle** — `_run_retrospective()`, `_retrospective_needs_rerun()`
3. **Follow-up issue creation** — `_run_follow_up_issues()`, `_parse_follow_up_items()`
4. **Git/PR operations** — `_commit_changes()`, `_ensure_pr_created()`, `_create_pr()`

## Cluster Analysis

### Cluster 1: Retrospective (~80 lines saved)

**Methods extracted**: `_run_retrospective`, `_retrospective_needs_rerun`

**New file**: `scylla/automation/retrospective.py`

**Parameter translation**:
- `self.state_dir` → `state_dir: Path`
- `self.status_tracker` → `slot_id: int | None` (already a param, just passed through)

### Cluster 2: Follow-up Issues (~150 lines saved)

**Methods extracted**: `_run_follow_up_issues`, `_parse_follow_up_items`

**New file**: `scylla/automation/follow_up.py`

**Parameter translation**:
- `self.state_dir` → `state_dir: Path`
- `self.status_tracker` → `status_tracker: StatusTracker | None`

### Cluster 3: PR/Git Operations (~190 lines saved)

**Methods extracted**: `_commit_changes`, `_ensure_pr_created`, `_create_pr`

**New file**: `scylla/automation/pr_manager.py`

**Parameter translation**:
- `self.options.auto_merge` → `auto_merge: bool = False`
- `self.status_tracker` → `status_tracker: StatusTracker | None`

## Unused Imports Removed from implementer.py

After extraction, these imports became unused and were removed:
- `import re` (used only in `_parse_follow_up_items`)
- `from .github_api import gh_issue_comment, gh_issue_create, gh_pr_create`
- `from .prompts import get_follow_up_prompt, get_pr_description` (kept `get_implementation_prompt`)

## Existing Test Failures After Extraction

10 tests in `test_implementer.py` failed with:
```
AssertionError: Expected 'run' to have been called once. Called 0 times.
```

**Root cause**: Tests patched `scylla.automation.implementer.run` but the code moved to
`scylla.automation.retrospective.run` and `scylla.automation.follow_up.run`.

**Fix**: Updated patch targets in:
- `TestRunRetrospective` (4 tests): `implementer.run/logger` → `retrospective.run/logger`
- `TestRunFollowUpIssues` (6 tests): `implementer.run/gh_*/logger` → `follow_up.run/gh_*/logger`

## Pre-commit Issues Encountered

### Round 1: ruff auto-fixed 9 issues
- Import ordering (isort-style reordering of new imports)
- Unused import cleanup

### Round 2: mypy errors

1. **`"object" has no attribute "update_slot"`** in `pr_manager.py:148`
   - Fix: Changed `status_tracker: object | None` → `status_tracker: StatusTracker | None`
   - Added `from .status_tracker import StatusTracker`

2. **`Missing type parameters for generic type "dict"`** in `test_follow_up.py:90`
   - Fix: `list[dict]` → `list[dict[str, Any]]` in `_make_claude_output` helper

### Round 3: mypy still failing
After fixing #1: `type: ignore[union-attr]` became an `unused-ignore` error because the type
was now correctly narrowed. Removed the `# type: ignore` comment.

After fixing #2: `list[dict[str, Any]]` caused a new `arg-type` error at the call sites
because test data `[{"title": "T", "labels": ["bug"]}]` has type `list[dict[str, Sequence[str]]]`
which is narrower than `object`. Fix: changed `dict[str, object]` → `dict[str, Any]` and
added `from typing import Any` import.

### Round 4: All pass ✅

## Test Results

```
336 passed (automation unit tests)
4363 passed, 1 skipped (full unit suite)
75.56% overall coverage (threshold: 75%)
```

## Commands Used

```bash
# Check line count
wc -l scylla/automation/implementer.py

# Smoke tests
pixi run python -c "from scylla.automation.implementer import IssueImplementer; print('OK')"
pixi run python -c "from scylla.automation.retrospective import run_retrospective; print('OK')"
pixi run python -c "from scylla.automation.follow_up import parse_follow_up_items; print('OK')"
pixi run python -c "from scylla.automation.pr_manager import commit_changes; print('OK')"

# Pre-commit
SKIP=audit-doc-policy pre-commit run --files \
  scylla/automation/implementer.py \
  scylla/automation/retrospective.py \
  scylla/automation/follow_up.py \
  scylla/automation/pr_manager.py \
  tests/unit/automation/test_retrospective.py \
  tests/unit/automation/test_follow_up.py \
  tests/unit/automation/test_pr_manager.py \
  tests/unit/automation/test_implementer.py

# Full test suite
pixi run python -m pytest tests/unit/ -q --no-header
```
