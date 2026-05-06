---
name: github-actions-required-fanin-conflict-resolution
description: "Pattern for resolving rebase conflicts in _required.yml GitHub Actions fan-in workflows when sibling PRs each add new upstream workflows. Use when: (1) rebasing a sibling PR onto a main that absorbed other siblings adding fan-in entries (CodeQL SAST, Sanitizers, Lock Check, Integration Tests, etc.), (2) conflict in workflows: array under on.workflow_run, (3) conflict in fan-in jobs section, (4) rebase conflict on actions/checkout SHA pin where main has newer SHA than branch, (5) Dockerfile conflict where main added security packages and branch added build packages."
category: ci-cd
date: 2026-05-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - rebase
  - merge-conflict
  - workflow_run
  - fan-in
  - branch-protection
---

# GitHub Actions `_required.yml` Fan-In Conflict Resolution

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-05 |
| **Objective** | Document the deterministic merge-both-sides rule for rebase conflicts in `_required.yml` fan-in workflows when multiple sibling PRs each add a new upstream workflow + fan-in job |
| **Outcome** | Verified across 14 sibling PRs in HomericIntelligence/ProjectCharybdis on 2026-05-05; uniform application of merge-both-sides resolved every conflict without dropping a required status check |

## When to Use

- You are rebasing a sibling PR onto a `main` that has already absorbed one or more sibling PRs that each added a new upstream workflow + companion fan-in job to `.github/workflows/_required.yml`.
- A merge/rebase produces conflict markers inside the `workflows:` array under `on.workflow_run` of `_required.yml`.
- A merge/rebase produces conflict markers inside the fan-in jobs section of `_required.yml` (the jobs that mirror each upstream workflow's success/failure).
- A rebase conflict on a SHA-pinned action (e.g., `actions/checkout@<sha>`) where `main` pins a newer SHA than the branch.
- A rebase conflict in a `Dockerfile` where `main` added security/runtime packages (e.g., `python3-venv`, non-root `USER`) and the branch added build/feature packages (e.g., `libasan8 libubsan1` for sanitizer support).

## Verified Workflow

> **Verification level:** verified-ci — pattern confirmed on HomericIntelligence/ProjectCharybdis on 2026-05-05 across 14 sibling PRs (9 of which touched `_required.yml`); uniform merge-both-sides resolution unblocked every PR without missing-required-check failures.

### Quick Reference

```bash
# When _required.yml conflicts, the rule is ALWAYS merge-both-sides:
# 1. workflows: array — keep every entry from both sides
# 2. Fan-in jobs section — keep every job block from both sides
# 3. Concurrency / on triggers / non-job sections — main wins (newer infra)
# 4. SHA-pin conflicts on actions/checkout, etc. — main's SHA wins (newer)
```

### Detailed Steps

1. **Identify the conflict regions.** In `_required.yml`, conflicts almost always cluster in two places:
   - The `workflows:` list under `on.workflow_run.workflows`.
   - The fan-in jobs (one job per upstream workflow, named `<workflow-slug>` and using `needs:`/`if:` on the upstream `workflow_run` conclusion).

2. **For the `workflows:` array — keep every entry from both sides.** Each entry corresponds to a required status check in branch protection. Dropping one (by picking a single side) makes the missing fan-in job's check name unattainable, so the PR sits in "expected status checks not received" forever. Example resolved state:

   ```yaml
   on:
     workflow_run:
       workflows:
         - "Build"
         - "Tests"
         - "CodeQL SAST"          # from PR #124
         - "Sanitizers"           # from PR #57/72
         - "Lock Check"           # from PR #120
         - "Integration Tests"    # from PR #88
         - "Container Build and Publish"  # from PR #153
       types: [completed]
   ```

3. **For the fan-in jobs section — keep every job block from both sides.** Each block mirrors an upstream workflow's conclusion into a stable status context name. Typical job names seen in this session: `security-codeql`, `sanitizers`, `pixi-lock-check`, `integration-tests`, `docker-build`. Concatenating both sides preserves every required context.

4. **For non-job sections (`concurrency`, `permissions`, top-level `name`, top-level `on` keys other than the `workflows:` list) — let `main` win.** These are infrastructure tweaks, not additive feature lists; the branch's older copy is virtually always stale.

5. **For SHA-pinned action conflicts (e.g., `uses: actions/checkout@<sha>`) — take main's SHA.** The newer SHA has been audited at least as much as the older one; reverting it regresses supply-chain hardening (and may trigger CodeQL/Trivy findings on the next scan). Same rule for `actions/setup-*`, `docker/build-push-action`, etc.

6. **For Dockerfile apt package conflicts — keep all package names from both sides in the same `apt-get install` call.** Apt packages are additive. If `main` added `python3-venv` and the branch added `libasan8 libubsan1`, the resolved line lists all three.

7. **For Dockerfile structural directive conflicts (`USER`, `WORKDIR`, multi-stage `FROM ... AS ...`) — keep both intents.** A non-root `USER` directive from `main` is security-driven; sanitizer build steps from the branch are feature-driven. Reorder if needed (e.g., do package installs as root, then drop to the non-root user) but never delete one to satisfy the other.

8. **Rerun CI.** After resolution, push and confirm every required check name lights up. If a fan-in context shows pending forever, you missed an entry in step 2 or step 3.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Picking one side of `workflows:` array | Took the branch's version, which had `Sanitizers` but not `CodeQL SAST` | Branch protection's required check `security-codeql` is now missing — PR became BLOCKED with "expected status checks not received" | Always merge both sides of the `workflows:` array — every entry corresponds to a required check |
| Picking one side of fan-in jobs section | Took main's version, dropping the branch's new fan-in job | Branch's upstream workflow now reports a status check that nothing fans in, leaving the PR perpetually pending on that context | Always keep all fan-in job blocks from both sides — they're additive |
| Taking branch's older SHA pin in actions/checkout conflict | Branch pinned v4.2.2 (`11bd71901...`); main had v4.3.1 (`34e114876...`); took the branch | Reverted main's intentional bump, regressing supply-chain hardening; CodeQL/Trivy may flag the older SHA on subsequent scan | When SHA-pin conflicts on the same action, main's SHA wins (newer = at least as audited) |
| Picking one Dockerfile package list over the other | Branch added `libasan8 libubsan1` for sanitizers; main added `python3-venv` for build isolation. Took only one side. | Either sanitizer builds break (missing libasan/libubsan) or non-root venv setup breaks (missing python3-venv). | Apt packages are additive — keep all package names from both sides in the same `apt-get install` call. |

## Results & Parameters

### Resolution Cheatsheet

| Conflict Region | Resolution | Why |
| --------------- | ---------- | --- |
| `on.workflow_run.workflows:` array in `_required.yml` | Merge both sides — union of entries | Every entry maps to a required status check name |
| Fan-in jobs section in `_required.yml` | Merge both sides — concatenate job blocks | Every job mirrors an upstream conclusion into a required context |
| `concurrency`, top-level `permissions`, `name`, other `on:` keys | Take `main` | Infrastructure-level changes; branch copy is stale |
| `uses: actions/<x>@<sha>` SHA pin | Take `main`'s (newer) SHA | Newer SHA is at least as audited; older SHA regresses supply chain |
| Dockerfile `apt-get install` package list | Merge both sides — keep all packages | Apt packages are strictly additive |
| Dockerfile `USER` / multi-stage structure | Keep both intents (reorder if needed) | Security and feature directives are orthogonal |

### Concrete Data

- **Project:** HomericIntelligence/ProjectCharybdis
- **Date:** 2026-05-05
- **PRs affected:** 14 sibling PRs; 9 touched `_required.yml`
- **Upstream workflow additions seen:** "CodeQL SAST" (PR #124), "Sanitizers" (PR #57, #72), "Lock Check" (PR #120), "Integration Tests" (PR #88), "Container Build and Publish" (PR #153)
- **Companion fan-in job names:** `security-codeql`, `sanitizers`, `pixi-lock-check`, `integration-tests`, `docker-build`
- **`actions/checkout` SHA conflict:** main pinned v4.3.1 (`34e114876...`), branch had v4.2.2 (`11bd71901...`); took main's SHA
- **Dockerfile conflict:** main added `python3-venv` + non-root `USER`; branch added `libasan8 libubsan1`; merged both

### Why Merge-Both-Sides Is the Only Safe Default

- The `workflows:` array is **declarative branch-protection coupling**, not an alternative-selection list. Every entry is a required check name; dropping one removes a fan-in target while branch protection still expects it.
- Fan-in jobs are **status-context publishers**, not alternative implementations. Two siblings' fan-in jobs never collide on the same context name (they were named after distinct upstream workflows), so concatenating is always safe.
- Picking-one-side never leaves the system in a better state than merge-both-sides for these regions; the worst case of merge-both-sides is a temporarily redundant entry, which CI surfaces immediately.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/ProjectCharybdis | 2026-05-05 — 14 sibling PR rebase wave | 9 PRs hit `_required.yml` conflicts; uniform merge-both-sides resolution unblocked every PR; no missing-required-check failures observed post-resolution |

## References

- [GitHub Actions: `workflow_run` trigger](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_run)
- [GitHub: Branch rulesets and required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [ci-cd-reusable-workflow-required-checks-aggregator.md](ci-cd-reusable-workflow-required-checks-aggregator.md) — companion skill on the `workflow_call` aggregator pattern (orthogonal: prevents the fat-`_required.yml` problem in the first place)
- [github-ruleset-pr-blocked-diagnose-missing-check-requirements.md](github-ruleset-pr-blocked-diagnose-missing-check-requirements.md) — diagnosing missing required check failures
