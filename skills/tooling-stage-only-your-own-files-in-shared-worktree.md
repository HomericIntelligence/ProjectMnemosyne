---
name: tooling-stage-only-your-own-files-in-shared-worktree
description: "Use when: (1) an automation/address-review loop runs in a SHARED worktree that already carries unrelated pre-existing dirty changes (modified/deleted/untracked files) from a different change; (2) you are about to commit your fix and are tempted to run `git add -A` / `git add .`; (3) a commit accidentally bundled unrelated files (scratch artifacts like .claude-address-review-*.md, deletions, sibling edits); (4) you need to un-bundle a too-broad commit without losing the other (not-yours) changes; (5) reviewing whether an agent's commit scope matches only the files it actually edited; (6) implementing a salvage-commit path for a REUSED worktree (preserve in-progress changes across re-sync) — specifically when `git add -A` in the salvage commit followed by cherry-pick after `reset --hard` produces a CONFLICT that hard-fails the entire issue."
category: tooling
date: 2026-06-15
version: "1.1.0"
history: tooling-stage-only-your-own-files-in-shared-worktree.history
user-invocable: false
verification: verified-ci
tags: [git, git-add, staging, git-add-all, address-review, automation-loop, shared-worktree, dirty-working-tree, commit-scope, git-reset-soft, signed-commit, pr-hygiene, clobber, salvage-commit, reused-worktree, cherry-pick, git-add-u]
---

