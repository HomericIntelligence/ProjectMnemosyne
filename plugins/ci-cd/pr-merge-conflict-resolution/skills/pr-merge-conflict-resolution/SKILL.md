---
name: pr-merge-conflict-resolution
description: "Systematic workflow for rebasing PRs and resolving merge conflicts. Use when PR branch is behind main with conflicts."
user-invocable: false
---

# PR Merge Conflict Resolution

Workflow for rebasing pull request branches and resolving merge conflicts efficiently.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | Rebase ProjectOdyssey PR #3097 with 23 merge conflicts |
| Outcome | Successfully rebased and force-pushed with all conflicts resolved |
| Time | ~15 minutes for 23 conflicts |

## When to Use

- PR branch is behind main with merge conflicts
- Bulk-fixing similar conflicts across many files (e.g., YAML frontmatter)
- Resolving conflicts between new field additions and existing fields
- Need to merge changes from two competing feature branches

## Verified Workflow

### 1. Check PR Status

```bash
# Get PR merge status
gh pr view <PR_NUMBER> --repo <owner>/<repo> --json mergeable,mergeStateStatus

# Example output:
# {"mergeable": "CONFLICTING", "mergeState": "DIRTY"}
```

### 2. Clone and Checkout PR Branch

```bash
# Clone repository
git clone https://github.com/<owner>/<repo>.git repo-work
cd repo-work

# Fetch and checkout PR branch
git fetch origin <branch-name>
git checkout <branch-name>
```

### 3. Attempt Rebase

```bash
# Fetch latest main
git fetch origin main

# Attempt rebase
git rebase origin/main
```

This will show conflicts:
```
Auto-merging file1.md
CONFLICT (content): Merge conflict in file1.md
...
error: could not apply <sha>... <commit message>
```

### 4. Identify Conflict Pattern

List all conflicted files:
```bash
git diff --name-only --diff-filter=U
```

Check conflict structure in one file:
```bash
git diff --diff-filter=U <file> | head -30
```

**Common patterns**:
- Frontmatter field additions: `<<<<<<< HEAD\nagent: value\n=======\nuser-invocable: false`
- Line breaks: `<<<<<<< HEAD\nlong line\n=======\nbroken\nline`

### 5. Bulk-Fix Conflicts (For Similar Patterns)

**Pattern A: Merge two fields (keep both)**

When conflict is between two new fields:
```bash
# Example: Keep both agent and user-invocable fields
for file in $(git diff --name-only --diff-filter=U); do
  sed -i '/<<<<<<< HEAD/,/>>>>>>> /c\
agent: test-engineer\
user-invocable: false' "$file" 2>/dev/null && echo "Fixed: $file"
done
```

**Pattern B: Choose one side**

Keep HEAD version:
```bash
git checkout --ours <file>
git add <file>
```

Keep incoming version:
```bash
git checkout --theirs <file>
git add <file>
```

### 6. Fix Remaining Conflicts Manually

For files needing manual review:
```bash
# Read conflicted file
cat <file> | grep -A5 -B5 "<<<<<<< HEAD"

# Edit file to resolve conflict
# Remove conflict markers and choose correct resolution
```

### 7. Stage Resolved Files

```bash
# Stage all resolved files
git add .

# Verify no conflicts remain
git diff --name-only --diff-filter=U | wc -l
# Should output: 0
```

### 8. Continue Rebase

```bash
# If conflicts resolved
git rebase --continue

# If more commits to rebase, repeat steps 4-7
```

**Common errors**:

| Error | Solution |
|-------|----------|
| `you have staged changes in your working tree` | Run `git commit --no-edit` then `git rebase --continue` |
| `fatal: You are in the middle of a cherry-pick` | Don't use `--amend`, just `git commit --no-edit` |
| New conflicts on next commit | Repeat steps 4-7 for new conflicts |

### 9. Force Push Rebased Branch

```bash
# Check commit history looks correct
git log --oneline -5

# Force push (overwrites remote branch)
git push --force-with-lease origin <branch-name>
```

**CRITICAL**: Only force-push to feature branches, NEVER to main!

### 10. Verify CI Starts

```bash
# Check CI is running
gh pr view <PR_NUMBER> --repo <owner>/<repo> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.status == "IN_PROGRESS") | .name'

# Add comment to PR
gh pr comment <PR_NUMBER> --repo <owner>/<repo> --body "✅ Rebased against main and resolved conflicts"
```

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| Created Python script for conflict resolution | User rejected, wanted direct fix | Use shell commands directly for transparency and speed |
| Used `git commit --amend` during rebase | Wrong command - amend fails during cherry-pick | Use `git commit --no-edit` during rebase, not `--amend` |
| Tried to use `--disallowedTools` field | Field not supported in Claude Code v2.1.0 | Always verify features exist before implementing |
| Single sed command for all file types | Some files needed different patterns | Categorize files by conflict pattern before bulk-fixing |

## Results & Parameters

### Bulk Conflict Resolution Template

```bash
# For YAML frontmatter conflicts (keep both fields)
for file in $(git diff --name-only --diff-filter=U); do
  sed -i '/<<<<<<< HEAD/,/>>>>>>> /c\
field1: value1\
field2: value2' "$file" 2>/dev/null && echo "Fixed: $file"
done

# Stage and continue
git add .
git rebase --continue
```

### Force Push Checklist

- [ ] Verify branch is feature branch (NOT main)
- [ ] Check commit history: `git log --oneline -5`
- [ ] Confirm all conflicts resolved: `git diff --name-only --diff-filter=U`
- [ ] Use `--force-with-lease` for safety
- [ ] Comment on PR after push

### Common Rebase Commands

```bash
# Start rebase
git rebase origin/main

# Abort if something goes wrong
git rebase --abort

# Skip a commit (if it's already applied)
git rebase --skip

# Continue after resolving conflicts
git rebase --continue

# Check rebase status
git status
```

### Sed Pattern for Frontmatter Conflicts

```bash
# Template: Replace conflict markers with resolved content
sed -i '/<<<<<<< HEAD/,/>>>>>>> /c\
line1\
line2\
line3' file.md

# Example: Merge agent and user-invocable fields
sed -i '/<<<<<<< HEAD/,/>>>>>>> /c\
agent: test-engineer\
user-invocable: false' skill.md
```

**Note**: The `\` at end of each line is required for multi-line replacement.

## Key Insights

1. **Bulk-fix similar patterns**: When 20+ files have identical conflicts, use sed/awk to fix all at once

2. **Check conflict structure first**: Read 1-2 files to understand pattern before bulk operations

3. **--force-with-lease is safer**: Protects against overwriting changes others pushed

4. **Don't amend during rebase**: Use `git commit --no-edit` when rebase asks for commit

5. **Verify CI runs after force push**: Ensure GitHub triggers new CI run

6. **Comment on PR**: Let reviewers know branch was rebased

7. **Close obsolete PRs early**: If feature already in main, close PR instead of rebasing

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3097 - user-invocable field | 23 conflicts, 74 files changed |

## References

- [Git Rebase Documentation](https://git-scm.com/docs/git-rebase)
- [GitHub CLI PR Commands](https://cli.github.com/manual/gh_pr)
- Related skill: git-worktree-workflow (branch management)
