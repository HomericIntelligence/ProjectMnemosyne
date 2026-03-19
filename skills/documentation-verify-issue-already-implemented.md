---
name: verify-issue-already-implemented
description: 'Check whether a GitHub issue is already implemented before starting
  work. Use when: (1) handed an issue via .claude-prompt-NNNN.md with branch already
  checked out, (2) git log shows a recent commit matching the issue title, (3) an
  open PR already exists for the branch.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Verify Issue Already Implemented

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Confirm a GitHub issue is already done before re-doing the work |
| **Outcome** | Detected that issue #3090 was fully implemented (commit `47f87aba`, PR #3201 open); no duplicate work performed |
| **Related Issues** | ProjectOdyssey #3090, #2704 |

## When to Use This Skill

Use this skill immediately when:

- You receive a `.claude-prompt-NNNN.md` prompt file telling you to implement an issue
- The working branch name is `<N>-auto-impl` or similar, suggesting automated issue dispatch
- The repo/worktree was pre-configured before you were invoked (branch already checked out)

These are signs that the issue may have been dispatched to a fresh agent even though a previous
agent already completed the work.

**Triggers:**

- `git log --oneline -5` shows a commit with a message that matches the issue title
- `git status` shows a clean tree with no outstanding work
- `gh pr list --head <branch>` returns an open PR number

## Verified Workflow

### Step 1: Read the Prompt File

```bash
cat .claude-prompt-<N>.md
```

Note the issue number, branch name, and expected deliverables.

### Step 2: Check git log

```bash
git log --oneline -5
```

If the top commit message matches the issue title (e.g., "docs(testing): document epsilon values
in gradient checking"), the implementation is already done.

### Step 3: Check git status

```bash
git status
```

A clean tree (no staged/unstaged changes, only untracked `.claude-prompt-*.md`) confirms
no pending work remains.

### Step 4: Check for existing PR

```bash
gh pr list --head <branch-name>
```

If a PR is open and linked to the branch, the full workflow (implement → commit → push → PR)
is already complete.

### Step 5: Verify the implementation

Quickly read the affected files to confirm the changes match the issue requirements:

```bash
# Read the specific lines mentioned in the issue
grep -n "GRADIENT_CHECK_EPSILON\|epsilon=3e-4" shared/testing/layer_testers.mojo
```

Confirm the success criteria from the issue are met.

### Step 6: Report and stop

Report the findings to the user:

- Which commit implemented the issue (hash + message)
- Which PR is open (number + URL)
- That all success criteria are met
- No further action is needed

Do NOT:

- Re-implement anything already done
- Create a second commit or PR
- Modify files that are already correct

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Starting implementation immediately | Reading the prompt and jumping to implementation without checking git log | Would have created duplicate commits and a second PR | Always check `git log` and `gh pr list` before touching any files |
| Assuming the branch is new | Treating a pre-checked-out branch as a fresh workspace | The branch `3090-auto-impl` already had a commit and open PR | A pre-configured worktree does not mean the work is pending |

## Results & Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Detection signal | `git log --oneline -5` | Top commit message matches issue title |
| Confirmation signal | `gh pr list --head <branch>` | Returns an open PR number |
| False-positive risk | Low | Only skip if BOTH signals are positive and code matches requirements |
| Time saved | ~5-10 minutes | Avoided re-implementing a 3-location documentation update |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3090, PR #3201 | Branch `3090-auto-impl`; commit `47f87aba` already done |
