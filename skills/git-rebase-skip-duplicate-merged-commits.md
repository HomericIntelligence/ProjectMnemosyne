---
name: git-rebase-skip-duplicate-merged-commits
description: >-
  Use when: (1) a PR branch has commits that duplicate work already merged upstream,
  (2) a rebase onto origin/main encounters conflicts from commits whose content is
  identical to already-merged work, (3) you want to land the branch cleanly on top
  of main with no duplicate commits, (4) a branch was created before upstream completed
  the same work and now both exist—skip deduplicates automatically, (5) you have
  validated that the conflicts are solely from duplicate/superseded content, not new work.
  Use `git rebase --skip` to skip those duplicate commits during rebase instead of
  manually resolving conflicts that would delete/undo changes main already has.
category: ci-cd
date: 2026-07-06
version: "1.0.0"
verification: verified-local
---

# Git Rebase Skip for Duplicate Merged Commits

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-06 |
| **Objective** | Recognize when a branch's commits are duplicates of already-merged upstream work and use `git rebase --skip` to cleanly land the branch on top of main without the duplicate commits |
| **Outcome** | Branch rebased successfully with duplicate commits skipped, ending cleanly on top of origin/main with no manual conflict resolution needed |
| **Verification** | verified-local |

## When to Use

Use this skill when:

1. **A PR branch has duplicate commits**: The branch was created before upstream completed the same work.
   Both the branch and upstream have commits with the same or nearly-identical content.

2. **Rebase encounters conflicts from duplicate content**: Running `git rebase origin/main` hits
   conflicts where the conflicting file versions are **identical or nearly identical** between
   the branch's commit and the already-merged upstream commit.

3. **You want to land cleanly on main**: The goal is to have the branch end up on top of
   origin/main with no leftover duplicate commits, not to preserve the duplicate history.

4. **Validation confirmed no unique work is lost**: You've checked that:
   - The conflicting commits on the branch match already-merged commits on origin/main
   - There is no unique work in the conflicting commits that would be lost by skipping
   - All post-conflict commits in the branch (if any) are unique additions

5. **Manual conflict resolution would just discard the changes**: Instead of manually resolving
   merge conflicts that would require deleting the branch's changes (because main has them already),
   skip the commits that are now redundant.

### Trigger Phrases

- "Branch has duplicate commits after upstream merged the same work"
- "Rebase conflicts but all changes are already on main"
- "Skip these duplicate commits and land cleanly on main"
- "Branch created before upstream finished; now both have the same commits"
- "Use --skip instead of resolving; the work already merged"

## Verified Workflow

### Quick Reference

```bash
# 1. Fetch to ensure origin/main is current
git fetch origin main

# 2. Start a rebase onto origin/main
git rebase origin/main

# 3. When a conflict appears (conflicts on duplicate content)
#    Read the conflict markers to confirm the content is identical/duplicated
git diff --cached                                    # review staged changes
git log origin/main..HEAD --oneline | head -5       # upcoming commits on the branch

# 4. If the conflicting commit is a duplicate (already on main):
git rebase --skip                                    # skip this commit, move to next

# 5. Repeat step 4 for each duplicate commit
#    When rebase completes, branch is on top of origin/main

# 6. Verify the branch is clean
git log --oneline origin/main..HEAD                 # should show only non-duplicate commits
git status                                          # should be clean ("nothing to commit")

# 7. Validate the result
git log --oneline -3                                # verify commits present
git diff origin/main -- .                           # verify tree matches intent
```

### Detailed Steps

#### Step 1: Prepare for rebase

```bash
# Ensure you have the latest main
git fetch origin main

# Create a worktree if doing this in an isolated way (recommended for PRs)
git worktree add /tmp/rebase-<branch> origin/<branch>
cd /tmp/rebase-<branch>
git fetch origin main
```

#### Step 2: Identify duplicate commits before rebasing

Before you start the rebase, understand which commits are duplicates:

