---
name: git-stacked-prs-rebase-merge-worktree-orchestration
description: "End-to-end playbook for driving a stack of dependent PRs through a rebase-merge-ONLY GitHub repo (allow_merge_commit:false, allow_squash_merge:false) using parallel git worktrees. Use when: (1) a repo permits only rebase-merge and you must merge stacked PRs — retarget every still-open stacked PR to main BEFORE merging anything below it, because deleting a stack-base branch on merge makes GitHub CLOSE (not retarget) dependent PRs UNRECOVERABLY, (2) a stacked branch re-conflicts on its base's commits after those commits were rebase-merged into main with conflict resolutions — use `git rebase --onto origin/main <old-base-sha> <branch>` to replay only the branch's own commits, (3) preventing committed conflict markers from reaching main — check `git diff --name-only --diff-filter=U` AND `git grep -nE '^(<<<<<<< |>>>>>>> )'` before every `git rebase --continue`, plus a CI guard step, (4) parallel worktree agents on stacked branches keep conflicting on shared doc/registry/__init__/changelog files — resolve as chronological additive unions, never pick-one-side; regenerate (don't hand-merge) tool-generated report files, (5) `git worktree remove` fails on an agent-locked worktree (unlock first) or a chained checkout silently fails and later commands run on the wrong branch, (6) local main diverges patch-identically after rebase-merges — `git pull --rebase origin main` drops duplicates, (7) gh quirks: stale `gh pr diff` right after push, `--delete-branch` failing while a worktree holds the branch, GraphQL rate-limit exhaustion from tight CI-polling loops across many PRs."
category: tooling
date: 2026-07-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - git
  - stacked-prs
  - rebase-merge
  - worktrees
  - rebase-onto
  - conflict-markers
  - gh-cli
  - multi-agent
---

# Git Stacked PRs Through a Rebase-Merge-Only Repo with Parallel Worktrees

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Objective** | Drive 6 dependent PRs, developed by parallel worktree agents, through a GitHub repo that permits ONLY rebase-merge — without losing any PR, committing conflict markers, or replaying already-merged conflicts |
| **Outcome** | All 6 PRs merged with real CI passes; one committed-conflict-marker incident reached main and was remediated with a permanent CI guard; one stacked-PR class of unrecoverable closure identified and a prevention rule adopted |
| **Verification** | verified-ci |

Related skills (adjacent hazards, different merge methods or scopes):
`parallel-pr-worktree-workflow` (squash-merge stacked-orphan variant, parallel-agent isolation),
`pr-rebase-conflict-resolution-patterns` (general rebase-conflict taxonomy),
`git-rebase-skip-duplicate-merged-commits` (patch-identical duplicates → `git rebase --skip`),
`github-auto-merge-ci-gating-merge-method` (choosing/arming the merge method).
This skill is specifically the rebase-merge-only stack-orchestration workflow.

## When to Use

- The target repo has `allow_merge_commit: false` and `allow_squash_merge: false` — every merge is a **rebase-merge that rewrites SHAs**, so stacked branches are never patch-identical to what lands on main.
- You are about to merge the bottom PR of a stack and other stacked PRs are still open (the retarget-first rule below is MANDATORY — violation closes dependents unrecoverably).
- A dependent branch's rebase onto `origin/main` re-conflicts on commits that belong to its already-merged base (the base was rebase-merged WITH conflict resolutions, so it is no longer patch-identical).
- Multiple parallel agents each own a worktree + branch, dependent work is stacked on its dependency's branch, and shared registry-style files (CLAUDE.md status docs, `__init__` re-exports, changelogs/followup ledgers, regenerated reports) conflict on every rebase.
- You need to guarantee no conflict markers ever reach main (pre-`--continue` checks + CI guard).
- After several rebase-merges, local main "diverges" from origin with patch-identical commits.
- `gh pr diff` shows a stale diff right after a push, `gh pr merge --delete-branch` can't delete a worktree-held local branch, or CI-polling loops start hitting GraphQL rate limits.

## Verified Workflow

### Quick Reference

