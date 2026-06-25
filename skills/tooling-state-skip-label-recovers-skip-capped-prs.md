---
name: tooling-state-skip-label-recovers-skip-capped-prs
description: "The state:skip label blocks the hephaestus automation loop from re-attempting a PR. ROOT CAUSE (fixed in PR #1584): the script was wrongly ADDING state:skip in a self-perpetuating cycle (sticky non-recovery + repo-level rc mis-attribution + closed-issue bypass) — the loop re-tagged everything every iteration, converging on nothing. The fix makes state:skip operator-only and absolute (read live, never auto-added, never auto-removed). To recover an ALREADY-stranded PR, remove the label by hand (gh issue edit <N> --remove-label state:skip), rebase if DIRTY, re-run. Use when: (1) the loop keeps skipping everything / re-tags state:skip every loop and converges on nothing, (2) hephaestus-automation-loop --issues <N> logs 'Skipping #<N> (state:skip)' and does nothing (~3s loops), (3) a green-but-unarmed pending-review PR gets spuriously skipped, (4) a CLOSED issue passed via --issues is driven and tagged, (5) recovering a skip-capped PR after the blocker is fixed."
category: tooling
date: 2026-06-23
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: tooling-state-skip-label-recovers-skip-capped-prs.history
tags:
  - state-skip
  - hephaestus-automation-loop
  - skip-capped
  - self-perpetuating-cycle
  - max-review-iterations
  - iteration-cap
  - re-attempt
  - sticky-label
  - remove-label
  - operator-only-label
  - pending-review-bucket
  - closed-issue-filter
  - genuinely-stuck-pr
  - dirty-pr-rebase
  - recovery
---

# `state:skip`: Self-Perpetuating Cycle (Root Cause) and Skip-Capped PR Recovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-23 |
| **Objective** | Stop the hephaestus automation loop from wrongly ADDING `state:skip` in a self-perpetuating cycle (re-tagging everything every loop, converging on nothing), AND recover PRs already stranded by the label. |
| **Outcome** | Root cause fixed in PR #1584: `state:skip` is now operator-only and absolute (read live, never auto-added, never auto-removed). A clean end-to-end run (after #1584 + companions #1572/#1575/#1589) merged PR #1590 with 0 errors, 0 skips. |
| **Verification** | verified-ci |
| **History** | [changelog](./tooling-state-skip-label-recovers-skip-capped-prs.history) |

## When to Use

- The loop "keeps skipping everything": it re-tags `state:skip` every loop and converges on nothing (e.g. a batch of issues re-tagged each iteration across all 5 loops, accomplishing nothing).
- `hephaestus-automation-loop --issues <N>` runs but the implementer logs `Skipping #<N> (state:skip)` and does nothing (~3-second loops).
- A green-but-UNARMED pending-review PR (lacks `state:implementation-go`) gets spuriously skipped because a repo-level CI-driver run returned non-zero.
- A CLOSED issue passed via `--issues` is still driven and tagged.
- You need to recover a PR ALREADY stranded by `state:skip` (the script never removes it — only an operator does).

## Verified Workflow

The prevention fix shipped in **PR #1584** ("stop wrongly applying state:skip in
a self-perpetuating cycle"), with companion fixes **#1572** (review-loop
off-by-one), **#1575** (no-commit retry), and **#1589** (remaining bugs). A
clean run after they merged (output.log 2026-06-23 20:52, issues 1550,1548)
merged PR #1590 with 0 errors and 0 skips, and the closed issue #1550 logged
`is closed — excluding from phase loop`. **verified-ci.**

The key maintainer decision: **`state:skip` is OPERATOR-ONLY and ABSOLUTE.** The
automation must NEVER remove it and NEVER auto-recover; it must be read LIVE from
the GitHub issue (not from a cache). The fix stops the script from wrongly
ADDING it. As a corollary, recovering an already-stranded PR is still a manual
operator action — the script will not undo it for you.

### Quick Reference

