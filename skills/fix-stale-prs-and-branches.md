---
name: fix-stale-prs-and-branches
description: 'Rebase open PRs with no CI / failing CI, delete stale remote branches,
  commit orphaned local work as a new PR. Use when: open PRs show no checks, CI fails
  due to merge conflicts, stale remote branches need cleanup.'
category: tooling
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Skill: Fix Stale PRs and Branches

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-06 |
| Category | tooling |
| Objective | Rebase open PRs with no CI / failing CI, delete stale remote branches, commit orphaned local work as a new PR |
| Outcome | All 3 PRs rebased and CI triggered; 2 stale remote branches deleted; local work committed as PR #1450 |

## When to Use

- `gh pr list` shows open PRs with "no checks reported" (diverged from main before CI ran)
- A PR has a pre-commit CI failure caused by merge conflicts with new hooks added to main
- `git branch -a` shows remote branches with no associated open PR
- Local `git status` shows uncommitted changes that should become a PR

## Verified Workflow

### 1. Triage open PRs and stale branches

```bash
gh pr list --state open
git fetch --prune origin
git branch -a
```

For each open PR: check CI status with `gh pr checks <number>`.

### 2. Rebase a PR branch with merge conflicts

```bash
# Stash any local uncommitted work first
git stash

git switch <branch>
git rebase origin/main
```

If there are conflicts (e.g., both branches added hooks to `.pre-commit-config.yaml`):
- Include **both** sets of changes — do not discard either side
- `git add <file>` then `git rebase --continue`

### 3. Fix pre-commit hook failures after rebase

```bash
pre-commit run --all-files
```

Common issues and fixes:

| Error | Fix |
|-------|-----|
| `RUF022 __all__ is not sorted` | Re-order the new entry alphabetically in `__all__` |
| `SIM102 Use a single if statement` | Combine nested `if` conditions with `and`; extract long condition to a named variable if it exceeds 100 chars |
| `E501 Line too long` | Extract part of the boolean condition to a named variable |
| `audit-doc-policy Failed` | Harmless if caused by untracked `ProjectMnemosyne/` dir — CI only checks committed files, so safe to ignore locally |

### 4. Force-push to trigger CI

```bash
git push --force-with-lease origin <branch>
gh pr merge <number> --auto --rebase
```

### 5. For a PR with no local tracking branch (remote-only)

```bash
git switch -c <local-name> origin/<branch>
git rebase origin/main
# run pre-commit, fix issues
git push --force-with-lease origin <local-name>:<remote-branch>
gh pr merge <number> --auto --rebase
```

### 6. Delete stale remote branches

```bash
git push origin --delete <branch-name>
```

Note: the push hook runs the full test suite even for branch deletions. Use `run_in_background: true` when deleting multiple branches to avoid blocking.

### 7. Delete local tracking branches

```bash
git branch -d <branch>   # safe delete (fails if not merged)
```

For rebased branches whose PR has merged but git doesn't recognize as merged (different SHA after rebase):
- Confirm PR is merged: `gh pr view <number> --json state`
- Ask user to run `git branch -D <branch>` (Safety Net blocks force-delete)

### 8. Commit orphaned local work as a new PR

```bash
git stash pop stash@{0}   # restore the stashed work
git switch -c <descriptive-branch-name>
# run pre-commit, fix issues
git add <specific files>
git commit -m "feat(...): ..."
git push -u origin <branch>
gh pr create --title "..." --body "..."
gh pr merge <pr-number> --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Context | Outcome |
|---------|---------|
| 3 rebased PRs with CI conflicts | All CI triggered after rebase |
| 2 stale remote branches | Deleted with `git push origin --delete` |
| Orphaned local work | Committed as new PR |

## Key Gotchas

- **Push hook runs full test suite** on every push, including branch deletes (~2 min each). Use background tasks for multiple deletes.
- **`audit-doc-policy` fails locally** when `ProjectMnemosyne/` is an untracked directory. CI won't have it — safe to ignore.
- **Rebase vs merge for pre-commit config**: When two branches both add hooks to `.pre-commit-config.yaml`, always include both sets in the resolved conflict.
- **`__all__` must be sorted**: ruff RUF022 enforces this. After adding a new export, check alphabetical order.
- **Stash before switching branches**: Any uncommitted local work must be stashed before rebasing other branches.
- **`git branch -d` warns but succeeds** for branches that track a remote ref that is "ahead" — the warning is safe to ignore when the PR is merged.
