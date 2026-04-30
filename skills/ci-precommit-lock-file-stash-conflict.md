---
name: ci-precommit-lock-file-stash-conflict
description: "Use when: (1) a commit fails because pre-commit stash pop conflicts with ruff auto-fix staged changes, (2) pixi.lock or another lock file is modified but unstaged and pre-commit hooks auto-fix and stage files causing stash pop conflicts, (3) the repository is left in a dirty state after a failed commit with unstaged auto-generated files."
category: ci-cd
date: 2026-04-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pre-commit, stash, pixi, lock-file, ruff, conflict, commit]
---

# pre-commit Stash Pop Conflict: Unstaged Lock File + Ruff Auto-Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-29 |
| **Objective** | Fix commit failure caused by pre-commit stash mechanism conflicting with ruff auto-fix staged changes when a lock file is unstaged |
| **Outcome** | Success — staging `pixi.lock` before committing resolved the conflict |
| **Verification** | verified-local (commit succeeded after staging `pixi.lock`; CI validation pending) |
| **Project Context** | ProjectHephaestus PR #308 |

## When to Use

- `git commit` fails with a pre-commit stash pop warning or leaves repository in a dirty state
- `pixi.lock` (or any auto-generated lock file: `poetry.lock`, `package-lock.json`, `Cargo.lock`) is modified but not staged when committing
- Ruff or another auto-fix hook runs during pre-commit and stages formatting changes
- After a failed commit, ruff's auto-fixes appear to be "rolled back" even though ruff ran successfully
- You see a message like: `[WARNING] Stash pop conflict detected` or the commit leaves untracked/modified files that shouldn't be there

## Verified Workflow

### Quick Reference

```bash
# Always stage lock files before committing if they have changes:
git add pixi.lock
git add <other files>
git commit -m "your message"

# Alternative — if pixi.lock should NOT be part of this commit:
git stash push pixi.lock     # save just pixi.lock
git add <other files>
git commit -m "your message" # pre-commit runs cleanly
git stash pop                # restore pixi.lock
```

### Detailed Steps

1. **Diagnose the problem**: Check whether `pixi.lock` (or another large auto-generated file) is modified but not staged:
   ```bash
   git status
   # Look for "modified: pixi.lock" under "Changes not staged for commit"
   ```

2. **Decide whether to include the lock file in the commit**:
   - If the lock file changes are intentional (e.g., you ran `pixi add` or `pixi install`): stage it with `git add pixi.lock`
   - If the lock file is dirty but should not be in this commit: use the alternative workaround (stash it separately)

3. **Stage all intended files**:
   ```bash
   git add pixi.lock          # if the lock changes belong in this commit
   git add <other files>
   ```

4. **Commit normally** — pre-commit will now stash only truly unstaged changes (if any), and the stash pop will succeed cleanly:
   ```bash
   git commit -m "type(scope): description"
   ```

5. **If the repository is already in a dirty state from a prior failed commit**:
   - Do NOT run `git stash drop` (Safety Net blocks destructive stash operations)
   - Instead, manually inspect and restore any rolled-back ruff changes using the Edit tool
   - Then re-stage all files including `pixi.lock` and retry the commit

### The Underlying Mechanism

Understanding *why* this fails helps prevent it:

1. pre-commit runs: `git stash push --keep-index --message "pre-commit hook ..."` — saves unstaged changes (including `pixi.lock`) to stash
2. Hooks run — ruff `--fix` modifies files and stages them (these changes are *new* in the index)
3. pre-commit runs: `git stash pop` — **CONFLICT**: the stash contains the pre-hook version of files that ruff just modified and staged
4. `git stash pop` fails; pre-commit may print a warning; in some versions the commit proceeds but the ruff fixes are effectively rolled back, leaving the repo dirty

The root cause: any file that is (a) auto-generated/updated by the build system and (b) has unstaged changes when you commit is at risk of triggering this conflict if a hook also modifies files in that session.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Commit with unstaged pixi.lock | `git add <other files>; git commit` with `pixi.lock` modified but not staged | pre-commit stashed working tree, ruff auto-fixed files and staged them, stash pop conflicted → ruff fixes rolled back, commit failed | Always stage `pixi.lock` (or any large auto-generated lock file) when it has changes before committing |
| `git stash drop` to clean up conflict | Attempted to drop the bad stash state after failed commit | Safety Net hook blocked destructive git commands (`git stash drop`) | Use Edit tool to manually restore files instead of relying on `git stash drop` |

## Results & Parameters

### Lock Files Known to Trigger This Pattern

Any file that is frequently auto-modified by tooling and thus commonly left unstaged:

| File | Tool That Modifies It | Project Type |
|------|-----------------------|--------------|
| `pixi.lock` | pixi install / pixi add | Python (pixi) |
| `poetry.lock` | poetry install / poetry add | Python (poetry) |
| `package-lock.json` | npm install | Node.js |
| `Cargo.lock` | cargo build / cargo update | Rust |
| `requirements.txt` | pip-compile | Python (pip-tools) |

### Pattern: Pre-Commit Hook Impact on Stash

Hooks that auto-stage files are most likely to trigger this conflict:
- `ruff --fix` — auto-fixes Python formatting/linting and stages the result
- `black` — reformats Python files and stages them
- `prettier` — reformats JS/TS/YAML/JSON and stages them
- Any hook that uses `git add` internally

Hooks that only check (read-only) do NOT trigger this conflict:
- `ruff check` (without `--fix`)
- `mypy`
- `pytest`

### Expected Behavior After Fix

```
$ git add pixi.lock && git add hephaestus/module.py
$ git commit -m "feat(utils): add new helper"
[pre-commit] Running hooks...
  ruff.....................................................................Passed
  ruff-format..............................................................Passed
  mypy.....................................................................Passed
[main abc1234] feat(utils): add new helper
 2 files changed, 15 insertions(+)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #308 — commit with unstaged pixi.lock + ruff auto-fix | Resolved by staging pixi.lock before committing |
