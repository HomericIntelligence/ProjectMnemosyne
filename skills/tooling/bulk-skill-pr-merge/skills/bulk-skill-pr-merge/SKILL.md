---
name: bulk-skill-pr-merge
description: Bulk-merge many open skill PRs into main, including fixing failing CI and rebasing conflicts
category: tooling
date: 2026-03-03
user-invocable: false
---

# Bulk Skill PR Merge

## Overview

| Attribute | Value |
|-----------|-------|
| Date | 2026-03-03 |
| Objective | Merge 30 accumulated open skill PRs into main in one session |
| Outcome | Success — all 30 PRs merged; 6 needed CI fixes, 2 needed conflict resolution |

## When to Use

Use this skill when:
- 10+ open skill PRs have accumulated and need bulk merging
- Some PRs have failing CI from common plugin validation errors (missing `plugin.json`, invalid category, missing `version` field)
- Some PRs have become conflicted after other merges (linear history / rebase required)
- You need to triage which PRs can merge immediately vs. which need fixes first

**Trigger phrases:**
- "merge all open PRs"
- "bulk merge skill PRs"
- "clear the PR backlog"

## Verified Workflow

### Step 1: Triage PRs into two groups

```bash
# List all open PRs with CI status
gh pr list --state open --json number,title,headRefName,statusCheckRollup

# Or check individual PR checks
gh pr checks <PR_NUMBER>
```

Identify:
- **Group A**: PRs with passing CI → merge immediately
- **Group B**: PRs with failing CI → fix first

### Step 2: Merge Group A (passing CI)

Order by PR number (oldest first) to minimize rebase conflicts:

```bash
for pr in <PR_NUMBERS_IN_ORDER>; do
  echo "=== Merging PR #$pr ==="
  gh pr merge $pr --rebase --delete-branch 2>&1
done
```

**Note**: With `strict: false` on branch protection, PRs don't need to be up-to-date with main before merging. Merge all without rebasing between each one.

**Watch for**: `GraphQL: Pull Request is not mergeable` errors — these PRs became conflicted during the batch. Handle them in Step 4.

### Step 3: Diagnose and fix Group B (failing CI)

#### Common failure: Missing `plugin.json`

```bash
git switch skill/<category>/<name>
```

Create `.claude-plugin/plugin.json` using the SKILL.md frontmatter as source:

```json
{
  "name": "<from SKILL.md frontmatter>",
  "version": "1.0.0",
  "description": "<from SKILL.md frontmatter>",
  "category": "<from directory path>",
  "tags": ["<relevant>", "<tags>"],
  "date": "<from SKILL.md frontmatter>",
  "user-invocable": false
}
```

```bash
git add skills/<category>/<name>/.claude-plugin/plugin.json
git commit -m "fix: add missing .claude-plugin/plugin.json"
git push
```

#### Common failure: Missing `version` field

Add `"version": "1.0.0"` to the existing `plugin.json`.

#### Common failure: Invalid category

Valid categories: `architecture`, `ci-cd`, `debugging`, `documentation`, `evaluation`, `optimization`, `testing`, `tooling`, `training`

If the skill is in an invalid category (e.g., `automation`):
1. Change `"category"` in `plugin.json`
2. Change `category:` in `SKILL.md` frontmatter
3. The directory path does NOT need to change (validator checks field values, not path)

```bash
# Edit plugin.json and SKILL.md frontmatter, then:
git add skills/<wrong-category>/<name>/.claude-plugin/plugin.json
git add skills/<wrong-category>/<name>/skills/<name>/SKILL.md
git commit -m "fix: change invalid category '<wrong>' to '<valid>'"
git push
```

### Step 4: Rebase conflicted PRs

After bulk merging Group A, some PRs become conflicted. Rebase them onto updated main:

```bash
git switch main && git pull
git switch skill/<category>/<name>
git rebase origin/main
```

**If conflict in SKILL.md** (add/add or content conflict):

For skill SKILL.md files, both conflicting versions typically contain valid knowledge. Merge strategy:
- If HEAD version is more complete/expanded → keep HEAD (`resolve_keep_ours`)
- If both versions have unique content → manually merge both sections

```python
# Quick conflict resolver (run as python3 - <<'PYEOF' ... PYEOF)
def resolve_keep_ours(content):
    result = []
    lines = content.split('\n')
    in_ours = in_theirs = False
    for line in lines:
        if line.startswith('<<<<<<<'):
            in_ours, in_theirs = True, False
        elif line.startswith('=======') and in_ours:
            in_ours, in_theirs = False, True
        elif line.startswith('>>>>>>>') and in_theirs:
            in_theirs = False
        elif not in_theirs:
            result.append(line)
    return '\n'.join(result)
```

After resolving:
```bash
git add <conflicted-file>
git rebase --continue
git push --force-with-lease
```

Then merge the PR:
```bash
gh pr merge <PR_NUMBER> --rebase --delete-branch
```

### Step 5: Verify

```bash
# Confirm all target PRs are merged
for pr in <ALL_PR_NUMBERS>; do
  state=$(gh pr view $pr --json state --jq '.state')
  echo "PR #$pr: $state"
done

# Check remaining open PRs
gh pr list --state open
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| `git checkout <branch>` to switch branches | Blocked by Safety Net hook (positional args may overwrite files) | Always use `git switch <branch>` instead of `git checkout <branch>` for branch switching |
| Merging all 24 Group A PRs in one loop | 2 of 24 became `CONFLICTING` after earlier merges moved main forward | Expected behavior with linear history; handle conflicts in a separate step after the bulk merge |
| `gh pr merge` on already-merged PR | "Pull request was already merged" warning | GitHub sometimes auto-merges PRs when branch is pushed; check state before merging to avoid noise |
| Force-push without `--force-with-lease` | Risk of overwriting concurrent pushes | Always use `git push --force-with-lease` after rebase to fail safely if remote changed |

## Results & Parameters

### Session stats (2026-03-03)

| Metric | Value |
|--------|-------|
| Total PRs targeted | 30 |
| Group A (passing CI) | 24 |
| Group B (failing CI fixed) | 6 |
| Needed rebase | 2 |
| Successfully merged | 30 |

### CI failure breakdown

| Error type | Count | Fix |
|-----------|-------|-----|
| Missing `.claude-plugin/plugin.json` | 4 | Create with name/version/description/category/tags/date |
| Invalid category (`automation`) | 1 | Change to `tooling` in plugin.json and SKILL.md |
| Missing `version` field | 1 | Add `"version": "1.0.0"` |

### Merge command

```bash
gh pr merge $pr --rebase --delete-branch
```

### Check all target PRs merged

```bash
for pr in <SPACE_SEPARATED_PR_NUMBERS>; do
  echo "PR #$pr: $(gh pr view $pr --json state --jq '.state')"
done
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | 30 open skill PRs, 2026-03-03 | [notes.md](../references/notes.md) |
