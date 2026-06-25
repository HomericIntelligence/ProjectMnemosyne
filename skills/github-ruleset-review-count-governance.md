---
name: github-ruleset-review-count-governance
description: "Use when: (1) auditing GitHub org or repo branch-protection ruleset JSON files for a zero-review governance gap (`required_approving_review_count: 0`), (2) fixing `required_approving_review_count` in canonical ruleset JSON files and the issue only names a subset of the files, (3) adding a CI regression guard to assert the review count cannot regress silently, (4) checking whether existing `bypass_actors` already mitigate the self-merge deadlock that requiring >=1 review creates, (5) leaving `enforcement` untouched and treating activation as a separate operational step."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-actions
  - branch-protection
  - ruleset
  - governance
  - review-count
  - bypass-actors
  - jq
---

# GitHub Ruleset Required Approving Review Count Governance

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Fix `required_approving_review_count: 0` in all canonical GitHub branch-protection ruleset JSON files (including `-active.json` variants the issue may not name), add a CI regression guard using a `first()`-wrapped jq assertion, verify existing `bypass_actors` mitigate deadlock, and leave `enforcement` untouched |
| **Outcome** | All four canonical ruleset files updated to count=1; CI guard added to `_required.yml`; no bypass actor added (existing ones sufficient); PR #308 opened on HomericIntelligence/Odysseus |
| **Verification** | verified-local — four jq checks + grep + JSON parse all pass locally; CI on Odysseus PR #308 pending |
| **History** | n/a (initial version) |

## When to Use

- An issue reports `required_approving_review_count: 0` in one or two specific ruleset JSON files — check ALL canonical files (both base and `-active.json` variants) before scoping the fix.
- An apply script selects the `-active.json` variant for enforcing mode; fixing only the base file leaves the gap live when the ruleset is activated.
- You want a CI guard that asserts the review count cannot regress to zero silently (JSON-parse/lint validation alone does not check values).
- You are about to add `bypass_actors` to prevent a self-merge deadlock — first inspect what bypass actors already exist.
- A fix touches the `pull_request` rule but should NOT change `enforcement` (disabled/active/evaluate) — that is a separate rollout step.

## Verified Workflow

> **Warning:** This skill is `verified-local`. Local verification commands all pass. CI on the Odysseus PR is pending at the time of writing. Do not treat this as `verified-ci` until the PR gate goes green.

### Quick Reference

```bash
# 1. Find all ruleset files carrying the zero-review gap — not just the ones the issue named.
grep -n '"required_approving_review_count"' configs/github/*.json

# 2. Identify which variant is actually deployed in enforcing mode.
grep -nE 'active|--active|enforce' tools/github/apply-repo-rulesets.sh
# -> confirms -active.json is what gets pushed when --active mode is used

# 3. Fix the count in every file that carries 0 (one-field edit per file).
#    The pull_request rule already exists; no rule insertion needed.
#    jq:  .rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count
#    Change 0 → 1 in all four files:
#      configs/github/org-ruleset.json          line 21
#      configs/github/org-ruleset-active.json   line 21
#      configs/github/repo-ruleset.json         line 17
#      configs/github/repo-ruleset-active.json  line 17

# 4. Inspect existing bypass_actors BEFORE adding a new one.
jq '.bypass_actors' configs/github/org-ruleset-active.json
# -> OrganizationAdmin id 1, Integration id 49699333, RepositoryRole id 5 already present
#    => no new bypass actor needed

# 5. Add a CI regression guard — use first() to be robust against files
#    that could ever have multiple pull_request rules.
count=$(jq 'first(.rules[] | select(.type=="pull_request")
            | .parameters.required_approving_review_count)' \
        configs/github/org-ruleset-active.json)
[ "$count" -lt 1 ] && { echo "FAIL: $f has required_approving_review_count=$count"; exit 1; }

# 6. Verification — run all four checks.
for f in configs/github/org-ruleset.json configs/github/org-ruleset-active.json \
          configs/github/repo-ruleset.json configs/github/repo-ruleset-active.json; do
  jq '.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count' "$f"
done
# Expected: 1 1 1 1

! grep -rn '"required_approving_review_count": 0' configs/github/
# Expected: exit 0 (no matches)

for f in configs/github/*.json; do jq empty "$f" && echo "OK: $f"; done
# Expected: OK for all four files
```

### Detailed Steps

1. **Scope the fix by grepping all files, not just those the issue named.**
   Run `grep -n required_approving_review_count configs/github/*.json`. In a four-file
   canonical layout (base + active, org + repo), the same `0` appears in all four.
   An issue citing only `org-ruleset.json` and `repo-ruleset.json` omits the
   `-active.json` variants — those are what the apply script deploys in enforcing mode.

2. **Read the apply script to find the enforcing path.**
   `tools/github/apply-repo-rulesets.sh` selects `*-active.json` when `--active` is
   passed. Fixing only the base files leaves the gap live on activation.

3. **Apply the one-field fix to every affected file.**
   The `pull_request` rule is already present — no new rule insertion needed.
   Change `"required_approving_review_count": 0` to `1` in each of the four files.
   Leave all other PR rule flags unchanged (`dismiss_stale_reviews_on_push`,
   `require_code_owner_review`, etc. are out of scope).

4. **Leave `enforcement` untouched.**
   The `"enforcement"` field (`"disabled"` / `"active"` / `"evaluate"`) controls
   whether the ruleset is enforced. Activation is a separate operational step covered
   by the rollout runbook — do not change it as part of a review-count fix.

5. **Inspect existing `bypass_actors` before adding a new one.**
   A `pull_request`-mode admin bypass actor already in place mitigates the solo-author
   self-merge deadlock that requiring >=1 review would otherwise create. In the Odysseus
   canonical files, OrganizationAdmin id 1, Integration id 49699333, and RepositoryRole
   id 5 are already present. Do not add a redundant actor.

