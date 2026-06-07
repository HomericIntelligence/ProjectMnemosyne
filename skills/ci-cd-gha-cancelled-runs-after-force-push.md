---
name: ci-cd-gha-cancelled-runs-after-force-push
description: "CANCELLED GitHub Actions runs masquerade as PR failures from TWO distinct triggers. Trigger 1 (force-push): after git push --force-with-lease (e.g. post-rebase), GHA marks in-flight runs on the prior sha as CANCELLED, and these appear in the PR's status-check rollup as failure indicators alongside the new sha's runs. Trigger 2 (concurrency supersession): a rerun's jobs CANCELLED with 'Canceling since a higher priority waiting request for required-Required Checks-<branch> exists' — gh pr checks shows N fail but they are superseded/cancelled runs, not real failures (concurrency-group supersession reads as failure). PR looks broken even though the current tip / latest run is healthy. Use when: (1) a PR shows many failed checks but mergeStateStatus is BLOCKED with mergeable=MERGEABLE, (2) you need to distinguish real failures from rebase-orphaned or concurrency-superseded cancelled runs, (3) gh pr checks reports 'N fail' right after a rerun, (4) deciding whether to manually relaunch or just wait."
category: ci-cd
date: 2026-06-06
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: ci-cd-gha-cancelled-runs-after-force-push.history
tags: [github-actions, rebase, force-push, concurrency, supersession, status-checks, mergeability, gh-cli]
---

# GHA Status Rollup After Force-Push: Distinguishing Real Failures from Cancelled-by-Rebase

## Overview

CANCELLED GitHub Actions runs can masquerade as PR failures from **two distinct triggers**:

- **Trigger 1 — force-push (verified-local, 2026-05-10):** post-rebase `git push --force-with-lease` cancels in-flight runs on the prior sha.
- **Trigger 2 — concurrency supersession (verified-ci, 2026-06-06):** a higher-priority queued run cancels an in-flight rerun for the same branch's Required Checks; `gh pr checks` then reports "N fail" for runs that never actually failed.

