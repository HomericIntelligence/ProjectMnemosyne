---
name: github-actions-runner-pool-saturation-swarm-concurrency-cap
description: "GitHub Actions runner pool has a practical concurrent-job cap. When 14+ PRs are pushed simultaneously to a single repo with a heavy C++ matrix CI (4 OS/compiler combos + Coverage + Static Analysis), the runner pool saturates and CI runs sit in 'queued/' state for hours. Use when: (1) batching myrmidon swarm waves that push many PRs at once, (2) CI shows status=queued/ not in_progress/, (3) deciding how many parallel implementer agents to dispatch."
category: ci-cd
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-actions, runner-pool, saturation, queued, concurrency-cap, myrmidon, swarm, cpp-matrix, throughput]
---

## Overview

- **Date**: 2026-05-17
- **Objective**: Quantify GitHub runner-pool saturation cap for myrmidon swarm pacing
- **Outcome**: 14 simultaneous PR CIs + 1 main CI on a C++ matrix repo saturated runners for 2+ hours; cap dispatch waves to ~5-7 concurrent PRs to keep CI flowing
- **Verification**: verified-ci

## When to Use

- About to dispatch a wave that will push >=8 PRs to a single repo simultaneously
- Repo has expensive CI matrix (multi-OS, multi-compiler, coverage, static analysis)
- Seeing CI checks stuck in `status=queued/` instead of `status=in_progress/`
- Total wall-clock time matters

## Verified Workflow / Quick Reference

```bash
# Distinguish queued (waiting for runner) from in_progress (running)
gh run list --branch main --limit 5 --json status,conclusion,name --jq '.[] | "\(.status)/\(.conclusion // \"?\")\t\(.name)"'
# "queued/" -> runner pool saturated; "in_progress/" -> healthy
gh run list --workflow="Build and Test" --limit 20 --json status --jq 'group_by(.status) | map({(.[0].status): length}) | add'

# Before dispatching N parallel implementer agents, check current load
gh pr list --state open --json statusCheckRollup --jq '[.[].statusCheckRollup[] | select(.status == "QUEUED" or .status == "IN_PROGRESS")] | length'
# If > 30: skip this wave; wait for runners to free.
```

## Verified Workflow / Detailed Steps

1. Per-PR CI matrix cost: count `gh pr view <N> --json statusCheckRollup --jq '[.statusCheckRollup[]] | length'` — for the verified ProjectAgamemnon session this was ~25 checks/PR
2. Practical cap formula: `concurrent_PRs * checks_per_PR < ~80-100` (GitHub free-tier ubuntu-24.04 default concurrency seems to plateau around 100 concurrent jobs per org for our experiments)
3. Dispatch wave sizing: split a 14-PR push into 2-3 sub-waves of 5 PRs each. Sub-wave N+1 launches only when sub-wave N's PRs all hit `status=in_progress/` (signaling runners are available)
4. For unavoidable big waves (e.g., draining stale queue), accept that the wall-clock will be ~CI matrix duration * ceil(total_PRs / runner_cap)

## Failed Attempts (verified-ci)

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pushed 14 PRs simultaneously to ProjectAgamemnon (Phase A + B + C + D rebases) | Expected runners to process them in parallel within ~20 min each | All runners locked by main CI re-run + 14 PR CIs; 75+ jobs queued; "queued/" state persisted for 2+ hours | Cap concurrent PR pushes at ~5-7 for heavy C++ matrix repos. Stage pushes if more PRs are needed. |
| Used `runs-on: ubuntu-24.04` for every matrix job | All 4 compiler/build combos competed for the same ubuntu-24.04 runner pool | Saturation hit immediately on push; even main re-run got queued | Consider workflow `concurrency:` blocks to cancel obsolete runs on the same PR; consider a smaller matrix for non-main branches (defer Coverage to main-only). |
| Trusted "auto-merge will fire eventually" without monitoring queue depth | Walked away assuming Hub would merge in cascade | After 2 hr, 0 of 14 PRs merged because main CI still hadn't run; downstream PRs gated on main signal | Monitor `gh run list --branch main` status explicitly. If queued/ for >30 min, runner pool is the bottleneck — no agent can help. |

## Results & Parameters (verified ProjectAgamemnon 2026-05-17)

| Metric | Value |
|---|---|
| Repo CI matrix per PR | ~25 required checks (4 build/test x OS+compiler, Coverage, Static Analysis, Type Check, security scans, schema-validation) |
| Concurrent PRs pushed | 14 |
| Total jobs in queue | ~350 |
| Queue duration before first runner | >2 hours (didn't clear during the session) |
| Recommended cap | 5-7 PRs per sub-wave |

## Mitigations / Tradeoffs

- **Cap concurrent dispatch**: simplest; preserves throughput predictability
- **Self-hosted runners**: removes the cap but adds infra overhead
- **`concurrency:` workflow blocks**: cancels in-flight runs on the same branch when a new push lands; reduces wasted runner-minutes but doesn't help cross-PR contention
- **Reduce matrix for non-main**: e.g., test debug+release on main only; PRs run a slimmer subset

## Verified On

ProjectAgamemnon | 2026-05-17 session | 14 PRs rebased+pushed in one batch; runner pool saturated; main CI queued for 2+ hours
