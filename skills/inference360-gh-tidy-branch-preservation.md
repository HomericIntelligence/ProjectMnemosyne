---
name: inference360-gh-tidy-branch-preservation
description: "Run `gh tidy` branch cleanup safely by understanding its env-var config and its lack of a dry-run flag. Use when: (1) `$tidy` or `hephaestus-tidy` is unavailable and you need the direct `gh tidy --rebase-all` fallback, (2) Inference360 uses `master` as trunk, (3) you want to know whether your `GH_TIDY_AUTO_DELETE_MERGED` config will delete merged branches without a prompt, (4) a branch was cleaned up and you want to confirm its patches are already on trunk, (5) you want to preview what `gh tidy` will delete — there is no `--dry-run` flag, so preview manually via `git branch --merged main`."
category: tooling
date: 2026-07-11
version: "1.1.0"
user-invocable: false
verification: verified-local
history: inference360-gh-tidy-branch-preservation.history
tags: [inference360, gh-tidy, tidy, branch-preservation, worktree, rebase-all, auto-delete-merged, master, h200-slurm]
---

# Inference360 gh-tidy Branch Preservation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-29 |
| **Objective** | Run `$tidy`-equivalent branch cleanup in the Inference360 H200 Slurm repo after PR #291 merged, while preserving branch safety and avoiding unnecessary branch resurrection. |
| **Outcome** | Successful local cleanup. The direct `gh tidy --rebase-all` fallback fast-forwarded local `master` to `origin/master` at `4292e87`, no rebase failures occurred, and the final local branch inventory was only `master` with a clean working tree. |
| **Verification** | verified-local. This was executed locally in the Inference360 repo on 2026-06-29 and re-confirmed on 2026-07-11 in a mvillmow/Random predictive-coding-mojo session where `gh tidy` correctly cleaned merged branches per the configured env vars and left the live parity-training worktree untouched; CI validation is not applicable to the branch-cleanup operation. |
| **History** | [changelog](./inference360-gh-tidy-branch-preservation.history) |

## When to Use

- You are running `$tidy` or equivalent branch cleanup in Inference360 after one or more PRs merged.
- The `hephaestus-tidy` wrapper is not on `PATH`, but the `gh tidy` extension is available.
- You need to preserve branches unless the user explicitly asked to prune them.
- The environment may contain `GH_TIDY_*` variables that alter deletion behavior.
- A merged local branch disappeared during tidy and you need to decide whether to recreate it.

## Verified Workflow

> Verification note: This workflow is verified locally only. It records a successful
> Inference360 branch-cleanup run from 2026-06-29, not a CI-validated code path.

### Quick Reference

```bash
cd <INFERENCE360_REPO>

# Preflight: do not start tidy from a dirty or surprising checkout.
git status --short --branch
git worktree list --porcelain
git remote show origin | sed -n '/HEAD branch/s/.*: //p'
env | rg '^GH_TIDY_' || true

# Inference360 uses master as trunk. Neutralize auto-delete explicitly when
# branch preservation is the expected behavior.
env GH_TIDY_AUTO_DELETE_MERGED=false \
  gh tidy --rebase-all --trunk master --skip-gc --skip-update-check

# If a branch was already auto-deleted, prove whether it is subsumed before
# restoring it.
git cherry master <old-tip>
git diff --stat <old-tip> master
git branch --list
git status --short --branch
```

### Detailed Steps

1. Confirm the current Inference360 working tree is clean with `git status --short --branch`. Stop and resolve unrelated dirty state before running tidy.
2. Inspect all worktrees with `git worktree list --porcelain`. Branches checked out elsewhere can block rebases or make cleanup decisions ambiguous.
3. Verify the repo trunk instead of assuming the ecosystem default. Inference360 used `master` in the verified run.
4. Inspect `GH_TIDY_*` variables before invoking tidy. If branch preservation matters, run tidy with `GH_TIDY_AUTO_DELETE_MERGED=false` in the command environment.
5. If `hephaestus-tidy` is not installed, use the direct fallback:

   ```bash
   env GH_TIDY_AUTO_DELETE_MERGED=false \
     gh tidy --rebase-all --trunk master --skip-gc --skip-update-check
   ```

6. Read the `gh tidy` output for fast-forwards, failed rebases, and branch deletions. In the verified run, local `master` fast-forwarded to `origin/master` at `4292e87`, and there were no rebase failures.
7. If `gh tidy` deleted a local merged branch because auto-delete was enabled, do not immediately recreate it. First compare the old branch tip against trunk:

   ```bash
   git cherry master <old-tip>
   git diff --stat <old-tip> master
   ```

   In the verified run, `git cherry master <old-tip>` showed patch-equivalent `-` lines and `git diff --stat <old-tip> master` was empty, so leaving the branch absent was safe.
8. Finish by confirming the final branch inventory and working tree:

   ```bash
   git branch --list
   git status --short --branch
   ```

   The verified final state was only local `master`, aligned with `origin/master`, with a clean working tree.

### Preview without a dry-run flag (there isn't one)

**CORE FINDING:** `gh tidy` has no `--dry-run` flag. `gh tidy --help` shows only
`Usage: gh tidy` with no flags. Passing `--dry-run` is silently ignored — a harmless no-op,
NOT honored as a preview. `gh tidy` runs the same either way. So to preview what it WILL
delete, do not reach for a nonexistent flag; inspect the candidate set manually first.

**`gh tidy` is a safe branch-cleanup tool by design** — these are real tool properties, not
luck:

