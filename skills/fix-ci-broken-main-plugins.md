---
name: fix-ci-broken-main-plugins
description: Fix broken CI on main caused by plugins missing plugin.json or SKILL.md
  YAML frontmatter, then rebase all blocked PRs
category: debugging
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Skill: fix-ci-broken-main-plugins

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Fix broken CI on main (3 plugins missing plugin.json/frontmatter), rebase 13 PRs, enable auto-merge |
| Outcome | Success — all validations pass, 9 open PRs rebased and auto-merge enabled, 4 PRs auto-closed (content already on main) |

## When to Use

Use this skill when:

- All PR CI runs fail with plugin validation errors (even PRs that don't touch plugins)
- A plugin directory exists but has no `.claude-plugin/plugin.json`
- `SKILL.md` exists but does not start with `---` (missing YAML frontmatter block)
- CI error is `SKILL.md missing YAML frontmatter (must start with ---)` or `Missing .claude-plugin/plugin.json`
- Many PRs are blocked by a root-cause CI failure on main

**Don't use when:**

- CI fails on an individual PR branch (not a main-branch root cause)
- The plugin.json exists but has incorrect field values (different fix needed)

## Verified Workflow

### 1. Identify broken plugins

Run the validator locally to find all failures:

```bash
python3 scripts/validate_plugins.py plugins/
```

Look for `FAIL:` entries. Common errors:
- `Missing .claude-plugin/plugin.json`
- `SKILL.md missing YAML frontmatter (must start with ---)`
- `Missing Failed Attempts section (REQUIRED)`

### 2. Create missing plugin.json files

Required fields: `name`, `version`, `description` (minimum 20 chars).

```json
{
  "name": "<plugin-name>",
  "version": "1.0.0",
  "description": "<40+ char description with trigger conditions>",
  "skills": "./skills",
  "tags": ["tag1", "tag2"]
}
```

Create the `.claude-plugin/` directory first:

```bash
mkdir -p plugins/<category>/<name>/.claude-plugin/
```

### 3. Add YAML frontmatter to SKILL.md

Insert at the very top of the file (line 1 must be `---`):

```markdown
---
name: "<skill-name>"
description: "<description>"
category: <category>
date: <YYYY-MM-DD>
user-invocable: false
---
# Skill: <skill-name>
```

### 4. Add Failed Attempts table if missing

The validator warns (not errors) if `## Failed Attempts` has no `|` table.
Add a minimal table immediately after the section header:

```markdown
## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| <attempt> | <reason> | <lesson> |
```

### 5. Validate locally before pushing

```bash
python3 scripts/validate_plugins.py plugins/
```

Must show `ALL VALIDATIONS PASSED` before committing to main.

### 6. Commit and push fixes to main

```bash
git add plugins/<category>/<name>/.claude-plugin/plugin.json \
        plugins/<category>/<name>/skills/<name>/SKILL.md
git commit -m "fix(plugins): Add missing plugin.json and YAML frontmatter for broken plugins"
git push origin main
```

### 7. Rebase all open PR branches

After main is fixed, rebase each open PR branch sequentially:

```bash
gh pr list --state open --json number,headRefName --jq '.[].headRefName' | while read branch; do
  git fetch origin "$branch"
  git checkout "$branch"
  git rebase origin/main
  git push --force-with-lease origin "$branch"
done
git checkout main
```

**Expected**: Some branches may have "skipped previously applied commits" — this means their content was already on main. Those PRs will auto-close (this is correct behavior, not an error).

### 8. Enable auto-merge on remaining open PRs

```bash
gh pr list --state open --json number --jq '.[].number' | while read pr; do
  gh pr merge "$pr" --auto --rebase
done
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Pushing plugin.json without running validate first | Would have missed that SKILL.md frontmatter was also required | Always run `validate_plugins.py` locally before pushing to main |
| Enabling auto-merge on PRs that were already closed | `gh pr merge --auto` fails with `Pull request is closed` error | Check PR state first; closed-not-merged PRs had content already on main |
| Assuming "skipped previously applied commits" is an error | Those branches became empty and auto-closed — the content WAS already on main | Verify skills directory before investigating further |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Plugins fixed | 3 (ci-deprecation-enforcement, config-filename-model-id-audit, deprecation-warning-migration) |
| PRs rebased | 13 branches processed |
| PRs auto-closed (content already on main) | 4 (#132, #133, #134, #142) |
| PRs with auto-merge enabled | 9 |
| PR closed as duplicate | 1 (#145) |
| Validation result after fix | ALL VALIDATIONS PASSED |

### Minimum plugin.json (required fields only)

```json
{
  "name": "kebab-case-name",
  "version": "1.0.0",
  "description": "At least 20 characters describing trigger conditions",
  "skills": "./skills"
}
```

### YAML frontmatter template

```yaml
---
name: "skill-name"
description: "Short description"
category: <one of: training|evaluation|optimization|debugging|architecture|tooling|ci-cd|testing>
date: YYYY-MM-DD
user-invocable: false
---
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Fixed 3 broken plugins blocking all PR CI | [notes.md](../references/notes.md) |
