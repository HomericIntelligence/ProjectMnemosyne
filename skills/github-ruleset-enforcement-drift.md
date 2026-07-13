---
name: github-ruleset-enforcement-drift
description: "Canonical config file says `evaluate` but live GitHub ruleset is already `active`; idempotent re-apply would silently downgrade enforcement. Use when: (1) flipping a GitHub branch ruleset from evaluate to active mode and the on-disk JSON carries `evaluate`, (2) confirming whether a canonical config file matches its live deployed state before re-applying, (3) preserving a rollback/shadow-test path after the base config file changes enforcement mode, (4) aligning variant apply-target files (e.g. `*-active.json`) that were not updated when the base file was fixed, (5) auditing required_status_checks context strings for the correct bare-name + integration_id form vs stale prefixed form."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github, rulesets, branch-protection, enforcement, drift, rollback, evaluate, active, integration_id]
---

# GitHub Ruleset Enforcement Drift

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Fix `enforcement: evaluate` in canonical GitHub ruleset JSON files that should be `active`, without downgrading the live deployed state or breaking the rollback/shadow-test path |
| **Outcome** | Successful — on-disk config aligned with live enforcing ruleset; rollback path preserved via dedicated evaluate file and explicit `--evaluate` flag; stale prefixed contexts in variant files corrected |
| **Verification** | verified-local — pre-commit and jq assertions passed; PR #307 merged to HomericIntelligence/Odysseus; Mnemosyne CI gate not observed |

## When to Use

- A GitHub branch ruleset config file has `"enforcement": "evaluate"` but the live ruleset (queried via `gh api repos/<ORG>/<REPO>/rulesets/<ID>`) reports `"enforcement": "active"` — the file is drifted and an idempotent re-apply would DOWNGRADE the live enforcing state.
- The apply script does a PUT-if-exists (idempotent) — re-applying a stale `evaluate` file when live is `active` silently removes enforcement.
- A runbook's two-phase rollout uses bare script invocation as the "shadow (evaluate) pass", but the script's bare default was changed to `active` — the documented flow is now silently active-then-active.
- A variant file (`*-active.json`, `*-evaluate.json`) was left unedited when the base file was fixed, remaining a live apply path with stale context strings.
- `required_status_checks` context entries use the stale prefixed form (`"Required Checks / lint"`) instead of the canonical bare-name + `integration_id` form (`"lint"` + `"integration_id": 15368`).

## Verified Workflow

### Quick Reference

```bash
# 1. Check live enforcement vs on-disk (detect drift before re-applying)
RULESET_ID=$(gh api repos/ORG/REPO/rulesets \
  --jq '.[] | select(.name=="homeric-main-baseline") | .id')
LIVE=$(gh api repos/ORG/REPO/rulesets/$RULESET_ID --jq .enforcement)
DISK=$(jq -r .enforcement configs/github/repo-ruleset.json)
echo "live=$LIVE disk=$DISK"
# If live=active and disk=evaluate → file is stale; fix disk to match live.
# If live=evaluate and disk=active → file is ahead; re-apply will activate.

# 2. Confirm context string format from live ruleset (bare vs prefixed)
gh api repos/ORG/REPO/rulesets/$RULESET_ID \
  --jq '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[]'
# Correct form: {"context":"lint","integration_id":15368}
# Stale form:   {"context":"Required Checks / lint"}   ← NO integration_id, wrong prefix

# 3. After flipping base file, create a dedicated evaluate rollback file
cp configs/github/repo-ruleset.json configs/github/repo-ruleset-evaluate.json
# Edit repo-ruleset-evaluate.json to set "enforcement": "evaluate"
# Now rollback is: ./tools/github/apply-repo-rulesets.sh --evaluate

# 4. Verify both canonical files match intended enforcement
jq -e '.enforcement == "active"' configs/github/org-ruleset.json configs/github/repo-ruleset.json
jq -e '.enforcement == "evaluate"' configs/github/repo-ruleset-evaluate.json

# 5. Check all variant files for stale prefixed contexts
jq '[.rules[] | select(.type=="required_status_checks")
     | .parameters.required_status_checks[].context]' configs/github/org-ruleset-active.json
# Any "Required Checks / *" entries are stale — replace with bare names + integration_id

# 6. Verify context count and no non-canonical entries
jq '[.rules[] | select(.type=="required_status_checks")
     | .parameters.required_status_checks[]] | length' configs/github/repo-ruleset.json
# Expected: 8 (not 9 — forbid-suppressions is a workflow job, NOT a required context)
```

### Detailed Steps

1. **Detect drift before editing.** Query `gh api repos/<ORG>/<REPO>/rulesets/<ID>` to get live `enforcement` and `required_status_checks`. Compare against the on-disk canonical file. If live is `active` and disk says `evaluate`, the file is drifted — flipping the file to `active` closes the regression window; re-applying the stale evaluate file would downgrade enforcement.

2. **Confirm context string format from live state.** The live ruleset tells you the exact form GitHub reports: bare job `name:` values (`"lint"`) with `"integration_id": 15368`, NOT the prefixed `"Required Checks / lint"` form. Use whatever the live ruleset says, not what a KB note or stale file says.

3. **Flip the base canonical file** (`repo-ruleset.json`, `org-ruleset.json`) to `"enforcement": "active"`. Do NOT change context strings in `repo-ruleset.json` if they already match the live enforcing ruleset — only line 4 changes.

