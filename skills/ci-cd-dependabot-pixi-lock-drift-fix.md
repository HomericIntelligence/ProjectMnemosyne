---
name: ci-cd-dependabot-pixi-lock-drift-fix
description: "Use when: (1) a Dependabot PR fails CI with 'lock-file not up-to-date with the workspace', (2) a Dependabot PR updates requirements*.txt or pyproject.toml but pixi.lock was not regenerated, (3) CI on a Dependabot branch completes in 6-12 seconds (pre-flight lock rejection, not a test failure)"
category: ci-cd
date: 2026-05-03
version: "1.1.0"
user-invocable: false
tags: [pixi, dependabot, lock-file, pip, ci, rebase, squash-merge]
---

# CI — Dependabot pixi.lock Drift Fix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Fix `lock-file not up-to-date with the workspace` CI failures on Dependabot PRs that update Python package constraints without regenerating `pixi.lock` |
| **Outcome** | Successful — fetch + rebase + `pixi install` regenerates the lock file; CI passes after force-push |

## When to Use

- A Dependabot PR updates `requirements*.txt`, `pyproject.toml`, or other Python constraint files
- CI fails immediately with `lock-file not up-to-date with the workspace`
- CI job duration is 6–12 seconds (pre-flight `pixi install --locked` rejection — not a test failure)
- After rebasing a Dependabot branch, CI still fails even though the rebase was clean
- The Dependabot PR includes a `pixi.lock` update commit but it has gone stale after main advanced further

## Verified Workflow

### Quick Reference

```bash
# 1. Fetch first — never skip this; local cache of origin/main may be stale
git fetch origin main

# 2. Check out the Dependabot branch (or use a worktree for isolation)
git checkout <dependabot-branch>

# 3. Rebase onto fresh main
git rebase origin/main
# If pixi.lock conflicts: resolve by deleting and staging the empty path, then continue
# rm pixi.lock && git add pixi.lock && git rebase --continue

# 4. Regenerate pixi.lock from scratch
pixi install

# 5a. Normal case — stage and commit the updated lock file
git add pixi.lock
git commit -m "chore: update pixi.lock for <package> constraint change"

# 5b. If pixi.lock shows as untracked after conflict resolution (rebase deleted it):
#     fold it into the existing rebase commit instead of adding a separate commit
git add pixi.lock
git commit --amend --no-edit

# 6. Verify all pre-commit hooks pass
SKIP=audit-doc-policy pre-commit run --all-files

# 7. Force-push to the Dependabot branch
git push --force-with-lease origin <dependabot-branch>

# 8. Re-enable auto-merge (squash only — rebase merging not allowed)
gh pr merge <pr-number> --auto --squash
```

### Detailed Steps

1. Identify the failing Dependabot PR and confirm the CI error is `lock-file not up-to-date with the workspace`.
   - A 6–12 second CI failure duration is the diagnostic signal: `pixi install --locked` fails as a pre-flight check before any tests run.

2. **Always fetch before rebasing** — local `origin/main` may be stale cached data:
   ```bash
   git fetch origin main
   ```
   Skipping this step causes `git rebase origin/main` to report "Current branch is up to date"
   even when main has actually advanced 10+ commits. After fetching, the rebase sees the real
   divergence (including recently merged PRs that modify `pyproject.toml`, which cause genuine
   pixi.lock conflicts).

3. Fetch and check out the Dependabot branch locally:
   ```bash
   git fetch origin
   git checkout <dependabot-branch>
   ```

4. Rebase onto the freshly fetched main:
   ```bash
   git rebase origin/main
   ```
   - If `pixi.lock` conflicts during rebase, do NOT manually merge it — just delete and mark resolved:
     ```bash
     rm pixi.lock
     git add pixi.lock
     git rebase --continue
     ```

5. Regenerate the lock file (reads updated constraints and resolves the full dependency graph):
   ```bash
   pixi install
   ```

6. Stage and commit `pixi.lock`. Two cases:

   **Normal case** (pixi.lock was not deleted during rebase):
   ```bash
   git add pixi.lock
   git commit -m "chore: update pixi.lock for <package> constraint change"
   ```

   **After conflict resolution** (pixi.lock was deleted during rebase, now shows as untracked):
   The rebase commit records pixi.lock as deleted. `pixi install` regenerates it as an untracked file.
   Fold it into the existing rebase commit to keep history clean:
   ```bash
   git add pixi.lock
   git commit --amend --no-edit
   ```

7. Verify pre-commit hooks pass:
   ```bash
   SKIP=audit-doc-policy pre-commit run --all-files
   ```

