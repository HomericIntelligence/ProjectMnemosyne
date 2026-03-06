---
name: no-op-review-fix-detection
description: "Recognize when a review-fix plan requires zero implementation changes and verify the worktree is already correct. Use when: a .claude-review-fix-*.md plan explicitly states no fixes are required."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | no-op-review-fix-detection |
| **Category** | tooling |
| **Trigger** | `.claude-review-fix-*.md` plan with "No fixes required" conclusion |
| **Outcome** | Confirm worktree is already in correct state; avoid phantom commits |

## When to Use

- A `.claude-review-fix-*.md` plan is provided and its "Fix Order" section says "No fixes required"
- A PR review summary concludes "The PR is ready to merge as-is"
- You need to verify the committed state matches the plan before the external script pushes
- You want to avoid creating an empty or unnecessary commit on an already-clean branch

## Verified Workflow

1. **Read the plan file** — look for the "Problems Found" and "Fix Order" sections
2. **Confirm no-op** — if both sections say none/no fixes, skip all implementation steps
3. **Check git status** — run `git status && git log --oneline -5` to verify the expected commit is present
4. **Confirm and report** — tell the user the fix is already committed and no action is needed
5. **Do NOT create an empty commit** — the script that calls this agent handles pushing

### Key Commands

```bash
# Verify worktree state
git status && git log --oneline -5

# Confirm the target change is in history
git log --oneline --grep="<expected commit keyword>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Blindly following "implement all fixes" instruction | Started looking for code to change despite the plan saying no fixes needed | The task wrapper says "implement all fixes" even when the plan says there are none — the wrapper is generic | Always read the plan body first; the wrapper instruction is a template, not a guarantee of work |
| Creating a commit anyway to satisfy the script | Considered making a trivial no-op commit | Would pollute history and could confuse CI or rebase operations | An empty/no-op commit is worse than no commit; trust the plan |

## Results & Parameters

### Plan File Pattern

```
## Problems Found
None. The PR:
- <reason 1>
- <reason 2>

## Fix Order
No fixes required.
```

When this pattern is present, the correct action is:

1. Verify `git status` shows no modified tracked files
2. Verify the expected commit appears in `git log --oneline -5`
3. Report to user: "No action needed — fix already committed"
4. Do NOT push (the calling script handles that)

### Worktree State Verification

```bash
git status           # Should show: "nothing to commit" or only untracked files
git log --oneline -5  # Should show the expected change at HEAD or recently
```
