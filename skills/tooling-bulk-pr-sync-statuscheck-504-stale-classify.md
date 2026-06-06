---
name: tooling-bulk-pr-sync-statuscheck-504-stale-classify
description: "Three compounding bugs that stop a bulk PR-sync tool (e.g. hephaestus.github.fleet_sync) from rebasing a large PR queue after a fix lands on main. (1) statusCheckRollup 504: `gh pr list --json ...,statusCheckRollup --limit 100` returns HTTP 504 Gateway Timeout at ~50+ open PRs because the rollup aggregates every check on every PR; drop statusCheckRollup from the bulk list and fetch CI per-PR via `gh pr view <n> --json statusCheckRollup` (one PR per call does not 504), downgrading a flaky per-PR fetch to CI=UNKNOWN instead of aborting. (2) Silent no-op on list failure: code that catches the gh error and `return []` logs 'No open PRs' and exits SUCCESS while skipping the whole queue; distinguish 'no PRs' from 'list failed' and RAISE on a genuine list failure so the run's exit status reflects the unprocessed queue. (3) Stale-failing misclassification: marking ANY CI=FAILURE PR as FAILING (skip) strands the queue, because after a fix lands on main every BEHIND PR shows its OLD failing run; require mergeStateStatus==CLEAN for the FAILING classification — a BEHIND/BLOCKED+MERGEABLE red PR must classify as OUTDATED so it gets rebased (re-running CI fresh); CONFLICTING stays CONFLICTED. Use when: (1) building or debugging any tool that bulk-lists PRs via gh, (2) a gh pr list with statusCheckRollup times out / 504s at scale, (3) a fix landed on main and the whole PR queue needs rebasing, (4) a sync tool reports 'no PRs' or success but did nothing, (5) PRs show stale failing CI after a main fix and the tool skips them all, (6) a classifier needs to tell genuine PR-specific failures from stale red CI on behind branches."
category: tooling
date: 2026-06-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - fleet-sync
  - gh-pr-list
  - statusCheckRollup
  - 504-gateway-timeout
  - mergeStateStatus
  - stale-ci
  - silent-noop
  - bulk-pr-sync
  - pr-classification
  - rebase-queue
  - per-pr-ci-fetch
---
# Bulk PR-Sync Tooling: statusCheckRollup 504, Silent List No-op, and Stale-Failing Classification

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Make a fleet/bulk PR-sync tool (`hephaestus.github.fleet_sync`) actually rebase a large PR queue after a fix lands on main |
| **Outcome** | Fixed; the real run listed all 56 open PRs and rebased 49 of them (the remaining 7 were genuine merge conflicts) |
| **Verification** | verified-ci — PRs #1028 and #1030 merged to main; the subsequent fleet-sync run listed 56 PRs and rebased 49 (ProjectHephaestus, 2026-06-06) |

Three independent-but-compounding bugs each silently neutered the tool. Any one of
them alone makes the tool "succeed" while rebasing nothing. They are documented
together because they share one search surface: *a bulk PR-sync tool that runs but
fails to drain the queue.*

## When to Use

- Building or debugging any tool that bulk-lists PRs via `gh` (especially `gh pr list --json ...`).
- A `gh pr list` request that includes `statusCheckRollup` times out / returns HTTP 504 at scale (~50+ open PRs).
- A fix landed on main and the whole PR queue needs rebasing, but the sync tool rebases nothing.
- A sync tool reports "no PRs" / SUCCESS but did nothing (silent no-op masking the queue).
- PRs show stale failing CI after a main fix and the tool skips all of them.
- Writing or reviewing a PR classifier that must tell a genuine PR-specific failure from stale red CI on a behind branch.
- See also the `batch-pr-rebase-workflow` skill (trigger 28: stale CI results need a rebase push to re-run fresh CI) for the rebase mechanics once classification is correct.

## Verified Workflow

### Quick Reference

```bash
# 1. Bulk list WITHOUT statusCheckRollup (does not 504 even at 56+ PRs):
gh pr list --state open --limit 100 \
  --json number,title,headRefName,baseRefName,headRefOid,mergeable,mergeStateStatus

# 2. Fetch CI state PER-PR (one PR per call never 504s):
gh pr view <n> --json statusCheckRollup
#    A flaky/failed per-PR fetch => CI = UNKNOWN (fall through to rebase),
#    NOT an abort of the whole run.

# 3. List-failure is FATAL, not empty:
#    "no open PRs"  => return []        (legitimate empty)
#    gh call failed => raise            (caller counts it a failure, continues to next repo)
```

### Detailed Steps

