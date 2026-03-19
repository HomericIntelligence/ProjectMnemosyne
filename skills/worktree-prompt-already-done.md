---
name: worktree-prompt-already-done
description: 'Detect when a worktree issue prompt''s implementation is already complete
  in git history. Use when: invoked with a .claude-prompt-<N>.md in a worktree branch
  and work may already be done.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Worktree Prompt Already Done

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Implement GitHub issue #3060 (delete deprecated schedulers.mojo stub) |
| **Outcome** | Work already complete - HEAD commit and open PR detected immediately |
| **Root Cause** | Auto-impl pipeline had already run; worktree prompt file was stale |
| **Key Learning** | Always check `git log --oneline -3` and `gh pr list --head <branch>` before any implementation work |

## When to Use

Use this verification workflow when:

- You are invoked via a `.claude-prompt-<N>.md` file in a worktree
- The branch is named `<N>-auto-impl` or similar
- The issue describes a simple cleanup/deletion task
- You suspect the auto-implementation pipeline may have already run

## Verified Workflow

### Step 1: Read the Prompt File

```bash
cat .claude-prompt-<N>.md
```

Note the issue number, branch name, and task description.

### Step 2: Check Recent Git History First

```bash
git log --oneline -5
```

**Key insight**: If the most recent commit message matches the task description (e.g., `cleanup(training): delete deprecated schedulers.mojo stub`), the work is already done.

### Step 3: Verify the Target State

Confirm the expected outcome is already in place:

```bash
# For a deletion task - verify the file is gone
ls <expected-directory>

# For a general task - spot-check the relevant files
```

### Step 4: Check for an Existing PR

```bash
gh pr list --head <branch-name>
```

If a PR exists and is open, the work is complete and awaiting review/merge.

### Step 5: Confirm and Report

Report the status clearly:
- Commit hash that completed the work
- PR number and status
- No further action needed

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Starting implementation without checking git log | Read the prompt file, planned to search for imports and delete the file | The file was already deleted in HEAD commit `a7e56eb1` | Always run `git log --oneline -3` before any planning |
| Checking only the directory listing | Confirmed `schedulers.mojo` was absent from directory listing | This was correct but incomplete - needed to also confirm PR exists | Combine directory check with `gh pr list --head <branch>` |

## Results & Parameters

### Correct Verification Sequence

```bash
# 1. Read prompt to get issue number and branch
cat .claude-prompt-3060.md

# 2. Check recent commits (< 1 second)
git log --oneline -5
# Output: a7e56eb1 cleanup(training): delete deprecated schedulers.mojo stub
# => Work already done in HEAD

# 3. Verify target state
ls shared/training/
# => schedulers.mojo absent, schedulers/ directory present

# 4. Check for existing PR
gh pr list --head 3060-auto-impl
# Output: 3250  cleanup(training): delete deprecated schedulers.mojo stub  3060-auto-impl  OPEN
# => PR exists and is open

# 5. Report: done, no action needed
```

### Time Saved

- **Without verification**: Would have searched for imports, run mojo build, etc. (~10 tool calls)
- **With verification**: 4 tool calls, ~10 seconds, immediate answer

### Distinguishing Scenarios

| git log result | PR exists | Action |
|---------------|-----------|--------|
| HEAD matches task | Yes (OPEN) | Report complete, no action |
| HEAD matches task | No | Check if merged; may need to create PR |
| HEAD does NOT match | No | Proceed with implementation |
| HEAD does NOT match | Yes (OPEN) | Check PR diff; may be partial |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3060, branch `3060-auto-impl` | [notes.md](../../references/notes.md) |

## Related Skills

- `verify-issue-before-work` - Broader check before starting any issue work
- `issue-completion-verification` - When PR automation fails to auto-close an issue
- `gh-check-ci-status` - Verify CI on the existing PR
