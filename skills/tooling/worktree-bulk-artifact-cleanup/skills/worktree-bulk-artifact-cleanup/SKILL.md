---
name: worktree-bulk-artifact-cleanup
description: "Clean generated artifacts from multiple git worktrees without losing real changes. Use when: (1) worktrees have __pycache__ or build artifacts showing as uncommitted changes, (2) bulk cleanup of generated files across many worktrees needed."
category: tooling
date: 2026-03-10
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | worktree-bulk-artifact-cleanup |
| **Category** | tooling |
| **Complexity** | Medium |
| **Risk** | Low-Medium — only removes artifacts, preserves real changes |
| **Time** | 2-5 minutes for 20+ worktrees |

Cleans generated artifacts (`__pycache__/*.pyc`, `ProjectMnemosyne/`, build dirs) from multiple
git worktrees while preserving real source code changes. Distinguishes between tracked and
untracked artifacts and handles each correctly. Also identifies worktrees needing PRs or removal.

## When to Use

- Multiple worktrees report "uncommitted changes" that are only generated artifacts
- After bulk implementation sessions leave `__pycache__` or build artifacts in worktrees
- Before auditing worktree status to separate real changes from noise
- When `git status --short` across worktrees shows only `.pyc` or build directory changes

## Verified Workflow

### Phase 1: Audit worktrees to classify changes

```bash
# Check what each worktree has
for d in .worktrees/issue-*; do
  changes=$(git -C "$d" status --short 2>/dev/null)
  [ -n "$changes" ] && echo "$d:" && echo "$changes" | head -5
done
```

Classify each worktree into:

- **Artifact-only**: Only `__pycache__/*.pyc`, `ProjectMnemosyne/`, build dirs
- **Real changes**: Actual source code modifications
- **Empty**: No commits beyond main

### Phase 2: Two-pass cleanup (CRITICAL — order matters)

**Pass 1 — Restore tracked files** (e.g., tracked `.pyc` files):

```bash
for issue in $ISSUE_LIST; do
  wt=".worktrees/issue-${issue}"
  git -C "$wt" checkout -- . 2>/dev/null
done
```

**Pass 2 — Remove untracked artifacts**:

```bash
for issue in $ISSUE_LIST; do
  wt=".worktrees/issue-${issue}"
  git -C "$wt" clean -fd --quiet 2>/dev/null
done
```

### Phase 3: Handle real changes separately

For worktrees with real (non-artifact) uncommitted changes, decide per-worktree:

- **Destructive/accidental changes**: `git checkout -- <files>` to discard
- **Legitimate changes**: Stage and commit, or leave for manual review

### Phase 4: Create missing PRs and remove empty worktrees

```bash
# Push and create PRs for worktrees without PRs
git -C "$wt" push -u origin "$branch"
gh pr create --head "$branch" --title "$title" --body "Closes #$issue"
gh pr merge --auto --rebase "$pr_number"

# Remove worktrees with no changes from main
git worktree remove ".worktrees/issue-$issue"
git branch -d "$branch"
```

### Phase 5: Verify

```bash
for d in .worktrees/issue-*; do
  changes=$(git -C "$d" status --short 2>/dev/null)
  [ -n "$changes" ] && echo "$d: $changes"
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `find + rm -rf __pycache__` then verify | Tracked `.pyc` files showed as "D" (deleted) in git status | Deleting tracked files from disk makes git report them as deleted — must use `git checkout` to restore |
| 2 | Single-pass `git clean -fd` for all artifacts | Only removes untracked files; tracked `.pyc` files still show as deleted | Need two passes: `git checkout -- .` first (restore tracked), then `git clean -fd` (remove untracked) |
| 3 | Running `git checkout -- '**/__pycache__/'` with glob pattern | Glob patterns in git checkout don't reliably match nested paths | Use `git checkout -- .` to restore all tracked files, then selectively clean untracked |

## Results & Parameters

### Configuration

```bash
# Artifact patterns to clean
ARTIFACT_PATTERNS="__pycache__ ProjectMnemosyne .pyc"

# Two-pass cleanup commands
PASS1="git -C \$wt checkout -- ."           # Restore tracked files
PASS2="git -C \$wt clean -fd --quiet"       # Remove untracked artifacts
```

### Results from session

- **23 worktrees** cleaned in ~2 minutes
- **22 of 23** had only artifact changes (all cleaned successfully)
- **1 worktree** had destructive real changes (discarded with targeted `git checkout`)
- **6 PRs** created for worktrees missing them
- **1 empty worktree** removed (no changes from main)
- **Zero data loss** — two-pass approach preserved all tracked files

### Key insight

Always use the two-pass approach when cleaning artifacts from worktrees:

1. `git checkout -- .` — restores any tracked files that were deleted/modified
2. `git clean -fd` — removes only untracked files and directories

Never use `rm -rf` or `find -exec rm` on files that might be tracked by git.
