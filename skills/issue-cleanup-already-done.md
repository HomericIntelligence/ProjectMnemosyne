---
name: issue-cleanup-already-done
description: 'Detects when a GitHub issue cleanup task was already completed in a
  prior session before re-implementing. Use when: the target file no longer contains
  the stale marker from the issue, recent commits on the branch reference the same
  issue number, or a PR already exists for the branch.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | issue-cleanup-already-done |
| **Category** | documentation |
| **Trigger** | Implementing a cleanup/docs issue that references a stale NOTE/TODO marker |
| **Outcome** | Avoid re-doing work; verify state then surface existing PR |

## When to Use

- You are assigned a `[Cleanup]` or `[Docs]` GitHub issue that says "remove NOTE at line X"
- The issue branch already has recent commits whose messages mention the same issue number
- The stale marker referenced in the issue body is absent from the current file
- A PR already exists for the branch (`gh pr list --head <branch>`)

## Verified Workflow

1. **Read the issue body** to identify the exact file and line marker to change.
2. **Read the target file** (use `Read` tool, not `cat`) to check current state.
3. **Check git log** for commits that already address the issue:
   ```bash
   git log --oneline -10
   ```
4. **Check for an existing PR**:
   ```bash
   gh pr list --head <branch-name>
   ```
5. If the marker is already gone **and** a PR exists:
   - Confirm PR body contains `Closes #<issue>`.
   - Confirm auto-merge is enabled (`gh pr view <PR> --json autoMergeRequest`).
   - Report completion — no further action needed.
6. If the marker is still present, proceed with normal implementation (remove/convert marker, commit, push, PR).

## Results & Parameters

```bash
# Step 2 — read target file
Read /path/to/file.mojo

# Step 3 — recent commits
git log --oneline -10

# Step 4 — existing PR check
gh pr list --head 3094-auto-impl

# Step 5 — verify auto-merge
gh pr view 3213 --json autoMergeRequest,state,title
```

Example output that confirms "already done":
```
3213  docs(training): remove stale NOTE and update TrainingLoop trait bounds  3094-auto-impl  OPEN
{"autoMergeRequest":{"mergeMethod":"REBASE","enabledAt":"2026-03-05T16:09:36Z",...},"state":"OPEN"}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-implement immediately | Started editing file before reading git log | Would have created a duplicate commit with no-op change | Always check git log and existing PRs before any edit |
| Search only for the NOTE text | Grepped for "NOTE: TrainingLoop" — found nothing | Marker was already removed | Absence of the marker is the key signal; check git history to understand why |
