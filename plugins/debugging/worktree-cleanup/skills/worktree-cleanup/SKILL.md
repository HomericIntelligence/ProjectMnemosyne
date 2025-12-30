---
name: worktree-cleanup
description: "Remove merged or stale git worktrees safely"
category: debugging
source: ProjectOdyssey
date: 2025-12-30
---

# Worktree Cleanup

Remove worktrees safely to free disk space and maintain organization.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Clean up worktrees after PR merge | Reduced disk usage, cleaner worktree list |

## When to Use

- (1) PR has been merged
- (2) Worktree no longer needed
- (3) Freeing disk space
- (4) Maintaining clean worktree list

## Verified Workflow

1. **Verify state** - Check no uncommitted changes: `cd worktree && git status`
2. **Commit changes** - Make sure all changes are committed and task is finished
3. **Switch away** - Don't be in the worktree you're removing
4. **Remove worktree** - Use git command
5. **Verify** - Run `git worktree list` to confirm removal

## Results

Copy-paste ready commands:

```bash
# List all worktrees
git worktree list

# Remove single worktree by path
git worktree remove ../ProjectName-42-feature

# Force remove (if uncommitted changes exist - USE WITH CAUTION)
git worktree remove --force ../ProjectName-42-feature

# Prune stale worktree entries
git worktree prune

# Delete local branch after worktree removal
git branch -d 42-feature

# Delete remote branch
git push origin --delete 42-feature
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Removed worktree with uncommitted changes | Lost work (uncommitted changes deleted) | Always commit or stash before cleanup |
| Removed worktree while still in it | Git error: cannot remove current worktree | Switch to different directory first |
| Deleted directory without git worktree remove | Left orphan worktree entry in .git | Always use `git worktree remove`, then prune |
| Forgot to delete branch after worktree removal | Branch clutter in local repo | Delete local and remote branches after |

## Safety Checks

Before removing a worktree:

- Branch is merged to main (check GitHub PR status)
- No uncommitted changes (run `git status` in worktree)
- Not currently using the worktree (be in different directory)
- PR is actually merged (check "Development" section on issue)

## Error Handling

| Error | Solution |
|-------|----------|
| "Worktree has uncommitted changes" | Commit or stash changes first |
| "Not a worktree" | Verify path with `git worktree list` |
| "Worktree is main" | Don't remove primary worktree |
| "Cannot remove locked worktree" | Unlock with `git worktree unlock` |

## References

- See worktree-create for creating worktrees
- See worktree-sync for syncing before cleanup
- Git docs: https://git-scm.com/docs/git-worktree
