---
name: tooling-sequential-rebase-loop-for-stuck-pr-queue-recovery
description: "Use when: (1) N PRs are simultaneously stuck in mergeStateStatus=UNKNOWN or BLOCKED because their last CI run is against an old base SHA (e.g. a systemic CI fix just landed on main), (2) GitHub's auto-recompute of PR mergeability is unreliable or too slow and you need to actively refresh CI, (3) you are tempted to dispatch parallel rebase agents to 'go faster' — STOP, use one sequential loop instead, (4) a fix PR has landed on main resolving a CI gate that was blocking an entire PR queue and you need to clear all blocked PRs efficiently, (5) PRs show 'mergeStateStatus: BLOCKED' with no new commits but a stale base SHA, (6) you need a safe pattern for force-push + auto-merge re-arm that will not clobber concurrent pushes, (7) some PRs in the queue have 'deleted by us, modified by them' conflicts that require a dedicated follow-up agent rather than auto-resolution."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - gh-cli
  - github
  - rebase
  - force-push
  - pr-queue
  - sequential
  - auto-merge
  - merge-conflict
  - stuck-prs
  - ci-recovery
  - worktree
---

# Sequential Rebase Loop for Stuck PR Queue Recovery

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-05-18 |
| **Objective** | Refresh CI on 12 PRs simultaneously blocked because their last run targeted an old base SHA, after a systemic markdownlint fix landed on `main` |
| **Outcome** | 10/12 rebased mechanically with zero intervention; 2 had "deleted by us, modified by them" conflicts (expected pattern when a fix-PR edits a file an in-flight merge-PR was about to delete); conflict PRs were ABORT-AND-SKIPped and resolved by a targeted follow-up agent using `git rm`. All 12 PRs merged on green CI after rebase. |

## When to Use

- (1) N PRs are in `mergeStateStatus=UNKNOWN` or `BLOCKED` with no merge conflict — just a stale base SHA from before a fix landed
- (2) GitHub's auto-recompute is not firing (common when the base-SHA mismatch is subtle)
- (3) You need to force-push rebased branches and re-arm auto-merge for each
- (4) A single fix PR has resolved a systemic CI failure across an entire PR queue
- (5) You have 5–20 stuck PRs and want a safe, zero-race pattern
- (6) Some PRs may have real conflicts (fix-PR modified a file that an in-flight PR was about to delete) and need isolated per-PR resolution

## Verified Workflow

### Hard Rules (Read Before Starting)

1. **NEVER dispatch parallel rebase agents against the same shared clone.** They race on `git checkout` operations and clobber each other's branch state.
2. **One agent, sequential loop** — this is not a performance concern. Rebase + force-push takes seconds per PR; sequencing is fast enough for N≤20.
3. **ABORT on conflict, never auto-resolve.** The orchestrator dispatches a targeted follow-up for each conflict PR.
4. **`--force-with-lease`, not `--force`.** Prevents clobbering a concurrent push.
5. **Re-arm auto-merge after every push.** GitHub clears `--auto` on force-push.
6. **Fresh worktree per PR.** Prevents branch-state contamination across iterations.

### Quick Reference — Sequential Rebase Loop

```bash
#!/usr/bin/env bash
# Sequential rebase loop — safe, no race, conflict-aware
# Usage: set BRANCHES to the list of branch names to rebase onto origin/main

BRANCHES=(
  feature/branch-one
  feature/branch-two
  feature/branch-three
)

FAILED=()
CONFLICTED=()
SUCCEEDED=()

git fetch origin main

for branch in "${BRANCHES[@]}"; do
  wt="/tmp/rebase-wt-$$-${branch//\//-}"

  # Create a fresh worktree for this branch
  if ! git worktree add "$wt" "$branch" 2>/tmp/rebase-wt-err.log; then
    echo "ERROR: could not create worktree for $branch — skipping"
    FAILED+=("$branch")
    continue
  fi

  (
    cd "$wt" || exit 1

    # Sync local branch tip to remote (fast-forward only — no divergence expected)
    git pull --ff-only origin "$branch" 2>/dev/null || true

    # Rebase onto fresh main
    if git rebase origin/main; then
      # Success — push with lease (safe against concurrent pushes)
      if git push --force-with-lease origin "$branch"; then
        # Re-arm auto-merge (GitHub clears it on force-push)
        gh pr merge --auto --squash "$branch" 2>/dev/null || \
          echo "WARN: auto-merge re-arm failed for $branch (may already be merging)"
        echo "OK: $branch"
        exit 0
      else
        git rebase --abort 2>/dev/null || true
        echo "PUSH FAILED: $branch"
        exit 2
      fi
    else
      # Conflict — abort cleanly, never auto-resolve
      git rebase --abort
      echo "CONFLICT: $branch"
      exit 1
    fi
  )

  rc=$?
  case $rc in
    0) SUCCEEDED+=("$branch") ;;
    1) CONFLICTED+=("$branch") ;;
    *) FAILED+=("$branch") ;;
  esac

  # Cleanup worktree regardless of outcome
  git worktree remove --force "$wt" 2>/dev/null || true
done

echo ""
echo "=== Rebase Loop Summary ==="
echo "Succeeded (${#SUCCEEDED[@]}): ${SUCCEEDED[*]}"
echo "Conflicted — needs follow-up (${#CONFLICTED[@]}): ${CONFLICTED[*]}"
echo "Failed — needs investigation (${#FAILED[@]}): ${FAILED[*]}"
```

### Getting the Branch List From PR Numbers

