---
name: git-worktree-mass-cleanup
description: "Remove all git worktrees in bulk, distinguishing merged vs active PRs, cleaning untracked dirs, and switching main checkout to main. Use when: accumulated worktrees need purging after parallel development, or resetting repo to clean single-checkout state."
category: tooling
date: 2026-03-06
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | git-worktree-mass-cleanup |
| **Category** | tooling |
| **Complexity** | Medium |
| **Risk** | Medium — force-removes worktrees with uncommitted changes |
| **Time** | 2-5 minutes for 30+ worktrees |

Removes all git worktrees accumulated during parallel development sessions, categorizing them by
status (merged/stale vs active open PRs), cleaning untracked directories that block removal,
and finally switching the main repo checkout to `main`.

## When to Use

- After a parallel auto-implementation session leaves 20+ worktrees behind
- Resetting a repository to a single clean checkout
- Removing worktrees whose remote branches are `[gone]` (PR was merged/closed)
- Cleaning up before switching development focus

## Verified Workflow

### Phase 1: Audit Worktrees

```bash
# List all worktrees with branch status
git worktree list

# Check tracking status (identifies [gone] = remote deleted = merged)
git branch -v
```

### Phase 2: Remove Stale Worktrees (Merged PRs)

Clean untracked directories that block `git worktree remove`, then remove:

```bash
# Clean blockers first
for issue in <list>; do
  wt=".worktrees/issue-$issue"
  rm -rf "$wt/ProjectMnemosyne" "$wt/.issue_implementer"
done

# Remove worktrees
for issue in <list>; do
  git worktree remove ".worktrees/issue-$issue"
done

# Delete local branches — use -D because rebase-merged PRs show as "not fully merged"
for issue in <list>; do
  git branch -D "${issue}-auto-impl"
done
```

**Key insight**: `git branch -d` fails for rebase-merged PRs (they lack a merge commit).
Always use `git branch -D` for branches whose remote is confirmed deleted.

### Phase 3: Check Active Worktrees for Uncommitted Changes

```bash
for issue in <list>; do
  wt=".worktrees/issue-$issue"
  status=$(git -C "$wt" status --short 2>&1)
  if [ -n "$status" ]; then
    echo "=== $issue has changes ==="
    echo "$status"
  fi
done
```

Distinguish by change type:
- `?? ProjectMnemosyne/` — untracked build artifact, safe to delete
- ` M file.mojo` — modified tracked file, inspect before discarding

For modified tracked files, check if they represent unpushed work:

```bash
git -C "$wt" log --oneline origin/BRANCH..HEAD
git -C "$wt" diff path/to/file
```

### Phase 4: Remove Active Worktrees

```bash
for issue in <list>; do
  wt=".worktrees/issue-$issue"
  result=$(git worktree remove "$wt" 2>&1)
  if [ $? -ne 0 ]; then
    git worktree remove --force "$wt"
  fi
done
```

Use `--force` only for worktrees with modified/untracked files after verifying content.

### Phase 5: Cleanup and Switch to Main

```bash
# Prune stale worktree metadata
git worktree prune

# Remove stale remote refs
git fetch --prune

# Delete [gone] branches from active set
git branch -v | grep '\[gone\]' | awk '{print $1}' | xargs git branch -D

# Switch main checkout
git checkout main && git pull origin main

# Remove empty .worktrees/ dir entries manually if needed
rm -rf .worktrees/issue-NNNN  # for orphaned dirs without git tracking
```

### Verification

```bash
git worktree list          # Should show only main repo
git branch -v              # Should show main + branches with open PRs only
git status                 # Should be clean
ls .worktrees/             # Should be empty
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git branch -d` on merged branches | Used safe delete flag for rebase-merged PRs | "not fully merged" error — rebase leaves no merge commit in current branch history | Always use `git branch -D` when remote branch is confirmed deleted (PR merged) |
| `git worktree remove` without cleaning untracked dirs | Tried removing worktrees containing `ProjectMnemosyne/` | "contains modified or untracked files" error blocks removal | Pre-clean `rm -rf $wt/ProjectMnemosyne` before `git worktree remove` |
| `git -C path symbolic-ref HEAD` piped to `head -2` | Attempted to check branch with head pipe | `head` doesn't accept `-C` as git does — it's a git flag, not shell | Don't pipe `git -C` subcommands to `head`; use separate commands |
| Using `$$` in `mkdir -p` and `gh repo clone` in same command | Tried PID-scoped clone with `build/$$` | Shell expanded `$$` in one context but the existing `build/ProjectMnemosyne` dir caused conflict | Check for existing clone first; use `--ff-only pull` to update rather than re-clone |

## Results & Parameters

### Batch Loop Pattern (Copy-Paste)

```bash
STALE="3033 3061 3062 3063"  # space-separated issue numbers
ACTIVE="3071 3077 3083"      # issues with open PRs — keep branches

# Remove stale
for issue in $STALE; do
  rm -rf ".worktrees/issue-$issue/ProjectMnemosyne"
  git worktree remove ".worktrees/issue-$issue" 2>/dev/null || true
  git branch -D "${issue}-auto-impl" 2>/dev/null || true
done

# Remove active (keep branches)
for issue in $ACTIVE; do
  rm -rf ".worktrees/issue-$issue/ProjectMnemosyne"
  git worktree remove ".worktrees/issue-$issue" 2>/dev/null || \
    git worktree remove --force ".worktrees/issue-$issue"
done

# Final cleanup
git worktree prune && git fetch --prune
git checkout main && git pull origin main
```

### Identifying [gone] Branches

```bash
# List all branches with gone remotes
git branch -v | grep '\[gone\]'

# Delete them all at once
git branch -v | grep '\[gone\]' | awk '{print $1}' | xargs git branch -D
```

### Scale Reference

| Worktrees | Time | Notes |
|-----------|------|-------|
| 33 worktrees | ~3 min | All removed successfully |
| 20 stale (merged) | ~1 min | No --force needed after cleaning untracked dirs |
| 13 active | ~1 min | 2 needed --force for modified tracked files |
