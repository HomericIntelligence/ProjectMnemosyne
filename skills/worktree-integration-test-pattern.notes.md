# Session Notes — worktree-integration-test-pattern

## Context

- **Issue**: ProjectOdyssey #3780 — Add regression test: `fix_remaining_warnings` applied to real worktree-create SKILL.md
- **Follow-up from**: #3230
- **Branch**: `3780-auto-impl`
- **PR**: ProjectOdyssey #4796

## Objective

Add integration tests (not just synthetic-fixture unit tests) for `fix_remaining_warnings.py`
that use the real `.claude/skills/worktree-create/SKILL.md` as a fixture and assert:

1. `has_orphan_quick_reference()` returns `True` before fix
2. `fix_skill_file()` returns `modified=True`
3. `has_orphan_quick_reference()` returns `False` after fix
4. Content round-trips correctly (no data loss)

## Key Challenge: Worktree Import Path

The `fix_remaining_warnings.py` script lives in the standardized location
`$HOME/.agent-brain/ProjectMnemosyne/scripts/` which is consistent across all environments.

### Solution

Use the standardized clone location directly:

```python
sys.path.insert(0, str(Path.home() / ".agent-brain" / "ProjectMnemosyne" / "scripts"))
```

This works from any worktree or regular checkout, since all clones use the same
`$HOME/.agent-brain/ProjectMnemosyne` location.

## Real Fixture

The real `worktree-create` SKILL.md has:
- `## Quick Reference` at top level (line 19) — an "orphan" needing to be demoted
- No `## Verified Workflow` section — so `add_verified_workflow_wrapper()` is triggered
- This makes it a perfect regression fixture: it exercises the actual fix path

## Test Results

All 6 tests passed:

```
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_fixture_file_exists PASSED
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_real_file_has_orphan_quick_reference PASSED
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_fix_skill_file_returns_modified_true PASSED
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_fix_skill_file_removes_orphan_quick_reference PASSED
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_round_trip_no_data_loss PASSED
tests/test_quick_reference_transform.py::TestRealWorktreeCreateIntegration::test_fix_skill_file_is_idempotent PASSED
6 passed in 0.02s
```