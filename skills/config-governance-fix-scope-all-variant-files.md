---
name: config-governance-fix-scope-all-variant-files
description: "Planning discipline for scoping a security/governance config fix: when a finding cites one or two specific config files, grep the WHOLE config directory for the same field before scoping the change — duplicate/variant files (e.g. an enforcing `*-active.json` vs a baseline `*-evaluate`) often hold the same defective value, and the variant actually deployed may not be the one the issue names. Fixing only the cited files leaves the gap live under the enforcing path. Use when: (1) planning a fix for a security/governance finding (branch protection, rulesets, IAM, OPA) that names specific config files, (2) a repo keeps active/baseline or per-env variants of the same JSON/YAML config and an apply script selects which one is deployed, (3) the only existing test surface is JSON/YAML syntax validation and a defective value could silently regress, (4) a fix adds a review/approval requirement and you must check existing bypass_actors before adding a redundant one, (5) you are relying on governance-API numeric IDs or bypass semantics taken from existing JSON or a KB note without live-API confirmation."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Config Governance Fix: Scope Across All Variant Files

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture the planning discipline for correctly scoping a security/governance config-defect fix when a finding names only one or two config files but variant copies of the same config exist |
| **Outcome** | Plan corrected to fix ALL variant files (including the enforcing `-active.json` the issue never named) plus a CI regression guard; planning-time risks recorded honestly |
| **Verification** | verified-local — jq/grep verification commands run locally; GitHub-API IDs and bypass semantics NOT confirmed against live `gh api`; the skill PR's own CI gate not yet observed green |
| **History** | n/a (initial version) |

## When to Use

- Planning a fix for a security/governance finding (branch protection, rulesets, IAM policy, OPA, k8s admission config) that cites one or two specific config files by path and line.
- The repo keeps multiple variants of the same config — e.g. an enforcing `*-active.json` vs a baseline `*-evaluate`, or per-environment copies — and an apply script chooses which variant is deployed.
- The only existing "test surface" for a config is syntax validation (JSON parse, YAML lint), so a defective value can silently regress with no functional test catching it.
- A fix adds a review/approval requirement and you need to decide whether an existing `bypass_actors` entry already mitigates a solo-author self-approval deadlock.
- You are about to rely on governance-API numeric IDs (actor IDs, integration IDs) or bypass semantics pulled from existing JSON or a KB note, without confirming them against the live API.

## Verified Workflow

### Quick Reference

```bash
# 1. Grep the ENTIRE config dir for the cited field — not just the files the issue named.
grep -n required_approving_review_count configs/github/*.json
# -> reveals the same `0` in org-ruleset.json AND org-ruleset-active.json,
#    repo-ruleset.json AND repo-ruleset-active.json.

# 2. Find which variant the apply script actually deploys (the enforcing path).
grep -nE 'active|--active|enforce' tools/github/apply-repo-rulesets.sh
# -> the script selects the `-active.json` file for --active/enforcing mode,
#    a file the issue never named.

# 3. After fixing, add a CI regression guard (jq assertion) so the value can't silently regress.
jq -e '.rules[] | select(.type=="pull_request")
       | .parameters.required_approving_review_count >= 1' configs/github/org-ruleset-active.json

# 4. Before adding an approval requirement, inspect existing bypass_actors to avoid a redundant actor.
jq '.bypass_actors' configs/github/org-ruleset-active.json
```

### Detailed Steps

1. **Treat the cited paths as a starting point, not the scope.** A finding that says
   `configs/github/org-ruleset.json:21` and `repo-ruleset.json` is reporting where the author
   *looked*, not necessarily everywhere the defect lives.
2. **Grep the whole config directory for the offending field** (`grep -n <field> configs/<area>/*`).
   In this session that surfaced the same `required_approving_review_count: 0` in
   `org-ruleset-active.json:21` and `repo-ruleset-active.json:17` — neither named by the issue.
3. **Determine which variant is actually deployed.** Read the apply/deploy script. Here
   `tools/github/apply-repo-rulesets.sh` selects the `-active.json` file for `--active`/enforcing
   mode. The enforcing path uses a file the issue never named, so fixing only the cited files
   leaves the gap live whenever the ruleset is activated.
4. **Fix every variant that carries the defective value**, prioritizing the enforcing one.
5. **Add a CI regression guard when the only test surface is syntax validation.** A jq assertion
   (`required_approving_review_count >= 1`) in CI prevents a silent regression back to the
   defective state — JSON-parse validation alone would not catch it.
