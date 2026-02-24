---
name: create
description: "Create isolated git worktrees for parallel development"
user-invocable: false
---

# Worktree Create

Create separate working directories on different branches without stashing changes.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Enable parallel development on multiple issues | No stashing, no context switching overhead |

## When to Use

- (1) Starting work on a new issue
- (2) Need to work on multiple issues in parallel
- (3) Want to avoid stashing/context switching overhead
- (4) Testing changes across different branches

## Verified Workflow

1. **Create worktree** - Run create command with issue number and description
2. **Navigate** - `cd` to new worktree directory (parallel to main)
3. **Work normally** - Make changes, commit, push as usual
4. **Switch back** - `cd` to different worktree or main directory
5. **Clean up** - Remove worktree after PR merge (see cleanup skill)

## Results

Copy-paste ready commands:

```bash
# Create worktree for new branch
git worktree add ../ProjectName-42-implement-feature 42-implement-feature

# List all worktrees
git worktree list

# Example directory structure after creating worktrees:
# parent-directory/
# ├── ProjectName/                    # Main worktree (main branch)
# ├── ProjectName-42-feature/         # Issue #42 worktree
# ├── ProjectName-73-bugfix/          # Issue #73 worktree
# └── ProjectName-99-experiment/      # Experimental worktree
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Created worktree with branch already checked out | Git error: "fatal: 'branch' is already checked out" | Each branch can only be checked out in ONE worktree |
| Used existing directory name | Git error: directory already exists | Choose unique path or remove existing directory |
| Forgot to create remote branch first | Local-only branch, couldn't push | Create worktree from tracking branch or push after |
| Created worktree inside another worktree | Nested worktrees caused confusion | Always create worktrees as siblings in parent directory |

## Error Handling

| Error | Solution |
|-------|----------|
| Branch already exists | Use different branch name or delete old branch |
| Directory exists | Choose different location or remove directory |
| Cannot switch away | Ensure all changes are committed |
| Permission denied | Check directory permissions |

## Best Practices

- One worktree per issue (don't share branches)
- Use descriptive names: `<issue-number>-<description>`
- All worktrees share same `.git` directory
- Clean up after PR merge
- Each branch can only be checked out in ONE worktree

## Related Skills

- **switch** - Navigate between worktrees
- **sync** - Keep worktrees up-to-date with main
- **cleanup** - Remove worktrees after PR merge

## References

- Git docs: https://git-scm.com/docs/git-worktree
