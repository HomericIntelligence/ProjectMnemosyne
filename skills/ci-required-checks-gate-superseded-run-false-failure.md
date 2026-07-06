---
name: ci-required-checks-gate-superseded-run-false-failure
description: "Use when: (1) a PR's `gh pr view --json statusCheckRollup` shows the SAME check name (e.g. `required-checks-gate`) as BOTH FAILURE and SUCCESS and you're about to conclude CI failed, (2) a docs-only / path-filtered PR shows heavy jobs (lint, unit-tests, build, pixi-check, schema-validation, shellcheck, license-scan) as SKIPPED or CANCELLED and you worry they're 'missing', (3) you see CANCELLED jobs paired with SKIPPED ones in the rollup and can't tell if the PR is red, (4) a path-filtering `changes-gate` feeds a `required-checks-gate` aggregator and you need to know the healthy shape, (5) you're tempted to 'fix' a non-existent CI failure on an otherwise-mergeable PR. The trap: the FAILURE/CANCELLED rollup entries belong to an EARLIER workflow run superseded and cancelled by concurrency; a cancelled run's gate reports FAILURE. Authoritative signal = the LATEST run for the head SHA, not the aggregated rollup."
category: ci-cd
date: 2026-07-01
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-actions, required-checks-gate, changes-gate, path-filter, docs-only, concurrency, cancel-in-progress, superseded-run, status-check-rollup, false-failure, gh-run-list, branch-protection, verified-ci]
---

# CI `required-checks-gate` Superseded-Run False Failure (docs-only PRs)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Objective** | Stop misreading a healthy docs-only PR as failed. A path-filtering `changes-gate` correctly SKIPS heavy jobs and `required-checks-gate` PASSES, but `gh pr view --json statusCheckRollup` shows the SAME check name as BOTH FAILURE and SUCCESS because a concurrency-superseded (cancelled) earlier run's gate reports FAILURE. |
| **Outcome** | Successful — diagnosed by ignoring the mixed rollup and inspecting the NEWEST "Required Checks" run for the head SHA (`gh run list` → `gh run view --json jobs`). The latest run was all-green with heavy jobs `skipped`; the FAILURE/CANCELLED entries were a superseded run. No "fix" was needed; the PR merged clean. |
| **Verification** | verified-ci — ProjectHephaestus PR #1740 (issue #1496), a docs-only change (`CLAUDE.md` + `docs/plugin-installation.md`), merged 2026-07-01 with the latest Required Checks run (28550035548) at conclusion=success. |
| **History** | n/a (initial version) |

## When to Use

- `gh pr view <n> --json statusCheckRollup` shows a check name (e.g. `required-checks-gate`) appearing as **both `FAILURE` and `SUCCESS`**, and you're about to conclude CI failed.
- A **docs-only / path-filtered PR** shows heavy jobs (`lint`, `unit-tests`, `integration-tests`, `build`, `pixi-check`, `schema-validation`, `shellcheck`, `license-scan`, `symlink-check`, `deps/version-sync`, `security/*`, `justfile-check`) as **SKIPPED** and you worry they're "missing" or the gate is broken.
- You see **CANCELLED** jobs paired with **SKIPPED** jobs in the rollup and can't tell if the PR is red.
- The repo uses a path-filtering **`changes-gate`** job feeding a **`required-checks-gate`** aggregator, and you need the healthy shape to compare against.
- You're tempted to "fix" a CI failure on a PR that is actually green and mergeable.

## The Core Insight: mixed FAILURE/SUCCESS = an old run was superseded

ProjectHephaestus CI wires a path-filtering `changes-gate` job into a `required-checks-gate`
aggregator. On a docs-only PR (only `*.md`/docs paths changed), `changes-gate` yields the skip
path: it path-filters the heavy jobs out, they report **SKIPPED**, and `required-checks-gate`
**PASSES** because gate-skipped jobs count as satisfied. That is the correct, green docs-only shape.

The trap is `gh pr view --json statusCheckRollup`. It aggregates statuses **across runs** and can
show MULTIPLE entries per check name:

- `required-checks-gate` as **both `FAILURE` and `SUCCESS`**, and
- many heavy jobs as **CANCELLED** paired with **SKIPPED**.

Read naively, this looks like CI failed. It did not. The `FAILURE`/`CANCELLED` entries belong to an
**EARLIER "Required Checks" workflow run** that was **superseded and cancelled by concurrency** when
a newer push/run started. **A cancelled run's gate reports FAILURE** — that FAILURE is an artifact
of cancellation, not a genuine test failure.

The authoritative signal is the **LATEST run for the head SHA**, not the aggregated rollup. Dedupe
by newest run per check: a check name appearing as both FAILURE and SUCCESS means an old run was
superseded — trust the newest.

## Verified Workflow

> **Warning:** Do NOT trust the aggregate `statusCheckRollup` when the same check name shows both
> FAILURE and SUCCESS. Inspect the newest run's jobs instead.

### Quick Reference

```bash
# 1. List runs for the branch; find the NEWEST completed "Required Checks" run.
gh run list --branch <branch> --limit 15 \
  --json databaseId,name,conclusion,status,workflowName,createdAt

# 2. Inspect the NEWEST run's jobs (NOT the rollup):
gh run view <newest_run_id> --json jobs --jq '.jobs[] | {name, conclusion}'

# 3. Confirm the PR is actually clean (mergeable), not by eyeballing rollup colors:
gh pr view <n> --json mergeStateStatus,state,mergedAt
```

Healthy docs-only shape (the newest run):

