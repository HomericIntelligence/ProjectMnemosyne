---
name: git-rebase-stacked-prs-worktree-isolation
description: "Use git worktrees to rebase a stack of sibling PRs in parallel without cross-iteration corruption. Use when: (1) batch-rebasing many sibling branches onto main after their shared base advanced, (2) a naive in-place rebase loop fails with 'src refspec does not match any' or 'you need to resolve your current index first', (3) parallelizing conflict resolution across sub-agents (one worktree per agent), (4) a force-push pushed a half-rebased branch because exit-code check was masked by a piped tail/grep, (5) `git worktree add /tmp/wt <branch>` silently picked up a stale local branch tip and the subsequent rebase dropped a commit that lived only on origin."
category: tooling
date: 2026-05-17
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: git-rebase-stacked-prs-worktree-isolation.history
tags:
  - git
  - rebase
  - worktree
  - pr-stack
  - parallelism
  - conflict-resolution
---

# Git Rebase Stacked PRs with Worktree Isolation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-05 |
| **Objective** | Rebase a stack of sibling PRs onto an advanced main branch without cross-iteration corruption, by using one git worktree per branch and (optionally) one sub-agent per worktree |
| **Outcome** | Verified on ProjectCharybdis: 14 sibling auto-impl branches rebased + force-pushed across 5 parallel sub-agents in ~3 minutes wall-clock (vs ~30 minutes sequential). Zero corrupted force-pushes, zero index lock-outs. |
| **Context** | A naive in-place rebase loop in a single checkout corrupted the repo's index after the first conflicting branch and silently force-pushed a half-rebased branch. The worktree-per-branch pattern eliminates both failure modes. v1.1.0 (2026-05-17): documented the stale-local-branch pitfall after a Myrmidons cascade-rebase where `git worktree add /tmp/wt cleanup/c3-remove-reconciler` silently picked up a stale local branch tip and the subsequent rebase dropped a fix-up commit that lived only on `origin`. |
| **History** | [changelog](./git-rebase-stacked-prs-worktree-isolation.history) |

## When to Use

Use this skill when:

1. Batch-rebasing many sibling branches onto main after their shared base advanced (e.g., after 20+ sibling PRs merged).
2. A naive in-place rebase loop fails with `error: you need to resolve your current index first` and `error: src refspec X does not match any`.
3. Parallelizing conflict resolution across sub-agents — one worktree per agent so they cannot collide on the index/HEAD.
4. A previous force-push pushed a half-rebased branch because an exit-code check was masked by a piped `tail`/`grep`.
5. You need crash-safe iteration: failure of one rebase must not poison the rest.

Do NOT use this skill if:

- You only have 1-2 branches to rebase (the worktree overhead is not worth it).
- All branches share identical conflict resolution and you would rather use `git rebase --onto` once and cherry-pick.

## Verified Workflow

### Quick Reference

**Critical rule:** Always pass `origin/<branch> --detach` to `git worktree add`. Never pass the
bare local branch name — local branches can be stale relative to `origin/<branch>`, and a rebase
launched from a stale tip will silently drop commits that exist only on the remote. Always
`git fetch origin --prune` first.

```bash
REPO=/path/to/repo
git -C "$REPO" fetch origin --prune   # required — refresh remote refs before any worktree add
mkdir -p /tmp/rebases

for branch in branch-a branch-b branch-c; do
  wtpath="/tmp/rebases/$branch"
  rm -rf "$wtpath"
  git -C "$REPO" worktree add "$wtpath" "origin/$branch" --detach
  result=$(git -C "$wtpath" rebase origin/main 2>&1)
  if echo "$result" | grep -q "CONFLICT\|error:"; then
    echo "CONFLICT $branch"
    git -C "$wtpath" rebase --abort 2>/dev/null
    # Hand off to manual or sub-agent resolution
  else
    git -C "$wtpath" checkout -b "$branch"
    # Verify the rebase actually moved the merge-base before pushing
    if [ "$(git -C "$wtpath" merge-base origin/main HEAD)" = "$(git -C "$wtpath" rev-parse origin/main)" ]; then
      git -C "$wtpath" push origin "$branch" --force-with-lease
    else
      echo "NOT REBASED $branch — refusing to push"
    fi
  fi
  git -C "$REPO" worktree remove "$wtpath"
done
```

### Step 1 — Fetch the latest refs in the canonical repo

```bash
REPO=/path/to/repo
git -C "$REPO" fetch origin --prune
```

### Step 2 — Create one detached worktree per branch

Worktrees share the object database but have independent indexes and HEADs, so a corrupted rebase in one cannot poison another.

```bash
for branch in $BRANCHES; do
  wtpath="/tmp/rebases/$branch"
  rm -rf "$wtpath"
  git -C "$REPO" worktree add "$wtpath" "origin/$branch" --detach
done
```

### Step 3 — Rebase inside each worktree, capturing output safely

Never check `$?` after a piped command — `tail`/`grep` will clobber the exit code. Capture output to a variable first:

```bash
result=$(git -C "$wtpath" rebase origin/main 2>&1)
if echo "$result" | grep -q "CONFLICT\|error:"; then
  git -C "$wtpath" rebase --abort 2>/dev/null
  echo "CONFLICT $branch — needs sub-agent or manual resolution"
fi
```

### Step 4 — Verify rebase succeeded BEFORE force-push

A successful `git rebase` exit code is necessary but not sufficient — verify the merge-base actually advanced:

