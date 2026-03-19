# Git Worktree Workflow - Notes

## Plugin Overview

This plugin consolidates 4 related worktree skills into a single coherent workflow:

1. **create** - Create new worktrees for parallel development
2. **switch** - Navigate between worktrees
3. **sync** - Keep worktrees synchronized with main
4. **cleanup** - Remove worktrees after PR merge

## Typical Workflow

```
1. git worktree add ../Project-42-feature 42-feature  (create)
2. cd ../Project-42-feature                           (switch)
3. [make changes, commit, push]
4. git fetch && git rebase origin/main                (sync)
5. git push --force-with-lease
6. [PR merged]
7. git worktree remove ../Project-42-feature          (cleanup)
```

## Key Insight

The biggest advantage of worktrees is **zero stash overhead**. Each branch has its own directory, so switching is just `cd`, not `git stash && git checkout && git stash pop`.

## Consolidated From

This plugin was created by merging:
- `debugging/worktree-create`
- `debugging/worktree-switch`
- `debugging/worktree-sync`
- `debugging/worktree-cleanup`

Moved to `tooling/` category because worktrees are a workflow tool, not a debugging tool.

## Source

- ProjectOdyssey development workflow
- Date: 2025-12-30
