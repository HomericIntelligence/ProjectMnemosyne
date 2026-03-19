# Session Notes: fix-yaml-frontmatter-colon-bug

## Context

- **Issue**: #3929 — Fix same `partition(':')` bug in `ProjectMnemosyne/scripts/migrate_to_skills.py`
- **Parent fix**: PR #3928 — `fix(migrate): use yaml.safe_load() to handle colons in frontmatter values`
- **Parent issue**: #3310
- **Branch**: `3929-auto-impl`
- **Date**: 2026-03-15

## What Happened

### Problem

`extract_frontmatter()` in `ProjectMnemosyne/scripts/migrate_to_skills.py` (lines 65-68) used
`line.partition(":")` to parse YAML frontmatter. This silently truncated any value containing a
colon — e.g. `description: "Create PR linked to issue: #123"` would be parsed as
`description = "Create PR linked to issue"`.

The identical bug had already been fixed in `scripts/migrate_odyssey_skills.py` via PR #3928.

### Fix Applied

1. Added `import yaml` to `ProjectMnemosyne/scripts/migrate_to_skills.py`
2. Replaced the `for line in frontmatter_text.splitlines()` loop with `yaml.safe_load()`
3. Created 7 regression tests in `tests/scripts/test_migrate_to_skills_frontmatter.py`

### Key Discovery

The script is NOT tracked in the ProjectOdyssey git repo. It lives in a separate
`ProjectMnemosyne` repository, cloned locally at `~/ProjectMnemosyne/` and dynamically at
`build/<PID>/ProjectMnemosyne/` during skill commands. The fix must be committed to the
ProjectMnemosyne repo directly.

Tests in ProjectOdyssey use `importlib.util.spec_from_file_location()` with multiple candidate
paths (local checkout + PID-scoped build) and `pytest.mark.skipif` when neither is found.

### Tests

All 7 new tests passed:

```text
7 passed in 0.07s
```

Test cases:
- `test_plain_value` — baseline
- `test_colon_in_quoted_value` — regression case
- `test_colon_in_unquoted_value` — bare string with colon
- `test_no_frontmatter` — returns `{}`
- `test_unclosed_frontmatter` — returns `{}`
- `test_invalid_yaml_returns_empty_dict` — no exception raised
- `test_multiple_colons_in_value` — full value preserved

## Files Changed

- `ProjectMnemosyne/scripts/migrate_to_skills.py` — fix applied
- `tests/scripts/test_migrate_to_skills_frontmatter.py` — regression tests (ProjectOdyssey)

## PRs

- ProjectOdyssey PR #4832: test file
- ProjectMnemosyne PR: fix (on branch `3929-fix-extract-frontmatter-colon-bug`)