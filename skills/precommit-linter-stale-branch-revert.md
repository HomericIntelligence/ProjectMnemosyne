---
name: precommit-linter-stale-branch-revert
description: "Pre-commit linter reverts files on branches created before an ecosystem migration. Use when: (1) a branch was created before a Makefile/justfile/config migration was merged to main, (2) CI lint job fails with unexpected file reversions, (3) files that were changed on main appear to regress on an older branch after rebase."
category: ci-cd
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pre-commit, linter, rebase, migration, branch, stale]
---

# Pre-Commit Linter Stale Branch Revert

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 |
| **Objective** | Understand and fix the pattern where pre-commit hooks revert Makefile/justfile changes on branches created before a migration was merged to main |
| **Outcome** | Fixed by rebasing the stale branch onto current main before CI runs |
| **Verification** | verified-local |
| **Context** | During the ProjectKeystone Docker→Podman migration (PR #499), branches #497 and #498 were created before the migration. When they checked out, the pre-commit linter (which validates file state against current hooks) reverted `Makefile`, `justfile`, `CODEOWNERS`, and `CHANGELOG.md` back to the pre-migration state (restoring `NATIVE=1`, `docker-compose`, etc.). |

## When to Use

- A branch was created from `origin/main` before a significant file change was merged (Makefile refactor, CI config rewrite, justfile restructure)
- CI lint job fails on a branch with errors referencing files you didn't change on that branch
- After merging a migration PR, sibling branches that were in-flight show unexpected file regressions
- Pre-commit hooks report "reformatted" or "fixed" files that you didn't touch
- Files show `NATIVE=1`, `docker-compose`, or other pre-migration content that should have been removed

## Verified Workflow

### Quick Reference

```bash
# Fix: rebase the stale branch onto current main
git fetch --all
git checkout <stale-branch>
git rebase origin/main

# If conflicts arise in Makefile/justfile (migration files):
# Accept the incoming (main) version — it's the authoritative migration state
git checkout --theirs Makefile && git add Makefile
git rebase --continue

git push --force-with-lease origin <stale-branch>
```

### Detailed Steps

1. **Identify the symptom**: CI lint job fails; review shows files like `Makefile`, `justfile`, `CODEOWNERS` with `NATIVE=1` or `docker-compose` restored — content from before the migration.

2. **Root cause**: The branch tip contains files at the pre-migration commit. When pre-commit hooks run (e.g., yamllint, trailing-whitespace), they operate on the checked-out file state — which is the old state. The hooks may "fix" files by restoring them to a state that was valid before the migration but invalid after.

3. **Fix**: `git rebase origin/main` — this replays the branch's commits on top of the migration, so the branch now has the migrated files as its base.

4. **Conflict resolution**: If the branch also modified `Makefile`/`justfile` (unlikely but possible), resolve conflicts by keeping `main`'s migration changes and applying only the branch's unique changes on top:

   ```bash
   git checkout --theirs Makefile
   git add Makefile
   git rebase --continue
   ```

5. **Force-push**: After rebase, force-push with lease to update the PR branch:

   ```bash
   git push --force-with-lease origin <stale-branch>
   ```

6. **Verify**: CI should now see the branch as having the post-migration file state; lint runs against the new hooks on the new files.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Cherry-picking the migration commit onto the stale branch | Cherry-pick the Podman migration commit to bring the files forward | Cherry-pick only applies the diff of one commit; if the stale branch had other divergences, this creates conflicts without full context | Use `git rebase origin/main` instead of cherry-pick — rebase replays the entire history and handles the full context |
| Ignoring the revert and re-applying the migration manually | Manually edit Makefile/justfile on the stale branch to match main | Duplicates work and is error-prone; creates a maintenance burden if more files were changed in the migration | Always rebase; never manually re-apply a migration that's already in main |

## Results & Parameters

**Pattern**: Migration PR merged to main → sibling branches need rebase before CI passes

```
Timeline:
  origin/main: A --- B --- C(migration) --- D
  branch-497:  A --- B --- E(tls test)      <- pre-migration, CI fails lint
  branch-498:  A --- B --- F(sigterm test)  <- pre-migration, CI fails lint

Fix:
  branch-497 (after rebase): A --- B --- C --- D --- E  <- CI passes
  branch-498 (after rebase): A --- B --- C --- D --- F  <- CI passes
```

**Key indicator in CI output**: Files showing `NATIVE=1`, `docker-compose`, `docker.up` that should have been migrated — this confirms the branch is using pre-migration file state.

**Key indicator in git log**: Running `git log --oneline origin/main..HEAD` on the stale branch will show only the branch's own commits, not the migration commit — confirming the migration hasn't been incorporated.

**Verification command**:

```bash
# Confirm migration commit is NOT yet in the branch
git log --oneline origin/main..HEAD
# If migration commit is missing, the branch needs rebase

# After rebase, confirm migration is present
git log --oneline | grep -i "migration\|podman\|docker"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | 2026-04-26 PRs #497, #498 stale branch revert after Podman migration PR #499 | Resolved by `git rebase origin/main` + `git push --force-with-lease` on both branches |
