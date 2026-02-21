# Notes

Migrated from plugins/uncategorized/skills/gh-implement-issue/ on 2026-01-02.

## Canonical Source

`preflight_check.sh` lives in the canonical ProjectScylla location:

```
tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh
```

Absolute path in ProjectScylla:
`/home/mvillmow/ProjectScylla/tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh`

## Skill Directory Resolution

The `<skill-dir>` placeholder in Quick Reference commands resolves to the absolute path of
the `gh-implement-issue` skill directory. Resolve it at runtime with:

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "${SKILL_DIR}/scripts/preflight_check.sh" <issue>
```

For ProjectScylla users, `<skill-dir>` is typically:
`tests/claude-code/shared/skills/github/gh-implement-issue`

## Sync History

- 2026-02-21: Added preflight_check.sh sections (pre-flight step in Quick Reference,
  Workflow step 1, Pre-Flight Check Results table, pre-flight Error Handling rows,
  issue-preflight-check reference). Path fixed from relative `bash scripts/` to
  `bash <skill-dir>/scripts/` (issue #801).