```text
changes-gate          = success
required-checks-gate  = success
pr-policy             = success
auto-merge-policy     = success
lint / unit-tests / integration-tests / build / pixi-check /
schema-validation / shellcheck / license-scan / ...  = skipped   # NOT failure
```

Older CANCELLED runs are concurrency-superseded — **ignore them; they are not genuine failures.**

### Detailed Steps and Durable Insights

#### 1. Dedupe the rollup by newest run per check name

`statusCheckRollup` is not per-run — it can carry stale statuses from a superseded run alongside the
current run's statuses. When a check name appears as both `FAILURE` and `SUCCESS`, that is the
signature of an old run being superseded and cancelled by concurrency. Do not average the colors;
find the newest run and read only its statuses.

#### 2. A cancelled run's gate reports FAILURE — that is not a test failure

When concurrency (`cancel-in-progress: true`) cancels an in-flight "Required Checks" run because a
newer push arrived, the cancelled run's aggregator job (`required-checks-gate`) resolves to
**FAILURE**, and its heavy jobs resolve to **CANCELLED**. These are artifacts of the cancellation,
not evidence anything is broken. The surviving newer run is authoritative.

#### 3. SKIPPED heavy jobs on a docs-only PR are the CORRECT green state

`changes-gate` path-filters heavy jobs out when only docs/`*.md` paths changed. Those jobs report
**SKIPPED**, and `required-checks-gate` still **PASSES** — a gate-skipped job counts as satisfied.
SKIPPED here is a feature, not a gap. Do not "fix" a docs-only PR to force lint/unit-tests to run.

#### 4. Confirm mergeability with `mergeStateStatus`, not rollup colors

To settle whether the PR is actually clean, query `gh pr view <n> --json mergeStateStatus,state,
mergedAt`. A `CLEAN`/`mergedAt`-set answer is decisive; the rollup's mixed colors are noise from the
superseded run.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Read `statusCheckRollup` and saw `required-checks-gate` FAILURE | Concluded CI failed and started trying to "fix" a non-existent problem on a docs-only PR | The FAILURE entry belonged to a superseded/cancelled concurrency run, not the head SHA's latest run; the check name also appeared as SUCCESS from the current run | Dedupe the rollup by newest run per check; a check name appearing as BOTH FAILURE and SUCCESS means an older run was superseded — trust the newest run, not the aggregate |
| Assumed a docs-only PR must run lint/unit-tests | Saw those jobs SKIPPED and worried they were "missing" / the gate was misconfigured | `changes-gate` path-filters them out by design; a gate-SKIPPED heavy job satisfies `required-checks-gate` | SKIPPED heavy jobs on a docs-only PR are the correct, green state — not a gap; do not force them to run |
| Interpreted CANCELLED jobs as real failures | Treated CANCELLED (paired with SKIPPED) rollup entries as evidence CI broke | CANCELLED came from a concurrency-superseded run cancelling in-flight jobs when a newer push started; a cancelled run's gate reports FAILURE | Ignore CANCELLED/FAILURE entries from superseded runs; inspect the NEWEST run's jobs via `gh run view <id> --json jobs` |
| Judged mergeability by rollup colors | Eyeballed the mixed red/green rollup to decide if the PR was blocked | The rollup mixes stale and current statuses; colors alone can't distinguish superseded from live | Query `gh pr view <n> --json mergeStateStatus,state,mergedAt` for the authoritative mergeability answer |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Repo / PR / issue** | HomericIntelligence/ProjectHephaestus, PR #1740, issue #1496 |
| **Branch / commit** | `1496-auto-impl` @ `3381da57` |
| **Change class** | Docs-only — `CLAUDE.md` (added an argument-hint column to the skill catalog) + `docs/plugin-installation.md` (usage examples); no Python/code touched |
| **Trigger** | Only `*.md`/docs paths changed → `changes-gate` yields the skip path for all heavy jobs |
| **Authoritative run** | "Required Checks" run **28550035548**, conclusion=**success** |
| **Latest-run job shape** | `changes-gate=success`, `pr-policy=success`, `auto-merge-policy=success`, `required-checks-gate=success`; every heavy job = `skipped` |
| **Superseded run** | An earlier "Required Checks" run cancelled by concurrency → its `required-checks-gate`=FAILURE, heavy jobs=CANCELLED (rollup artifacts, NOT genuine failures) |
| **Outcome** | PR merged 2026-07-01; no fix required — the "failure" was a superseded-run artifact |

### Evidence commands (copy-paste)

```bash
# The three commands that resolve the false failure:
gh run list --branch 1496-auto-impl --limit 15 \
  --json databaseId,name,conclusion,status,workflowName,createdAt
gh run view 28550035548 --json jobs --jq '.jobs[] | {name, conclusion}'
gh pr view 1740 --json mergeStateStatus,state,mergedAt
```

### Heavy jobs path-filtered out on docs-only PRs

`lint`, `unit-tests`, `integration-tests`, `build`, `pixi-check`, `schema-validation`,
`shellcheck`, `license-scan`, `symlink-check`, `deps/version-sync`, `security/*`, `justfile-check`
— all report **SKIPPED** via `changes-gate`, and `required-checks-gate` still passes.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1740 / issue #1496 | Docs-only change (`CLAUDE.md` + `docs/plugin-installation.md`) merged 2026-07-01. `statusCheckRollup` showed `required-checks-gate` as both FAILURE and SUCCESS and heavy jobs as CANCELLED+SKIPPED; the newest Required Checks run (28550035548) was all-green with heavy jobs `skipped`. The FAILURE/CANCELLED entries were a concurrency-superseded run — no real failure. |
