---
name: github-ruleset-required-status-checks-management
description: "Add a required status check to a GitHub repo branch-protection RULESET (rulesets API, not the legacy branch-protection API) and avoid the 'require-before-it-exists' ordering hazard. The rulesets PUT REPLACES the rule wholesale, so you must GET->append->PUT the full required_status_checks array (deriving integration_id from an existing Actions check, here 15368) or you DROP the existing checks. THE LOAD-BEARING HAZARD: a required context for a job that does NOT yet exist on the DEFAULT branch never reports, so it permanently BLOCKS every open PR — requiring a check must be sequenced AFTER the PR that adds the job merges to main. SEPARATELY, a follow-up issue can assert a FALSE premise (e.g. #282 said the SAST job 'was added in PR #264' but `gh pr view 264` showed PR #264 was still OPEN, not merged, and the `security/sast-scan` job lived only on the unmerged branch) — verify 'already done' premises against live state. Use when: (1) adding a new CI job's check context to a GitHub ruleset as a required status check; (2) a follow-up issue says 'add X to required checks' and you must verify the job exists on the default branch first; (3) diagnosing why adding a required status check could permanently block all PRs; (4) needing the correct integration_id for a GitHub Actions check context in a ruleset. Cross-link: gha-required-checks-branch-protection (the YAML/aggregator + legacy branch-protection PUT mechanics), github-ruleset-enforcement-drift (bare-name + integration_id context form), planning-verify-issue-claims-and-required-check-gating (runs-vs-gates + grep-the-claim discipline)."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - rulesets
  - branch-protection
  - required-status-checks
  - integration_id
  - ordering-hazard
  - get-append-put
  - issue-premise-verification
  - default-branch
  - ci-cd
---

# Add a Required Status Check to a GitHub Ruleset (API mechanics + the require-before-it-exists ordering hazard)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Capture how to add a new CI job's check context to a GitHub branch-protection RULESET (rulesets API) as a required status check — the GET->append->PUT mechanics that avoid dropping existing checks, the correct integration_id derivation — and the load-bearing ORDERING HAZARD: requiring a check whose job does not yet exist on the default branch permanently blocks every open PR. Plus the planning lesson that a follow-up issue's "already done" premise can be FALSE and must be verified against live state. |
| **Outcome** | Plan written for ProjectTelemachy issue #282 (follow-up from #157). The issue claimed the `security/sast-scan` SAST job "was added in PR #264", but `gh pr view 264` showed PR #264 was OPEN (not merged) and the job existed only on the unmerged branch `157-auto-impl` (commit `39a509a`), NOT on `main`. Conclusion: the required check must NOT be added until the job-adding PR lands on `main`; the GET->append->PUT mechanics were drafted from the live ruleset (8 existing checks, all `integration_id: 15368`). |
| **Verification** | **verified-local** — the live ruleset state was read directly via `gh api repos/HomericIntelligence/ProjectTelemachy/rulesets/15556487` and PR #264's merge state via `gh pr view 264 --json state,mergedAt`. The READ/diagnosis steps are verified. The actual PUT mutation was NOT executed (admin-only, out of scope for a planning agent), so the WRITE half (PUT/jq append step) is **proposed**, not verified. |

This skill is the **rulesets-API "add a required check"** counterpart to three related skills:

- `gha-required-checks-branch-protection` — fixing the *YAML/aggregator* wiring and the *legacy
  branch-protection* (`branches/main/protection`) PUT/PATCH mechanics. THIS skill is about the
  newer **rulesets API** (`repos/<o>/<r>/rulesets/<id>`) and the ordering hazard of adding a check.
- `github-ruleset-enforcement-drift` — the canonical bare-name + `integration_id` context form and
  evaluate-vs-active drift. THIS skill reuses that context form but focuses on *appending* a new check.
- `planning-verify-issue-claims-and-required-check-gating` — runs-vs-gates and grep-the-claim
  discipline. THIS skill adds the specific "verify the prerequisite PR actually merged" check.

> **Warning:** The PUT mutation in the Quick Reference was NOT run end-to-end (admin-only). The
> READ/diagnosis steps are `verified-local`; treat the WRITE step (the jq append + `gh api -X PUT`)
> as proposed until an admin executes it and reads the ruleset back.

## When to Use

- Adding a new CI job's check context to a GitHub branch-protection **ruleset** (rulesets API, not
  the legacy branch-protection API) as a required status check.
