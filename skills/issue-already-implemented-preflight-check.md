---
name: issue-already-implemented-preflight-check
description: "Use when: (1) assigned to implement a GitHub issue and the branch already exists or has prior commits, (2) working in an auto-impl worktree where a prior session may have completed the work, (3) git log shows commits referencing the issue number before any implementation work has started, (4) a PR already exists for the branch."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [preflight, duplicate-work, git-log, pr-check, already-implemented, worktree, auto-impl]
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Trigger** | Start of any issue implementation task on a pre-existing or auto-impl branch |
| **Goal** | Avoid duplicating work already committed in a prior session |
| **Outcome** | Either confirm PR exists and report status, or proceed with fresh implementation |
| **Time Saved** | Entire implementation session (if already done); ~5-10 min minimum |

## When to Use

- Working directory is `<repo>/.worktrees/<issue>-auto-impl` (or similar branch pattern)
- Branch name contains an issue number (e.g., `3065-auto-impl`)
- A `.claude-prompt-<N>.md` file exists describing the work to do
- `git status` shows a clean working tree with no staged changes
- `git log --oneline -5` shows commits referencing the issue number
- A PR already exists for the current branch (`gh pr list --head <branch>`)
- The issue title matches methods/functions already visible in the codebase
- When resuming work after an interruption or session restart

**Key insight**: A clean `git status` does NOT mean work hasn't started. Prior commits can have done all the work. Always check `git log` too.

## Verified Workflow

### Quick Reference

```bash
# 2-command minimum pre-flight (< 3 seconds, 2 tool calls)
git log --oneline -10
gh pr list --search "<issue-number>" --state all

# Decision: git log shows "Closes #N" -> done; gh pr list shows open PR -> done; neither -> implement
```

### Step 1: Check git log for prior commits

```bash
git log --oneline -10
```

Look for commits referencing the issue number or key terms from the issue title (e.g., `feat(scope): implement ... (#N)`, `Closes #N`). If a match is found, the work is done — stop here before reading any source files.

### Step 2: Confirm with PR search

```bash
# Find all PRs (open or merged) associated with the issue
gh pr list --search "<issue-number>" --state all
# OR search by branch
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)"
```

Expected: an open PR with auto-merge enabled, or a merged PR.

### Step 3: Verify no remaining work exists (optional)

```bash
# Search for the specific pattern the issue targets (if applicable)
grep -r "<target-pattern>" --include="*.<ext>" .

# Check what was already done
git show <commit-hash> --stat
```

Zero matches for the target pattern AND a prior commit confirms the issue is fully implemented.

### Step 4: Check PR auto-merge status

```bash
gh pr view <pr-number>
# or: gh pr view <pr-number> --json autoMergeRequest,state,title
```

If auto-merge is enabled, no further action is needed.

### Step 5: Report and stop

If work is complete:
- Note the existing PR URL
- Report status to user (use template below)
- Do NOT create a duplicate PR or commit

If PR exists but auto-merge is not enabled:
```bash
gh pr merge --auto --rebase
```

If PR is missing but commits exist:
```bash
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase <PR_NUMBER>
```

### Reporting Template

When an issue is already implemented:

```
Status: Already Done

- Commit: <sha> <message>
- PR: #<number> — <state>, auto-merge: <enabled/disabled>
- Files changed: <list from git show --stat>

No reimplementation needed.
PR URL: <url>
```

## Decision Matrix

| git log has issue commit | git status clean | PR exists | Action |
| -------------------------- | ----------------- | ----------- | -------- |
| Yes | Yes | Yes | Verify PR state, confirm auto-merge, report done |
| Yes | Yes | No | Create PR, enable auto-merge |
| Yes | No | No | Commit uncommitted work, create PR |
| No | Yes | No | Issue not yet implemented — proceed with impl |
| No | Any | Yes | Investigate PR content — unusual state |

Extended matrix with pattern search:

| git log has "Closes #N" | Pattern search finds results | PR exists | Action |
| ------------------------- | ------------------------------ | ----------- | -------- |
| Yes | No | Yes | Report done, exit |
| Yes | No | No | Create PR linking to issue |
| Yes | Yes | Any | Investigate — partial implementation |
| No | Yes | No | Implement the issue |
| No | No | No | Implement the issue (may be unrelated) |

## Full Verification Command Sequence

```bash
# Run these checks before starting any issue implementation
ISSUE_NUM=<N>
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "=== Recent commits ==="
git log --oneline -10

echo ""
echo "=== Open PRs on this branch ==="
gh pr list --head "$BRANCH"

echo ""
echo "=== Git status ==="
git status

# If suspicious, also run:
gh issue view $ISSUE_NUM --json state,title
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running tests locally before checking git | `pixi run mojo test tests/...` | GLIBC version too old; and work was already done | Check `git log` BEFORE reading issue description or running tests |
| Reading source files before checking git history | Read `.mojo` files to find patterns | Files had no matches — already fixed | Check `git log` before reading any source files |
| Assuming clean git status means fresh start | Relied on `git status` showing clean working tree | Clean status just means nothing unstaged — prior commits can have done all the work | `git status` clean != implementation not started |
| Assuming the worktree always has new work to do | Started planning implementation steps | Wasted tool calls on work already complete | Worktrees created by automation may lag behind main |
| Jump straight to implementation | Started reading issue and planning without checking git log | Found PR already open and commit had done all the work | Always check `git log --oneline -5` and `gh pr list --head <branch>` before any implementation work |
| Grep for patterns before checking git | Ran Grep on source files | No matches because prior session already removed/updated | A clean grep with no results is itself a signal the work is done — check branch state first |
| Starting full reimplementation | Began searching for NOTE comments to update | Files were already updated in prior session | Always check `git log` and `gh pr list` before implementing |
| Immediately searching for patterns | Searched codebase for `.__matmul__(` before checking git log | Would have found nothing and been confused | Always check git log first — a prior commit may have already done the work |

## Results & Parameters

### Success Indicators

- Detected already-complete work in 2 tool calls (vs 5+ if source files read first)
- Existing PR identified with auto-merge enabled
- No duplicate commits or PRs created
- Entire implementation session skipped when work was already present

### Why Pre-Created Worktrees Can Be Pre-Populated

In automated pipelines (e.g., ProjectOdyssey), worktrees are created by orchestration agents that may also run an initial implementation pass. When a second agent session opens the same worktree, the work may already be complete. The `.claude-prompt-NNNN.md` file is dropped into the worktree for agent context but does not indicate whether implementation is pending or done.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #2722, branch `2722-auto-impl`, PR #3161 | All ExTensor utility methods already in commit `20ddaee6` |
| ProjectOdyssey | Issue #3065, worktree `3065-auto-impl`, PR #3262 | Deprecated type aliases already removed in prior session |
| ProjectOdyssey | Issue #3076, branch `3076-auto-impl`, PR #3168 | Docs commit `af39dfda` already added all issue references |
| ProjectOdyssey | Issue #3090, PR #3201 | Branch `3090-auto-impl`; commit `47f87aba` already done |
| ProjectOdyssey | Issue #3091, PR #3206 | Commit `8c64d500` already documented callback import limitation |
| ProjectOdyssey | Issue #3093, PR #3217 | Commit `de97cd8a` already addressed commented-out imports |
| ProjectOdyssey | Issue #3112 | Branch `3112-auto-impl`; commit `86b485a3` already closed the issue |
