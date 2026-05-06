---
name: git-rebase-stacked-prs-worktree-isolation
description: "Use git worktrees to rebase a stack of sibling PRs in parallel without cross-iteration corruption. Use when: (1) batch-rebasing many sibling branches onto main after their shared base advanced, (2) a naive in-place rebase loop fails with 'src refspec does not match any' or 'you need to resolve your current index first', (3) parallelizing conflict resolution across sub-agents (one worktree per agent), (4) a force-push pushed a half-rebased branch because exit-code check was masked by a piped tail/grep."
category: tooling
date: 2026-05-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
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
| **Context** | A naive in-place rebase loop in a single checkout corrupted the repo's index after the first conflicting branch and silently force-pushed a half-rebased branch. The worktree-per-branch pattern eliminates both failure modes. |

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

```bash
REPO=/path/to/repo
git -C "$REPO" fetch origin
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
