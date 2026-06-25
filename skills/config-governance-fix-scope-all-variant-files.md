---
name: config-governance-fix-scope-all-variant-files
description: "Planning discipline for scoping a security/governance config fix: when a finding cites one or two specific config files, grep the WHOLE config directory for the same field before scoping the change — duplicate/variant files (e.g. an enforcing `*-active.json` vs a baseline `*-evaluate`) often hold the same defective value, and the variant actually deployed may not be the one the issue names. Fixing only the cited files leaves the gap live under the enforcing path. SEPARATELY: when an issue prescribes a LITERAL assertion over named files (e.g. 'guard that all four ruleset files are enforcement==active'), run that assertion against current HEAD with jq/grep BEFORE adopting it — the issue's premise may be factually wrong and ship a guard that is red-on-day-one or asserts the wrong invariant. Use when: (1) planning a fix for a security/governance finding (branch protection, rulesets, IAM, OPA) that names specific config files, (2) a repo keeps active/baseline or per-env variants of the same JSON/YAML config and an apply script selects which one is deployed, (3) the only existing test surface is JSON/YAML syntax validation and a defective value could silently regress, (4) a fix adds a review/approval requirement and you must check existing bypass_actors before adding a redundant one, (5) you are relying on governance-API numeric IDs or bypass semantics taken from existing JSON or a KB note without live-API confirmation, (6) an issue body or embedded fix sketch prescribes a blanket equality assertion over a set of named config files and you are about to encode it as a CI guard."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
history: config-governance-fix-scope-all-variant-files.history
tags:
  - config-governance
  - ruleset
  - enforcement-drift
  - verify-issue-premise
  - evaluate-vs-active
  - per-file-expected-value
  - ci-regression-guard
  - planning-discipline
---

# Config Governance Fix: Scope Across All Variant Files

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 (v1.1.0) · 2026-06-19 (v1.0.0) |
| **Objective** | Capture the planning discipline for (a) correctly scoping a security/governance config-defect fix across variant files, and (b) verifying an issue's literal-assertion PREMISE against current HEAD before encoding it as a CI guard |
| **Outcome** | v1.0.0: plan corrected to fix ALL variant files plus a CI guard. v1.1.0: a `jq` premise check showed an issue's prescribed `enforcement==active`-over-all-4-files guard was factually wrong (on-disk state is `evaluate,active,evaluate,active` by design) and would have been red-on-day-one; corrected to a per-file expected-value map |
| **Verification** | verified-local for the premise-check technique (the `jq` premise verification WAS run during planning and confirmed `evaluate,active,evaluate,active`). The proposed enforcement-drift guard / CI wiring is **unverified** (planning only — not implemented or CI-run). GitHub-API IDs and bypass semantics from v1.0.0 also NOT confirmed against live `gh api` |
| **History** | `config-governance-fix-scope-all-variant-files.history` (v1.0.0 → v1.1.0) |

## When to Use

- Planning a fix for a security/governance finding (branch protection, rulesets, IAM policy, OPA, k8s admission config) that cites one or two specific config files by path and line.
- The repo keeps multiple variants of the same config — e.g. an enforcing `*-active.json` vs a baseline `*-evaluate`, or per-environment copies — and an apply script chooses which variant is deployed.
- The only existing "test surface" for a config is syntax validation (JSON parse, YAML lint), so a defective value can silently regress with no functional test catching it.
- A fix adds a review/approval requirement and you need to decide whether an existing `bypass_actors` entry already mitigates a solo-author self-approval deadlock.
- You are about to rely on governance-API numeric IDs (actor IDs, integration IDs) or bypass semantics pulled from existing JSON or a KB note, without confirming them against the live API.
- **(v1.1.0)** An issue body or its embedded fix sketch prescribes a *literal* blanket assertion over a set of named config files (e.g. "guard that all four ruleset files have `enforcement == "active"`") and you are about to encode it as a CI guard — run the assertion against current HEAD first; the premise may be wrong.
- **(v1.1.0)** A repo deliberately keeps a two-form split of the same config (a base/`evaluate` form and an `*-active.json`/enforcing form) with different per-file intended values, so a single blanket equality check is the wrong invariant and a per-file expected-value map is required.

## Verified Workflow

### Enforcement Guard Quick Reference

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

### Verify the issue premise before planning to it (v1.1.0)