8. Force-push with lease (safer than `--force`):
   ```bash
   git push --force-with-lease origin <dependabot-branch>
   ```

9. Re-enable auto-merge — GitHub silently clears it on force-push. Use `--squash` (rebase merging
   is disabled in this repository):
   ```bash
   gh pr merge <pr-number> --auto --squash
   ```

### Multi-PR Sequential Fixing

When fixing multiple Dependabot PRs in sequence, **re-fetch before each rebase**. A branch fixed
earlier may merge to main while you're working on the next branch, invalidating `origin/main` again.

```bash
# Pattern for each PR in sequence:
git fetch origin main          # always re-fetch before each rebase
git checkout <next-branch>
git rebase origin/main
# ... pixi install, commit, push, gh pr merge --auto --squash ...
```

### Using a Worktree for Isolation

For cleaner separation (avoids touching your working branch):

```bash
BRANCH="$(gh pr view <pr-number> --json headRefName --jq '.headRefName')"
WORKTREE="/tmp/dep-$(echo "$BRANCH" | tr '/' '-')"
REPO_DIR="<project-root>"

git -C "$REPO_DIR" fetch origin main
git -C "$REPO_DIR" worktree add "$WORKTREE" "origin/$BRANCH"
cd "$WORKTREE"
git rebase origin/main
# If pixi.lock conflict: rm pixi.lock && git add pixi.lock && git rebase --continue
pixi install
git add pixi.lock
git commit -m "chore: update pixi.lock for dependabot constraint change"
# OR: git commit --amend --no-edit  (if pixi.lock was deleted during conflict resolution)
SKIP=audit-doc-policy pre-commit run --all-files
git push --force-with-lease origin "HEAD:$BRANCH"
gh pr merge <pr-number> --auto --squash
git -C "$REPO_DIR" worktree remove "$WORKTREE"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Rebasing without regenerating `pixi.lock` | Clean `git rebase origin/main` with no conflicts | `pixi.lock` still encodes constraint hashes from before the Dependabot bump; CI immediately rejects it | A clean rebase is not enough — always run `pixi install` after rebasing a Dependabot branch |
| Relying on Dependabot's included `pixi.lock` commit | Dependabot sometimes regenerates `pixi.lock` in its own commit | That commit goes stale once `main` advances past it; the hash no longer matches | Never trust Dependabot's `pixi.lock` commit after main has moved; always regenerate locally |
| Skipping `git fetch origin main` before rebase | Ran `git rebase origin/main` directly | Reported "Current branch is up to date" — stale local cache; main had actually advanced 10+ commits including a just-merged pytest-asyncio PR that caused a real pixi.lock conflict | Always run `git fetch origin main` first; the rebase command uses locally cached ref data |
| `gh pr merge --auto --rebase` | Attempted rebase-style auto-merge | GraphQL error: "Merge method rebase merging is not allowed on this repository" | Use `--squash` instead of `--rebase` for auto-merge in repositories that disable rebase merging |
| Adding a separate commit for pixi.lock after conflict resolution | Ran `git add pixi.lock && git commit -m "..."` after `rm pixi.lock ... git rebase --continue` | Creates an extra commit in history; the rebase commit already recorded pixi.lock as deleted — the regenerated file belongs in that same commit | Use `git commit --amend --no-edit` after `pixi install` when pixi.lock shows as untracked post-conflict |

## Results & Parameters

### Diagnosis Signal: Fast CI Failure

```
CI job duration: 6–12 seconds
Error: lock-file not up-to-date with the workspace
```

This is a pre-flight check — `pixi install --locked` runs before any tests and rejects a stale lock immediately.

### Expected Output After Fix

```
$ git fetch origin main
From https://github.com/<org>/<repo>
 * branch              main       -> FETCH_HEAD

$ git rebase origin/main
Successfully rebased and updated refs/heads/<dependabot-branch>.

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
| ProjectScylla | Three sequential Dependabot PRs (pandas, vl-convert-python, matplotlib); pixi.lock conflict during rebase when main had advanced; resolved with rm+add+continue pattern; squash auto-merge used | verified-local 2026-05-02 |

## References

- [pixi-lock-rebase-regenerate](pixi-lock-rebase-regenerate.md) — comprehensive multi-branch / multi-scenario pixi.lock fix (includes Dependabot Phase 3b, double-rebase, parallel worktree patterns)
- [ci-cd-pixi-lock-stale-multi-pr-triage](ci-cd-pixi-lock-stale-multi-pr-triage.md) — org-wide CI triage when many PRs fail simultaneously