The frontmatter `verification: verified-ci` reflects the new supersession finding, which was verified on live CI (ProjectHephaestus PR #1073). The original force-push finding remains **verified-local** — it was diagnosed by inspecting the rollup, not by re-running CI to confirm.

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 (Trigger 2 added); 2026-05-10 (Trigger 1 original) |
| **Objective** | Distinguish CANCELLED runs that merely *look* like failures in a PR rollup from genuine `FAILURE` conclusions — whether the cancellation came from a force-push (Trigger 1) or concurrency-group supersession (Trigger 2). |
| **Outcome (Trigger 1)** | On PR #5380, all 50+ "failures" were CANCELLED runs from the rebased-out sha (`73691f415`). The current tip (`db8ee2a0f`) had zero `FAILURE` checks — only `success`, `queued`, and `in-progress`. PR was healthy; the GitHub UI's red indicator was misleading. |
| **Outcome (Trigger 2)** | On ProjectHephaestus PR #1073, `gh pr checks` summarized "4 fail" after a `gh run rerun --failed`; all four (unit-tests, integration-tests, pixi-check, shellcheck) were CANCELLED mid-run by a higher-priority queued run. Zero tests actually failed; the latest run concluded success. |
| **Verification** | verified-ci (Trigger 2, 2026-06-06); verified-local (Trigger 1, 2026-05-10) |

## When to Use

- A PR's status-check page shows many red indicators after a recent rebase / force-push
- `gh pr view <N> --json mergeStateStatus,mergeable` returns `BLOCKED` + `MERGEABLE` (not `DIRTY`)
- You're tempted to "rerun failed jobs" but want to confirm there's anything actually failed first
- You need to filter `gh pr view ... --json statusCheckRollup` to see only real `FAILURE` (excluding `CANCELLED`)
- `gh pr checks <N>` reports "N fail" shortly after you ran `gh run rerun <id> --failed`, and the failing jobs' logs end with `The operation was canceled.` / `Canceling since a higher priority waiting request for required-Required Checks-<branch> exists` — these are concurrency-superseded runs, not real failures (Trigger 2)

## Verified Workflow

### Quick Reference

```bash
# Get the rollup, broken down by conclusion
gh pr view <PR> --json statusCheckRollup --jq '
  {
    real_failures: [.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name],
    cancelled_count: ([.statusCheckRollup[] | select(.conclusion == "CANCELLED")] | length),
    in_progress_count: ([.statusCheckRollup[] | select(.status != "COMPLETED" and (.conclusion // "") == "")] | length),
    success_count: ([.statusCheckRollup[] | select(.conclusion == "SUCCESS")] | length)
  }'

# Tighter filter: only runs on the current PR tip sha
TIP_SHA=$(gh pr view <PR> --json headRefOid --jq .headRefOid)
gh run list --branch <branch> --limit 60 --json databaseId,name,conclusion,status,headSha \
  | jq --arg sha "$TIP_SHA" '
      [.[] | select(.headSha == $sha)]
      | group_by(.conclusion // "queued")
      | map({key: (.[0].conclusion // "queued"), count: length})
    '
```

### Detailed Steps

1. **Identify the current tip sha** of the PR with `gh pr view <PR> --json headRefOid`. Anything not on this sha is from a prior force-push and is irrelevant.
2. **Filter the run list** to only entries on that sha. Counts of `success` / `queued` / `in_progress` / `failure` are the real story.
3. **Distinguish "stuck queued" from "true bottleneck."** `gh run list ... --json createdAt` + current UTC time gives queue age. >30 min queued during heavy CI load = expected; >2 hr = stuck, file a runner-availability concern.
4. **Decide action**:
   - `failure` count == 0 + queued only → **wait**, do not rerun (per `feedback_no_ci_retries` in this org's memory).
   - `failure` count > 0 → investigate the named jobs; rerun ONLY if reproducibly clean (gitleaks-flake-on-network class), otherwise root-cause the failure.
   - Many CANCELLED on a sha that's no longer the tip → ignore; they're stale.

### Trigger 2: Concurrency Supersession (verified-ci, 2026-06-06)

The same "cancelled reads as failure" symptom also arises **without any force-push**, via GitHub Actions concurrency-group supersession. When a higher-priority run is queued for the same branch's Required Checks while a rerun is in flight, GHA cancels the in-flight rerun's jobs mid-execution. In the PR rollup and especially in `gh pr checks` output, these CANCELLED jobs render as "fail" even though zero tests failed.

**Observed live on ProjectHephaestus PR #1073:** after `gh run rerun <id> --failed` to clear a stale `pr-policy` failure, a higher-priority run was queued for the same branch. The rerun's jobs (unit-tests, integration-tests, pixi-check, shellcheck) were CANCELLED with:

```text
Canceling since a higher priority waiting request for required-Required Checks-<branch> exists
The operation was canceled.
```

`gh pr checks` summarized "4 fail" — but `gh run view --log --job=<jobid> | grep -c 'FAILED'` returned 0, the "Run unit tests" step was only ~4% through (last line PASSED) when CANCELLED, and the actual latest run for the branch concluded success.

**Cancellation-reason string to grep for** (distinguishes supersession from a real failure):

```bash
# A superseded job's log ends with "The operation was canceled." and contains
# the higher-priority-request banner, with NO preceding "FAILED".
gh run view --log --job=<jobid> | grep -E 'Canceling since a higher priority waiting request|The operation was canceled\.'
```

**Verify against the LATEST run for the branch** (the authoritative signal — a "fail" in `gh pr checks` can be a cancelled/superseded run):

```bash
# 1. Look at the most recent runs for the branch; the newest is what matters.
gh run list --branch <branch> --limit 3

# 2. Show ONLY true failures from the rollup (excludes CANCELLED via state/conclusion):
gh pr view <N> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select((.conclusion // .state) == "FAILURE")'

# 3. Confirm a suspected job is a supersession artifact, not a real failure:
gh run view --log --job=<jobid> | grep -c 'FAILED'   # 0 => no real failures
gh run view --log --job=<jobid> | tail -n 5          # ends with "The operation was canceled."
```

If step 2 prints nothing and the latest run (step 1) is `completed/success` (or still in progress), the "N fail" from `gh pr checks` is a supersession artifact — **just re-run or wait for the latest run**; do not treat it as a genuine failure.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Read the PR's UI showing "50+ failed checks" and assumed real test failures | Most of those entries had `conclusion: CANCELLED`, not `FAILURE`. They were from the previous sha that got force-pushed away. UI doesn't distinguish them visually from the current sha's entries. | The rollup mixes runs from ALL commits the PR has had, not just the tip. Filter by sha explicitly. |
| 2 | `gh pr view <PR> --json statusCheckRollup --jq '.statusCheckRollup[] \| select(.conclusion != "SUCCESS")'` | Surfaces CANCELLED, FAILURE, AND in-progress runs as a single bucket — still misleading. | Filter by `conclusion == "FAILURE"` specifically; treat `CANCELLED` as a separate (mostly ignorable) category. |
| 3 | Run `gh run rerun --failed <run_id>` on a workflow whose only failures were CANCELLED-by-rebase | The workflow was already in `queued` (the new sha had auto-triggered new runs). Rerun was a no-op or briefly contended with the auto-triggered run. | After force-push, GHA auto-schedules new workflow runs on the new sha. No manual rerun needed for the new sha. |
| 4 | Read `gh pr checks <N>` output reporting "4 fail" as a real test failure (ProjectHephaestus PR #1073) | The 4 "fail" entries were jobs CANCELLED by concurrency-group supersession after a `gh run rerun --failed` — a higher-priority run for the same Required Checks was queued and cancelled the in-flight rerun (`Canceling since a higher priority waiting request ... exists`). Zero tests failed; the latest run concluded success. | A "fail" in `gh pr checks` can be a cancelled/superseded run. Confirm against the LATEST run for the branch (`gh run list --branch <b> --limit 3`) and grep the job log for `FAILED` (count 0 + ending in "The operation was canceled." => supersession artifact, not a real failure). |

## Results & Parameters

```bash
# Quick health check after a force-push
PR=5380
TIP=$(gh pr view $PR --json headRefOid --jq .headRefOid)
gh pr view $PR --json statusCheckRollup,mergeable,mergeStateStatus --jq "{
  mergeable, mergeState: .mergeStateStatus,
  real_failures: [.statusCheckRollup[] | select(.conclusion == \"FAILURE\") | .name],
  cancelled: [.statusCheckRollup[] | select(.conclusion == \"CANCELLED\")] | length
}"
# If real_failures: [] and mergeable: "MERGEABLE" -> PR is healthy, just wait.
```

Heuristic table:

| Indicator | Meaning |
|---|---|
| `mergeable: MERGEABLE` + `mergeStateStatus: BLOCKED` + `real_failures: []` | Healthy, blocked only on in-progress / queued required checks |
| `mergeable: CONFLICTING` + `mergeStateStatus: DIRTY` | Real conflict — rebase needed |
| `mergeable: MERGEABLE` + `mergeStateStatus: BLOCKED` + `real_failures: [...]` | Real failures — investigate |
| Many `CANCELLED` entries, all on the same non-tip sha | Stale from a force-push, ignore |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5380 after rebase to resolve a conflict; appeared to have 50+ failures but all were CANCELLED from the prior sha (Trigger 1, force-push) | Distinguishing CANCELLED-by-rebase from real FAILURE saved a wasteful rerun cycle (verified-local) |
| ProjectHephaestus | PR #1073 (2026-06-06); `gh pr checks` reported "4 fail" after `gh run rerun --failed`, but all four jobs were CANCELLED by concurrency-group supersession (Trigger 2). Grepping the job log returned 0 `FAILED`; the latest run concluded success (verified-ci) | Confirmed that `gh pr checks` "fail" can be a concurrency-superseded run; verifying against the latest run avoided a false failure diagnosis |
