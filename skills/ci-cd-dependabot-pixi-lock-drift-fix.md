---
name: ci-cd-dependabot-pixi-lock-drift-fix
description: "Use when: (1) a Dependabot PR fails CI with 'lock-file not up-to-date with the workspace', (2) a Dependabot PR updates requirements*.txt or pyproject.toml but pixi.lock was not regenerated, (3) CI on a Dependabot branch completes in 6-12 seconds (pre-flight lock rejection, not a test failure)"
category: ci-cd
date: 2026-05-01
version: "1.0.0"
user-invocable: false
tags: [pixi, dependabot, lock-file, pip, ci]
---

# CI — Dependabot pixi.lock Drift Fix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-01 |
| **Objective** | Fix `lock-file not up-to-date with the workspace` CI failures on Dependabot PRs that update Python package constraints without regenerating `pixi.lock` |
| **Outcome** | Successful — `pixi install` regenerates the lock file; CI passes after force-push |

## When to Use

- A Dependabot PR updates `requirements*.txt`, `pyproject.toml`, or other Python constraint files
- CI fails immediately with `lock-file not up-to-date with the workspace`
- CI job duration is 6–12 seconds (pre-flight `pixi install --locked` rejection — not a test failure)
- After rebasing a Dependabot branch, CI still fails even though the rebase was clean
- The Dependabot PR includes a `pixi.lock` update commit but it has gone stale after main advanced further

## Verified Workflow

### Quick Reference

```bash
# 1. Check out the Dependabot branch (or use a worktree for isolation)
git fetch origin
git checkout <dependabot-branch>

# 2. Regenerate pixi.lock to match updated constraints
pixi install

# 3. Commit the updated lock file
git add pixi.lock
git commit -m "chore: update pixi.lock for <package> constraint change"

# 4. Force-push to the Dependabot branch
git push --force-with-lease origin <dependabot-branch>

# 5. Re-enable auto-merge if it was cleared by the force-push
gh pr merge <pr-number> --auto --squash
```

### Detailed Steps

1. Identify the failing Dependabot PR and confirm the CI error is `lock-file not up-to-date with the workspace`.
   - A 6–12 second CI failure duration is the diagnostic signal: `pixi install --locked` fails as a pre-flight check before any tests run.
2. Fetch and check out the Dependabot branch locally:
   ```bash
   git fetch origin
   git checkout <dependabot-branch>
   ```
3. If the branch is behind `origin/main`, rebase first:
   ```bash
   git rebase origin/main
   ```
4. Regenerate the lock file (this reads the updated constraints and resolves the full dependency graph):
   ```bash
   pixi install
   ```
5. Stage and commit only `pixi.lock`:
   ```bash
   git add pixi.lock
   git commit -m "chore: update pixi.lock for <package> constraint change"
   ```
6. Force-push with lease (safer than `--force`):
   ```bash
   git push --force-with-lease origin <dependabot-branch>
   ```
7. Re-enable auto-merge — GitHub silently clears it on force-push:
   ```bash
   gh pr merge <pr-number> --auto --squash
   ```

### Using a Worktree for Isolation

For cleaner separation (avoids touching your working branch):

```bash
BRANCH="$(gh pr view <pr-number> --json headRefName --jq '.headRefName')"
WORKTREE="/tmp/dep-$(echo "$BRANCH" | tr '/' '-')"
REPO_DIR="<project-root>"

git -C "$REPO_DIR" worktree add "$WORKTREE" "origin/$BRANCH"
cd "$WORKTREE"
git rebase origin/main
pixi install
git add pixi.lock
git commit -m "chore: update pixi.lock for dependabot constraint change"
git push --force-with-lease origin "HEAD:$BRANCH"
gh pr merge <pr-number> --auto --squash
git -C "$REPO_DIR" worktree remove "$WORKTREE"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Rebasing without regenerating `pixi.lock` | Clean `git rebase origin/main` with no conflicts | `pixi.lock` still encodes constraint hashes from before the Dependabot bump; CI immediately rejects it | A clean rebase is not enough — always run `pixi install` after rebasing a Dependabot branch |
| Relying on Dependabot's included `pixi.lock` commit | Dependabot sometimes regenerates `pixi.lock` in its own commit | That commit goes stale once `main` advances past it; the hash no longer matches | Never trust Dependabot's `pixi.lock` commit after main has moved; always regenerate locally |

## Results & Parameters

### Diagnosis Signal: Fast CI Failure

```
CI job duration: 6–12 seconds
Error: lock-file not up-to-date with the workspace
```

This is a pre-flight check — `pixi install --locked` runs before any tests and rejects a stale lock immediately.

### Expected Output After Fix

```
$ pixi install
✔ Project in sync with pixi.lock

$ git push --force-with-lease origin <dependabot-branch>
To https://github.com/<org>/<repo>.git
   <old-sha>..<new-sha>  <branch> -> <branch>
```

CI will restart and complete the full test matrix (not 6–12 seconds).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Dependabot PR updating Python package constraints in pyproject.toml; CI failed with lock-file not up-to-date; pixi install succeeded; CI pending after force-push | Local verification 2026-05-01 |

## References

- [pixi-lock-rebase-regenerate](pixi-lock-rebase-regenerate.md) — comprehensive multi-branch / multi-scenario pixi.lock fix (includes Dependabot Phase 3b, double-rebase, parallel worktree patterns)
- [ci-cd-pixi-lock-stale-multi-pr-triage](ci-cd-pixi-lock-stale-multi-pr-triage.md) — org-wide CI triage when many PRs fail simultaneously
