---
name: auto-impl-already-done-detection
description: 'Detect when an auto-impl worktree arrives with work already completed
  on main and a PR already open. Use when: invoked via .claude-prompt-<N>.md in a
  clean worktree where recent git log shows ''Closes #<N>'' already on main.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Auto-Impl Already-Done Detection

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Implement GitHub issue #3065 (remove deprecated type aliases) |
| **Outcome** | Work was already complete - detected via git log, confirmed via PR search |
| **Root Cause** | A prior Claude Code session already committed + pushed + opened the PR |
| **Key Learning** | Always check `git log --oneline -10` and `gh pr list --search "<N>"` BEFORE reading any source files |

## When to Use

Use this pre-flight check **first** when invoked in a worktree context:

1. Working directory is `<repo>/.worktrees/<issue>-auto-impl` (or similar branch pattern)
2. `git status` shows a clean working tree with no staged changes
3. Branch name contains an issue number (e.g., `3065-auto-impl`)
4. A `.claude-prompt-<N>.md` file exists describing the work to do

These signals suggest a prior session may have already completed the work.

## Verified Workflow

### Step 1: Read the prompt file and check git log simultaneously

```bash
# Read prompt to understand what issue number to check
cat .claude-prompt-<N>.md

# Check recent commits for "Closes #<N>" or issue number
git log --oneline -10
```

**Key signal**: If `git log` shows a commit like `cleanup(foo): remove deprecated X - Closes #<N>`,
the work is done. Stop here.

### Step 2: Confirm with PR search

```bash
# Find all PRs (open or merged) associated with the issue
gh pr list --search "<issue-number>" --state all
```

**Expected**: You will find an open PR with auto-merge enabled, or a merged PR.

### Step 3: Inspect what was already done

```bash
# Verify the commit removed the right things
git show <commit-hash> --stat

# Check issue state
gh issue view <N> --json state,title
```

### Step 4: Report and stop

If work is complete:
- Note the existing PR URL
- Report status to user
- Do NOT create a duplicate PR or commit
- Optionally close the issue if it remains open but all work is merged

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reading source files before checking git history | Read `linear.mojo` to find deprecated aliases | File had no aliases - already removed | Check `git log` before reading any source files |
| Searching codebase for deprecated symbols | Grep for `LinearBackwardResult` across all `.mojo` files | No results - already deleted | A clean grep with no results is itself a signal the work is done |
| Assuming the worktree always has new work to do | Started planning implementation steps | Wasted tool calls on work already complete | Worktrees created by automation may lag behind main |

## Results & Parameters

### Minimum Pre-Flight Sequence (2 commands)

```bash
# 1. Check git log for issue number commits
git log --oneline -10

# 2. If suspicious, search for PRs
gh pr list --search "<N>" --state all
```

**Time cost**: < 3 seconds, 2 tool calls

**Decision tree**:
- `git log` shows `Closes #<N>` on main -> Work done, find existing PR, report
- `gh pr list` shows open PR with auto-merge -> Work done, PR will merge when CI passes
- Neither signal found -> Proceed with normal implementation workflow

### Success Indicators

- Detected already-complete work in 2 tool calls (vs 5+ if source files read first)
- Existing PR #3262 identified with auto-merge enabled
- No duplicate commits or PRs created

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3065, worktree `3065-auto-impl` | [notes.md](../references/notes.md) |

## Related Skills

- `verify-issue-before-work` - General issue state verification before starting
- `issue-completion-verification` - Closing orphaned open issues after work is merged
- `gh-check-ci-status` - Monitoring PR CI after detecting existing work
