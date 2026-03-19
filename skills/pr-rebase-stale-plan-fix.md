---
name: pr-rebase-stale-plan-fix
description: 'Rebase a diverged PR onto main when the automated fix plan has stale
  state information, resolving comment-only merge conflicts. Use when: automated fix
  plan claims branch is merged but PR is still open, comment-only changes conflict
  on rebase, or PR needs force-push + auto-merge after stale assessment.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Skill: PR Rebase with Stale Fix Plan Assessment

## Overview

| Property | Value |
|----------|-------|
| **Date** | 2026-03-06 |
| **Objective** | Rebase PR #3286 (issue #3073) onto main and enable auto-merge after automated fix plan contained stale state information |
| **Outcome** | Successfully rebased, resolved 1 comment-only conflict, force-pushed, auto-merge enabled |
| **Context** | ProjectOdyssey PR making comment-only changes (`# NOTE:` -> `# NOTE(#NNNN):`) was behind main by ~15 commits. Automated fix plan incorrectly stated the branch commit was already merged to main. |

## When to Use

Use this skill when:

- An automated fix plan (`.claude-review-fix-*.md`) claims the PR's changes are already in `main` but the PR is still open
- A PR with comment-only or cosmetic changes is blocked by a merge conflict on rebase
- You need to verify the actual state of a branch vs what a stale plan claims
- A PR needs to be rebased, force-pushed, and auto-merge enabled

**Key Indicators**:

- Fix plan says "commit `XXXXXXXX` is already in `main` history" but `git log --oneline origin/main | grep XXXXXXXX` returns nothing
- `git log --oneline origin/main..HEAD` shows the PR's commit is still only on the branch
- `git rebase origin/main` produces conflicts in files only touched by comments

## Verified Workflow

### 1. Verify Actual State (Don't Trust Stale Plans)

Always verify the actual git state before acting on automated fix plans:

```bash
# Check if the PR commit is actually in main
git log --oneline origin/main | grep <short-sha>

# Compare branch vs main
git log --oneline origin/main..HEAD   # commits in branch not in main
git log --oneline HEAD..origin/main   # commits in main not in branch

# Check PR state
gh pr view <PR_NUMBER> --json state,mergedAt,headRefName
```

If the plan says "already merged" but `origin/main..HEAD` shows the commit, the plan is stale — proceed with rebase.

### 2. Rebase onto Latest Main

```bash
git fetch origin
git rebase origin/main
```

If conflicts occur, check the conflict markers:

```bash
grep -n "<<<\|>>>\|===" <conflicted-file>
```

### 3. Resolve Comment-Only Conflicts

For comment-only conflicts (e.g., two branches updated the same comment differently), determine intent:

- **PR's goal**: The PR is adding `# NOTE(#NNNN):` format to issue-reference NOTE tags
- **Main's version**: May have updated the comment text with more detail
- **Resolution**: Combine — use the PR's `# NOTE(#NNNN):` format with main's more precise wording

Example conflict:
```
<<<<<<< HEAD
        # NOTE: Python data loader integration blocked by Track 4.
        # Tracked in #3076 (parent: #3059). Placeholder tensors used until Track 4 is ready.
=======
        # NOTE(#3076): Python data loader integration blocked by Track 4.
        # For now, we create placeholder tensors until Track 4 infrastructure is ready.
>>>>>>> 1d3afd6b (chore(cleanup): link workaround NOTEs to tracking issues)
```

Resolution: Take PR's `NOTE(#3076):` format + main's more detailed tracking text:
```mojo
        # NOTE(#3076): Python data loader integration blocked by Track 4.
        # Tracked in #3076 (parent: #3059). Placeholder tensors used until Track 4 is ready.
```

Then continue rebase:
```bash
git add <resolved-file>
git rebase --continue
```

### 4. Force-Push and Enable Auto-Merge

```bash
# Safe force-push (will fail if remote has new commits you haven't seen)
git push --force-with-lease origin <branch-name>

# Enable auto-merge with rebase strategy
gh pr merge <PR_NUMBER> --auto --rebase

# Verify auto-merge is set
gh pr view <PR_NUMBER> --json state,autoMergeRequest
```

Expected output confirms `autoMergeRequest.mergeMethod == "REBASE"`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting fix plan's "already merged" claim | Plan said commit `1d3afd6b` was in main; plan said close PR or re-target | `git log origin/main \| grep 1d3afd6b` returned nothing — commit was only on the branch | Always verify git state independently; automated plans can have stale snapshots |
| Assuming no conflicts for comment-only changes | Expected `git rebase origin/main` to succeed cleanly | Main had also updated the same comment in `trainer_interface.mojo` between branch creation and rebase | Comment-only PRs can still conflict if main updated the same comments independently |

## Results & Parameters

**Rebase command**:
```bash
git fetch origin && git rebase origin/main
```

**Conflict resolution strategy for NOTE tag format conflicts**:
- Keep PR's `# NOTE(#NNNN):` format (the PR's stated goal)
- Keep main's comment body text if it's more detailed/accurate

**Force-push command** (safe):
```bash
git push --force-with-lease origin <branch>
```

**Auto-merge command**:
```bash
gh pr merge <PR_NUMBER> --auto --rebase
```

**Verification that auto-merge is set**:
```bash
gh pr view <PR_NUMBER> --json state,autoMergeRequest | jq '.autoMergeRequest.mergeMethod'
# Expected: "REBASE"
```
