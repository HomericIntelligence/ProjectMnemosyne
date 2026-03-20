---
name: worktree-sync
description: Sync git worktrees with remote and main branch changes. Use to keep long-running
  feature branches up-to-date.
category: tooling
date: 2025-01-01
version: 1.0.0
user-invocable: false
---
# Worktree Sync

## Overview

| Item | Details |
|------|---------|
| Name | worktree-sync |
| Category | tooling |
| Description | Sync git worktrees with remote and main branch changes. Use to keep long-running feature branches up-to-date. |

## When to Use

- Long-running feature branches
- Main branch has new commits
- Before creating/updating PR
- Resolving merge conflicts
- Feature branch is diverged from main

### Quick Reference

```bash
# Fetch latest from remote (works in any worktree)
git fetch origin

# Update main worktree
cd ../<project-name> && git pull origin main

# Update feature worktree (rebase approach)
cd ../<project-name>-42-feature && git rebase origin/main

# Update feature worktree (merge approach)
cd ../<project-name>-42-feature && git merge origin/main

# Auto-sync all worktrees
./scripts/sync_all_worktrees.sh
```

## Rebase vs Merge

| Approach | Use When | Command |
|----------|----------|---------|
| Rebase | Linear history preferred | `git rebase origin/main` |
| Merge | Preserving branch history | `git merge origin/main` |

## Error Handling

| Error | Solution |
|-------|----------|
| Conflicts during rebase | Run `git status`, fix files, `git add .`, `git rebase --continue` |
| Diverged branches | Use `git pull --rebase origin main` |
| Uncommitted changes | Commit or stash before syncing |
| Detached HEAD | Check `git status` and `git checkout <branch>` |

## Conflict Resolution

```bash
# If conflicts occur
git status  # See conflicted files

# Edit files to resolve conflicts
# Then continue
git add .
git rebase --continue

# Or abort if something went wrong
git rebase --abort
```

## Best Practices

- Fetch regularly to catch conflicts early
- Sync before creating PR to avoid merge conflicts
- Keep feature branches short-lived (2-3 days max)
- Resolve conflicts immediately
- Use rebase for linear history (preferred for this project)

## References

- See `worktree-create` skill for creating worktrees
- [worktree-strategy.md](../../../notes/review/worktree-strategy.md)

## Verified Workflow

1. **Fetch remote** - `git fetch origin` (any worktree)
2. **Update main** - Navigate to main worktree, `git pull origin main`
3. **Update feature** - Navigate to feature worktree, `git rebase origin/main` or `git merge`
4. **Resolve conflicts** - If conflicts occur, fix files and `git rebase --continue`
5. **Verify** - Check `git log` to confirm main branch changes are included

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

See the workflow sections above for commands and expected outputs.