```bash
if [ "$(git -C "$wtpath" merge-base origin/main HEAD)" = "$(git -C "$wtpath" rev-parse origin/main)" ]; then
  git -C "$wtpath" checkout -b "$branch"
  git -C "$wtpath" push origin "$branch" --force-with-lease
fi
```

### Step 4b — Content-check the rebased branch (catches stale-local-branch pickup)

`merge-base` only confirms the rebase landed on top of `origin/main`. It does NOT confirm the
worktree started from the canonical remote tip of the branch being rebased. If `git worktree add`
silently picked up a stale local branch, the rebased history will be missing commits that exist
only on `origin/<branch>` — and `--force-with-lease` will erase them on push.

After the rebase succeeds, sanity-check the branch content against `origin/<branch>`:

```bash
# Expected commits/files from origin must be present in the rebased branch.
# Any commit reachable from origin/<branch> but missing from HEAD is a red flag.
missing=$(git -C "$wtpath" log --oneline "origin/$branch" --not HEAD)
if [ -n "$missing" ]; then
  echo "ABORT $branch — worktree started from stale ref; missing commits:"
  echo "$missing"
  # Do NOT force-push. Re-create the worktree with origin/<branch> --detach and retry.
fi
```

If you have a known content invariant (e.g. "this branch must delete file X"), assert it directly:

```bash
git -C "$wtpath" diff --name-status "origin/main..HEAD" | grep -q '^D\s.*path/to/X' \
  || { echo "ABORT $branch — expected deletion of path/to/X missing"; exit 1; }
```

### Step 5 — Parallelize across sub-agents (optional)

With one worktree per branch, dispatch one sub-agent per worktree (or batch 2-3 per agent). Each agent operates on its own `git -C <wtpath>` and cannot collide with siblings. We verified 5 agents handling 14 ProjectCharybdis branches in ~3 min.

### Step 6 — Clean up worktrees

```bash
git -C "$REPO" worktree remove "$wtpath"   # without --force; safe after push
git -C "$REPO" worktree prune
```

If the Safety Net hook blocks `--force` removal, push first (no dirty state remains), then remove without `--force`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| In-place rebase loop in shared checkout | `for b in ...; do git checkout -B $b origin/$b; git rebase origin/main; git push; done` | First branch had real conflicts; rebase left index dirty; subsequent iterations errored with "you need to resolve your current index first" and "src refspec X does not match any" | Use one worktree per branch — never run multiple rebases sequentially in the same checkout |
| Trusting `$?` after piped command | `git rebase origin/main 2>&1 \| tail -3; if [ $? -eq 0 ]` | `tail` clobbers `$?` — the check evaluates `tail`'s exit code, not git's | Capture rebase output to a variable first: `result=$(... 2>&1); if echo "$result" \| grep -q CONFLICT` |
| Force-push without verifying rebase succeeded | Pushed branch immediately after rebase command, no exit-code or content check | Pushed a half-rebased / unrebased state to remote; PR remained DIRTY because merge-base was unchanged | Verify `git log origin/main..HEAD` is non-empty AND `git merge-base origin/main HEAD` equals `origin/main`'s tip before pushing |
| `git worktree remove` blocked by Safety Net `--force` | Tried `git worktree remove <path> --force` to clean up after push | Safety Net hook blocks the flag because it can drop uncommitted work | Push first, then `git worktree prune` and `git worktree remove <path>` without `--force` (no dirty state once pushed) |
| Bare local branch name passed to `git worktree add` (Myrmidons cascade-rebase, 2026-05-17) | `git worktree add /tmp/wt cleanup/c3-remove-reconciler` (no `origin/` prefix, no `--detach`) — the local branch pointer was stale relative to `origin/cleanup/c3-remove-reconciler`, which had a newer fix-up commit. The rebase replayed only the stale commits and `--force-with-lease` then erased the fix-up commit from the remote. | `git worktree add <branch>` uses whatever the local branch tip is; a previous push had updated the remote ref but not the local pointer (the local branch had last been touched in a different worktree). Took ~15 min to detect — only caught by noticing expected file deletions were missing from the rebased branch. | Always `git fetch origin --prune` first, then `git worktree add <path> origin/<branch> --detach`. After rebasing, run `git diff --name-status origin/<base>..HEAD` and confirm the expected files (e.g. recent deletions) are present — if missing, the worktree was created from a stale ref and the push must be aborted. |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Branches rebased | 14 sibling auto-impl branches |
| Parallelism | 5 sub-agents |
| Wall-clock (parallel) | ~3 minutes |
| Wall-clock (sequential estimate) | ~30 minutes |
| Speedup | ~10x |
| Corrupted force-pushes | 0 |
| Index lock-outs | 0 |
| Worktree base path | `/tmp/rebases/<branch>` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectCharybdis | 2026-05-05: 14 sibling auto-impl branches rebased onto main after 23 sibling PRs were merged. 5 sub-agents in parallel, one worktree per branch. All 14 successfully pushed. | Wall-clock ~3 min vs ~30 min sequential |
| HomericIntelligence/Myrmidons | 2026-05-17: cascade-rebase session — `git worktree add /tmp/wt cleanup/c3-remove-reconciler` picked up a stale local branch tip, dropping a fix-up commit on force-push. Detected after ~15 min via missing expected file deletions. Fix: re-run with `origin/<branch> --detach` after `git fetch origin --prune`. | verified-local; CI confirmed corrected push valid |
