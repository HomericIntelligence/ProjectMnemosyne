---
name: git-worktree-path-detection
description: "Fix git worktree path extraction from porcelain output. Use when: parsing worktree list, extracting paths by branch, managing multiple worktrees."
category: tooling
date: 2026-03-09
user-invocable: false
---

# Git Worktree Path Detection

## Overview

| Field | Value |
|-------|-------|
| Problem | `git worktree list --porcelain` outputs multi-line blocks; naive grep on `branch` line extracts the ref, not the path |
| Root Cause | The path is on the preceding `worktree` line, not the `branch` line |
| Fix | Use awk to track the most recent `worktree` line and emit it when the branch matches |
| Impact | Scripts silently fail to locate worktree paths, falling back to main repo root |

## When to Use

- Parsing `git worktree list --porcelain` output to find worktree paths
- Building bash scripts that manage or iterate over multiple worktrees
- Extracting worktree paths by branch name for rebase, cleanup, or status scripts
- Adding stale worktree cleanup to automation scripts

## Verified Workflow

### 1. Correct worktree path extraction

The porcelain format outputs multi-line blocks:

```text
worktree /home/user/repo/.worktrees/issue-3198
HEAD 38f3c196...
branch refs/heads/3198-auto-impl
```

**Wrong** (extracts the ref, not the path):

```bash
WORKTREE_PATH=$(git worktree list --porcelain | grep "branch.*/$BRANCH$" | awk '{print $2}')
# Returns: refs/heads/3198-auto-impl  ← WRONG
```

**Correct** (tracks preceding worktree line):

```bash
WORKTREE_PATH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v branch="$BRANCH" '/^worktree /{path=$2} /^branch / && $2 ~ "/" branch "$" {print path}')
# Returns: /home/user/repo/.worktrees/issue-3198  ← CORRECT
```

### 2. Extracting branch name from worktree path

When iterating worktrees and need the branch name:

```bash
WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
  awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
```

### 3. Stale worktree cleanup pattern

After rebase/maintenance, clean worktrees with no uncommitted changes and no open PRs:

```bash
while IFS= read -r WT_PATH; do
    [ -z "$WT_PATH" ] && continue
    [ "$WT_PATH" = "$MAIN_REPO_ROOT" ] && continue

    WT_BRANCH=$(git worktree list --porcelain 2>/dev/null | \
      awk -v wt="$WT_PATH" '/^worktree /{path=$2} /^branch / && path == wt {sub("refs/heads/", "", $2); print $2}')
    [ -z "$WT_BRANCH" ] && continue

    # Skip if dirty
    [ -n "$(git -C "$WT_PATH" status --porcelain 2>/dev/null)" ] && continue

    # Skip if has open PR
    OPEN_PRS=$(gh pr list --head "$WT_BRANCH" --state open --json number 2>/dev/null)
    [ -n "$OPEN_PRS" ] && [ "$OPEN_PRS" != "[]" ] && continue

    # Safe to remove
    git worktree remove "$WT_PATH" 2>/dev/null
    git branch -d "$WT_BRANCH" 2>/dev/null  # Use -d (safe), NOT -D (force)
done < <(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')

git worktree prune 2>/dev/null
```

### 4. Add repo context for git commands in worktrees

When running git commands that may execute in a different directory context:

```bash
# Wrong - runs without explicit repo context
git merge-base --is-ancestor main "$BRANCH"

# Correct - explicit context
git -C "$WORK_DIR" merge-base --is-ancestor main "$BRANCH"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| grep + awk on branch line | `grep "branch.*/$BRANCH$" \| awk '{print $2}'` | Extracts the ref (`refs/heads/...`), not the worktree path | Porcelain format is multi-line; the path is on the preceding `worktree` line |
| `git branch -D` for cleanup | Force-delete branches after removing stale worktrees | Too aggressive — deletes unmerged branches without warning | Use `git branch -d` (safe delete) to preserve unmerged branches |
| merge-base without `-C` | `git merge-base --is-ancestor main "$BRANCH"` | Runs in wrong repo context when processing worktrees | Always use `git -C "$WORK_DIR"` for explicit context |

## Results & Parameters

### Configuration

```bash
# Verify worktree path extraction
git worktree list --porcelain | awk '/^worktree /{path=$2} /^branch / {print path, $2}'

# Check for stale worktrees (dry run)
git worktree list --porcelain | awk '/^worktree /{path=$2} /^branch / {sub("refs/heads/", "", $2); print path, $2}' | while read wt branch; do
  echo "$branch: changes=$(git -C "$wt" status --porcelain 2>/dev/null | wc -l) pr=$(gh pr list --head "$branch" --state open --json number 2>/dev/null)"
done
```

### Key Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Branch delete flag | `-d` (not `-D`) | Safe delete preserves unmerged branches |
| Porcelain format | `--porcelain` | Machine-parseable, stable output format |
| Stale check | status --porcelain + gh pr list | Two-condition safety: dirty check AND open PR check |
