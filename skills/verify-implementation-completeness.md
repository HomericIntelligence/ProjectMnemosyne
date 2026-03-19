---
name: verify-implementation-completeness
description: 'Verify that a GitHub issue''s implementation is already complete before
  re-doing work. Use when: assigned to an existing branch for an issue, suspecting
  prior session completed the work, or a .claude-prompt file says ''implement issue
  #N''.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | documentation |
| **Trigger** | Assigned to implement issue on existing branch |
| **Outcome** | Avoid duplicate work; confirm PR exists if done |
| **Time saved** | Prevents re-implementing already-merged or committed work |

## When to Use

- A `.claude-prompt-<N>.md` file instructs you to "implement issue #N"
- You are working on a branch named `<N>-auto-impl` or similar
- The branch already has commits beyond the base
- `git log` shows a commit message referencing the issue
- You want to confirm state before starting implementation

## Verified Workflow

1. **Check git log** for existing commits referencing the issue:

   ```bash
   git log --oneline -10
   ```

2. **Read all target files** listed in the issue to see if changes are already applied.

3. **Check for an open PR** on the current branch:

   ```bash
   gh pr list --head <branch-name>
   ```

4. **If already complete**: Report findings to the user — commit hash, PR number, and that no further action is needed.

5. **If incomplete**: Proceed with implementation per issue requirements.

## Results & Parameters

### Issue #3070 — Template TODO Placeholders

- **Branch**: `3070-auto-impl`
- **Completion commit**: `9567628f docs(templates): mark intentional TODO placeholders with TEMPLATE: prefix`
- **PR**: `#3268` (open, linked to issue)
- **Files verified**: 5 template files — all had `# TEMPLATE:` prefix and header comments

### Key Signals That Work Is Done

| Signal | Command |
|--------|---------|
| Commit message matches issue title | `git log --oneline -5` |
| PR exists on branch | `gh pr list --head <branch>` |
| Target files contain expected changes | `Read` each file |
| `git status` shows clean working tree | `git status` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Skipping file verification | Trusting commit message alone | Commit could exist but be partial | Always read target files to confirm |
| Re-running implementation | Starting changes without checking history | Would duplicate already-committed work | Check `git log` first on any existing branch |
| Checking only `git status` | Looking at untracked/modified files | Clean status doesn't prove issue is done | Must check log AND files AND PR existence |