4. **Fix ALL variant files** that carry stale context strings or enforcement. Read the apply script to find which file each flag selects: `--active` → `*-active.json`, bare default → base file, `--evaluate` → (after this fix) evaluate file. Each selectable variant must be consistent.

5. **Create a dedicated evaluate file** (`repo-ruleset-evaluate.json`): a copy of the base file with `"enforcement": "evaluate"`. This preserves the shadow-test and rollback path after the base file flips to `active`.

6. **Add an explicit `--evaluate` flag** to the apply script pointing at the new evaluate file. The bare default should now apply the canonical (active) file. Update the usage comment in the script.

7. **Update ALL runbook two-phase rollout examples.** Any runbook section that says "bare invocation = shadow/evaluate pass" is now wrong once the bare default is `active`. Replace bare calls with `--evaluate` explicitly:
   - "Adding a new repo" step 3: use `--evaluate --repos <NewRepo>`
   - "Re-applying to all repos" shadow step: use `--evaluate`
   - Rollback section: use `--evaluate`

8. **Validate all JSON files are syntactically valid** after edits:
   ```bash
   jq empty configs/github/org-ruleset.json configs/github/repo-ruleset.json \
     configs/github/repo-ruleset-evaluate.json && echo OK
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Leave `org-ruleset-active.json` untouched | Fixed `org-ruleset.json` contexts but left `org-ruleset-active.json` with 9 stale prefixed entries | `apply-org-ruleset.sh` accepts the JSON file as an argument — `org-ruleset-active.json` remains a live apply path that would push wrong contexts, re-introducing drift | When fixing context strings, grep for ALL variant files (`*-active.json`, `*-evaluate.json`) and fix every live apply path |
| Change bare default without updating runbook | Apply script bare default changed from evaluate to active, but runbook still called bare invocation as the "evaluate mode shadow pass" | Reviewer caught that the two-phase rollout was now silently active-then-active — shadow step lost | Every time a script flag default changes, audit ALL runbook examples that relied on that bare invocation and update them to use explicit flags |
| Remove `-active.json` variant files to reduce duplication | Prior plan proposed deleting `repo-ruleset-active.json` and `org-ruleset-active.json` as they were now identical to the base | Removing them broke the rollback path and the `--active` flag; the NOGO review flagged scope creep + irreversible delete | Preserve variant files even when they become temporarily identical to the base — they serve as explicit named apply paths; cleanup is a separate issue |
| Use prefixed context form in org-ruleset-active.json | Kept `"Required Checks / lint"` form from the original config | GitHub Actions reports bare job `name:` values (`"lint"`), not workflow-prefixed; contexts without `integration_id` are also unreliable | Always derive context strings from the LIVE ruleset API, not from the config file or KB assumption |

## Results & Parameters

**Canonical required_status_checks entry (HomericIntelligence `homeric-main-baseline`):**

```json
{ "context": "lint",                    "integration_id": 15368 }
{ "context": "unit-tests",              "integration_id": 15368 }
{ "context": "integration-tests",       "integration_id": 15368 }
{ "context": "security/dependency-scan","integration_id": 15368 }
{ "context": "security/secrets-scan",   "integration_id": 15368 }
{ "context": "build",                   "integration_id": 15368 }
{ "context": "schema-validation",       "integration_id": 15368 }
{ "context": "deps/version-sync",       "integration_id": 15368 }
```

**Count:** 8 required contexts. `forbid-suppressions` is a 9th workflow job intentionally NOT a required context. If runbook or docs say "9 contexts", they are counting workflow jobs, not required contexts — correct them against the live ruleset length.

**Apply script flag → JSON file mapping (post-fix):**

| Flag | JSON file | Enforcement |
|------|-----------|-------------|
| (none / bare) | `repo-ruleset.json` | `active` (canonical) |
| `--active` | `repo-ruleset-active.json` | `active` |
| `--evaluate` | `repo-ruleset-evaluate.json` | `evaluate` (rollback/shadow) |

**Org endpoint note:** `gh api orgs/<ORG>/rulesets` returns 404 on the GitHub free plan (requires `admin:org`). Per-repo rulesets (`repos/<org>/<repo>/rulesets`) are the enforcing path and work on the free plan. Do not designate `org-ruleset.json` as an activation path or include an org-endpoint verification command.

**Live-state comparison (verification commands):**

```bash
# On-disk vs live enforcement — must match after fix
test "$(jq -r .enforcement configs/github/repo-ruleset.json)" = \
     "$(gh api repos/ORG/REPO/rulesets/$RULESET_ID --jq .enforcement)" && echo OK

# Context count must be 8
test "$(jq '[.rules[] | select(.type=="required_status_checks")
             | .parameters.required_status_checks[]] | length' \
        configs/github/repo-ruleset.json)" = 8 && echo OK

# Rollback file must say evaluate
jq -e '.enforcement == "evaluate"' configs/github/repo-ruleset-evaluate.json
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | PR #307, issue #177, 2026-06-19 | Flipped `repo-ruleset.json` and `org-ruleset.json` to `active`; fixed `org-ruleset-active.json` prefixed contexts; added `repo-ruleset-evaluate.json`; added `--evaluate` flag; updated runbook two-phase rollout |