```bash
# See what commits are on your branch
git log --oneline origin/main..HEAD

# For each commit, check if it appears (by message) on main
# or if the same files with the same content were already merged
git log origin/main --oneline | grep -i "pipeline coordinator"   # example: search for part of your commit message

# If found on main, that commit is a duplicate and should be skipped during rebase
```

#### Step 3: Start the rebase and encounter conflicts

```bash
# Start rebasing onto origin/main
git rebase origin/main

# Git will stop at the first conflict and show:
# CONFLICT (content): <file path>
# Automatic merge failed; fix conflicts and then run "git rebase --continue".
```

#### Step 4: Analyze the conflict

When the rebase stops at a conflict:

```bash
# See which commit caused the conflict
git status

# Look at the conflicting file to understand the conflict
cat <conflicting-file> | head -50                  # preview the conflict markers

# Compare the conflict markers to see if content is truly identical
# If the markers show <<<<<< / ===== / >>>>>> and both sides are the same,
# this is a duplicate commit you can safely skip
```

#### Step 5: Decide to skip or resolve

If the conflicting commit is a duplicate (already merged on main):

```bash
# SKIP this commit — it's already on main
git rebase --skip

# Git will move to the next commit in the rebase sequence
# If the next commit also conflicts due to duplication, skip again
# Repeat until all duplicate commits are skipped
```

If the conflicting commit has unique work not on main, resolve manually:

```bash
# Edit the file to resolve the conflict (keep the unique parts)
vim <file>
git add <file>
git rebase --continue
```

#### Step 6: Complete the rebase

When all commits have been processed (skipped or resolved):

```bash
# Git will report:
# Successfully rebased X commits onto origin/main

# Verify the rebase was successful
git status                                   # "On branch <branch>" (clean)
git log --oneline -5                         # see the final commits
```

#### Step 7: Validate the result

```bash
# Confirm only non-duplicate commits remain
git log --oneline origin/main..HEAD          # branch-only commits (should have no duplicates)

# Verify the tree is correct
git diff origin/main -- .                    # should show only intended changes

# Compare file counts and content
git ls-tree --name-only -r HEAD | wc -l     # file count
git ls-tree --name-only -r origin/main | wc -l

# Test the content matches expectations (repo-specific)
pixi run pytest tests/ -x                    # run tests
pixi run mypy                                # type check
```

### Example: Issue #1817

**Scenario**: Branch `1817-auto-impl` on ProjectHephaestus had commits implementing
the pipeline coordinator. Work was completed and merged in PR #1851 on origin/main.
The local branch `1817-auto-impl` still had the original (duplicate) commits.

**Problem**: Commits on the branch conflicted with the already-merged upstream version,
but the content was identical—just a different commit SHA due to the merge.

**Solution**:

```bash
# 1. Fetch current main
git fetch origin main

# 2. Start rebase
git rebase origin/main

# 3. Conflicts appear (the pipeline coordinator commits already exist on main)
# 4. Check one conflict to confirm it's a duplicate:
git log origin/main --oneline | grep -i "pipeline"
# Found: "feat(automation): pipeline coordinator implementation" on main

# 5. Since the commit is a duplicate, skip it
git rebase --skip

# 6. Next conflict appears (another duplicate commit)
git rebase --skip

# 7. Rebase completes
# Successfully rebased 7 commits onto origin/main

# 8. Verify the branch is clean and on top of main
git log origin/main..HEAD --oneline
# Should show only commits that weren't duplicated (if any)

git status
# On branch 1817-auto-impl
# nothing to commit, working tree clean
```

**Result**: Branch `1817-auto-impl` now sits cleanly on top of origin/main with no
duplicate commits. Ready to push and open a follow-up PR if needed.

## Decision Tree

**During rebase, when a conflict appears:**

```
Does the conflicting commit appear on origin/main?
├─ YES (message matches, content is identical)
│   └─ This is a duplicate → git rebase --skip
│
└─ NO (unique work not yet on main)
    └─ This has unique content → resolve manually, git add, git rebase --continue
```

## Common Patterns