**Fix 1 — Don't fetch `statusCheckRollup` in the bulk list.**
`statusCheckRollup` aggregates every check on every PR, so a single bulk
`gh pr list --json ...,statusCheckRollup --limit 100` makes GitHub fan out across
the whole queue and returns **HTTP 504 Gateway Timeout** once there are ~50+ open PRs.
Request only the cheap fields in the bulk call
(`number,title,headRefName,baseRefName,headRefOid,mergeable,mergeStateStatus`) and
fetch CI state **per PR** with `gh pr view <n> --json statusCheckRollup`. One PR per
call does not 504. If a per-PR fetch is flaky, downgrade *that* PR to `CI = UNKNOWN`
(so it falls through to a rebase) rather than aborting the entire run.

**Fix 2 — Distinguish "no PRs" from "list failed".**
The original code caught the `gh` error and `return []`, so the tool logged
"No open PRs" and exited SUCCESS while skipping the entire queue — a dangerous silent
no-op that masks every PR. Make a genuine list failure **raise**; the caller counts it
as a failure so the run's exit status reflects the unprocessed queue (and the run can
still continue to other repos). Only a true empty result returns `[]`.

**Fix 3 — Require `mergeStateStatus == CLEAN` for the FAILING classification.**
The classifier marked ANY PR with `CI = FAILURE` as `FAILING` (skip), even when the red
result was **stale** — the branch was `BEHIND`/`BLOCKED` and its checks ran against an
OLD base (commonly a failure already fixed on main). After a fix lands on main, EVERY
behind PR shows its old failing run, so the tool skips ALL of them and rebases nothing.
Only a PR that is **up to date with its base yet still red** is a genuine PR-specific
failure worth skipping, so gate `FAILING` on `mergeStateStatus == CLEAN`. A
`BEHIND`/`BLOCKED` + `MERGEABLE` PR with stale red CI must classify as **OUTDATED** so it
gets rebased (which re-runs CI fresh). `CONFLICTING` stays `CONFLICTED`.

Classification table after the fix:

| mergeable | mergeStateStatus | CI state | Classification | Action |
|-----------|------------------|----------|----------------|--------|
| MERGEABLE | CLEAN | FAILURE | FAILING | skip (genuine PR-specific failure) |
| MERGEABLE | BEHIND / BLOCKED | FAILURE (stale) | OUTDATED | rebase (re-runs CI fresh) |
| MERGEABLE | BEHIND / BLOCKED | SUCCESS / UNKNOWN | OUTDATED | rebase |
| CONFLICTING | DIRTY | any | CONFLICTED | per-PR conflict resolution |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Bulk `gh pr list --json ...,statusCheckRollup --limit 100` | HTTP 504 Gateway Timeout once ~50+ PRs are open — the rollup aggregates every check on every PR in one request | Never request `statusCheckRollup` in a bulk list; fetch CI per-PR via `gh pr view <n>` |
| 2 | Catch the `gh` list error and `return []` | Tool logged "No open PRs" and exited SUCCESS while silently skipping the whole queue | A list failure is fatal, not empty — raise so exit status reflects the unprocessed queue |
| 3 | Dry-run after only fixing #1 + #2 | 55 of 56 PRs classified FAILING and skipped (Rebased: 1, Skipped: 55) — the classifier still skipped every behind PR's stale red CI | Classifying ANY `CI=FAILURE` as FAILING strands the queue after a main fix |
| 4 | Abort the whole run when one per-PR `gh pr view` is flaky | One transient fetch error would block the entire queue | Downgrade the flaky PR to `CI=UNKNOWN` (falls through to rebase); don't abort the run |

## Results & Parameters

**Diagnosis sequence (ProjectHephaestus, 2026-06-06):**

- Dry-run after Fix 1 + Fix 2 only: `Rebased: 1, Skipped: 55` (55/56 misclassified FAILING).
- Dry-run after Fix 3 (classification): all 56 OUTDATED → `Rebased+re-signed: 56, Skipped: 0`.
- Real run: rebased **49 / 56**. The 7 remaining were genuine merge CONFLICTS
  (`DIRTY` + `CONFLICTING`) needing per-PR resolution; the conflict-resolution agent
  process can time out (exit 143) on large/overlapping diffs.

**Field set for the bulk list (cheap, no 504):**

```text
number,title,headRefName,baseRefName,headRefOid,mergeable,mergeStateStatus
```

**Per-PR CI fetch (one call per PR):**

```bash
gh pr view <n> --json statusCheckRollup
```

**Key invariants:**

- `mergeStateStatus == CLEAN` is the *only* state in which a red PR is a genuine
  PR-specific failure (skip). Every other red state on a `MERGEABLE` PR is stale → rebase.
- A `gh` list failure must change the run's exit status; a true empty result must not.
- A per-PR CI fetch failure affects only that PR (→ `UNKNOWN`), never the whole run.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | `hephaestus.github.fleet_sync`; fixes shipped as PRs #1028 and #1030; subsequent run listed 56 PRs, rebased 49 | 2026-06-06, verified-ci |
