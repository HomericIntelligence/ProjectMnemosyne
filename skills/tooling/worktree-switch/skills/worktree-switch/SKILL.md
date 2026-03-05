---
name: worktree-switch
description: Switch between git worktrees for parallel development. Use when working on multiple issues simultaneously.
category: tooling
date: 2025-01-01
user-invocable: false
---

# Worktree Switch

## Overview

| Item | Details |
|------|---------|
| Name | worktree-switch |
| Category | tooling |
| Description | Switch between git worktrees for parallel development. Use when working on multiple issues simultaneously. |

## When to Use

- Working on multiple issues
- Need to context switch without stashing
- Testing different branches side-by-side
- Comparing implementations

## Quick Reference

```bash
# List all worktrees
git worktree list

# Switch worktree (simple cd)
cd ../<project-name>-42-feature

# Verify current worktree
git worktree list | grep "*"

# Switch by issue number (script)
./scripts/switch_worktree.sh 42
```

## Common Patterns

### Terminal Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias wt='git worktree list'
alias wtcd='cd $(git worktree list | fzf | awk "{print \$1}")'
```

### Tmux Sessions

```bash
# Create persistent session per worktree
tmux new -s issue-42 -c ../<project-name>-42-feature

# Switch sessions
tmux attach -t issue-42

# List sessions
tmux list-sessions
```

## Best Practices

- One worktree per issue (don't share branches)
- Use clear naming: `<issue-number>-<description>`
- Keep worktrees organized in parent directory
- Use terminal multiplexer (tmux/screen) for persistent sessions
- Clean up completed worktrees (see `worktree-cleanup` skill)

## Limitations

- Each branch can only be checked out in ONE worktree
- Cannot be in worktree while removing it
- All worktrees share the same `.git` directory (some operations affect all)

## References

- See `worktree-create` skill for creating worktrees
- See `worktree-cleanup` skill for removing worktrees
- [worktree-strategy.md](../../../notes/review/worktree-strategy.md)

## Verified Workflow

1. **List worktrees** - See all available worktrees and their paths
2. **Navigate** - `cd` to desired worktree directory
3. **Verify** - Check `git branch` to confirm you're on right branch
4. **Work** - Make changes, commit normally
5. **Switch** - Move to different worktree with simple `cd`

## Failed Attempts

| Attempt | Why Failed | Lesson Learned |
|---------|-----------|----------------|
| N/A | No recorded failures | N/A |

## Results & Parameters

See the workflow sections above for commands and expected outputs.

