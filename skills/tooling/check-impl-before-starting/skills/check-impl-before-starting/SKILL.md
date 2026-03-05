---
name: check-impl-before-starting
description: "Check if an issue's implementation already exists before starting work. Use when: implementing an issue on a pre-existing branch, resuming interrupted work, or verifying PR status before creating duplicates."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Name | check-impl-before-starting |
| Category | tooling |
| Trigger | Before implementing any GitHub issue |
| Outcome | Avoids duplicate work; discovers existing commits and PRs |

## When to Use

- When assigned to implement a GitHub issue and the branch already exists
- Before creating a new commit to check if the work is already done
- Before creating a PR to check if one already exists
- When resuming work after an interruption or session restart

## Verified Workflow

1. Check git log for recent commits on the current branch:

   ```bash
   git log --oneline -10
   ```

2. Check git status for any pending changes:

   ```bash
   git status
   ```

3. Check if a PR already exists for the current branch:

   ```bash
   gh pr list --head <branch-name>
   ```

4. If PR exists, view it to understand current state:

   ```bash
   gh pr view <pr-number>
   ```

5. If work is already done (commits exist + PR open), report status and skip implementation.

6. If PR is missing but commits exist, create the PR:

   ```bash
   gh pr create --title "..." --body "Closes #<issue>"
   ```

7. If neither commits nor PR exist, proceed with implementation.

## Results & Parameters

**Key check commands** (run these first for any issue implementation):

```bash
# Step 1: What's on this branch already?
git log --oneline -5

# Step 2: Is there a PR?
gh pr list --head $(git branch --show-current)

# Step 3: What's the PR state?
gh pr view <number>
```

**Decision matrix**:

| Commits exist | PR exists | Action |
|--------------|-----------|--------|
| Yes | Yes | Report done, skip |
| Yes | No | Create PR |
| No | No | Implement from scratch |
| No | Yes | Investigate — unusual state |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Jump straight to implementation | Started reading issue and planning without checking git log | Found PR #3176 was already open and commit `e21e00b9` had done all the work | Always check `git log --oneline -5` and `gh pr list --head <branch>` before any implementation work |
| Assume clean state because git status is clean | Relied on `git status` showing clean working tree as signal that work hasn't started | Clean status just means nothing unstaged — prior commits can have done all the work | `git status` clean != implementation not started; check `git log` too |
