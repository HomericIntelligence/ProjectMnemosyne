---
name: preflight-verify-before-implementing
description: "Use when: (1) starting work on any GitHub issue or prompt file, (2) resuming interrupted work on a pre-existing branch, (3) verifying PR/commit state before creating duplicates, (4) issue references prior sub-issues or codebase may have evolved since filing"
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [preflight, verification, github, duplicate-prevention, issue-management, workflow]
---

# Preflight: Verify Before Implementing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-28 |
| **Objective** | Prevent duplicate work and wasted effort by verifying current state before implementing |
| **Outcome** | Consistently prevents 30-60 minutes of duplicated or unnecessary work |
| **Key Learning** | Always run `git log --oneline -5` and `gh issue view <N> --json state` BEFORE any planning or implementation |

Consolidates: `auto-impl-preflight`, `check-impl-before-starting`, `issue-preflight-check`, `verify-issue-before-work`, `issue-triage-verify-before-implementing`, `verify-before-fix`.

## When to Use

Use this preflight **before any implementation work** when:

- Given a `.claude-prompt-<N>.md` auto-impl file on a pre-created worktree branch
- Assigned to implement a GitHub issue (new assignment or resumed work)
- About to create a branch, worktree, or PR for an issue
- An issue consolidates multiple prior sub-issues or codebase has evolved since filing
- A fix plan is provided but the PR may already be in the correct state
- Resuming work after an interruption or session restart

## Verified Workflow

### Quick Reference

```bash
# Run these 5 checks in order before ANY implementation work (~6 seconds total)

# 1. Check current branch commits (catches auto-impl duplicates)
git log --oneline -5

# 2. Check issue state
gh issue view <issue-number> --json state,title,closedAt

# 3. Check for existing PR on this branch
gh pr list --head $(git branch --show-current)

# 4. Search all PRs and commits for this issue
gh pr list --search "<issue-number>" --state all --json number,title,state
git log --all --oneline --grep="<issue-number>" | head -5

# 5. Check for worktree/branch conflicts
git worktree list | grep "<issue-number>"
git branch --list "*<issue-number>*"
```

### Decision Matrix

| Commits on branch | PR exists | Action |
|-------------------|-----------|--------|
| Yes (issue ref) | Yes (open) | Report done, stop — do NOT re-implement |
| Yes (issue ref) | No | Create PR, do NOT re-commit |
| No | No | Proceed with implementation |
| No | Yes (merged) | STOP — issue complete, do not duplicate |

### Detailed Steps

**Step 1: Check git log on the current branch (most important for auto-impl)**

```bash
git log --oneline -5
```

Look for commits referencing the issue number or describing the deliverables. In auto-impl workflows, a previous orchestration pass may have already committed.

**Step 2: Check issue state** — always run BEFORE reading the issue or planning

```bash
gh issue view <issue-number> --json state,title,closedAt
```

If `"state": "CLOSED"`, stop immediately. Do not proceed.

**Step 3: Check PR on current branch**

```bash
gh pr list --head $(git branch --show-current)
```

If open PR found and commits exist: report done, stop.

**Step 4: Verify current code state** — before writing any new code

For issues referencing specific files or functions:

```bash
# Verify referenced functions actually exist
grep -r "fn <function_name>" <file_path>

# Run existing tests FIRST
just test-group "<test-path>" "<test-file>"

# Search for stale TODOs referencing the issue
grep -r "TODO.*#<issue-number>" --include="*.mojo" .
```

**Step 5: Check worktree and branch conflicts**

```bash
git worktree list | grep "<issue-number>"
git branch --list "*<issue-number>*"
```

**Step 6: Load full context (only after all checks pass)**

```bash
gh issue view <issue-number> --comments
```

Always use `--comments` to load the full discussion thread — critical context is often in comments, not the issue body.

### For Fix Plans (`.claude-review-fix-<N>.md`)