```bash
# 0) One worktree + branch per work-stream; stack dependent work on its dependency's branch
git worktree add /tmp/wt-featB -b featB featA   # NOT main, if B depends on A

# 1) BEFORE merging any PR that other open PRs are stacked on: retarget the dependents to main
gh pr edit <dependent-PR> --base main           # for EVERY still-open stacked PR, FIRST
gh pr merge <base-PR> --rebase --delete-branch  # only THEN merge the base

# 2) After the base rebase-merges into main (with conflict resolutions), replay ONLY the
#    dependent branch's own commits — plain `git rebase origin/main` re-conflicts on base commits
git fetch origin
git rebase --onto origin/main <old-base-tip-sha> featB

# 3) BEFORE every `git rebase --continue` (non-negotiable pair):
git diff --name-only --diff-filter=U            # MUST print nothing
git grep -nE '^(<<<<<<< |>>>>>>> )'             # MUST print nothing
git rebase --continue

# 4) CI guard step (permanent; note the trailing space in the patterns — a bare
#    7-equals line is a legal markdown setext underline, so do NOT match '^=======$'):
#      - name: No committed conflict markers
#        run: |
#          if git grep -nE '^(<<<<<<< |>>>>>>> )' -- ':!*.lock'; then
#            echo "Conflict markers found"; exit 1
#          fi

# 5) Shared registry-file conflicts (status docs, __init__ re-exports, changelogs):
#    resolve as chronological additive UNION — keep BOTH sides, ordered by execution date.
#    Regenerated report files: resolve arbitrarily, then re-run the generator and amend.

# 6) Worktree lifecycle
git worktree unlock /path/to/wt 2>/dev/null; git worktree remove /path/to/wt
git branch --show-current                       # verify after ANY chained checkout

# 7) Local main diverged patch-identically after rebase-merges
git pull --rebase origin main                   # drops the duplicate local commits cleanly

# 8) gh freshness check after push (gh pr diff can serve a STALE diff)
git rev-parse HEAD
gh pr view <N> --json headRefOid --jq .headRefOid   # must match before trusting gh pr diff
```

### Detailed Steps

1. **Set up one worktree per work-stream.** Each parallel agent gets its own `git worktree` and branch. If stream B depends on stream A's unmerged work, branch B **from A's branch**, not from main. This keeps B's diff reviewable (only B's own commits) and CI meaningful.

2. **Merge order: retarget first, merge second.** Because the repo is rebase-merge-only, merging a PR rewrites its commits' SHAs on main and (with `--delete-branch`) deletes the head branch. If any still-open PR uses that branch as its base, GitHub **CLOSES** the dependent PR when the base branch is deleted — it does **not** retarget it, and a closed PR's base cannot be changed (`Cannot change the base branch of a closed pull request`). The close is unrecoverable; you must open a brand-new PR. Rule exercised in the session: **before merging anything below it, run `gh pr edit <N> --base main` on every still-open stacked PR.**

3. **Replay dependents with `--onto`.** After the base merges, the base's commits on main are new SHAs and — if conflicts were resolved during its final rebase — no longer patch-identical. A plain `git rebase origin/main featB` therefore re-conflicts on the base's commits. Instead:

   ```bash
   git rebase --onto origin/main <old-base-tip-sha> featB
   ```

   where `<old-base-tip-sha>` is the tip of the dependency branch as featB last saw it (recover via `git merge-base featB <old-base-branch>` before deletion, or from reflog/PR head SHA). This replays ONLY featB's own commits. This avoided a full conflict replay twice in the session. (If the base commits ARE still patch-identical, plain rebase auto-skips them, or see `git-rebase-skip-duplicate-merged-commits`.)

4. **Conflict-marker hygiene (incident-driven, both preventions adopted).** A real incident put conflict markers on main: during a rebase, `git add -A` staged a file whose conflict was never resolved, because the operator checked only `git status --short | head -3` and the conflicted file was below the cutoff. Preventions:
   - Before every `git rebase --continue`: `git diff --name-only --diff-filter=U` must be empty AND `git grep -nE '^(<<<<<<< |>>>>>>> )'` must be empty. Run both, every time — never truncate status output.
   - Permanent CI guard: `if git grep -nE '^(<<<<<<< |>>>>>>> )' -- ':!*.lock'; then exit 1; fi`. Match only the `<<<<<<< ` / `>>>>>>> ` forms **with a trailing space**; do not match a bare `=======` line — a 7-equals line is a legal markdown setext underline and matching it produces false positives.

5. **Shared-file conflicts between streams are structural, not accidental.** Files every stream touches — CLAUDE.md-style status docs, `__init__` re-export files, changelog/followup ledgers, regenerated report files — conflict on EVERY cross-stream rebase. Resolve them as **chronological additive unions** (keep both sides, ordered by execution date); never pick one side, which silently drops a sibling stream's entries. Exception: regenerated report files (e.g., dated audit reports) — don't hand-merge; resolve arbitrarily, re-run the generating tool, and amend the commit.

6. **Worktree lifecycle safety.** `git worktree remove` fails on an agent-locked worktree — run `git worktree unlock <path>` first, then remove (no `--force`). After ANY chained checkout (`git checkout X && ...`), verify `git branch --show-current`: a checkout silently blocked by an untracked regenerated file leaves you on the previous branch, and subsequent rebase commands then run on the **wrong branch**.

