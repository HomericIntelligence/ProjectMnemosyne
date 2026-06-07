---
name: stale-branch-superseded-by-main-diagnosis
description: "Diagnose whether a long-lived branch has zero remaining value because main has already absorbed all of its changes. Use when: (1) a branch is many commits behind main and its remote tracking ref is gone, (2) the task is 'get all PRs merged' but you first need to know if there are any PRs worth creating, (3) a branch shows hundreds of staged/unstaged file differences vs main and you need to determine net new contribution."
category: tooling
date: 2026-06-07
version: "1.0.0"
verification: verified-ci
user-invocable: false
tags: [git, branch, stale, triage, superseded, fork-point, merge-base, diff-filter, diagnosis]
---

# Stale Branch Superseded by Main — Diagnosis

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Determine whether `feature/myrmidon-merge-triage` (32 ahead, 525 behind main, remote gone) had any remaining contribution not already absorbed by main |
| **Outcome** | Success — branch confirmed fully superseded; no PRs needed |

## When to Use

- A branch is many commits behind main **and** its remote tracking ref is gone (`[gone]` in `git branch -vv`)
- The task is "get all open PRs merged" — check `gh pr list --state open` first; if zero open PRs the premise has changed
- A `git diff origin/main...HEAD` shows a large file count difference but you suspect most of it is merge noise
- Files present in HEAD but absent from main could be "new work" or "old work that main later consolidated/deleted"
- Staged files with AD status in `git status --short` (added in index, deleted from working dir) — need to determine if their content is already on main

## Verified Workflow

### Quick Reference

```bash
# Step 0: check premise first
gh pr list --state open

# Step 1: find fork point
FORK=$(git merge-base HEAD origin/main)
echo "Fork point: $FORK"

# Step 2: file inventory — three-way comparison
git ls-tree --name-only -r HEAD skills/ | sort > /tmp/head_skills.txt
git ls-tree --name-only -r origin/main skills/ | sort > /tmp/main_skills.txt
comm -23 /tmp/head_skills.txt /tmp/main_skills.txt  # in HEAD only (possibly new or old)
comm -13 /tmp/head_skills.txt /tmp/main_skills.txt  # in main only (post-branch additions)
comm -12 /tmp/head_skills.txt /tmp/main_skills.txt  # in both (modified candidates)

# Step 3: for files in HEAD not on main — find how main disposed of them
git log --diff-filter=D --oneline origin/main -- <path> | head -1
# message like "feat(skill-merge): consolidate N skills into <bundle>" = intentional; empty = unknown

# Step 4: for files in both — compare versions
grep "^version:" skills/<name>.md       # branch version
git show origin/main:skills/<name>.md | grep "^version:"  # main version
# if main version > branch version → main is newer; branch change is stale

# Step 5: staged-index no-op check
# If all staged files are already on main with identical content, the index is a no-op
git ls-files --stage | awk '{print $1, $4}' | sort > /tmp/staged_hashes.txt
git ls-tree -r origin/main | awk '{print $3, $4}' | sort > /tmp/main_hashes.txt
comm -23 /tmp/staged_hashes.txt /tmp/main_hashes.txt  # staged files NOT on main (true new work)
```

### Detailed Steps

1. **Check the premise**: run `gh pr list --state open` before any branch archaeology. If there are zero open PRs, report that to the user — the task "get all PRs merged" is already done. Do not proceed to branch analysis.

2. **Find the fork point**: `git merge-base HEAD origin/main` gives the SHA where the branch diverged. All analysis is relative to this point.

3. **Three-way file inventory**: Compare `git ls-tree` outputs for HEAD and origin/main on the relevant directories. Pipe through `sort` then `comm` to get three sets: HEAD-only, main-only, both.

4. **For each HEAD-only file**: run `git log --diff-filter=D --oneline origin/main -- <path>`. A commit message containing "consolidate", "merge", "absorb" means main intentionally deleted it via a consolidation PR. An empty result means the file genuinely never reached main — this is rare if the branch is old.

5. **For each file in both**: compare `version:` frontmatter. If main's version number is strictly greater, main has the newer copy and the branch's version is stale.

6. **Staged index check**: if `git status --short` shows many AD-status files (added in index, deleted in working tree), use `git ls-files --stage` to hash-compare against `git ls-tree origin/main`. If every staged hash matches a main hash, the staged index is a complete no-op.

7. **Apply the three-condition test**: a branch is fully superseded when **all three** are true:
   - Its deletions are already absent from main (condition 1)
   - Its modified files have lower version numbers than main's versions (condition 2)
   - Its "new" files are already present on main (condition 3)

   When all three hold, the branch has zero net contribution and can be discarded.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Treating HEAD-only files as unmerged value | Assumed "file present in HEAD but not in main" = "work not yet on main" | Most of the 1,193 HEAD-only files were OLD files that main subsequently deleted or consolidated through later PRs after the branch diverged | Always check HOW a file left main (`--diff-filter=D`) before assuming it was never there |
| Using plain `git log` to find deletions | `git log --oneline origin/main -- <path>` showed nothing | Plain log only shows commits that touched the file; use `--diff-filter=D` to specifically find the deletion commit | `--diff-filter=D` is required to reliably surface the commit that removed a file |
| Treating AD status as uncommitted work | `git status --short` showed hundreds of AD lines (added in index, deleted from working dir) and looked like staged changes needing attention | AD status is normal for branches created in worktrees that were not fully restored to disk — the files exist in the staged index but not on disk | AD means "added in index, deleted from working dir" — verify if the hashes already match main before treating as new work |

## Results & Parameters

### Decision Matrix

| Condition | Check Command | "Stale" Verdict |
| --------- | ------------- | --------------- |
| Deletions already absent from main | `comm -23 head.txt main.txt` → each result: `git log --diff-filter=D origin/main -- <path>` | consolidation commit found for all |
| Modified files have lower version | `grep "^version:" skills/<f>.md` vs `git show origin/main:skills/<f>.md \| grep "^version:"` | branch version < main version |
| "New" files already on main | `comm -23 staged_hashes.txt main_hashes.txt \| wc -l` | result = 0 |

### Expected Output for a Fully Superseded Branch

```
# gh pr list --state open
No pull requests match your search

# comm -23 /tmp/head_skills.txt /tmp/main_skills.txt | wc -l
1193    ← look alarming, but all are old deletions

# git log --diff-filter=D --oneline origin/main -- skills/old-skill.md | head -1
a3f2b1c feat(skill-merge): consolidate 12 skills into automation-bundle (C086)

# comm -23 staged_hashes.txt main_hashes.txt | wc -l
0       ← zero true new files; staged index is a no-op
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | Branch `feature/myrmidon-merge-triage` (32 ahead, 525 behind, remote gone) | Confirmed fully superseded; no PRs opened |

## References

- [diverged-branch-cherry-pick-fix.md](diverged-branch-cherry-pick-fix.md) — related: recovering a diverged branch that still has value worth keeping
- [fix-stale-prs-and-branches.md](fix-stale-prs-and-branches.md) — related: rebasing/fixing open PRs with CI failures
- [clean-branches.md](clean-branches.md) — related: bulk cleanup of local/remote stale branches
