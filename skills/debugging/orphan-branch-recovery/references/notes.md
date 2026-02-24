# Session Notes: Orphan Branch Recovery

## Date: 2026-01-01

## Context

Branch `skill/debugging/fixme-todo-cleanup-v2` in ProjectMnemosyne-marketplace was reported as "completely diverged from main". Investigation revealed it was pushed from a different repository entirely (ProjectOdyssey).

## Investigation Steps

### 1. Initial Fetch and Analysis

```bash
git fetch origin skill/debugging/fixme-todo-cleanup-v2

# Check commits ahead of main - showed ProjectOdyssey commits
git log --oneline origin/main..origin/skill/debugging/fixme-todo-cleanup-v2 | head -20
# Output included: training, core, tests, mojo commits - wrong repo!

# Check commits behind main - showed all ProjectMnemosyne commits
git log --oneline origin/skill/debugging/fixme-todo-cleanup-v2..origin/main | head -20
# Output: All marketplace skill commits
```

### 2. Confirm No Common Ancestor

```bash
git merge-base origin/main origin/skill/debugging/fixme-todo-cleanup-v2
# Exit code 1, no output - confirmed no merge base
```

### 3. Identify Wrong Repository

```bash
# Check oldest commits
git log --oneline origin/skill/debugging/fixme-todo-cleanup-v2 | tail -10
# Output:
# c2c68b6e Initial commit
# fca85e8d feat: initial commit of the repository
# These are ProjectOdyssey's initial commits!

# Check files on branch
git ls-tree --name-only origin/skill/debugging/fixme-todo-cleanup-v2 | head -20
# Output included: .mojo-version, CONTRIBUTING.md, agent hierarchy
# These are ProjectOdyssey files, not marketplace files
```

### 4. Extract Valuable Content

The tip commit `9f65c6f3` did contain valid skill content:

```bash
git show origin/skill/debugging/fixme-todo-cleanup-v2 --name-only
# plugins/debugging/fixme-todo-cleanup/.claude-plugin/plugin.json
# plugins/debugging/fixme-todo-cleanup/skills/fixme-todo-cleanup/SKILL.md
# plugins/debugging/fixme-todo-cleanup/references/notes.md
```

### 5. Discovery: Skill Already Merged

Before recreating, checked if skill existed on main:

```bash
git log --oneline origin/main -- plugins/debugging/fixme-todo-cleanup/
# ada780a7 feat(skills): add fixme-todo-cleanup skill from retrospective
```

The skill was already merged! The `-v2` branch was a stale duplicate.

### 6. Resolution

```bash
# Delete the broken branch
git push origin --delete skill/debugging/fixme-todo-cleanup-v2

# No recreation needed - content already on main
```

## Root Cause

Someone ran `/retrospective` from within ProjectOdyssey's working directory but pushed to ProjectMnemosyne-marketplace's remote. This created a branch with ProjectOdyssey's entire history instead of branching from ProjectMnemosyne-marketplace's main.

## Prevention

1. Always verify you're in the correct repository before pushing
2. Check `git remote -v` matches expected repository
3. Use separate directories for different projects
4. The `/retrospective` command now clones the target repo to a build directory to avoid this issue

## Key Commands Reference

| Command | Purpose |
|---------|---------|
| `git merge-base A B` | Find common ancestor (empty = orphan) |
| `git log A..B` | Commits in B not in A |
| `git ls-tree --name-only ref` | List files at ref |
| `git show ref:path` | Extract file content |
| `git push origin --delete branch` | Delete remote branch |
