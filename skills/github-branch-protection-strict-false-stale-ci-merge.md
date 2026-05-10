---
name: github-branch-protection-strict-false-stale-ci-merge
description: "GitHub branch protection with `strict_required_status_checks_policy: false` allows stale-but-passing CI on any historical commit SHA to satisfy required checks — enabling auto-merge to fire on the current HEAD even when the latest commit's CI is still queued. Use when: (1) running a high-volume cascade-rebase or PR drainage session and CI runners are under heavy contention, (2) investigating why a PR merged even though the latest commit had no CI run yet, (3) configuring branch protection and deciding whether to enable strict mode, (4) diagnosing why 80+ PRs successfully drained despite GitHub Actions runs being queued for 30+ minutes."
category: ci-cd
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github
  - branch-protection
  - required-status-checks
  - strict
  - stale-ci
  - auto-merge
  - cascade-rebase
  - gh-api
  - pr-drainage
---

# GitHub Branch Protection `strict: false` — Stale CI Satisfies Required Checks

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-09 |
| **Objective** | Document the behavioral difference of `strict_required_status_checks_policy: false` in GitHub branch protection rulesets and how it enables high-volume PR drainage sessions despite CI runner contention |
| **Outcome** | Observed and confirmed in a live session: 80+ PRs drained at 84.7% success rate on HomericIntelligence/ProjectAgamemnon despite GitHub Actions runner contention causing many CI runs to queue for 30+ minutes |
| **Verification** | verified-ci — confirmed by observed merge behavior on 2026-05-09; PRs #154, #210, #342 merged via auto-squash where latest commit CI was still queued at merge time |

## When to Use

- Running a batch PR drainage session (80+ PRs) while GitHub Actions runners are under heavy load
- Investigating why a PR merged even though the current HEAD's CI run had not yet completed
- Deciding whether to set `strict_required_status_checks_policy: true` or `false` when configuring branch protection rulesets
- Understanding why `gh pr merge --auto --squash` fires on a PR immediately after an amendment push, without waiting for the new CI run
- Auditing branch protection security posture — `strict: false` is a deliberate weakening

## Verified Workflow

### Quick Reference

```bash
# Detect the strict setting on a repo's main branch
gh api repos/<org>/<repo>/branches/main --jq '.protection.required_status_checks.strict'
# Returns: true or false

# Detect via ruleset (newer API for repos using rulesets)
gh api repos/<org>/<repo>/rulesets --jq '.[] | select(.name == "homeric-main-baseline") | .rules[] | select(.type == "required_status_checks") | .parameters.strict_required_status_checks_policy'
# Returns: true or false

# Check all HomericIntelligence repos at once
for repo in $(gh repo list HomericIntelligence --json name --jq '.[].name' --limit 50); do
  strict=$(gh api "repos/HomericIntelligence/$repo/branches/main" --jq '.protection.required_status_checks.strict' 2>/dev/null || echo "N/A")
  echo "$repo: strict=$strict"
done
```

### Detailed Steps

1. **Understand the behavioral difference**

   | Setting | Behavior |
   | ------- | -------- |
   | `strict: true` | Required checks MUST pass on the PR's current HEAD commit. After any push, all checks must re-run and pass before auto-merge fires. |
   | `strict: false` | Passing checks on ANY commit SHA in the PR's history satisfy required checks. A CI run that passed on an older commit counts — even if a newer commit's run is still queued. |

2. **Why `strict: false` enables high-volume PR drainage**

   During a cascade-rebase session:
   - You push a rebased branch → GitHub Actions queues a CI run (may wait 30+ min under load)
   - You push again (fix or additional rebase) → another CI run queues
   - Under `strict: false`, the OLD passing run from the prior push satisfies required checks
   - `gh pr merge --auto --squash` fires on the CURRENT HEAD (latest commit) even though that commit's CI is still queued
   - The PR merges with the latest content, validated by the prior commit's CI results

3. **Detect whether a repo uses strict mode**

   ```bash
   # Classic branch protection (legacy API)
   gh api repos/ORG/REPO/branches/main \
     --jq '.protection.required_status_checks.strict'

   # Ruleset-based protection (newer API)
   gh api repos/ORG/REPO/rulesets \
     --jq '.[] | select(.name=="homeric-main-baseline")
           | .rules[]
           | select(.type=="required_status_checks")
           | .parameters.strict_required_status_checks_policy'
   ```

4. **HomericIntelligence baseline uses `strict: false`**

   The `homeric-main-baseline` ruleset (applied to all 15 HomericIntelligence repos) sets:

   ```json
   "parameters": {
     "strict_required_status_checks_policy": false
   }
   ```

   This was deliberate (see `github-branch-protection-org-standardize` skill). The tradeoff:
   acceptable for single-author single-purpose PRs; risky for multi-author PRs touching
   fundamentally different concerns.

5. **Recognize this behavior in a live drainage session**

   Signs that `strict: false` is carrying the session:
   - `gh pr list --json mergeStateStatus` shows `MERGEABLE` for PRs pushed seconds ago
   - `gh run list --branch <head>` shows the latest CI run as `queued` or `in_progress`
   - Yet `gh pr merge --auto --squash` arms and fires successfully
   - The PR merges via squash on the latest commit SHA despite that commit having no finished CI

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Assuming `strict: true` by default | Waited for new CI to complete after each push before enabling auto-merge | Not required — stale passing CI already satisfies the check under `strict: false` | Check the `strict` setting before implementing a wait-for-CI pattern; `strict: false` makes the wait unnecessary |
| Using `gh pr view --json statusCheckRollup` to determine readiness | Checked if all status checks in the rollup were passing | Rollup shows the latest commit's checks, which may be missing/queued; it does NOT show whether older passing checks satisfy branch protection | Under `strict: false`, a missing rollup check does NOT block merge — check `mergeStateStatus: MERGEABLE` instead |

## Results & Parameters

### Observed Session Metrics (2026-05-09, HomericIntelligence/ProjectAgamemnon)

| Metric | Value |
| ------ | ----- |
| Total PRs in drainage session | 80+ |
| Success rate | 84.7% |
| CI runner contention | GitHub Actions runs queuing 30+ minutes |
| Example PRs merging with queued CI | #154, #210, #342 |
| `strict_required_status_checks_policy` | `false` |
| Merge method | squash (`--squash`) |

### Branch Protection Config That Enables This

```json
{
  "type": "required_status_checks",
  "parameters": {
    "strict_required_status_checks_policy": false,
    "required_status_checks": [
      { "context": "lint",              "integration_id": 15368 },
      { "context": "unit-tests",        "integration_id": 15368 },
      { "context": "integration-tests", "integration_id": 15368 }
    ]
  }
}
```

### Security Tradeoff Guidance

| PR Type | Recommended `strict` Setting | Reason |
| -------- | ---- | ------ |
| Single-author, single-purpose skill/fix | `false` acceptable | Autoformatting commits only change aesthetics; no functional regression risk |
| Multi-author or cross-cutting PRs | `strict: true` preferred | Different concerns may interact; individual passing does not guarantee combined passing |
| High-volume drainage session (80+ PRs) | `false` required in practice | `strict: true` would stall every PR until CI completes under contention |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/ProjectAgamemnon | 2026-05-09 PR drainage session | 80+ PRs, 84.7% drain rate; PRs #154, #210, #342 merged with queued CI |
| HomericIntelligence org (all 15 repos) | `homeric-main-baseline` ruleset | `strict_required_status_checks_policy: false` set during org-wide rollout 2026-04-26 |