7. **Post-merge local-main hygiene.** After rebase-merges, local main holds patch-identical commits with different SHAs than origin. `git pull --rebase origin main` detects the duplicates and drops them cleanly (do not `pull --ff-only`, which just fails; do not reset unless you've confirmed nothing local is unpushed).

8. **gh CLI quirks (all observed in-session):**
   - `gh pr merge N --rebase --delete-branch` fails to delete the **local** branch when a worktree holds it. Harmless — clean up the worktree first next time.
   - `gh pr diff N` immediately after `git push` can serve a **stale** diff. Confirm `gh pr view N --json headRefOid` matches `git rev-parse HEAD` before trusting it.
   - GitHub GraphQL rate limit (~5000/hr) is easy to exhaust with tight CI-polling loops across many PRs. Poll at 45–60 s with backoff, tolerate transient `i/o timeout` and `rate limit` lines, and run one poll loop per PR — not one per check.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Merge stack bottom-up without retargeting | Merged a stack-base PR with `--delete-branch` while dependent PRs still targeted its branch | Rebase-merge deleted the base branch; GitHub CLOSED (did not retarget) the stacked PRs, and a closed PR's base cannot be changed — unrecoverable, required opening brand-new PRs | Retarget EVERY still-open stacked PR to main (`gh pr edit N --base main`) BEFORE merging anything below it |
| Plain `git rebase origin/main` on a dependent branch | Rebased the dependent after its base was rebase-merged into main with conflict resolutions | The base's commits on main were no longer patch-identical, so the rebase re-conflicted on all the base's commits — a full conflict replay | `git rebase --onto origin/main <old-base-sha> <branch>` replays only the branch's own commits (avoided the replay twice) |
| `git add -A` + truncated status check during rebase | Staged everything, verified with `git status --short \| head -3`, then `git rebase --continue` | The still-conflicted file was below the `head -3` cutoff; conflict markers were committed and reached main via the rebase-merge | Before every `--continue`: `git diff --name-only --diff-filter=U` empty AND `git grep -nE '^(<<<<<<< \|>>>>>>> )'` empty; add the CI guard as a backstop |
| CI conflict-marker guard matching `^=======$` | First guard draft matched all three marker forms including the bare equals line | A 7-equals line is a legal markdown setext-heading underline — false positives on documentation | Match only `^(<<<<<<< \|>>>>>>> )` with the trailing space, and exclude lockfiles (`':!*.lock'`) |
| Pick-one-side resolution on shared registry files | Took ours/theirs on status docs, `__init__` re-exports, changelog ledgers | Silently dropped the sibling stream's entries; the loss resurfaced as a re-conflict or missing re-export later | Resolve as chronological additive UNION (both sides, execution-date order); regenerate tool-generated reports instead of hand-merging |
| `git worktree remove` on an agent's worktree | Direct remove of a worktree an agent had locked | Fails on locked worktrees | `git worktree unlock <path>` first, then remove; verify `git branch --show-current` after chained checkouts |
| Tight per-check CI polling across 6 PRs | Polled every few seconds, one loop per check | Exhausted the ~5000/hr GraphQL rate limit; polls started failing with rate-limit and `i/o timeout` errors | Poll at 45–60 s with backoff, tolerate transient error lines, one poll loop per PR |

## Results & Parameters

- **Session outcome:** 6 PRs merged into a rebase-merge-only repo, all with real CI passes; multi-agent parallel worktrees throughout.
- **Repo merge settings that trigger this skill:** `allow_merge_commit: false`, `allow_squash_merge: false`, `allow_rebase_merge: true` (check with `gh api repos/<owner>/<repo> --jq '{merge: .allow_merge_commit, squash: .allow_squash_merge, rebase: .allow_rebase_merge}'`).
- **Mandatory merge-ordering invariant:** number of open PRs based on a branch must be 0 before that branch's PR merges.
- **Pre-`--continue` gate (both must be empty):**

  ```bash
  git diff --name-only --diff-filter=U
  git grep -nE '^(<<<<<<< |>>>>>>> )'
  ```

- **CI guard step (copy-paste):**

  ```yaml
  - name: Fail on committed conflict markers
    run: |
      if git grep -nE '^(<<<<<<< |>>>>>>> )' -- ':!*.lock'; then
        echo "Committed conflict markers detected"; exit 1
      fi
  ```

- **Dependent-branch replay:** `git rebase --onto origin/main <old-base-tip-sha> <branch>`.
- **Polling parameters:** 45–60 s interval, exponential backoff on `rate limit` / `i/o timeout`, one loop per PR.
- **Local main after merges:** `git pull --rebase origin main`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| predictive-coding-mojo | Multi-agent session, 6 PRs merged through a rebase-merge-only GitHub repo using parallel git worktrees; every practice above exercised with real CI passes and merges (verified-ci) | Stacked-PR retarget-first rule, `--onto` replay (used twice), committed-marker incident + CI guard remediation, union resolution of per-stream registry files, worktree unlock/checkout-verification, GraphQL rate-limit-aware polling |