6. **Add a CI guard using `first()` wrapper for robustness.**
   Use `jq 'first(.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count)'`
   rather than bare `.rules[] | select(...) | .parameters.required_approving_review_count`.
   Without `first()`, if a file ever grows multiple `pull_request` rules, jq emits
   multiple lines and the bash `[ "$count" -lt 1 ]` guard sees `[: too many arguments`
   and exits non-zero regardless of the actual values.

7. **Run verification checks before committing.**
   See Quick Reference step 6 for the four-check suite (jq value check, grep for
   remaining zeros, JSON parse, and the CI guard logic mirroring).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix only the two files named in the issue | Planned to edit only `org-ruleset.json` and `repo-ruleset.json` as the issue stated | `org-ruleset-active.json` and `repo-ruleset-active.json` also had `0`; the apply script uses `-active.json` for enforcing mode, so leaving them at `0` would keep the gap live on activation | Grep the whole config directory for the offending field; the deploy path may use a file the issue never named |
| Use bare jq select without `first()` in CI guard | `count=$(jq '...rules[]\|select\|.parameters.required_approving_review_count' "$f")` — pipes inside code span trigger cell splitting | If a file ever has multiple `pull_request` rules, jq emits multiple lines; bash `[ "$count" -lt 1 ]` errors with `too many arguments` | Wrap the jq expression with `first(...)` so the guard always receives a single scalar value |
| Change `enforcement` field while fixing review count | Considered activating the ruleset as part of the same PR | Activation is a separate operational step with its own rollout runbook; bundling it expands scope and risk | Leave `enforcement` unchanged; activation is a distinct step |
| Add new bypass actor to prevent self-merge deadlock | Considered adding a bypass for admin authors so they can self-merge after requiring >=1 review | Existing `pull_request`-mode bypass actors (OrganizationAdmin id 1, Integration id 49699333, RepositoryRole id 5) already address the deadlock | Inspect existing `bypass_actors` before adding any; a redundant actor is unnecessary and may confuse future audits |
| Change other PR rule flags alongside review count | Considered setting `dismiss_stale_reviews_on_push: true` while touching the file | The issue's sole finding is `required_approving_review_count: 0`; other fields are out of scope | Minimal-diff principle: change only the field the issue names; other improvements go in separate PRs |

## Results & Parameters

**Files fixed (HomericIntelligence/Odysseus, PR #308, issue #178):**

```text
configs/github/org-ruleset.json          line 21: 0 → 1
configs/github/org-ruleset-active.json   line 21: 0 → 1
configs/github/repo-ruleset.json         line 17: 0 → 1
configs/github/repo-ruleset-active.json  line 17: 0 → 1
```

**CI guard added to `.github/workflows/_required.yml` (lines 275-276):**

```bash
# Four-file guard — replaces single-file JSON-parse check
for f in configs/github/org-ruleset.json configs/github/org-ruleset-active.json \
          configs/github/repo-ruleset.json configs/github/repo-ruleset-active.json; do
  count=$(jq 'first(.rules[] | select(.type=="pull_request")
              | .parameters.required_approving_review_count)' "$f")
  [ "$count" -lt 1 ] && { echo "FAIL: $f has required_approving_review_count=$count"; exit 1; }
done
```

**Key design decisions:**

- `first()` wrapper: makes the guard robust if files ever grow multiple `pull_request` rules
- Four-file scope: covers both base and enforcing (`-active.json`) variants
- `>= 1` threshold (not `== 1`): a future tightening to 2 would not break the guard
- Existing bypass actors: OrganizationAdmin id 1, Integration id 49699333, RepositoryRole id 5 already present — no new actor added

**Verification suite (all four checks passed locally):**

```bash
# 1. jq value check — should print: 1 1 1 1
for f in configs/github/org-ruleset.json configs/github/org-ruleset-active.json \
          configs/github/repo-ruleset.json configs/github/repo-ruleset-active.json; do
  jq '.rules[] | select(.type=="pull_request") | .parameters.required_approving_review_count' "$f"
done

# 2. grep check — should produce no output (exit 0)
! grep -rn '"required_approving_review_count": 0' configs/github/

# 3. JSON validity
for f in configs/github/*.json; do jq empty "$f" && echo "OK: $f"; done

# 4. CI guard logic mirror — should exit 0 on count=1
count=1; [ "$count" -lt 1 ] && echo "FAIL" || echo "PASS"
```

**Unverified assumptions (recorded as risks):**

- `bypass_actors` numeric IDs (`actor_id: 1` OrganizationAdmin, `5` RepositoryRole admin,
  `49699333` Integration) taken from existing JSON — NOT confirmed against live `gh api`.
- Bypass-actor merge semantics (a `pull_request`-mode bypass lets an admin author merge
  a self-PR the review requirement would block) NOT empirically tested against live GitHub.
- Line numbers (`org:21`, `repo:17`) are checkout-relative and may drift.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | Issue #178, PR #308 (2026-06-19) | Fixed all four canonical ruleset JSON files; CI guard added; verified-local only — PR CI pending at skill creation time |

## References

- [GitHub: Rulesets documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [GitHub REST: Rulesets API](https://docs.github.com/en/rest/repos/rules?apiVersion=2022-11-28)
- [jq `first()` function](https://jqlang.org/manual/#first-last)
- [Related skill: config-governance-fix-scope-all-variant-files](config-governance-fix-scope-all-variant-files.md)
- [Related skill: ci-cd-ruleset-bootstrap-deadlock](ci-cd-ruleset-bootstrap-deadlock.md)
- [Related skill: github-branch-protection-org-standardize](github-branch-protection-org-standardize.md)
