---
name: auto-impl-preflight
description: "Pre-flight check when given a .claude-prompt-<N>.md auto-impl file: verify the issue isn't already implemented on the current branch before doing any work. Use when: (1) given a prompt file named .claude-prompt-<N>.md, (2) working in a worktree branch like <N>-auto-impl, (3) before implementing any GitHub issue from an automated prompt."
category: tooling
date: 2026-03-05
user-invocable: false
---

# Auto-Impl Preflight Check

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Implement GitHub issue #3063 (delete deprecated skill directories) |
| **Outcome** | ✅ Detected work already done — commit + PR already existed |
| **Root Cause** | Auto-impl workflow runs in a pre-created worktree branch that may already have commits |
| **Key Learning** | Always check `git log --oneline -5` first when given a `.claude-prompt-<N>.md` file |

## When to Use

Use this preflight **before any implementation work** when:

- You are given a file named `.claude-prompt-<N>.md` to implement
- The working directory is a git worktree on a branch like `<N>-auto-impl`
- You are about to start implementing changes for a GitHub issue

The auto-impl workflow pre-creates branches and worktrees. A previous automation pass
may have already committed the implementation. Do not duplicate work.

## Verified Workflow

### Step 1: Check Git Log on Current Branch (30 seconds)

```bash
git log --oneline -5
```

Look for commits that:

- Reference the issue number (e.g., `#3063`)
- Say "Closes #N" in the message
- Describe the exact changes from the issue deliverables

**If found**: skip to Step 4 (verify PR).

### Step 2: Check for Existing PR

```bash
gh pr list --head <current-branch-name> 2>/dev/null || gh pr list --search "<issue-number>" --state all --limit 5
```

**If open PR found**: the work is complete. Report to user and stop.

### Step 3: Verify No Broken References

Only if steps 1-2 show no prior work, check whether references to deleted/changed items
still exist:

```bash
grep -r "plan-validate-structure\|plan-create-component" . --include="*.md" -l
```

### Step 4: Report Status and Stop

If work is already done:

1. State which commit and PR cover the issue
2. Confirm the PR is open or merged
3. Do NOT re-implement, re-commit, or open a duplicate PR

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Start implementing without checking git log | Read the prompt file, began planning the deletions | Commit `e738761d` already contained the exact implementation | Always run `git log --oneline -5` before any work |
| Check only the issue state | Looked at issue description to understand what needs doing | Issue state (open/closed) doesn't tell you if the branch already has commits | Check git log on the **current branch**, not just the issue |
| Assume auto-impl starts from a clean branch | Expected the worktree to have no commits since the branch was just created | Auto-impl orchestration may run multiple passes; branch may have prior commits | Never assume a fresh worktree — verify with git log |

## Results & Parameters

### Commands That Caught the Duplicate

```bash
# This revealed the existing commit immediately
git log --oneline -5
# Output: e738761d chore(skills): delete deprecated plan-* skill directories and update references

# This confirmed the PR already existed
gh pr list --head 3063-auto-impl
# Output: 3261  chore(skills): delete deprecated plan-* skill directories  3063-auto-impl  OPEN
```

### Time Saved

- **Without preflight**: Would have re-deleted already-deleted directories, gotten errors,
  attempted a duplicate PR that would fail
- **With preflight**: 2 tool calls, ~5 seconds, immediate detection

### Preflight Checklist

Before implementing from a `.claude-prompt-<N>.md` file:

- [ ] `git log --oneline -5` — any commits referencing the issue?
- [ ] `gh pr list --head $(git branch --show-current)` — open PR already?
- [ ] If both show existing work: report and stop, do not re-implement

## Related Skills

- `verify-issue-before-work` — checks issue state before starting (complements this skill)
- `issue-completion-verification` — handles closing issues when auto-close fails
- `gh-implement-issue` — end-to-end implementation when preflight confirms no prior work