```bash
# --- Recover an ALREADY-stranded PR (operator action; the script never removes the label) ---

# 1. Confirm the issue carries state:skip
gh issue view <N> --json labels | grep state:skip

# 2. Remove the label by hand (ONLY after the original blocker is genuinely fixed)
gh issue edit <N> --remove-label state:skip

# 3. If the PR is also DIRTY, rebase onto current origin/main
git fetch origin
git rebase origin/main          # resolve conflicts, resign with key email
git push --force-with-lease

# 4. Re-run the loop scoped to the issue
hephaestus-automation-loop --issues <N>

# --- Diagnose a self-perpetuating cycle (if you are on an UNPATCHED baseline) ---
# Symptom: every loop re-tags state:skip on the same issues; nothing converges.
# Check whether a skipped issue actually OWNS a genuinely-stuck PR (conflict/red CI)
# vs. merely BLOCKED-on-review (awaiting review = NOT stuck), and whether any
# CLOSED issue is being driven. If so, you are hitting the pre-#1584 defects.
```

### Detailed Steps (root cause + fix)

1. **Recognize the self-perpetuating cycle.** A run on issues `[1554 OPEN, 1552 CLOSED]` re-tagged BOTH with `state:skip` every loop, accomplishing nothing across all 5 loops. This is DISTINCT from oscillation or unpushed-fix bugs — here the loop actively (re)applies the label itself.

2. **Understand the three stacked defects** (all behind the cycle):
   - **(a) `state:skip` was STICKY.** The only recovery path, `implementer._should_recover_stale_skip`, refused to recover whenever an OPEN PR existed (`if pr_number is not None: return False`). So an open issue with `state:plan-go` + an open PR was skipped forever.
   - **(b) drive-green's rc is REPO-LEVEL** (one CI-driver run over the whole batch), but `loop_runner` attributed a non-zero rc to EVERY issue in the batch and tagged each `state:skip` — with no check that the issue OWNED the failing PR. A green-but-UNARMED-pending-review PR (lacks `state:implementation-go`) landed in `ci_driver`'s `needs_action` bucket → rc=1 → spurious skip.
   - **(c) CLOSED issues pinned via `--issues`** bypassed the open-state filter and were driven + tagged too.

3. **Understand the deadlock.** The implementer won't touch the issue (skip honored, PR exists) BUT drive-green keeps driving the PR (found by branch, independent of skip) → green-but-unarmed → rc=1 → re-tags `state:skip`. Nothing converges.

