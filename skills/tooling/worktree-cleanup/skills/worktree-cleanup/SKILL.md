---
name: worktree-cleanup
description: Remove merged or stale git worktrees. Use after PRs are merged, work is done, or when worktrees are no longer needed.
category: tooling
date: 2025-01-01
user-invocable: false
---

# Worktree Cleanup

## Overview

| Item | Details |
|------|---------|
| Name | worktree-cleanup |
| Category | tooling |
| Description | Remove merged or stale git worktrees. Use after PRs are merged, work is done, or when worktrees are no longer needed. |

## When to Use

- PR has been merged
- Worktree no longer needed
- Free disk space
- Maintain clean worktree list

## Quick Reference

```bash
# Remove single worktree by path
git worktree remove worktrees/<project-name>-42-feature

# Auto-clean all merged worktrees
./scripts/cleanup_merged_worktrees.sh
```

## Safety Checks

Before removing a worktree:

- Branch is merged to main (check GitHub PR status)
- No uncommitted changes (run `git status` in worktree)
- Not currently using the worktree (be in different directory)
- PR is actually merged (check "Development" section on issue)

## Error Handling

| Error | Solution |
|-------|----------|
| "Worktree has uncommitted changes" | Commit changes |
| "Not a worktree" | Verify path with `git worktree list` |
| "Worktree is main" | Don't remove primary worktree |

## Scripts Available

- `scripts/cleanup_merged_worktrees.sh` - Auto-clean merged worktrees

## References

- See `worktree-create` skill for creating worktrees

## Verified Workflow

1. **Verify state** - Check no uncommitted changes: `cd worktrees/<project-name>-42 && git status`
1. **Commit changes** - Make sure all changes are committed and the task is finished
1. **Switch away** - Don't be in the worktree you're removing
1. **Remove worktree** - Use git command
1. **Verify** - Run `git worktree list` to confirm removal

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| N/A | No recorded failures | N/A |

## Results & Parameters

See the workflow sections above for commands and expected outputs.

