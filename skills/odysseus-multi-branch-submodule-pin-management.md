---
name: odysseus-multi-branch-submodule-pin-management
description: >-
  Manage submodule pins across multiple Odysseus branches with rebase, cherry-pick avoidance,
  and justfile recipe collision resolution. Use when: (1) updating a submodule SHA on a feature
  branch while main has a different pin, (2) rebasing an Odysseus feature branch onto main after
  justfile changes on both sides, (3) cherry-picking a submodule pointer update between branches
  fails with CONFLICT (submodule), (4) CI "Harden checks" job fails with justfile recipe
  redefinition error after rebase, (5) branch-switching causes missing files/directories in the
  working tree.
category: ci-cd
date: 2026-05-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - odysseus
  - submodule
  - pin
  - rebase
  - justfile
  - multi-branch
  - cherry-pick
  - force-with-lease
---

# Odysseus Multi-Branch Submodule Pin Management

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-04 |
| **Objective** | Fix CI on feat/issue-22-ci-hardening; manage 13+ submodule pins across branches; resolve justfile recipe collisions; handle rebases onto a moving main branch |
| **Outcome** | Successful — branch rebased, recipe collisions renamed, submodule pins updated, PR force-pushed and re-evaluated by GitHub |
| **Verification** | verified-local — all steps executed locally; CI validation in progress |

## When to Use

- A submodule's upstream PR (e.g., ProjectHephaestus adding `install.sh`) merges to main while your Odysseus feature branch still pins the old SHA
- You need to cherry-pick a submodule pointer update between branches but get `CONFLICT (submodule)`
- Rebasing an Odysseus feature branch fails because both main and your branch added justfile recipes
- CI "Harden checks" fails with `Recipe 'X' first defined on line N is redefined on line M`
- Switching branches in the same Odysseus worktree causes `ls tests/install/` or similar to fail with "no such file or directory"
- You need to force-push a rebased branch without clobbering concurrent remote changes

## Verified Workflow

### Quick Reference

```bash
# --- Submodule pin update on feature branch ---
git -C <submodule-path> fetch origin
git -C <submodule-path> checkout main
git -C <submodule-path> pull --ff-only origin main
git -C <submodule-path> log --oneline -3   # verify the right commits are present
git add <submodule-path>
git commit -m "chore(deps): update <submodule> submodule to include <feature>"
git push origin <feature-branch>

# --- Safe rebase + push workflow ---
git fetch origin main
git rebase origin/main
# resolve conflicts (justfile most common), then:
git add <resolved-files>
git rebase --continue
git push --force-with-lease origin <feature-branch>
# wait for GitHub to re-evaluate merge status
sleep 15 && gh pr view <PR> --repo HomericIntelligence/Odysseus --json mergeable,mergeStateStatus

# --- Check for justfile recipe collisions before adding ---
just --list 2>&1 | grep "redefined\|error"
grep "^<recipe-name>" justfile   # check if name already exists
```

### Detailed Steps

#### Step 1: Confirm working branch before any file operations

```bash
git branch --show-current
```

**Why:** Branch switching causes `scripts/install/` and `tests/install/` directories to appear/disappear. Always confirm the active branch before running `ls`, `podman build`, or other path-dependent commands.

#### Step 2: Avoid cherry-picking submodule pointer updates

When a submodule's feature branch merges to main and you want that SHA on your feature branch, **do not** cherry-pick the submodule commit from another branch. Instead, directly advance the submodule on the target branch:

```bash
# On your feature branch:
git -C shared/ProjectHephaestus fetch origin
git -C shared/ProjectHephaestus checkout main
git -C shared/ProjectHephaestus pull --ff-only origin main

# Verify the new SHA has what you need
git -C shared/ProjectHephaestus log --oneline -3

# Pin the new SHA in Odysseus
git add shared/ProjectHephaestus
git commit -m "chore(deps): update ProjectHephaestus submodule to include install.sh"
git push origin <feature-branch>
```

#### Step 3: Detect justfile recipe collisions before adding new recipes

Before adding a new recipe to `justfile`, check for name collisions:

