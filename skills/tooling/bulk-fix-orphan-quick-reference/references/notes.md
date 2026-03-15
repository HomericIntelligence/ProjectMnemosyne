# Session Notes — bulk-fix-orphan-quick-reference

**Date**: 2026-03-15
**Issue**: ProjectOdyssey #3777
**PR**: ProjectOdyssey #4795

## Context

During implementation of `validate_plugins.py`, a new warning was added for SKILL.md files
where `## Quick Reference` appears as a top-level section alongside `## Verified Workflow`.
Running this validator against the existing `skills/` directory in ProjectMnemosyne surfaced
54 files with this structural issue.

`fix_remaining_warnings.py` already had `merge_quick_reference_into_verified_workflow()` to
fix this, but the `main()` function's hardcoded list of `plugins_with_workflow_warning` did
not include these 54 files.

## Key Discovery: Format Distinction

The critical insight was understanding two distinct SKILL.md formats:

- **Odyssey format** (`.claude/skills/`): Uses `## Workflow` — Quick Reference is a valid top-level section here per the SKILL_FORMAT_TEMPLATE.md
- **Mnemosyne format** (`skills/`): Uses `## Verified Workflow` — Quick Reference must be a `### subsection` of Verified Workflow

Running the fix against `.claude/skills/` correctly returned 0 hits because those files use
`## Workflow`, not `## Verified Workflow`.

## Implementation

Created `scripts/fix_quick_reference_batch.py` with:
- `has_orphan_quick_reference()` — regex check for top-level `## Quick Reference`
- `has_verified_workflow()` — regex check for `## Verified Workflow`
- `collect_affected_files()` — recursive scan filtering for both conditions
- `merge_quick_reference_into_verified_workflow()` — extract+demote+reinsert transformation
- `fix_skill_file()` — read/transform/write for single file
- `run_batch_fix()` — orchestrates batch with dry-run support
- `verify_no_warnings()` — second-pass check post-fix

## Test Gotcha

`assert "## Quick Reference" not in result` always fails because `### Quick Reference`
contains `## Quick Reference` as a substring. Must use:

```python
assert not re.search(r"^## Quick Reference", result, re.MULTILINE)
```

## Files Created

- `scripts/fix_quick_reference_batch.py` (ProjectOdyssey)
- `tests/scripts/test_fix_quick_reference_batch.py` (33 tests, all passing)
