---
name: detect-already-implemented-issue
description: "Detect when a GitHub issue was already implemented in a previous session and has an open PR. Use when: implementing a GitHub issue, session starts on a branch with commits, or a PR already exists for the issue."
category: documentation
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Avoid duplicate work by detecting pre-existing implementation before starting |
| **Trigger** | Starting implementation of a GitHub issue |
| **Outcome** | Either confirm PR exists and report status, or proceed with fresh implementation |
| **Time saved** | Prevents re-implementing already-complete work |

## When to Use

- When `gh issue view <number> --comments` shows a previous session's work
- When `git log --oneline` shows commits referencing the issue number
- When `git status` is clean on a branch named `<issue-number>-*`
- When starting any `impl` or `gh-implement-issue` workflow

## Verified Workflow

1. **Check git log for prior commits** referencing the issue:

   ```bash
   git log --oneline -10
   ```

   If the most recent commit message references the issue (e.g., `docs(training): document callback import limitation`), prior work exists.

2. **Check for an open PR** linked to the issue:

   ```bash
   gh pr list --search "Closes #<issue-number>" --state open
   # or directly:
   gh pr view <pr-number>
   ```

3. **If PR exists and is open** with auto-merge enabled:
   - Report the PR URL and status to the user
   - Do NOT re-implement — the work is done
   - Confirm auto-merge is enabled so it will merge when CI passes

4. **If no PR exists** but commits are present:
   - Review the commits with `git diff HEAD~N HEAD -- <file>` to understand what was done
   - Create the PR if it is missing: `gh pr create --title "..." --body "Closes #<issue>"`

5. **If nothing exists** (clean branch, no commits):
   - Proceed with normal implementation workflow

## Results & Parameters

### Detection commands (copy-paste)

```bash
# Step 1: Check git log
git log --oneline -5

# Step 2: Check for open PR
gh pr list --search "closes:#<ISSUE_NUMBER>" --state open

# Step 3: If PR number is known
gh pr view <PR_NUMBER>
```

### Output interpretation

| Scenario | `git log` | `gh pr list` | Action |
|----------|-----------|--------------|--------|
| Already done | Recent commit for issue | Open PR found | Report PR URL, done |
| Partial | Commits present | No PR | Create PR from existing commits |
| Fresh start | No issue commits | No PR | Implement normally |

### Example session (issue #3091)

```
git log --oneline -5
# 8c64d500 docs(training): document callback import limitation in __init__.mojo

gh pr view 3206
# title: docs(training): document callback import limitation
# state: OPEN
# auto-merge: enabled
```

Result: Work was already complete from a prior session. PR #3206 open with auto-merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reading file directly | Read `__init__.mojo` to see if Note was present | File on current branch didn't show the Note (it was on the PR branch) | Check `git log` first to see if a prior commit exists before reading files |
| Assuming fresh start | Preparing to add documentation | Would have duplicated work already done | Always run `git log --oneline -5` at session start |
