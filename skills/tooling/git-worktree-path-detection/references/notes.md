# Session Notes: Fix rebase-all-branches.sh

## Date: 2026-03-09

## Context

Script: `scripts/rebase-all-branches.sh` in Odyssey2 repository.
The script rebases all local branches against main and force-pushes with lease.
With 44+ worktrees in `.worktrees/`, the script had critical bugs.

## Bug 1: Worktree Path Detection (CRITICAL)

`git worktree list --porcelain` outputs:

```
worktree /home/user/repo/.worktrees/issue-3198
HEAD 38f3c196...
branch refs/heads/3198-auto-impl
```

The code `grep "branch.*/$BRANCH$" | awk '{print $2}'` matched the `branch` line and
extracted `refs/heads/3198-auto-impl` — the git ref, NOT the filesystem path. The path
is on the **preceding** `worktree` line.

Fix: awk that tracks the most recent `worktree` line:

```bash
awk -v branch="$BRANCH" '/^worktree /{path=$2} /^branch / && $2 ~ "/" branch "$" {print path}'
```

This bug appeared at 3 locations in the script (lines 52, 166, 183).

## Bug 2: merge-base Without Repo Context (MINOR)

`git merge-base --is-ancestor main "$BRANCH"` ran without `-C "$WORK_DIR"`, which could
produce wrong results when the script had `cd`'d into a worktree directory.

## Feature: Stale Worktree Cleanup

Added a cleanup phase after the rebase loop:
1. Iterate all worktrees (skip main repo root)
2. Extract branch name using awk on porcelain output
3. Check for uncommitted changes: `git -C "$WT_PATH" status --porcelain`
4. Check for open PRs: `gh pr list --head "$WT_BRANCH" --state open --json number`
5. If clean AND no open PR: `git worktree remove` + `git branch -d`
6. End with `git worktree prune`

## User Correction

Initially used `git branch -D` (force delete). User requested `-d` (safe delete) to
avoid deleting branches that haven't been fully merged. This is the safer choice —
`-d` will refuse to delete unmerged branches, acting as a safety net.