```bash
# Show all defined recipe names
just --list 2>&1

# Check if your intended name is already defined
grep "^install\b\|^install-dev\b\|^install-check\b" justfile
```

If the name exists, prefix with a scope. For Odysseus ecosystem recipes: use `ecosystem-` prefix (e.g., `ecosystem-install`, `ecosystem-install-dev`, `ecosystem-install-check`).

#### Step 4: Rebase feature branch onto main

```bash
git fetch origin main
git rebase origin/main
```

If the justfile has conflicts from both sides adding content at the end:

```bash
# The conflict markers show two completely new blocks
# Resolution: keep BOTH, with their own section comments
# Edit the file to remove conflict markers and keep all content
git add justfile
git rebase --continue
```

#### Step 5: Force-push with safety

After a rebase, the branch history has changed so a regular push is rejected:

```bash
git push --force-with-lease origin <feature-branch>
```

`--force-with-lease` refuses if the remote has commits you haven't fetched, preventing accidental overwrites of concurrent work.

#### Step 6: Wait for GitHub merge status re-evaluation

After a force-push, GitHub shows `mergeStateStatus: DIRTY` for 10-30 seconds while it re-evaluates:

```bash
sleep 15 && gh pr view <PR-number> --repo HomericIntelligence/Odysseus --json mergeable,mergeStateStatus
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Cherry-pick submodule pointer update | `git cherry-pick <sha>` to copy submodule pin from one branch to another | Submodule pointer conflicts when both branches have different SHAs: `CONFLICT (submodule): Merge conflict in shared/ProjectHephaestus` | Abort cherry-pick; on target branch, run `git -C <submodule> pull --ff-only origin main` then `git add <submodule> && git commit` directly |
| Standard push after rebase | `git push origin <branch>` after `git rebase origin/main` | Rejected as non-fast-forward — rebase rewrites history | Use `git push --force-with-lease origin <branch>` |
| Using `install` as justfile recipe name | Named ecosystem installer recipe `install` | Existing justfile already had `install PREFIX` (cmake binary install recipe) — CI "Harden checks" caught the collision | Check `just --list` for name collisions first; use namespaced prefix like `ecosystem-install` |
| Assuming branch is stable during background tasks | Ran background `podman build` while performing git operations in the foreground | Git checkout in the foreground changed working tree; subsequent `ls tests/install/` failed with "no such file" because the branch switched away | Always run `git checkout <branch>` before any branch-specific file operations; treat the working tree as volatile during multi-branch git sessions |
| Checking GitHub merge status immediately after force-push | `gh pr view --json mergeable` right after `git push --force-with-lease` | Shows `CONFLICTING` / `DIRTY` for 10-30 seconds while GitHub re-evaluates | `sleep 15 && gh pr view <PR> --json mergeable,mergeStateStatus` |

## Results & Parameters

### Submodule pin facts

- Odysseus has 13+ submodules, each pinned to a SHA **per branch**
- When a submodule's upstream PR merges to main: the local working copy advances, but the Odysseus branch still records the old SHA
- `git add <submodule-path>` + commit updates the recorded SHA on the **current** branch only
- Other branches retain their own submodule SHAs — each branch is independent

### Harden checks CI job validates

- markdownlint on all `.md` files
- pixi.toml consistency
- justfile syntax (`just --list`) — catches recipe redefinition collisions
- symlink validity

### Rebase conflict: keep both justfile sections

When both main and the feature branch added recipes at the end of `justfile`, conflict markers show two complete new blocks. Resolution: keep ALL content from both sides, separated by section headers:

```justfile
# === Recipes from main ===
main-recipe:
    ...

# === Recipes from feature branch ===
ecosystem-install:
    ...
```

### Rename collision pattern

| Original name (collided) | Renamed to |
|--------------------------|------------|
| `install` | `ecosystem-install` |
| `install-dev` | `ecosystem-install-dev` |
| `install-check` | `ecosystem-install-check` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | feat/issue-22-ci-hardening — CI hardening PR with justfile extensions and submodule updates | Session 2026-05-04 |