6. **Check existing `bypass_actors` before adding an approval requirement.** A `pull_request`-mode
   admin/Integration bypass actor already present can mitigate the solo-author self-approval
   deadlock that the `ci-cd-ruleset-bootstrap-deadlock` KB warns about — do not add a redundant
   actor.
7. **Record planning-time assumptions you could not verify as explicit risks** (see Failed
   Attempts) rather than presenting them as facts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Scope the fix to only the cited files | Plan would have edited only `org-ruleset.json` and `repo-ruleset.json` as the issue named | A whole-dir grep found the same `0` in `org-ruleset-active.json:21` and `repo-ruleset-active.json:17`; the apply script deploys the `-active.json` variant | Grep the entire config dir for the field before scoping; the deployed variant may not be the file the issue names |
| Assume JSON-syntax validation is enough coverage | Relied on existing `just ruleset-validate` (JSON parse) as the test surface | Syntax validation never asserts the *value*; the defective `0` could silently regress unnoticed | Add a jq value-assertion (`>= 1`) CI guard when the only test surface is syntax validation |
| Add a new bypass actor to avoid the self-approval deadlock | Considered adding an admin/Integration bypass to unblock a solo author after requiring approvals | An existing `pull_request`-mode bypass actor already mitigated the deadlock | Inspect existing `bypass_actors` first; do not add a redundant actor |
| Trust governance-API IDs from existing JSON / KB | Took `actor_id: 1` (OrganizationAdmin), `5` (RepositoryRole admin), `49699333` (Integration), `integration_id: 15368` (GitHub Actions app) at face value | Never confirmed against live `gh api`; numeric IDs and app IDs can differ per org/install | Verify governance-API IDs against the live API before relying on them in a security fix |
| Assume bypass-actor merge semantics | Assumed a `pull_request`-mode bypass lets an admin author merge a self-PR the review requirement would block | Never empirically tested against GitHub's live behavior — it is the deadlock-mitigation claim and remains unverified | Empirically verify bypass behavior against live GitHub before relying on it to resolve a deadlock |
| Cite exact line numbers in the plan | Referenced `org:21`, `repo:17` from the current checkout | Line numbers drift as files change; they are checkout-relative | Reference the field name and file, not just line numbers; re-grep at apply time |

## Results & Parameters

**Concrete evidence from the session (issue #178 — branch protection requires zero approving reviews):**

```text
Field:          required_approving_review_count
Cited by issue: configs/github/org-ruleset.json:21, repo-ruleset.json
Grep revealed:  same `0` ALSO in org-ruleset-active.json:21, repo-ruleset-active.json:17
Apply script:   tools/github/apply-repo-rulesets.sh selects *-active.json for --active mode
                => enforcing path uses a file the issue never named
Guard added:    jq assertion required_approving_review_count >= 1 in CI
Bypass check:   existing pull_request-mode admin/Integration bypass actor already mitigates
                the ci-cd-ruleset-bootstrap-deadlock solo-author self-approval risk
```

**Regression-guard snippet (copy-paste):**

```bash
for f in configs/github/org-ruleset-active.json configs/github/repo-ruleset-active.json; do
  jq -e '[.rules[]? | select(.type=="pull_request")
         | .parameters.required_approving_review_count]
         | all(. >= 1)' "$f" >/dev/null \
    || { echo "REGRESSION: $f has required_approving_review_count < 1"; exit 1; }
done
```

**Unverified assumptions recorded as risks (Failed-or-unverified):**

- `bypass_actors` numeric IDs (`actor_id: 1` OrganizationAdmin, `5` RepositoryRole admin,
  `49699333` Integration, `integration_id: 15368` GitHub Actions app) taken from existing JSON +
  KB note; NOT confirmed against live `gh api`.
- Bypass-actor semantics (a `pull_request`-mode bypass lets an admin author merge a self-PR the
  review requirement would block) NOT empirically tested against live GitHub.
- Line numbers (`org:21`, `repo:17`) are checkout-relative and can drift.
- `just ruleset-validate` requires `gh` auth + network; not runnable in a plan-time sandbox.

**Related skills (apply/debug rulesets — distinct from this planning-scope discipline):**
`github-branch-protection-org-standardize`, `ci-cd-ruleset-bootstrap-deadlock`,
`github-ruleset-pr-blocked-diagnose-missing-check-requirements`.
