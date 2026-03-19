---
name: skills-to-plugins-migration
description: Migrate PRs that add skills to the flat skills/ directory into the correct
  plugins/<category>/<name>/ structure so CI triggers and the validate check passes.
  Use when a PR branch puts files under skills/ instead of plugins/, or when the validate
  CI check never appears on a PR.
category: ci-cd
date: 2026-02-22
version: 1.0.0
user-invocable: true
---
# Skills-to-Plugins Migration

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-22 |
| Objective | Migrate 5 open PRs from flat `skills/` directory to `plugins/<category>/<name>/` so CI triggers and PRs can merge |
| Outcome | All 5 PRs migrated, validated, pushed, and merged successfully |

## When to Use

- A PR branch adds files under `skills/<name>/` instead of `plugins/<category>/<name>/`
- The `validate` CI status check never appears on a PR (CI path filter doesn't match)
- Branch protection requires the `validate` check but it's missing because files are in `skills/`
- A skill PR has been open for a long time with no CI feedback

**Root cause**: CI workflow has a path filter like `paths: ['plugins/**']`. Files committed to `skills/` never trigger the workflow, so the `validate` check is never posted, and the PR cannot merge through branch protection.

## Verified Workflow

### Step 1: Identify affected PRs

```bash
# List all open PRs
gh pr list --limit 50 --json number,title,headRefName,state

# For each suspicious PR, check what files it changes
gh pr diff <PR_NUMBER> --name-only | head -20
```

PRs that show `skills/<name>/SKILL.md` instead of `plugins/<category>/<name>/...` are affected.

### Step 2: For each PR — inspect the existing content

```bash
git switch <branch-name>
git rebase origin/main  # Bring up to date first

# Check what files exist
find skills/ -type f 2>/dev/null
```

Read the existing SKILL.md and plugin.json (if present) to understand the content before migrating.

### Step 3: Create the correct plugin structure

```bash
CATEGORY=<category>   # See valid categories below
NAME=<skill-name>

mkdir -p plugins/$CATEGORY/$NAME/.claude-plugin
mkdir -p plugins/$CATEGORY/$NAME/skills/$NAME
mkdir -p plugins/$CATEGORY/$NAME/references
```

**Valid categories**: `training`, `evaluation`, `optimization`, `debugging`, `architecture`, `tooling`, `ci-cd`, `testing`, `documentation`

### Step 4: Create plugin.json (standard fields only)

```json
{
  "name": "<skill-name>",
  "version": "1.0.0",
  "description": "<trigger conditions — what problem does this solve? when should it be used?>",
  "category": "<category>",
  "date": "YYYY-MM-DD",
  "tags": ["tag1", "tag2"]
}
```

**Do NOT include non-standard fields**: `skill_name`, `created_date`, `use_cases`, `prerequisites`, `success_metrics`, `workflow_summary`, `key_commands`, `lessons_learned`, `outcomes`, `trigger_conditions`, `author`, `source`.

### Step 5: Create/fix SKILL.md

Required frontmatter and sections:

```markdown
---
name: <skill-name>
description: <same as plugin.json description>
category: <category>
date: YYYY-MM-DD
user-invocable: true
---

# Skill: <Title>

## Overview

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Objective | ... |
| Outcome | ... |

## When to Use
...

## Verified Workflow
...

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| ... | ... | ... |

## Results & Parameters
...
```

**Critical requirements**:
- SKILL.md must start with `---` (YAML frontmatter)
- `## Failed Attempts` must contain a pipe table with `|` — prose-only sections get a warning
- Section header must be exactly `## Failed Attempts` (not `## Failed Approaches`, `## Failed Attempts / Pitfalls`, etc.)

### Step 6: Copy references if they exist

```bash
# If the original skill had a references/ directory
cp skills/<name>/references/*.md plugins/<category>/<name>/references/
```

### Step 7: Remove old files and validate

```bash
git rm -r skills/<name>/

# Validate — must pass before pushing
python3 scripts/validate_plugins.py plugins/
```

### Step 8: Special case — restored clobbered root plugin.json

If the PR branch overwrote `.claude-plugin/plugin.json` at the repo root (which belongs to a different plugin), restore it:

```bash
git show origin/main:.claude-plugin/plugin.json > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
```

### Step 9: Commit and force push

```bash
git add plugins/<category>/<name>/
git commit -m "refactor(skills): Migrate <name> to plugins/<category>/<name>/ structure

- Move from flat skills/ to plugins/<category>/<name>/
- Add YAML frontmatter to SKILL.md
- Add Overview table
- Convert Failed Attempts to pipe table format
- [List any other fixes]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push --force-with-lease origin <branch-name>
```

### Step 10: Enable auto-merge after pushing

```bash
gh pr merge <PR_NUMBER> --auto --rebase
```

Or batch all at once after all migrations:

```bash
for pr in <pr1> <pr2> <pr3>; do
  gh pr merge "$pr" --auto --rebase
done
```

## Failed Attempts

| Attempt | What Happened | Why It Failed |
|---------|--------------|---------------|
| Using category `vcs` in plugin.json | `validate_plugins.py` rejected the plugin | `vcs` is not in the approved category list — use `tooling` for VCS-related skills |
| Leaving prose-only Failed Attempts section | Validator issued a warning | `## Failed Attempts` requires a pipe table (`|`) — convert subsections to table rows |
| Not restoring root `.claude-plugin/plugin.json` | Root plugin would have wrong content (the PR's plugin) | Some branches clobber this file; always check `git diff origin/main .claude-plugin/plugin.json` |
| Using `git checkout` to switch branches | Safety net blocks multi-argument `git checkout` | Use `git switch <branch>` instead |
| Bare `git push --force` | Risky — overwrites remote changes without checking | Always use `--force-with-lease` |

## Results & Parameters

### Category mapping for common invalid values

| Invalid | Use Instead |
|---------|-------------|
| `vcs` | `tooling` |
| `documentation` | `documentation` (valid — was missing from some lists) |
| `research` | `evaluation` or `architecture` |
| `workflow` | `tooling` or `ci-cd` |

### Validator quick check

```bash
# Run on all plugins (fast, ~1 second)
python3 scripts/validate_plugins.py plugins/

# Expected output for success:
# ALL VALIDATIONS PASSED
```

### PR migration checklist

For each PR:
- [ ] `git switch <branch>` + `git rebase origin/main`
- [ ] Read existing SKILL.md and plugin.json content
- [ ] Create `plugins/<category>/<name>/.claude-plugin/plugin.json` (standard fields only)
- [ ] Create `plugins/<category>/<name>/skills/<name>/SKILL.md` with frontmatter + all required sections
- [ ] Copy `references/` files if they exist
- [ ] `git rm -r skills/<name>/`
- [ ] Restore root `.claude-plugin/plugin.json` if clobbered (PR #155 pattern)
- [ ] `python3 scripts/validate_plugins.py plugins/` — ALL VALIDATIONS PASSED
- [ ] `git push --force-with-lease origin <branch>`
- [ ] `gh pr merge <n> --auto --rebase`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PRs #155, #158, #160, #165, #167 — all 5 migrated and merged | [notes.md](../../references/notes.md) |