4. **The fix (prevention-only).** `state:skip` is operator-only and absolute; the fix stops the script from wrongly ADDING it:
   - **implementer:** removed `_should_recover_stale_skip`; a live `state:skip` is ALWAYS honored (the operator removes it between runs).
   - **ci_driver._evaluate_run_result:** new `pending_review` bucket — a green-but-unarmed PR that only lacks `state:implementation-go` (awaiting review) does NOT count toward `needs_action`/rc=1.
   - **loop_runner:** `_filter_open_issues` drops CLOSED issues from an explicit `--issues` batch before the phase loop; `_issue_owns_genuinely_failing_pr` gates the `state:skip` tag on the issue actually OWNING a genuinely-stuck PR (conflict/red CI), verified live.
   - **pr_manager.pr_is_genuinely_stuck:** shared classifier (DIRTY/CONFLICTING/red = stuck; BLOCKED-on-review/green = NOT stuck) — single source of truth for `ci_driver` + `loop_runner`. NOTE: a `BLOCKED` `mergeStateStatus` alone is NOT stuck (it's the awaiting-review state); only a conflict or a red `statusCheckRollup` conclusion is.

5. **Recover an already-stranded PR (operator action).** Because the script never removes `state:skip`, an operator must do it: confirm the label, `gh issue edit <N> --remove-label state:skip` ONLY after the original blocker is genuinely fixed, rebase the PR if DIRTY, then re-run the loop scoped to the issue. If you remove the label while the blocker still exists, the work will simply not converge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat `state:skip` as an inherent sticky safety cap and only recover manually | Re-run the loop, then have operators strip the label by hand each time | The loop was itself wrongly ADDING the label every iteration in a self-perpetuating cycle — manual removal alone never converged. | The stickiness was a BUG in how the script applied the label, not an inherent property. Fix the script (never auto-add); keep manual removal only for already-stranded PRs. |
| Let `_should_recover_stale_skip` auto-recover only when no PR exists | `if pr_number is not None: return False` — refuse recovery whenever an open PR exists | An open issue with `state:plan-go` + an open PR was skipped FOREVER; the implementer never touched it while drive-green kept re-tagging it. | Auto-recovery is the wrong model. Remove `_should_recover_stale_skip` entirely; `state:skip` is operator-only and absolute, honored live every run. |
| Attribute the repo-level drive-green rc to every issue in the batch | `loop_runner` tagged each issue `state:skip` on a non-zero CI-driver rc, with no ownership check | drive-green's rc is REPO-LEVEL (one run over the whole batch); a green-but-unarmed pending-review PR landed in `needs_action` → rc=1 → spurious skip of unrelated issues. | Gate the tag on `_issue_owns_genuinely_failing_pr` (verified live) and add a `pending_review` bucket so awaiting-review PRs never count toward rc=1. |
| Drive + tag CLOSED issues passed via `--issues` | Explicit `--issues` batch bypassed the open-state filter | CLOSED issues were driven and re-tagged `state:skip`, churning every loop. | Add `_filter_open_issues` to drop CLOSED issues from an explicit batch BEFORE the phase loop (`is closed — excluding from phase loop`). |
| Classify a `BLOCKED` `mergeStateStatus` PR as stuck | Used mergeStateStatus alone to decide a PR was failing | `BLOCKED` is the normal awaiting-review state — treating it as stuck caused spurious skips of healthy green PRs. | Use the shared `pr_manager.pr_is_genuinely_stuck` classifier: only DIRTY/CONFLICTING or a red `statusCheckRollup` conclusion is stuck; BLOCKED-on-review/green is NOT. |

## Results & Parameters

### The label and log lines

- Label: `state:skip` (operator-only, absolute, read live from the GitHub issue).
- Implementer log: `Skipping #<N> (state:skip)`.
- Closed-issue filter log: `is closed — excluding from phase loop`.
- Cycle signature (pre-#1584): the same issues re-tagged `state:skip` every loop, nothing converges across all 5 loops.

### Detection

```bash
gh issue view <N> --json labels | grep state:skip
```

### The fix (PR #1584) — components

| Component | Change |
|-----------|--------|
| `implementer` | Removed `_should_recover_stale_skip`; a live `state:skip` is ALWAYS honored. |
| `ci_driver._evaluate_run_result` | New `pending_review` bucket: green-but-unarmed (lacks `state:implementation-go`) does NOT count toward `needs_action`/rc=1. |
| `loop_runner._filter_open_issues` | Drops CLOSED issues from an explicit `--issues` batch before the phase loop. |
| `loop_runner._issue_owns_genuinely_failing_pr` | Gates the `state:skip` tag on the issue actually OWNING a genuinely-stuck PR (verified live). |
| `pr_manager.pr_is_genuinely_stuck` | Shared classifier: DIRTY/CONFLICTING/red = stuck; BLOCKED-on-review/green = NOT stuck. Single source of truth for ci_driver + loop_runner. |

### Verified end-to-end

- After #1584 (+ companions #1572 review-loop off-by-one, #1575 no-commit retry, #1589 remaining bugs) merged, a clean run (output.log 2026-06-23 20:52, issues 1550,1548) merged PR #1590 with 0 errors, 0 skips; closed #1550 logged `is closed — excluding from phase loop`. verified-ci.

### Recovering an already-stranded PR (still valid)

```bash
gh issue view <N> --json labels | grep state:skip       # confirm
gh issue edit <N> --remove-label state:skip             # ONLY after blocker is fixed
git fetch origin && git rebase origin/main && git push --force-with-lease  # if DIRTY
hephaestus-automation-loop --issues <N>                  # re-run scoped
```

The script never removes `state:skip` — so manual removal remains the correct
operator move for an already-stranded PR. Remove it ONLY when the original
blocker is genuinely resolved.

### Related

- Pair with the unpushed-fix-oscillation recovery (the loop may carry an unpushed fix commit).
- Pair with rebasing DIRTY PRs before the loop will touch them.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Root-cause fix for the self-perpetuating `state:skip` cycle (PR #1584 + #1572/#1575/#1589) | verified-ci; clean run merged PR #1590 with 0 errors/0 skips, excluded closed #1550; 2026-06-23 |
| ProjectHephaestus | Original operator recovery of skip-capped PRs (issue #719 / PR #1013) | verified-local; reached GO + CI-pending at capture; 2026-06-11 |
