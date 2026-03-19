---
name: verify-already-implemented-issues
description: 'Verify issue implementation status before starting work. Use when: assigned
  to implement a GitHub issue in a pre-created worktree, starting issue work, or suspecting
  duplicate effort.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | tooling |
| **Trigger** | Before implementing any GitHub issue in a worktree branch |
| **Outcome** | Avoid duplicate work when prior commits already address the issue |
| **Time saved** | Entire implementation session (if already done) |

## When to Use

- You are given a `.claude-prompt-NNNN.md` file instructing you to implement issue #NNNN
- The branch name is `NNNN-auto-impl` or similar pre-created branch
- You want to confirm no prior agent session already completed the work
- The git log or branch status looks "clean" but you're unsure

## Verified Workflow

### Step 1: Check git log for issue-related commits

```bash
git log --oneline -10
```

Look for commits mentioning the issue number or key terms from the issue title.

### Step 2: Read the target file(s) from the issue description

Read the file(s) listed in the issue to see if they already reflect the desired state.
The issue description typically names specific files and line numbers.

### Step 3: Check for an existing open PR on this branch

```bash
gh pr list --head <branch-name>
```

If a PR exists with the issue number in the title or `Closes #NNNN` in the body,
the work is already done.

### Step 4: Verify PR auto-merge status

```bash
gh pr view <PR-number>
```

If auto-merge is enabled, no further action is needed — just report the PR URL.

### Decision Matrix

| git log has issue commit | Open PR exists | Action |
|--------------------------|----------------|--------|
| Yes | Yes | Report PR URL, no work needed |
| Yes | No | Create PR if missing |
| No | No | Implement the issue |
| No | Yes | Investigate PR content |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Immediately starting implementation | Jumped straight to reading the file and planning changes without checking git log | Would have duplicated work already committed in `de97cd8a` | Always check `git log --oneline -10` and `gh pr list --head <branch>` first |
| Trusting branch "cleanliness" | Saw `git status` showed only untracked `.claude-prompt-NNNN.md` and assumed no work done | The commit was already in history, not in staging | `git status` shows uncommitted changes; `git log` shows committed history |

## Results & Parameters

### Copy-Paste Verification Snippet

```bash
# Run these before starting any issue implementation
ISSUE_NUM=3093
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "=== Recent commits ==="
git log --oneline -10

echo ""
echo "=== Open PRs on this branch ==="
gh pr list --head "$BRANCH"

echo ""
echo "=== Git status ==="
git status
```

### Session Example (Issue #3093)

- **Branch**: `3093-auto-impl`
- **Issue**: `[Cleanup] Review commented-out imports in shared/__init__.mojo`
- **Finding**: Commit `de97cd8a` already addressed the issue; PR #3217 was open with auto-merge enabled
- **Action taken**: Reported PR URL `https://github.com/HomericIntelligence/ProjectOdyssey/pull/3217`
- **Time saved**: Full implementation session

### Why Pre-Created Worktrees Can Be Pre-Populated

In ML Odyssey, worktrees are created by orchestration agents that may also run an initial
implementation pass. When a second agent session opens the same worktree, the work may already
be complete. The `.claude-prompt-NNNN.md` file is dropped into the worktree for agent context
but does not indicate whether implementation is pending or done.