1. Read the fix plan conclusion — if it says "no fixes required", verify independently before skipping
2. Check PR diff scope: `git diff main...HEAD --name-only`
3. A docs-only diff cannot cause Mojo/Python test failures — attribute CI failures to the diff

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Start implementing without checking git log | Read prompt file, began planning deletions | Commit `e738761d` already contained the exact implementation | Always run `git log --oneline -5` before any work on a pre-existing branch |
| Assume clean branch because `git status` is clean | Relied on `git status` showing nothing unstaged | Clean status means nothing unstaged — prior commits can have done all the work | `git status` clean != implementation not started; check `git log` too |
| Check only the issue state | Looked at issue description to understand deliverables | Issue state (open/closed) doesn't tell you if the branch already has commits | Check git log on the **current branch**, not just the issue |
| Assume auto-impl starts from a clean branch | Expected worktree to have no commits since branch was just created | Auto-impl orchestration may run multiple passes; branch may have prior commits | Never assume a fresh worktree — verify with git log |
| Jump straight to implementation | Started reading issue and planning without checking git log | Found PR #3176 was already open and commit `e21e00b9` had done all the work | Always check `git log --oneline -5` AND `gh pr list --head <branch>` before any implementation |
| Implement without verifying referenced code exists | Read issue plan suggesting functions needed implementation | All functions already existed in shape.mojo with full test coverage | Verify current codebase state; issues filed weeks/months ago may describe already-solved problems |
| Look for files at paths mentioned in issue | Issue referenced `shared/core/extensor.mojo:23-28` | File didn't exist — struct was renamed or never created | File paths in issues go stale; always glob/grep to find current locations |
| Treat all CI failures as blockers on a docs PR | Blocked merge on 3 failing test groups for a docs-only PR | Failures were pre-existing and unrelated to the diff | Attribute failures to the diff — docs changes cannot break Mojo/Python tests |
| Implement fixes when plan says none needed | Followed fix script template without reading the conclusion | Would create an empty or no-op commit | Always read the fix plan conclusion before taking action |
| Check PRs using `gh pr list --search` for closed issues | Expected issue state to tell you if work is done | Issue state doesn't reflect branch commit state | Check both `gh issue view` AND `git log` on the current branch |

## Results & Parameters

### Commands That Catch Duplicate Work

```bash
# Reveals existing commit immediately
git log --oneline -5

# Confirms PR already exists
gh pr list --head $(git branch --show-current)

# Finds work across all branches and states
git log --all --oneline --grep="<issue-number>" | head -5
gh pr list --search "<issue-number>" --state all --json number,title,state
```

### Stale TODO Search Pattern

```bash
# Find all actionable references to an issue
grep -r "TODO.*#<issue-number>\|Blocked on #<issue-number>" --include="*.mojo" .

# Verify cleanup is complete (should return empty)
grep -r "TODO.*#<issue-number>" --include="*.mojo" .
```

### Timing Benchmarks

| Phase | Time |
|-------|------|
| `git log --oneline -5` | <1s |
| `gh issue view` (state check) | ~1s |
| `gh pr list --head <branch>` | ~1s |
| `git log --all --grep` | ~2s |
| Worktree + branch check | ~1s |
| **Total** | **~6s** |

- Without preflight: 30-60+ minutes of duplicate/unnecessary work
- With preflight: ~6 seconds, immediate detection

### Success Criteria

All checks passed when:
- `git log` shows no commits referencing the issue
- Issue state is OPEN
- No merged PR covers this issue
- No worktree collision
- No orphaned branches (or all are merged)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3063 auto-impl worktree | Detected pre-existing commit `e738761d` in 2 tool calls |
| ProjectOdyssey | Issue #2672 training dashboard | Detected closed issue + existing implementation after 12 wasted calls |
| ProjectOdyssey | Issue #3013 ExTensor operations | All operations already existed; only stale TODOs needed updating |
| ProjectScylla | Issue #686 pre-flight skill | Confirmed current branch as expected in-progress state |