- A follow-up issue says "add X to required checks" — before doing so you must verify the job
  actually exists on the **default** branch (`main`), not just on an open PR's feature branch.
- Diagnosing why adding a required status check could permanently block all PRs.
- Needing the correct `integration_id` for a GitHub Actions check context in a ruleset.

## Verified Workflow

> **Warning:** The numbered discipline below was run live for the READ/diagnosis half
> (`verified-local`). The PUT half is proposed — admin-only, not executed end-to-end. The heading
> is "Verified Workflow" to satisfy the marketplace validator.

### Quick Reference

```bash
ORG=HomericIntelligence; REPO=ProjectTelemachy
# 0. Find the ruleset id
RS_ID=$(gh api repos/$ORG/$REPO/rulesets --jq '.[] | select(.name=="homeric-main-baseline") | .id')

# 1. READ the live ruleset's required checks (each entry = {context, integration_id})
gh api repos/$ORG/$REPO/rulesets/$RS_ID \
  --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks'
# For GitHub Actions checks, integration_id is the Actions app id (here 15368).
# COPY it from an existing Actions check in the SAME ruleset — never guess/hardcode from memory.

# 2. ORDERING GUARD (load-bearing) — the job MUST already exist on the DEFAULT branch.
#    If the context never reports, every open PR blocks forever.
gh api repos/$ORG/$REPO/contents/.github/workflows/_required.yml --jq '.content' | base64 -d \
  | grep -q 'name: security/sast-scan' && echo PASS || echo "BLOCK: job not on main"

# 3. VERIFY the follow-up issue's 'already added in PR #N' premise against LIVE state.
gh pr view 264 --repo $ORG/$REPO --json state,mergedAt,headRefName
# OPEN / mergedAt:null => prerequisite NOT landed; do NOT add the required check yet.

# 4. (PROPOSED, admin-only) GET -> append -> PUT the FULL array (PUT replaces the rule wholesale).
gh api repos/$ORG/$REPO/rulesets/$RS_ID > /tmp/rs.json
jq '{name, enforcement, conditions, bypass_actors,
  rules: (.rules | map(if .type=="required_status_checks"
    then .parameters.required_status_checks += [{"context":"security/sast-scan","integration_id":15368}]
    else . end))}' /tmp/rs.json > /tmp/rs-updated.json
gh api -X PUT repos/$ORG/$REPO/rulesets/$RS_ID --input /tmp/rs-updated.json   # admin-only
```

### Detailed Steps

1. **Read the live ruleset first.** `gh api repos/<o>/<r>/rulesets/<id>` and inspect
   `.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks`. Each
   entry is `{ "context": "...", "integration_id": <n> }`. At plan time ProjectTelemachy's
   `homeric-main-baseline` (id `15556487`) carried **8** checks — `lint, unit-tests,
   integration-tests, security/dependency-scan, security/secrets-scan, build, schema-validation,
   deps/version-sync` — all with `integration_id: 15368`, and `security/sast-scan` was NOT present.

2. **Derive integration_id from an existing check, do not guess.** For GitHub Actions checks the
   `integration_id` is the GitHub Actions app id. All Actions-produced checks in a repo share the
   same id (here `15368`). Copy it from any existing Actions check in the same ruleset rather than
   hardcoding from memory — a wrong id silently mis-binds the check.

