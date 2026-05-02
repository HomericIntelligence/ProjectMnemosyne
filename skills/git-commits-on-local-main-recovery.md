---
name: git-commits-on-local-main-recovery
description: "Recover when commits accidentally land on local main instead of a feature branch. Use when: (1) git branch --show-current shows 'main' but work was done there, (2) git log shows commits on local main ahead of origin/main, (3) main is protected and pushing directly will be rejected, (4) you need to salvage multiple commits without losing any work."
category: tooling
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# git-commits-on-local-main-recovery

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Recover commits made on local main and move them to a feature branch for PR submission |
| **Outcome** | Successful — branch created, pushed, PR #302 opened in ProjectHephaestus |
| **Verification** | verified-local — branch created, pushed, and PR opened successfully |

## When to Use

- `git branch --show-current` returns `main` after completing implementation work
- `git log --oneline origin/main..HEAD` shows commits that belong on a feature branch
- Pushing to `origin/main` is rejected because the branch is protected
- Multiple commits (feature, fix, test) all landed on local main by mistake
- Work session started from main without first creating a feature branch

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the situation
git branch --show-current          # Should show "main"
git log --oneline origin/main..HEAD  # Shows commits to rescue

# 2. Create feature branch at current HEAD (all commits included)
git checkout -b feat/<description>

# 3. Push the feature branch
git push -u origin feat/<description>

# 4. Create PR as normal
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge <PR-number> --auto --rebase
```

### Detailed Steps

1. **Verify the state** — confirm you are on main with commits ahead of origin:

   ```bash
   git branch --show-current
   git log --oneline origin/main..HEAD
   ```

   Expected output:
   ```
   main
   6723cfd test(automation): add unit tests...
   42c33c4 feat(automation): update run_automation_loop.sh...
   9873ddf feat(automation): add ci_driver module...
   ...
   ```

2. **Create a feature branch at the current HEAD** — this is the key step:

   ```bash
   git checkout -b feat/<issue-number>-<description>
   ```

   `git checkout -b` creates a new branch pointer at the current HEAD. All commits that were on local main are now on the feature branch. Local main stays at origin/main (diverged) but that is harmless — you will now work from the feature branch.

3. **Push the new feature branch** (NOT main):

   ```bash
   git push -u origin feat/<issue-number>-<description>
   ```

4. **Create the PR and enable auto-merge**:

   ```bash
   gh pr create --title "feat: <description>" --body "Closes #<issue-number>"
   gh pr merge <PR-number> --auto --rebase
   ```

5. **Optional: Reset local main** (cleanup after PR merges):

   Once the PR is merged, reset local main to match origin:

   ```bash
   git checkout main
   git fetch origin
   git reset --hard origin/main
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `git push origin main` | Push commits directly to protected main | Branch protection rules reject direct pushes to main | Never push directly to main; always use a feature branch + PR |
| `git reset --hard origin/main` | Undo all commits to start fresh | This destroys all the uncommitted work in local history | Never use reset --hard when there is work to save; create the branch first |

## Results & Parameters

### Why `git checkout -b` Works

When you run `git checkout -b <new-branch>` from any position:

- Git creates a new branch label pointing to the **current HEAD commit**
- All commits already in the local history are now reachable from the new branch
- The old branch label (main) stays pointing where it was before (origin/main SHA)
- Nothing is copied, moved, or deleted — only the branch pointer is new

This means local main will appear "diverged" from origin/main until you reset it, but the feature branch has a clean linear history from origin/main through all the rescue commits.

### State After Recovery

```
origin/main: A -- B -- C  (protected, unchanged)
local main:  A -- B -- C -- D -- E -- F  (diverged, harmless)
feat/branch: A -- B -- C -- D -- E -- F  (same as local main, pushed, PR created)
```

### Prevention

Always create a feature branch before starting work:

```bash
git fetch origin
git checkout -b feat/<issue-number>-<description> origin/main
```

Starting from `origin/main` (not `HEAD`) ensures the branch base is current even if local main is stale.

### Real-World Example

6 automation pipeline commits landed on local main in ProjectHephaestus:

```bash
$ git log --oneline origin/main..HEAD
6723cfd test(automation): add unit tests...
42c33c4 feat(automation): update run_automation_loop.sh...
9873ddf feat(automation): add ci_driver module...
395fe45 feat(automation): add address_review module...
0050e0c feat(automation): add pr_reviewer module...
7d14906 feat(automation): add plan_reviewer module...

$ git checkout -b feat/automation-6-phase-pipeline
$ git push -u origin feat/automation-6-phase-pipeline
# PR #302 opened successfully
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | 6 automation pipeline commits on local main | PR #302 opened via feat/automation-6-phase-pipeline |
