---
name: verify-pr-ci-preexisting-failures
description: 'Verify whether CI failures on a PR are pre-existing on main or introduced
  by the PR. Use when: reviewing a PR with red CI, auditing a cleanup/deletion PR,
  or confirming a PR is correct despite failing checks.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | ci-cd |
| **Skill** | verify-pr-ci-preexisting-failures |
| **Trigger** | PR has CI failures; need to determine if they predate the PR |
| **Outcome** | Confirm failures are pre-existing (no fix needed) or introduced (fix required) |

## When to Use

- A PR shows red CI checks and you need to confirm whether the PR caused them
- Reviewing a cleanup or deletion PR where no Mojo/logic code was changed
- A fix plan says "no changes needed" and you must verify the current state is clean
- Before closing a review loop to confirm no commits are required

## Verified Workflow

1. **Check branch state**: `git status` — confirm worktree is clean (no staged/unstaged changes)
2. **Confirm PR scope**: `git log --oneline main..HEAD` — verify only expected commits are present
3. **Check main CI history for the failing workflow**:
   ```bash
   gh run list --branch main --workflow "Workflow Name" --limit 5
   ```
   If all recent runs on `main` show `failure`, the failure is pre-existing.
4. **Confirm no Mojo code was changed** (for non-code PRs):
   ```bash
   git diff main...HEAD -- '*.mojo'
   ```
   Empty output confirms no logic changes.
5. **Document conclusion**: If failures are pre-existing, no commits are needed. The PR is ready to push.

## Results & Parameters

```bash
# Verify pre-existing Comprehensive Tests failures on main
gh run list --branch main --workflow "Comprehensive Tests" --limit 5
# Expected: all 5 most recent runs show "failure" status

# Verify pre-existing Markdown Link Check failures on main
gh run list --branch main --workflow "Check Markdown Links" --limit 5
# Expected: all 5 most recent runs show "failure" status

# Confirm PR only has expected commits
git log --oneline main..HEAD
# Expected: single cleanup commit, no Mojo changes

# Confirm working tree is clean
git status
# Expected: "nothing to commit" (only untracked review instruction files)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume CI failures require a fix | Automatically trying to fix red CI checks on a cleanup PR | The failures were unrelated to the PR — pre-existing on main from infrastructure issues and Mojo crashes | Always verify CI failure history on `main` before attempting any fix |
| Commit the review instructions file | Including `.claude-review-fix-*.md` in the commit | These are temporary instruction files, not implementation files | Never commit review instruction/orchestration files — leave them as untracked |