> **Warning — partially unverified.** The *premise-verification technique* below is
> **verified-local**: the `jq` premise check WAS actually run during this planning session and
> confirmed the on-disk state `evaluate,active,evaluate,active`. The *proposed enforcement-drift
> guard and its CI wiring are UNVERIFIED* — they were designed at planning time only, never
> implemented, never run in CI. Treat the guard snippet as a proposal, not a tested artifact.

When an issue (or its embedded fix sketch) prescribes a **literal assertion over named files** —
here, issue #309 asserted PR #177 flipped the two BASE files (`repo-ruleset.json:4`,
`org-ruleset.json:4`) from `evaluate` to `active` and prescribed a guard looping **all four**
ruleset files asserting `enforcement == "active"` — do **not** adopt it on faith.

1. **Run the literal assertion against current HEAD with a cheap `jq`/grep one-liner.**
   ```bash
   for f in repo-ruleset repo-ruleset-active org-ruleset org-ruleset-active; do
     printf '%s: %s\n' "$f" "$(jq -r .enforcement "configs/github/$f.json")"
   done
   # Actual on-disk state -> evaluate, active, evaluate, active
   ```
2. **Compare to the premise.** The issue claimed all four should be `active`. On disk the two
   BASE files (`*-ruleset.json`) are intentionally `"evaluate"` and only the `*-active.json`
   variants are `"active"`. The prescribed blanket guard would have **failed on day one against a
   correct repo** (red CI, no actual defect).
3. **Confirm the split is intentional, not drift.** `configs/github/canonical-checks.md:58-62`
   documents the two-form split as design (base/evaluate form vs active/enforcing form, with
   different required-check context strings). A blanket `== "active"` check encodes the wrong
   invariant.
4. **Encode the CORRECT invariant: a per-file expected-enforcement map** (catches drift in BOTH
   directions — an active config silently downgraded to evaluate, AND a base config silently
   upgraded to active). This is strictly stronger than the issue's blanket check. *(Proposed —
   unverified.)*
5. **Wire it per `ci-hygiene-and-validation-gates` Pattern 2**: add the value-assertion to an
   EXISTING static-check job (not a new workflow), keep echoes ASCII-only, and put the logic in a
   reusable `just` recipe that CI calls so it lives in one place. Follow
   `architecture-executable-convention-guard-pattern` for the prose-invariant → tested-blocking-
   check shape: loud collision-free failure, and two-sided verification (clean PASS on a correct
   tree + synthetic FAIL on a deliberately corrupted copy).

### Quick Reference

