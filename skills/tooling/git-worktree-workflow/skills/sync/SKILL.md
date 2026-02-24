---
name: sync
description: "Sync git worktrees with remote and main branch changes"
user-invocable: false
---

# Worktree Sync

Keep worktrees synchronized with remote changes.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Keep feature branches up-to-date with main | Avoid merge conflicts, clean PR history |

## When to Use

- (1) Long-running feature branches need updates
- (2) Main branch has new commits
- (3) Before creating/updating PR to avoid conflicts
- (4) Feature branch is diverged from main

## Verified Workflow

1. **Fetch remote** - `git fetch origin` (any worktree)
2. **Update main** - Navigate to main worktree, `git pull origin main`
3. **Update feature** - Navigate to feature worktree, `git rebase origin/main`
4. **Resolve conflicts** - If conflicts occur, fix files and `git rebase --continue`
5. **Verify** - Check `git log` to confirm main branch changes are included

## Results

Copy-paste ready commands:

```bash
# Fetch latest from remote (works in any worktree)
git fetch origin

# Update main worktree
cd ../ProjectName && git pull origin main

# Update feature worktree (rebase approach - preferred)
cd ../ProjectName-42-feature && git rebase origin/main

# Update feature worktree (merge approach)
cd ../ProjectName-42-feature && git merge origin/main

# Force push after rebase (required)
git push --force-with-lease origin 42-feature
```

### Conflict Resolution

```bash
# If conflicts occur during rebase
git status  # See conflicted files

# Edit files to resolve conflicts
# Then continue
git add .
git rebase --continue

# Or abort if something went wrong
git rebase --abort
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Rebased while other worktree had same branch | Caused branch divergence, confusing state | Coordinate rebase across worktrees - only one should have the branch |
| Forgot `--force-with-lease` after rebase | Push rejected: "non-fast-forward" | Rebase rewrites history, requires force push |
| Rebased with uncommitted changes | Git refused to start rebase | Commit or stash changes before rebasing |
| Used `git pull` instead of `fetch + rebase` | Created merge commits instead of linear history | Use `git fetch` + `git rebase` for clean history |

## Rebase vs Merge

| Approach | Use When | Command |
|----------|----------|---------|
| Rebase | Linear history preferred (recommended) | `git rebase origin/main` |
| Merge | Preserving branch history | `git merge origin/main` |

## Error Handling

| Error | Solution |
|-------|----------|
| Conflicts during rebase | Run `git status`, fix files, `git add .`, `git rebase --continue` |
| Diverged branches | Use `git pull --rebase origin main` |
| Uncommitted changes | Commit or stash before syncing |
| Detached HEAD | Check `git status` and `git checkout <branch>` |

## Best Practices

- Fetch regularly to catch conflicts early
- Sync before creating PR to avoid merge conflicts
- Keep feature branches short-lived (2-3 days max)
- Resolve conflicts immediately
- Use rebase for linear history (preferred)

## Related Skills

- **create** - Create new worktrees
- **switch** - Navigate between worktrees
- **cleanup** - Remove worktrees after PR merge

## References

- Git docs: https://git-scm.com/docs/git-rebase
