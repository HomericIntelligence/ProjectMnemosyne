# Raw Notes: fix-ci-broken-main-plugins

## Session Context

**Date**: 2026-02-22
**Repository**: ProjectMnemosyne (skills marketplace)
**Trigger**: 14 open PRs, all CI failing due to 3 broken plugins on main

## Root Cause Analysis

The `validate_plugins.py` script validates **all** plugins on main during every CI run.
If any plugin fails validation, the entire CI job fails — including for PRs that don't
touch plugins at all. Three plugins were breaking CI:

### Plugin 1: `plugins/ci-cd/ci-deprecation-enforcement/`

- **Problem**: Missing `.claude-plugin/plugin.json`
- **Problem**: `SKILL.md` started with `# Skill:` (no YAML frontmatter)
- **Problem**: `## Failed Attempts` section existed but had no `|` pipe table (only prose)
- **Fix**: Created `plugin.json`, prepended `---` frontmatter block, added table to Failed Attempts

### Plugin 2: `plugins/testing/config-filename-model-id-audit/`

- **Problem**: Missing `.claude-plugin/plugin.json`
- **Fix**: Created `plugin.json` (SKILL.md was already valid with frontmatter)

### Plugin 3: `plugins/testing/deprecation-warning-migration/`

- **Problem**: Missing `.claude-plugin/plugin.json`
- **Problem**: `SKILL.md` started with `# Skill:` (no YAML frontmatter)
- **Problem**: `## Failed Attempts` section had no `|` pipe table
- **Fix**: Created `plugin.json`, prepended frontmatter, added table to Failed Attempts

## Validation Script Requirements

From reading `scripts/validate_plugins.py`:

| Check | Severity | Field |
|-------|----------|-------|
| `.claude-plugin/plugin.json` exists | Error | Required |
| `name`, `version`, `description` fields present | Error | Required |
| `description` >= 20 chars | Error | Required |
| `name` matches `^[a-z0-9-]+$` | Error | Required |
| SKILL.md starts with `---` | Error | Required |
| `## Failed Attempts` section present | Error | Required |
| Failed Attempts contains `|` table | Warning | Recommended |
| `category` is one of 8 valid values | Error | If present |
| `date` matches `YYYY-MM-DD` | Error | If present |

## "Skipped Previously Applied Commits" — What It Means

During rebase, git reported:
```
note: skipped previously applied commit abc1234
hint: use --reapply-cherry-picks to include skipped commits
```

This means the commit's patch was already applied to the base branch (main). Git identifies
this by matching the patch diff content, not the commit SHA. When ALL commits on a branch
are skipped, the branch becomes identical to main → GitHub detects the PR has no diff → PR is auto-closed.

**4 PRs affected**: #132, #133, #134, #142

These PRs added skills to the flat `skills/` directory (not `plugins/`). Their content was
previously merged to main via a different path (likely another PR or direct commit).
Confirmed by checking `ls /home/mvillmow/ProjectMnemosyne/skills/`:
- `enforce-model-config-consistency-hook/` ✓ exists
- `config-default-model-drift/` ✓ exists
- `pydantic-frozen-consistency/` ✓ exists
- `skill-path-resolution-fix/` ✓ exists

## PR #145 — Stale Duplicate

The skill `fix-mypy-valid-type-errors` was already on main at
`skills/fix-mypy-valid-type-errors/`. PR #145 was a stale branch with merge
conflicts. Closed with:
```bash
gh pr close 145 --comment "Closing as duplicate - this skill was already merged to main."
```

## Exact File Changes Made

### Created files:
- `plugins/ci-cd/ci-deprecation-enforcement/.claude-plugin/plugin.json`
- `plugins/testing/config-filename-model-id-audit/.claude-plugin/plugin.json`
- `plugins/testing/deprecation-warning-migration/.claude-plugin/plugin.json`

### Modified files:
- `plugins/ci-cd/ci-deprecation-enforcement/skills/ci-deprecation-enforcement/SKILL.md`
  - Added 6-line YAML frontmatter block at top
  - Added `| Attempt | Why Failed | Lesson |` table to Failed Attempts section
- `plugins/testing/deprecation-warning-migration/skills/deprecation-warning-migration/SKILL.md`
  - Added 7-line YAML frontmatter block at top
  - Added `| Attempt | Why Failed | Lesson |` table to Failed Attempts section

## Git Commands Used

```bash
# Close duplicate PR
gh pr close 145 --comment "..."

# Validate locally
python3 scripts/validate_plugins.py plugins/

# Commit to main
git add plugins/...
git commit -m "fix(plugins): Add missing plugin.json and YAML frontmatter for 3 broken plugins"
git push origin main

# Rebase each branch
git fetch origin "$branch"
git checkout "$branch"
git rebase origin/main
git push --force-with-lease origin "$branch"

# Enable auto-merge
gh pr merge "$pr" --auto --rebase
```

## Final State

- 1 PR closed as duplicate (#145)
- 4 PRs auto-closed after rebase (content already on main): #132, #133, #134, #142
- 9 PRs open with auto-merge enabled: #131, #137, #138, #139, #152, #155, #158, #160, #165
