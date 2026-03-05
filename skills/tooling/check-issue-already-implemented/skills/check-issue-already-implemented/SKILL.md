---
name: check-issue-already-implemented
description: "Check if a GitHub issue was already implemented in a previous session. Use when: starting work on a branch that already exists, running an impl skill that finds clean working tree with recent commits, or when a PR already exists for the issue."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Name** | check-issue-already-implemented |
| **Category** | tooling |
| **Trigger** | Before spending effort reimplementing work on an issue branch |
| **Output** | Status report: already done / partially done / not started |

## When to Use

Invoke this check at the start of any `impl` skill run on a branch that already exists:

1. Branch `<issue-number>-*` already exists and is checked out
2. `git log --oneline -5` shows commits referencing the issue number
3. `git status` shows a clean working tree (no uncommitted changes)
4. A PR already exists for the branch (`gh pr list --head <branch>`)

If all four conditions are true, the issue is already implemented. Skip reimplementation and
verify the PR state instead.

## Verified Workflow

```bash
# Step 1: Check branch state
git log --oneline -5
git status

# Step 2: Check for existing PR
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)"

# Step 3: If PR exists, verify its state
gh pr view <pr-number>

# Step 4: Confirm auto-merge is enabled
# If auto-merge is not enabled:
gh pr merge --auto --rebase

# Step 5: Report status to user — no reimplementation needed
```

### Decision Matrix

| git log mentions issue? | git status clean? | PR exists? | Action |
|------------------------|-------------------|------------|--------|
| Yes | Yes | Yes | Verify PR state, confirm auto-merge, done |
| Yes | Yes | No | Create PR, enable auto-merge |
| Yes | No | No | Commit uncommitted work, create PR |
| No | Yes | No | Issue not yet implemented — proceed with impl |

## Context: Issue #3076

This skill was extracted from implementing issue #3076 (`[Cleanup] Clean up Python interop
blocker NOTEs`) in the ProjectOdyssey repository.

The `impl` skill was invoked, but investigation revealed:

- The branch `3076-auto-impl` already existed with a recent commit
  `af39dfda docs(training): add issue references to Track 4 Python interop NOTEs`
- `git status` showed a clean working tree (only an untracked prompt file)
- PR #3168 already existed, was open, labeled `cleanup`, with auto-merge enabled

The correct response was to **report the existing state** rather than reimplementing.

## Results & Parameters

### Detecting Already-Done Work

```bash
# Run these checks in parallel at the start of any impl run
git log --oneline -5 &
git status &
gh pr list --head "$(git rev-parse --abbrev-ref HEAD)" &
wait
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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Starting full reimplementation | Began searching for NOTE comments to update | Files were already updated in prior session; `git log` showed `af39dfda` already had the changes | Always check `git log` and `gh pr list` before implementing |
| Grep for NOTE patterns | Ran `Grep` on `shared/training/` | No matches because prior session already removed/updated the NOTEs | Check branch state before running searches |
