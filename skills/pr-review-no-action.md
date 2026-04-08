---
name: pr-review-no-action
description: 'Recognize when a PR review requires no code changes and take the correct
  minimal action. Use when: (1) a .claude-review-fix-*.md plan explicitly states no
  fixes are required, (2) a review fix plan concludes "No problems found" and CI is
  already passing, (3) a PR review summary concludes the PR is ready to merge as-is,
  or (4) you need to avoid creating empty/phantom commits on an already-clean branch.'
category: ci-cd
date: 2026-04-07
version: 2.0.0
user-invocable: false
tags:
  - pr-review
  - no-op
  - auto-merge
  - review-fix
  - clean-state
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | pr-review-no-action |
| **Category** | ci-cd |
| **Trigger** | `.claude-review-fix-*.md` plan with "No fixes required" or equivalent conclusion |
| **Outcome** | Enable auto-merge; avoid phantom commits; confirm worktree is already correct |

This skill covers the full lifecycle of a no-op PR review: detecting that no fixes are
needed, verifying the worktree is in the correct state, enabling auto-merge, and
explicitly NOT creating empty commits.

## When to Use

- A `.claude-review-fix-<issue>.md` plan file contains "No problems found" or "No fixes required"
- A PR review summary concludes "The PR is ready to merge as-is"
- CI is already passing (100% test pass rate, security scan clean)
- The implementation is already correct per the analysis
- You need to verify the committed state matches the plan before an external script pushes
- You want to avoid creating an empty or unnecessary commit on an already-clean branch

## Verified Workflow

### 1. Read the Plan File

Read `.claude-review-fix-<issue>.md` fully. Focus on:
- "Problems Found" section
- "Fix Order" section

**Important**: The wrapper task instructions always say "Implement all fixes from the
plan above." This is a generic template. The actual plan body determines whether any
work is needed — not the wrapper.

### 2. Confirm No-Op

If both "Problems Found" and "Fix Order" say none/no fixes:

- **DO**: Proceed to verify worktree state and enable auto-merge
- **DO NOT**: Invent unnecessary changes to justify a commit
- **DO NOT**: Run tests or pre-commit when there's nothing to test or commit

### 3. Verify Worktree State

```bash
git status && git log --oneline -5
```

Expected output:
- `git status`: "nothing to commit" or only untracked files (e.g., the ephemeral plan file)
- `git log`: expected commit is present at or near HEAD

```bash
# Confirm the target change is in history
git log --oneline --grep="<expected commit keyword>"
```

### 4. Enable Auto-Merge

```bash
# Confirm PR state and CI status
gh pr view <pr-number>

# Enable auto-merge
gh pr merge --auto --rebase <pr-number>
```

Auto-merge triggers once:
- All required CI checks pass
- Branch is up to date with base
- No merge conflicts exist

### 5. Report and Stop

Tell the user the branch is already in correct state and no action was needed. Do NOT push — the calling script handles that.

### Quick Reference

```bash
# Standard no-op review fix workflow
gh pr view <pr-number>                       # Confirm PR state and CI status
git status && git log --oneline -5           # Verify worktree is clean
gh pr merge --auto --rebase <pr-number>      # Enable auto-merge
```

### Plan File Pattern (No-Op)

```
## Problems Found
None. The PR:
- <reason 1 why it's already correct>
- <reason 2>

## Fix Order
No fixes required.
```

When this pattern is present, skip all implementation steps and go directly to verifying
worktree state and enabling auto-merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Blindly following "implement all fixes" wrapper | Started looking for code to change despite the plan saying no fixes needed | The task wrapper says "implement all fixes" even when the plan says there are none — the wrapper is a generic template | Always read the plan body first; the wrapper instruction is not a guarantee of work |
| Creating a commit anyway to satisfy the script | Considered making a trivial no-op commit | Would pollute history and could confuse CI or rebase operations | An empty/no-op commit is worse than no commit; trust the plan |
| Inventing changes to justify a commit | Creating a commit with no real changes just to satisfy the "commit" instruction | Adds noise to git history, violates minimal-change principle | Read the plan fully first; if no fixes, don't manufacture them |
| Running tests before enabling merge | Running `pixi run python -m pytest` before enabling auto-merge | Unnecessary work when CI already confirmed passing | Trust CI results — don't re-run passing tests locally for no-op fixes |

## Results & Parameters

### Verified No-Op Sessions

**Session 1 — PR #3386 (Issue #3166)**
- Plan: `.claude-review-fix-3166.md` — all CI passing, 3 tests already implemented, no human review comments
- Action: `gh pr merge --auto --rebase 3386` — no code changes, no commit, no test run
- File already correct: `tests/shared/core/test_utility.mojo`

**Session 2 — PR #3182 (Issue #3083)**
- Plan: `.claude-review-fix-3083.md` — "No problems found. The PR is ready to merge."
- Action: confirmed HEAD was `3fea321a cleanup(logging): remove unimplemented RotatingFileHandler placeholder`
- Reported no action needed; script handled push

### Worktree State Verification

```bash
git status           # Should show: "nothing to commit" or only untracked files
git log --oneline -5  # Should show the expected change at HEAD or recently
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3386 / Issue #3166 | No-op plan; auto-merge enabled |
| ProjectOdyssey | PR #3182 / Issue #3083 | No-op plan; worktree verification only |
