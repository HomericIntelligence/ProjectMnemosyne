---
name: git-worktree-workflow
description: "Git worktree workflow"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
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

---
name: switch
description: "Switch between git worktrees for parallel development"
user-invocable: false
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
- Clean up completed worktrees (see cleanup skill)

## Limitations

- Each branch can only be checked out in ONE worktree
- Cannot be in worktree while removing it
- All worktrees share the same `.git` directory (some operations affect all)

## Related Skills

- **create** - Create new worktrees
- **sync** - Keep worktrees up-to-date with main
- **cleanup** - Remove worktrees after PR merge

## References

- Git docs: https://git-scm.com/docs/git-worktree

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

---
name: cleanup
description: "Remove merged or stale git worktrees safely"
user-invocable: false
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

## Related Skills

- **create** - Create new worktrees
- **switch** - Navigate between worktrees
- **sync** - Keep worktrees up-to-date before cleanup

## References

- Git docs: https://git-scm.com/docs/git-worktree