# Stage Only Your Own Files in a Shared Worktree

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-15 |
| **Objective** | When fixing PR review threads or implementing salvage-commit paths inside an automation loop's shared/reused worktree, commit ONLY the files you actually edited — never `git add -A` — because the loop-runner worktree commonly carries unrelated pre-existing dirty state that a blanket add silently bundles into your commit; in salvage paths, the bundled unrelated state can cause a `git cherry-pick` conflict that hard-fails the entire issue |
| **Outcome** | Successful — bug was observed (9-file commit instead of 2-file commit; cherry-pick conflict aborting issue #1289), recovered with `git reset --soft`, re-staged explicitly, and re-committed with correct scope; salvage path fixed to use `git add -u` + non-fatal cherry-pick abort |
| **Verification** | verified-ci |

## When to Use

- You are running an address-review or automation loop inside a shared (loop-runner) worktree that may carry prior or sibling dirty state
- You are about to stage changes with `git add -A`, `git add .`, or `git add --all` in any worktree you did not freshly clone yourself
- A commit you already made contains files you did not intend to touch (scratch `.md` artifacts, unrelated edits, unexpected deletions)
- You need to un-bundle a too-broad signed commit without discarding the other party's uncommitted work
- You are reviewing whether an agent's commit diff is correctly scoped to only the files the agent actually edited
- You are implementing a "salvage in-progress changes" path for a REUSED worktree — specifically the pattern: `git add -A` → salvage commit → `reset --hard origin/{branch}` → `cherry-pick` that salvage commit back (the cherry-pick can CONFLICT on unrelated state swept in by `add -A`, hard-failing the whole issue)

## Verified Workflow

### Quick Reference

```bash
# BEFORE staging: audit what is dirty
git status --short

# Stage ONLY your files (explicit paths — never -A or .)
git add scripts/my_file.py tests/unit/scripts/test_my_file.py

# Verify scope before committing
git diff --cached --name-only   # must list ONLY your files
git diff --cached --stat        # must show only your intended hunks

# Commit signed
git commit -S -m "fix(scope): description"

# Verify post-commit
git show --stat --oneline HEAD   # must list only your files
git log --show-signature -1      # look for "Good signature"
```

### Detailed Steps

1. **Audit the worktree before touching anything.** Run `git status --short` and read every line. Identify which files belong to your task and which are pre-existing dirty state from a different change (prior loop turn, sibling operation, or scratch artifacts left by the automation harness).

2. **Stage only your files using explicit paths.**
   ```bash
   git add <file1> <file2> ...
   ```
   Never use `git add -A`, `git add .`, or `git add --all` in a shared or loop-runner worktree. These stage every dirty, untracked, and deleted file in the tree — including files that are not yours to commit.

3. **Confirm commit scope before committing.**
   ```bash
   git diff --cached --name-only
   ```
   This must list exactly the files you edited and nothing else. Also run `git diff --cached --stat` and scan the hunks to ensure no unrelated changes slipped in.

4. **Commit signed.** The committer email must match the signing key (e.g. `4211002+mvillmow@users.noreply.github.com`).
   ```bash
   git commit -S -m "fix(scope): description"
   ```

5. **Leave all other dirty files untouched.** They are not yours to commit. The loop runner or the next turn will handle them, or they will be cleaned up separately.

6. **Verify the commit scope after committing.**
   ```bash
   git show --stat --oneline HEAD
   git log --show-signature -1
   ```

### Verified-Workflow Note: Salvage-Commit in Reused Worktrees

When a reused worktree has in-progress changes that need to be preserved across a `reset --hard` re-sync:

- Use `git add -u` (stages TRACKED modifications only) — NOT `git add -A` (which also sweeps in untracked leftover state and deletions)
- After `reset --hard origin/{branch}`, re-apply the salvage commit via `git cherry-pick -S {sha}` — but wrap this in `try/except`: on conflict, run `git cherry-pick --abort` (check=False) and log a WARNING, then return normally
- A salvage-restore conflict is NOT fatal; the agent re-runs and regenerates its edits anyway; failing the whole issue over a salvage conflict is wrong

```python
# Salvage: preserve in-progress changes across re-sync (correct pattern)
result = subprocess.run(["git", "add", "-u"], ...)      # tracked mods only
subprocess.run(["git", "commit", "-S", "-m", "chore: preserve reused worktree changes"], ...)
salvage_sha = subprocess.run(["git", "rev-parse", "HEAD"], ...).stdout.strip()
subprocess.run(["git", "reset", "--hard", f"origin/{branch}"], ...)
try:
    subprocess.run(["git", "cherry-pick", "-S", salvage_sha], check=True, ...)
except subprocess.CalledProcessError:
    subprocess.run(["git", "cherry-pick", "--abort"], check=False, ...)
    logger.warning("Salvage cherry-pick conflicted; agent will regenerate edits")
```

### Recovery: Un-bundling a Too-Broad Commit

If you already committed too many files, recover without losing the other party's changes:

```bash
# Step 1: Undo the commit, keep all changes in index + worktree (--soft, NOT --hard)
git reset --soft HEAD~1

# Step 2: Unstage everything
git restore --staged .

# Step 3: Re-stage only your files
git add <file1> <file2> ...

# Step 4: Verify
git diff --cached --name-only   # must list only your files

# Step 5: Re-commit signed
git commit -S -m "fix(scope): description"

# Step 6: Confirm
git show --stat --oneline HEAD
git log --show-signature -1
```

**Critical**: use `--soft` (not `--mixed` or `--hard`). `--soft` keeps all changes staged in the index and in the working tree. `--hard` would destroy the other party's uncommitted working-tree changes — data loss with no recovery path.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `git add -A` then `git commit -S` in the loop's shared worktree | Staged all changes at once before committing the address-review fix | Committed 9 files instead of 2: swept up pre-existing unrelated dirty state — `.claude-address-review-1219.md` (loop scratch artifact), modified `.pre-commit-config.yaml`, `CONTRIBUTING.md`, `hephaestus/ci/precommit.py`, a test file, and DELETED two files that still exist on `origin/main` | In any shared/loop worktree, `git add -A` is unsafe; always stage explicit paths only |
| Trusting the worktree was clean because the session "started fresh" | Assumed no pre-existing dirty state at the start of an address-review turn | The loop-runner had pre-staged/modified files from a prior or sibling operation; the working tree was NOT clean at turn start | Never assume a loop worktree is clean; run `git status --short` every turn before staging |
| Recovering with `git reset --hard` | (Hypothetical: using --hard to undo an over-broad commit) | `--hard` resets the working tree to HEAD, destroying all uncommitted changes — including the other party's dirty files that were never yours to delete | Recover with `git reset --soft` and selective re-stage; never `--hard` when the worktree contains others' uncommitted work |
| `git add -A` in the salvage-commit path of a reused worktree, then `cherry-pick` after `reset --hard` | Salvage path used `git add -A` to capture in-progress changes before `reset --hard origin/{branch}`, then re-applied via `git cherry-pick -S {sha}` | Cherry-pick CONFLICTED on the unrelated leftover state swept in by `add -A`; the conflict hard-failed issue #1289 entirely (not just the salvage) | Use `git add -u` (tracked modifications only) in salvage paths; untracked leftover state must not enter the salvage commit |
| Treating the salvage cherry-pick as fatal (`check=True`) | `subprocess.run(["git", "cherry-pick", ...], check=True)` — any conflict raised `CalledProcessError` and propagated up as an issue failure | Salvage is best-effort; the agent regenerates its edits on the next run anyway; making it fatal loses the entire issue over a non-critical restore step | Wrap the cherry-pick in `try/except`; on conflict, `git cherry-pick --abort` (check=False) + `logger.warning`; return normally |

## Results & Parameters

### Safe-Staging Sequence (copy-paste ready)

```bash
# 1. Audit before touching anything
git status --short

# 2. Stage only your files (explicit paths)
git add <file1> <file2>

# 3. Verify scope
git diff --cached --name-only
git diff --cached --stat

# 4. Commit signed
git commit -S -m "fix(scope): description"

# 5. Verify post-commit
git show --stat --oneline HEAD
git log --show-signature -1
```

### Un-Bundle Recovery Sequence (copy-paste ready)

```bash
# 1. Undo the commit softly (keeps working tree intact)
git reset --soft HEAD~1

# 2. Unstage everything
git restore --staged .

# 3. Re-stage only your files
git add <file1> <file2>

# 4. Verify
git diff --cached --name-only

# 5. Re-commit signed
git commit -S -m "fix(scope): description"

# 6. Confirm scope + signature
git show --stat --oneline HEAD
git log --show-signature -1
```

### Key Verification Commands

| Command | What to Check |
| --------- | --------------- |
| `git status --short` | Understand full dirty state before staging anything |
| `git diff --cached --name-only` | Confirm only your files are staged |
| `git diff --cached --stat` | Confirm only your intended hunks are staged |
| `git show --stat --oneline HEAD` | Confirm committed scope after the fact |
| `git log --show-signature -1` | Confirm "Good signature" from the signing key |

This skill complements the team practice of always working in an isolated worktree when the automation loop runs — but even within that worktree, scope your staging to your own files only.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #1252 address-review of issue #1219 | Address-review fix targeted only `scripts/check_license_compatibility.py` and `tests/unit/scripts/test_check_license_compatibility.py`; `git add -A` swept up 7 additional unrelated files (scratch `.md`, sibling edits, two unrelated deletions); recovered with `git reset --soft HEAD~1` + selective re-stage + `git commit -S` |
| ProjectHephaestus | PR #1371 / issue #1369 (salvage cherry-pick conflict) | Reused-worktree salvage path used `git add -A`, swept unrelated untracked state into salvage commit; `cherry-pick` after `reset --hard` conflicted, hard-failing issue #1289; fixed to `git add -u` + non-fatal `try/except` cherry-pick abort |