### Pattern 1: Exact duplicate commits

**Scenario**: Branch was created with commits A, B, C. Before the branch could be merged,
upstream merged A, B, C independently. Now the branch is a duplicate.

**Git output**:
```
CONFLICT (content): hephaestus/automation/coordinator.py
Automatic merge failed; fix conflicts and then run "git rebase --continue".
```

**Resolution**:
```bash
git log origin/main --oneline | grep -i "coordinator"  # found on main
git rebase --skip
```

### Pattern 2: Partial duplicates with additions

**Scenario**: Branch has commits A, B, C, D, E. Upstream merged A, B, C.
Branch has unique work in D and E.

**Rebase behavior**:
```bash
git rebase origin/main   # conflicts on A, B, C (duplicates)
git rebase --skip        # skip A
git rebase --skip        # skip B
git rebase --skip        # skip C
# (D and E apply cleanly or with minor conflicts to be resolved)
```

### Pattern 3: Detecting false conflicts (redundant file deletes)

**Scenario**: A commit tried to delete a file that main had already deleted.
This manifests as a **modify/delete conflict** even though the end goal is the same.

**Git output**:
```
CONFLICT (modify/delete): <file> deleted in rebase and modified in HEAD
```

**Analysis**:
```bash
git log origin/main --diff-filter=D -- <file>  # find when main deleted it
# If found, the delete already happened upstream
git rm <file>                                   # resolve: file should be deleted
git rebase --continue                          # complete this commit's rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|--------------|--------|
| Manually resolving each conflict | Took each conflict and edited the files to match main | Time-consuming, error-prone, and missed the core insight that these commits were fully redundant | Trust `git rebase --skip`; if a commit is a complete duplicate, skipping is safer and faster than editing |
| Trying to cherry-pick only "unique" parts of duplicate commits | Attempted to keep pieces of the conflicting commits | The entire commit was a duplicate; attempting to extract pieces lost important metadata and left the branch in an inconsistent state | When a commit is fully duplicated upstream, skip the entire commit; partial preservation is a different use case (cherry-pick) |
| Continuing the rebase after conflicts without understanding if commits were duplicates | Ran `git rebase --continue` assuming the conflict resolution was correct | Led to phantom/duplicate commits on the branch, creating confusing history and making the final state unclear | Always verify a commit is truly a duplicate (via `git log origin/main --oneline \| grep`) before deciding to skip |
| Assuming all rebase conflicts from the same commit were duplicates | Saw conflicts and assumed because one file conflicted, the entire commit was a duplicate | Some commits had unique work on other files; skipping them would have lost that work | Inspect the full commit (`git show REBASE_HEAD`) before skipping; confirm there is no unique work |
| Not stashing uncommitted work before rebasing | Started rebase without a clean working tree | The rebase failed with "Cannot rebase: You have uncommitted changes" | Always `git stash` uncommitted work before `git rebase`, or use a worktree |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Branch** | `1817-auto-impl` (ProjectHephaestus) |
| **Upstream** | `origin/main` |
| **Already-merged PR** | PR #1851 |
| **Duplicate commits encountered** | Multiple (pipeline coordinator implementation) |
| **Rebase method** | `git rebase origin/main` with `--skip` for duplicates |
| **Commits skipped** | 7 duplicate commits |
| **Final state** | Clean, on top of origin/main, ready for follow-up work |
| **Verification** | `git log origin/main..HEAD` empty (or shows only new commits if any) |
| **Verification level** | verified-local (git state verified, no PR/CI checks yet) |

## References

- [git-branch-state-triage-and-recovery](git-branch-state-triage-and-recovery.md) — Broader branch state recovery patterns; this skill focuses on the `--skip` rebase pattern specifically
- [pr-rebase-conflict-resolution-patterns](pr-rebase-conflict-resolution-patterns.md) — Comprehensive rebase conflict resolution playbook for various conflict types
- Git documentation: `git rebase --skip` vs `git rebase --continue` vs `git rebase --abort`