- It only deletes branches it has verified are merged-to-main. It prints `merged into main`
  / `pull requests merged on Github` per branch before deleting, so the deletion set is
  exactly the merged set.
- It EXPLICITLY SKIPS branches checked out in a worktree, printing
  `Skipping deletion of branch 'X'`. A live long-running process in a worktree (e.g. a
  detached training run) is therefore safe by design — it is safe to run `gh tidy` with
  such runs in flight.
- It never touches the current branch or branches with unmerged commits.

Because of these guarantees, `gh tidy` is safe to run once you know two things: your
env-var config (see below) and which branches are currently merged.

**MANUAL PREVIEW WORKFLOW (in place of a dry-run):**

1. Know your config. `env | rg '^GH_TIDY_'` shows whether `GH_TIDY_AUTO_DELETE_MERGED` is
   set. If you have configured auto-delete, merged branches delete without a y/N prompt —
   that is the configured behavior. Know whether you have enabled it; if you want a prompt
   (or preservation) instead, run with `env GH_TIDY_AUTO_DELETE_MERGED=false gh tidy ...`.
2. Preview the deletion candidate set. Run `git fetch --prune` yourself first (updates
   remote-tracking refs so merged-detection is accurate), then inspect
   `git branch --merged main`. That list IS the auto-delete candidate set — what
   `git branch --merged main` shows is what `gh tidy` will delete.
3. Confirm your worktree-protected branches. `git worktree list` — every branch checked out
   in a worktree is protected and will be skipped.
4. For any branch with unmerged/unpushed work you want to keep, make sure it is either
   (a) checked out in a worktree (skipped) OR (b) pushed with an open PR (`gh tidy` only
   auto-deletes merged branches — unmerged branches are never deleted).
5. If you want to double-check a specific branch is recoverable before it is deleted:
   `git merge-base --is-ancestor <branch-tip-sha> origin/main` (exit 0 = subsumed, safe) or
   `git cherry origin/main <branch>` (all `-` = patches already on main).

**Companion pairing:** This pairs with `/hephaestus:worktree-cleanup`
(state-preservation-first, never deletes branches). Correct order: worktree-cleanup FIRST
(prune safe worktrees, commit stranded work), THEN `gh tidy` (delete merged branches). A
worktree checked out with a live long-running process (e.g. a detached training run) is
correctly protected by BOTH tools.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Expected wrapper availability | Tried to rely on `hephaestus-tidy` for the repo-local `$tidy` flow | The wrapper was not on `PATH` in the session environment | Fall back directly to `gh tidy --rebase-all --trunk master --skip-gc --skip-update-check` after the same clean-tree and worktree preflights |
| Assumed branch preservation default | Ran `gh tidy` without passing `--auto-delete-merged` and expected local branches to be preserved unless prompted | The environment had `GH_TIDY_AUTO_DELETE_MERGED` enabled, so `gh tidy` printed `AUTO_DELETE_MERGED is enabled` and auto-deleted local branch `bbqdif-8b-bm` | For branch-preserving runs, inspect `env \| rg '^GH_TIDY_'` or neutralize the environment with `env GH_TIDY_AUTO_DELETE_MERGED=false gh tidy ...` |
| Recreate deleted branch reflexively | Considered restoring the auto-deleted merged branch immediately | The branch commits were already patch-equivalent to trunk and the diff stat was empty | Use `git cherry master <old-tip>` and `git diff --stat <old-tip> master` first; recreating a subsumed branch adds noise to future tidy runs |
| Passed `--dry-run` expecting a preview | Ran `gh tidy --dry-run` expecting it to preview the cleanup without acting | `gh tidy` has no `--dry-run` flag (`gh tidy --help` shows only `Usage: gh tidy`); the arg is silently ignored (a harmless no-op) and `gh tidy` runs its normal cleanup | Check `--help` for a flag before assuming it exists — unrecognized args are ignored, not errored. To preview, inspect `git branch --merged main` (the deletion candidate set) instead of relying on a flag |

## Verified On

| Repo | Context | Verification |
| ------- | ------- | ------- |
| Inference360 | branch cleanup after PR #291 merged — local `master` fast-forwarded to `4292e87`, `bbqdif-8b-bm` auto-deleted (subsumed) | date 2026-06-29, verified-local |
| mvillmow/Random | predictive-coding-mojo session — `gh tidy` correctly cleaned merged branches per the configured env vars and protected the live parity-training worktree; confirmed `gh tidy --dry-run` is a silent no-op | date 2026-07-11, verified-local |

## Results & Parameters

Verified local parameters:

```text
Project: Inference360
Context: branch cleanup after PR #291 merged
Date: 2026-06-29
Trunk: master
Fallback command: gh tidy --rebase-all --trunk master --skip-gc --skip-update-check
Observed trunk update: local master fast-forwarded to origin/master at 4292e87
Rebase failures: none
Final local branches: master only
Final working tree: clean
Verification level: verified-local
```

Branch auto-delete config (behaved as configured):

```text
Observed message: AUTO_DELETE_MERGED is enabled
Cause: GH_TIDY_AUTO_DELETE_MERGED was enabled in the environment
Deleted local branch: bbqdif-8b-bm
Patch-equivalence check: git cherry master <old-tip> produced "-" lines
Tree-delta check: git diff --stat <old-tip> master was empty
Decision: leave the deleted branch absent
```

Branch-preserving command shape:

```bash
env GH_TIDY_AUTO_DELETE_MERGED=false \
  gh tidy --rebase-all --trunk master --skip-gc --skip-update-check
```
