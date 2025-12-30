---
name: worktree-switch
description: "Switch between git worktrees for parallel development"
category: debugging
source: ProjectOdyssey
date: 2025-12-30
---

# Worktree Switch

Navigate between isolated worktree directories quickly.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Fast context switching between issues | Zero stash overhead, instant switching |

## When to Use

- (1) Working on multiple issues simultaneously
- (2) Need to context switch without stashing
- (3) Testing different branches side-by-side
- (4) Comparing implementations

## Verified Workflow

1. **List worktrees** - See all available worktrees and their paths
2. **Navigate** - `cd` to desired worktree directory
3. **Verify** - Check `git branch` to confirm you're on right branch
4. **Work** - Make changes, commit normally
5. **Switch** - Move to different worktree with simple `cd`

## Results

Copy-paste ready commands:

```bash
# List all worktrees
git worktree list

# Switch worktree (simple cd)
cd ../ProjectName-42-feature

# Verify current worktree
git worktree list | grep "*"

# Check current branch
git branch --show-current

# Quick navigation with fzf (if installed)
cd $(git worktree list | fzf | awk '{print $1}')
```

### Terminal Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias wt='git worktree list'
alias wtcd='cd $(git worktree list | fzf | awk "{print \$1}")'
```

### Tmux Sessions

```bash
# Create persistent session per worktree
tmux new -s issue-42 -c ../ProjectName-42-feature

# Switch sessions
tmux attach -t issue-42

# List sessions
tmux list-sessions
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `git checkout` to switch branches | Git error: branch checked out in another worktree | Use `cd` to switch between worktrees, not git checkout |
| Forgot which worktree I was in | Made changes on wrong branch | Always check `git branch` or `pwd` after switching |
| Tried to check out same branch in two worktrees | Git prevents this by design | Each branch can only be checked out in ONE worktree |
| Used relative paths that broke after switching | cd commands failed | Use absolute paths or consistent relative paths |

## Best Practices

- One worktree per issue (don't share branches)
- Use clear naming: `<issue-number>-<description>`
- Keep worktrees organized in parent directory
- Use terminal multiplexer (tmux/screen) for persistent sessions
- Clean up completed worktrees (see worktree-cleanup)

## Limitations

- Each branch can only be checked out in ONE worktree
- Cannot be in worktree while removing it
- All worktrees share the same `.git` directory (some operations affect all)

## References

- See worktree-create for creating worktrees
- See worktree-cleanup for removing worktrees
- Git docs: https://git-scm.com/docs/git-worktree