```bash
# STEP 0 (CHEAP, ALWAYS DO THIS): verify the issue's literal premise against HEAD.
for f in repo-ruleset repo-ruleset-active org-ruleset org-ruleset-active; do
  printf '%s: %s\n' "$f" "$(jq -r .enforcement "configs/github/$f.json")"
done
# Expected/intended -> evaluate, active, evaluate, active  (NOT all "active")

# PROPOSED guard (UNVERIFIED): assert each file against its INTENDED per-file value.
# Two-sided drift detection: base must stay evaluate, active must stay active.
declare -A want=(
  [repo-ruleset]=evaluate  [repo-ruleset-active]=active
  [org-ruleset]=evaluate   [org-ruleset-active]=active
)
fail=0
for f in "${!want[@]}"; do
  got=$(jq -r .enforcement "configs/github/$f.json")
  if [ "$got" != "${want[$f]}" ]; then
    echo "DRIFT: configs/github/$f.json enforcement=$got expected=${want[$f]}"
    fail=1
  fi
done
[ "$fail" -eq 0 ] || exit 1
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Scope the fix to only the cited files | Plan would have edited only `org-ruleset.json` and `repo-ruleset.json` as the issue named | A whole-dir grep found the same `0` in `org-ruleset-active.json:21` and `repo-ruleset-active.json:17`; the apply script deploys the `-active.json` variant | Grep the entire config dir for the field before scoping; the deployed variant may not be the file the issue names |
| Assume JSON-syntax validation is enough coverage | Relied on existing `just ruleset-validate` (JSON parse) as the test surface | Syntax validation never asserts the *value*; the defective `0` could silently regress unnoticed | Add a jq value-assertion (`>= 1`) CI guard when the only test surface is syntax validation |
| Add a new bypass actor to avoid the self-approval deadlock | Considered adding an admin/Integration bypass to unblock a solo author after requiring approvals | An existing `pull_request`-mode bypass actor already mitigated the deadlock | Inspect existing `bypass_actors` first; do not add a redundant actor |
| Trust governance-API IDs from existing JSON / KB | Took `actor_id: 1` (OrganizationAdmin), `5` (RepositoryRole admin), `49699333` (Integration), `integration_id: 15368` (GitHub Actions app) at face value | Never confirmed against live `gh api`; numeric IDs and app IDs can differ per org/install | Verify governance-API IDs against the live API before relying on them in a security fix |
| Assume bypass-actor merge semantics | Assumed a `pull_request`-mode bypass lets an admin author merge a self-PR the review requirement would block | Never empirically tested against GitHub's live behavior — it is the deadlock-mitigation claim and remains unverified | Empirically verify bypass behavior against live GitHub before relying on it to resolve a deadlock |
| Cite exact line numbers in the plan | Referenced `org:21`, `repo:17` from the current checkout | Line numbers drift as files change; they are checkout-relative | Reference the field name and file, not just line numbers; re-grep at apply time |
| Adopt issue sketch's blanket `enforcement==active` guard over all 4 files (v1.1.0) | Issue #309 prescribed a guard looping all four ruleset files asserting `enforcement == "active"`, claiming PR #177 flipped the two base files | A `jq -r .enforcement` over all four files showed the on-disk state is `evaluate, active, evaluate, active`; the two base files are `evaluate` by design (`canonical-checks.md:58-62`), so the guard would be red on day one against a correct repo | Run the literal assertion against HEAD before adopting it; encode a per-file expected-value map (catches drift both directions), not a blanket equality check |

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

**Concrete evidence from the v1.1.0 session (issue #309 — "ruleset configs must stay enforcement=active"):**

```text
Issue premise:  PR #177 flipped repo-ruleset.json:4 and org-ruleset.json:4 from
                "evaluate" to "active"; prescribed guard loops ALL FOUR files
                asserting enforcement == "active".
Premise check:  jq -r .enforcement over all four files (RUN during planning) ->
                repo-ruleset.json         = evaluate   (base form, by design)
                repo-ruleset-active.json  = active
                org-ruleset.json          = evaluate   (base form, by design)
                org-ruleset-active.json   = active
Verdict:        Premise WRONG. Blanket enforcement=="active" guard would be
                red-on-day-one against a correct repo.
Design source:  configs/github/canonical-checks.md:58-62 documents the two-form
                split (base/evaluate vs active/enforcing, different required-check
                context strings) as intentional.
Corrected plan: per-file expected-enforcement map (evaluate for base, active for
                *-active) -> catches drift in BOTH directions, strictly stronger
                than the issue's blanket check. (PROPOSED — not implemented/CI-run.)
Verification:   premise-verification technique = verified-local (jq WAS run);
                proposed guard + CI wiring = UNVERIFIED (planning only).
```

**v1.1.0 unverified assumptions / unverified reliances recorded as risks:**

- Assumed `jq` is preinstalled on GitHub `ubuntu-latest` runners — relied on without a CI run in
  THIS repo's image confirming it (it is standard on `ubuntu-latest` but not asserted here).
- Line numbers cited at planning time (`justfile:679/693/695`, `ci.yml:10/21-25/44-48`,
  `canonical-checks.md:58-62`) were read at planning time and can drift before implementation —
  re-read / re-grep at apply time.
- The proposed per-file enforcement-drift guard and its `just`+CI wiring are **unverified**: never
  implemented, never run in CI, no clean-PASS / synthetic-FAIL two-sided check executed. Only the
  on-disk `jq` premise verification was actually run (and confirmed
  `evaluate,active,evaluate,active`).

**Related skills (apply/debug rulesets + the guard/CI patterns this plan leans on):**
`github-branch-protection-org-standardize`, `ci-cd-ruleset-bootstrap-deadlock`,
`github-ruleset-pr-blocked-diagnose-missing-check-requirements`,
`architecture-executable-convention-guard-pattern` (prose invariant → tested blocking check; loud
collision-free failure; two-sided clean-PASS + synthetic-FAIL verification),
`ci-hygiene-and-validation-gates` (Pattern 2: value-assertion step in an EXISTING static-check job,
ASCII-only echoes, reusable `just` recipe called by CI).
