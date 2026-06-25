---
name: worktree-deleted-mid-session-recovery
description: "When a git worktree directory is deleted between sessions (by git worktree prune, automation cleanup, or OS temp-dir purge), the shell cwd becomes invalid and Path.cwd() / os.getcwd() throws FileNotFoundError. Use when: (1) pytest or pixi run fails with FileNotFoundError on cwd, (2) git worktree list shows an entry but the directory is gone from disk, (3) resuming work on a branch after a gap and finding the worktree path missing."
category: ci-cd
date: 2026-06-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, worktree, cwd, FileNotFoundError, recovery, prune, mid-session, pytest, pixi]
---

# Worktree Deleted Mid-Session Recovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Recover a deleted git worktree so tests and builds can resume on the correct branch |
| **Outcome** | Worktree recreated successfully; 4976 tests passed at 85.83% coverage |
| **Verification** | verified-local |

When a git worktree directory is removed from disk (by `git worktree prune`, an automation
sweep of `build/.worktrees/`, or a prior session's cleanup script), the shell's CWD becomes
invalid. Any tool that calls `Path.cwd()` or `os.getcwd()` — including pytest, pixi, and many
Python utilities — throws `FileNotFoundError: [Errno 2] No such file or directory`. The fix
is to recreate the worktree with `git worktree add`.

Note: this is distinct from the "removed from inside the worktree" anti-pattern covered in
`git-worktree-parallel-execution-lifecycle`. Here the directory was deleted externally and the
branch still exists; there are no stashed edits to recover.

## When to Use

- `pixi run pytest` or `python -m pytest` fails immediately with `FileNotFoundError` from `Path.cwd()`
- `git worktree list` shows a branch entry but the directory on disk is absent
- A worktree was last known to be at `build/.worktrees/<issue-name>` but that path no longer exists
- Resuming after a long gap: an automation process (e.g., `git worktree prune`, a CI cleanup job) removed the directory since the last session
- The shell recovers to `$HOME` or `/` after `cd`-ing into the deleted path, causing subsequent commands to run in the wrong location

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the branch still exists
git -C <repo-root> branch --list <branch-name>

# 2. List all registered worktrees to see the stale entry
git -C <repo-root> worktree list

# 3. Recreate the deleted worktree on the same branch
git -C <repo-root> worktree add build/.worktrees/<issue-name> <branch-name>

# 4. Verify it's back on disk
ls build/.worktrees/<issue-name>

# 5. Confirm HEAD is the expected commit
git -C build/.worktrees/<issue-name> log --oneline -1
```

### Detailed Steps

1. Notice the error: `FileNotFoundError: [Errno 2] No such file or directory` from `Path.cwd()`
   or `getcwd`, typically surfaced by pytest, pixi, or the shell after `cd` into a deleted path.
2. Run `git -C <repo-root> worktree list` to see all registered worktrees.
   Identify any entry whose path does not exist on disk.
3. If the branch still exists (`git -C <repo-root> branch --list <branch>`), recreate the worktree:
   ```bash
   git -C <repo-root> worktree add <path> <branch>
   ```
4. If `git worktree list` still shows the stale entry after recreation, run:
   ```bash
   git -C <repo-root> worktree prune
   ```
   to clean up stale metadata, then recreate.
5. Resume work inside the recreated worktree path.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running pytest from deleted cwd | Shell recovered to home dir; pytest ran from the wrong directory | Tests ran from the repo root, not the worktree branch checkout; imports and coverage metrics were misleading | Always verify `pwd` and `git rev-parse --abbrev-ref HEAD` before running tests to confirm you are in the correct worktree |

## Results & Parameters

Example recovery command used for ProjectHephaestus issue #1554 (branch `1554-auto-impl`,
worktree at `build/.worktrees/issue-1554`):

```bash
git -C /home/mvillmow/Projects/ProjectHephaestus worktree add \
    build/.worktrees/issue-1554 1554-auto-impl
# Output: Preparing worktree (checking out '1554-auto-impl')
# HEAD is now at c7883e49 fix: Address CI failures for PR ProjectHephaestus#1570
```

After recreation, `pixi run python -m pytest tests/ -v` produced 4976 passed, 85.83% coverage.

Root cause of the deletion: likely `git worktree prune` or an automation process sweeping
`build/.worktrees/` between sessions. Any process that calls `git worktree prune` or removes
files under `build/.worktrees/` can silently invalidate an in-progress session. Before pruning,
check for active branch sessions with `git -C <repo-root> worktree list` and verify no
automation is running on those branches.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1554, branch 1554-auto-impl — worktree missing between CI fix sessions | Recreated with `git worktree add`; all 4976 tests passed at 85.83% coverage |