3. **Gate on the ORDERING HAZARD (most important step).** GitHub required status checks block a PR
   until the named context **reports a result**. If you add a context for a job that does NOT yet
   exist on the default branch (`main`), that check never reports, so **every open PR is permanently
   blocked** waiting on it. Verify the job exists on the default branch BEFORE adding the
   requirement (Quick Reference #2, reading `.github/workflows/_required.yml` via the contents API
   and matching the job's `name:` line). Requiring a check MUST be sequenced AFTER the PR that adds
   the job merges to the default branch.

4. **Verify the issue's "already done" premise against live state.** A follow-up issue body can
   assert a premise that is FALSE at planning time. Issue #282 stated the SAST job "was added in
   PR #264" — but `gh pr view 264 --json state` showed PR #264 was **OPEN, not merged**, and
   `git log --all -S 'security/sast-scan'` / grep confirmed the job lived only on the unmerged
   branch `157-auto-impl` (commit `39a509a`), NOT on `main`. Always verify the "already landed"
   premise of a follow-up issue with `gh pr view <n> --json state,mergedAt` + a grep on the default
   branch — do not trust the issue's claim.

5. **GET -> append -> PUT the FULL array (proposed, admin-only).** The ruleset UPDATE endpoint
   (`PUT /repos/.../rulesets/<id>`) REPLACES the rule wholesale. A payload that omits the existing
   checks DROPS them. Never hand-author the array; derive it from the live GET with jq
   (Quick Reference #4). The PUT payload accepts `name`, `enforcement`, `conditions`, `rules`,
   `bypass_actors` — strip server-managed fields (`id`, `node_id`, `created_at`, `updated_at`,
   `_links`, `source`, `source_type`, `current_user_can_bypass`) or the PUT may error.

6. **Match the context string to the job's `name:` field EXACTLY.** The required context is the
   job's `name:` value (`security/sast-scan`), NOT the YAML job key (`security-sast-scan`). A
   mismatch registers a context that never reports — re-creating the ordering-hazard deadlock.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting the issue's "added in PR #264" premise | Assumed the SAST job was already on `main` per the issue body | PR #264 was OPEN, not merged; the job existed only on the feature branch `157-auto-impl` (commit `39a509a`) | Verify follow-up-issue premises against live `gh pr view <n> --json state,mergedAt` / grep on the default branch before planning the dependent change |
| Adding the required check immediately | Would add `security/sast-scan` to the ruleset right away | The job is not on `main` yet, so the check never reports -> all open PRs permanently blocked | Gate the ruleset change on the job-adding PR merging to the default branch first |
| Blind PATCH/PUT of just the new check | Sending only the new context in the update payload | Ruleset PUT replaces the rule wholesale -> drops the existing 8 checks | GET->append->PUT the full array via jq; never hand-author it |
| Hardcoding/guessing integration_id | Guessing the GitHub Actions app id | Wrong id silently mis-binds the check | Copy integration_id from an existing Actions check in the same ruleset (here 15368) |
| Using the job YAML key as the context | Would register `security-sast-scan` (the job key) | The required context is the job's `name:` field (`security/sast-scan`), not the key; a wrong context never reports | Match the context string to the job's `name:` field exactly |

## Results & Parameters

- **Real repo / ruleset:** HomericIntelligence/ProjectTelemachy, ruleset `homeric-main-baseline`,
  id `15556487`, `enforcement: active`.
- **Required contexts at plan time (8, all `integration_id: 15368`):** `lint`, `unit-tests`,
  `integration-tests`, `security/dependency-scan`, `security/secrets-scan`, `build`,
  `schema-validation`, `deps/version-sync`. `security/sast-scan` was NOT present.
- **Prerequisite PR state:** PR #264 (`157-auto-impl`) was `OPEN`, `mergedAt: null` — the SAST job
  was NOT on `main`; therefore the required-check addition is BLOCKED on that PR merging first.
- **Proposed append payload entry:** `{"context":"security/sast-scan","integration_id":15368}`.

### Risks the reviewer should focus on

- **The PUT mutation step is NOT verified end-to-end (admin-only). Treat the WRITE half as
  proposed.** The READ/diagnosis half (`gh api .../rulesets`, `gh pr view`) was run live.
- `integration_id: 15368` is correct for THIS repo's Actions checks but is **repo-specific** —
  re-derive per repo from an existing Actions check.
- The exact context string must match the job's `name:` field exactly (`security/sast-scan`), not
  the YAML job key (`security-sast-scan`).
- If PR #264 is closed-unmerged or re-implemented, the context name must be re-confirmed against
  whatever PR actually lands the job.

### Related skills

- `gha-required-checks-branch-protection` — YAML/aggregator wiring + legacy branch-protection PUT.
- `github-ruleset-enforcement-drift` — bare-name + integration_id context form, evaluate/active drift.
- `planning-verify-issue-claims-and-required-check-gating` — runs-vs-gates + grep-the-claim discipline.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectTelemachy | Issue #282 (follow-up from #157) — plan only | verified-local; ruleset `homeric-main-baseline` (id `15556487`) read via `gh api`, 8 existing checks confirmed (all `integration_id: 15368`), `security/sast-scan` absent; PR #264 confirmed OPEN/unmerged via `gh pr view 264 --json state,mergedAt` (branch `157-auto-impl`). PUT mutation NOT executed (admin-only) — WRITE step proposed. |