```bash
# Map PR numbers to branch names
mapfile -t BRANCHES < <(
  for pr in 1710 1711 1712 1713 1714 1715; do
    gh pr view "$pr" --json headRefName --jq '.headRefName'
  done
)
```

### Quick Reference — Conflict Recovery Follow-Up Agent

For PRs where the loop emitted `CONFLICT: <branch>` due to **"deleted by us, modified by them"**
(the fix-PR edited a file that the in-flight PR was going to delete as part of its own merge):

```bash
#!/usr/bin/env bash
# Single-PR conflict resolution: "deleted by us, modified by them"
# The PR's intent was to delete the file; honor that intent with git rm.

BRANCH="feature/the-conflicted-branch"
CONFLICT_FILE="path/to/file/that/was/deleted.md"

wt="/tmp/resolve-wt-$$"
git fetch origin main
git worktree add "$wt" "$BRANCH"

(
  cd "$wt"
  git pull --ff-only origin "$BRANCH" 2>/dev/null || true
  git rebase origin/main || true   # starts, hits conflict, pauses

  # Honor the PR's deletion intent
  git rm "$CONFLICT_FILE"
  git rebase --continue            # should complete cleanly

  git push --force-with-lease origin "$BRANCH"
  gh pr merge --auto --squash "$BRANCH"
)

git worktree remove --force "$wt"
```

**Why `git rm` and not `git checkout --theirs`?** The PR's branch was going to delete this file
as part of its change set. The fix-PR on `main` modified it. The PR's intent wins: `git rm`
removes the file and signals to `git rebase --continue` that the conflict is resolved.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Waiting for GitHub auto-recompute | After fix PR landed on `main`, waited for GitHub to automatically refresh `mergeStateStatus` on stuck PRs | GitHub did not reliably recompute; PRs stayed `UNKNOWN`/`BLOCKED` because their last CI run SHA did not match new `main` | Do not rely on GitHub's auto-recompute after a systemic base-SHA shift; actively rebase each PR |
| Parallel rebase agents (N agents, one per PR) | Dispatched one Haiku agent per PR branch to rebase concurrently against `origin/main` | Agents racing on the shared clone clobbered each other's `git checkout` operations, leaving branches in detached-HEAD or wrong-branch state | NEVER parallelize rebase against the same clone. One agent, sequential loop only. |
| Auto-resolving conflicts in the loop | Loop attempted `git checkout --theirs <file>` on conflict to keep going | The "theirs" heuristic was wrong for "deleted by us, modified by them" — the resolution needed `git rm`, not a checkout. Auto-resolution produced corrupt state. | ABORT on conflict, report the branch name, dispatch a targeted follow-up agent that understands the specific conflict type. |
| Reusing the same worktree across iterations | Used one worktree and `git checkout <branch>` per loop iteration instead of a fresh worktree | Dirty index from a previous failed rebase leaked into the next iteration's branch checkout, causing phantom conflicts | Use a fresh worktree per PR; clean up with `git worktree remove --force` after each iteration. |
| `git push --force` instead of `--force-with-lease` | Used bare `--force` to push rebased branches | Potentially clobbers a concurrent push (e.g. from a developer or another agent working on the same branch) | Use `--force-with-lease`; it refuses the push if the remote tip has advanced since your last fetch, giving you a safe failure instead of data loss. |
| Forgetting to re-arm auto-merge after push | Pushed with `--force-with-lease` but did not call `gh pr merge --auto --squash` | GitHub clears the auto-merge flag on every force-push; PRs sat open waiting for manual merge even after CI went green | Re-arm `--auto` immediately after every successful `--force-with-lease` push. |

## Results & Parameters

### Empirical Results (2026-05-18 Session)

| Metric | Value |
| ------ | ----- |
| PRs in queue | 12 |
| Rebased cleanly | 10 |
| Conflicted (ABORT-AND-SKIP) | 2 |
| Conflict type | "deleted by us, modified by them" (fix-PR edited file that in-flight PR was deleting) |
| Follow-up agent interventions | 1 (resolved both conflict PRs with `git rm`) |
| Final merged on green CI | 12/12 |

### Decision Table

| Scenario | Recommended Pattern |
| -------- | ------------------- |
| N PRs stuck on stale base SHA, no real conflicts | Sequential rebase loop (this skill) |
| N PRs stuck, some have real conflicts | Sequential loop + ABORT on conflict; follow-up agent per conflict |
| Conflict type: "deleted by us, modified by them" | Follow-up agent: `git rm <file>` then `git rebase --continue` |
| N PRs already mergeable (no rebase needed), race on merge | See `tooling-gh-pr-merge-admin-parallel-base-branch-race` |
| Single PR with known conflict file | Use conflict-recovery snippet directly (no loop needed) |

### Related Skills

- **`tooling-gh-pr-merge-admin-parallel-base-branch-race`** — companion skill covering the merge-side race (after PRs are rebased and green, use sequential admin-merge to drain the queue without hitting the GraphQL base-branch race)
- **`documentation-markdownlint-table-cell-pipe-escape`** v1.2.0 — the queue-block trigger in this session: a systemic markdownlint MD056 failure on a shared file blocked an entire PR queue, which then required this rebase-loop recovery pattern to refresh CI after the fix landed

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectMnemosyne | 2026-05-18: 12 skill PRs blocked by markdownlint MD056 fix on `main`; sequential rebase loop cleared 10 cleanly, 2 resolved via `git rm` follow-up; all 12 merged on green CI | Direct observation in this session |
