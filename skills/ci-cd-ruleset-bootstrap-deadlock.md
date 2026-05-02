---
name: ci-cd-ruleset-bootstrap-deadlock
description: "Detect and resolve a CI ruleset chicken-and-egg deadlock where a PR introducing a new workflow file is permanently blocked because the ruleset requires check names that only exist in the workflow being added. Use when: (1) a PR adding a new CI workflow shows mergeStateStatus=BLOCKED with zero failing checks, (2) re-triggering CI produces no new runs, (3) auto-merge is armed but never fires despite all existing checks passing."
category: ci-cd
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github
  - rulesets
  - branch-protection
  - ci-bootstrap
  - deadlock
  - github-actions
---

# CI Ruleset Bootstrap Deadlock (Chicken-and-Egg)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-28 |
| **Objective** | Unblock a PR that introduces a new CI workflow whose job names are already in the branch ruleset's required_status_checks |
| **Outcome** | Successful — confirmed via admin bypass merge and ruleset inspection |
| **Verification** | verified-ci (confirmed on HomericIntelligence/ProjectCharybdis PRs #4 and #5, 2026-04-28) |

## When to Use

- A PR adding a new workflow file (e.g., `_required.yml`) is `BLOCKED` with no failing checks and no review comments
- `gh pr view` shows `mergeStateStatus=BLOCKED` but `statusCheckRollup` contains no failures — only successes, skips, or nulls
- Re-triggering CI creates no new workflow runs (the workflow doesn't exist on the base branch yet)
- Auto-merge is enabled on the PR but never fires
- The repository recently migrated from aggregate CI checks (e.g., `All Build/Test Checks`) to granular per-job check names in the ruleset

## Verified Workflow

### Quick Reference

```bash
# Step 1: Confirm BLOCKED with zero failing checks = bootstrap deadlock
gh pr view $PR --repo $REPO --json mergeStateStatus,statusCheckRollup \
  --jq '{status:.mergeStateStatus, failing_count: ([.statusCheckRollup[] | select(.conclusion != "SUCCESS" and .conclusion != "SKIPPED" and .conclusion != null)] | length)}'
# Deadlock signature: status=BLOCKED, failing_count=0

# Step 2: Confirm the required checks don't exist on the base branch
gh api repos/$OWNER/$REPO/rulesets \
  --jq '.[] | {name:.name, id:.id}'

gh api repos/$OWNER/$REPO/rulesets/$RULESET_ID \
  --jq '.rules[].parameters.required_status_checks[].context'

# Step 3: Confirm the workflow file is only in the PR branch, not on main
gh api repos/$OWNER/$REPO/contents/.github/workflows \
  --jq '.[].name'

# Step 4: Choose resolution (see below)
```

### Detailed Steps

1. Confirm the PR is blocked with no actionable failures:
   ```bash
   gh pr view $PR_NUMBER --repo $OWNER/$REPO \
     --json mergeStateStatus,statusCheckRollup \
     --jq '{
       status: .mergeStateStatus,
       failing: [.statusCheckRollup[] | select(.conclusion != "SUCCESS" and .conclusion != "SKIPPED" and .conclusion != null)]
     }'
   ```
   If `status` is `BLOCKED` and `failing` is `[]`, the block is a policy deadlock, not a test failure.

2. Inspect the active ruleset to find which check names are required:
   ```bash
   gh api repos/$OWNER/$REPO/rulesets --jq '.[].id'
   gh api repos/$OWNER/$REPO/rulesets/$RULESET_ID \
     --jq '.rules[].parameters.required_status_checks[].context'
   ```
   Note each required context name (e.g., `lint`, `unit-tests`, `build`, `security/dependency-scan`).

3. Confirm none of those contexts exist as workflow jobs on the base branch (main):
   ```bash
   gh api repos/$OWNER/$REPO/contents/.github/workflows --jq '.[].name'
   # If the new _required.yml is absent from this list, the workflow doesn't exist on main
   ```

4. Attempt to trigger CI manually — if no run is created, confirm the deadlock:
   ```bash
   gh workflow run _required.yml --repo $OWNER/$REPO --ref main
   # Expected: error — workflow does not exist on base branch
   ```

5. Pick one of the three resolution options below.

### Resolution Options

**Option 1 — Admin bypass (fastest, no ruleset changes needed)**

A repository admin uses the GitHub web UI "Merge without waiting for requirements" button (bypass), or:
```bash
# There is no direct gh CLI bypass — must use GitHub web UI as admin
# Navigate to the PR, click "Merge pull request" dropdown, select "Merge without waiting for requirements"
```
After merge, the workflow exists on main and future PRs will satisfy the ruleset naturally.

**Option 2 — Temporarily remove check names from ruleset (safest for automation)**

```bash
# Fetch ruleset
gh api repos/$OWNER/$REPO/rulesets/$RULESET_ID > /tmp/ruleset.json

# Remove the offending required_status_checks (or all of them temporarily)
python3 << 'EOF'
import json

with open("/tmp/ruleset.json") as f:
    ruleset = json.load(f)

# Remove required_status_checks temporarily
for rule in ruleset.get("rules", []):
    if "required_status_checks" in rule.get("parameters", {}):
        rule["parameters"]["required_status_checks"] = []

with open("/tmp/ruleset_patched.json", "w") as f:
    json.dump(ruleset, f, indent=2)
EOF

# Apply the patch
gh api -X PUT repos/$OWNER/$REPO/rulesets/$RULESET_ID \
  --input /tmp/ruleset_patched.json

# Merge the PR (now unblocked)
gh pr merge $PR_NUMBER --squash --repo $OWNER/$REPO

# Restore the required checks
gh api -X PUT repos/$OWNER/$REPO/rulesets/$RULESET_ID \
  --input /tmp/ruleset.json
```

**Option 3 — Transitional workflow PR (safest for governance continuity)**

1. Create a separate PR on a new branch that adds the new workflow to main WITHOUT removing the old aggregate check workflow.
2. The old check still satisfies the existing ruleset, so the transitional PR can merge.
3. Once merged, update the ruleset to require the new granular check names.
4. The original bootstrap PR can now satisfy the ruleset and merge normally.

```bash
git checkout main
git checkout -b chore/add-required-workflow-transitional
# Copy new workflow without removing old one
cp .github/workflows/_required.yml.draft .github/workflows/_required.yml
git add .github/workflows/_required.yml
git commit -m "chore(ci): add granular required checks workflow alongside existing aggregate check"
git push origin chore/add-required-workflow-transitional
gh pr create --base main --repo $OWNER/$REPO \
  --title "chore(ci): transitional required workflow" \
  --body "Adds granular CI checks alongside existing aggregate. Follow-up PR will remove aggregate and update ruleset."
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Re-triggered CI runs manually via `gh workflow run` and `gh pr comment` push triggers | No new workflow runs were created because the workflow file does not exist on the base branch (`main`); GitHub resolves workflow files from the base branch for PR checks | GitHub only runs workflows that exist on the **base branch** of a PR. A workflow added only in the PR branch cannot run against that PR. |
| Attempt 2 | Enabled auto-merge expecting it to fire once existing checks completed | Auto-merge armed successfully but never fired because `mergeStateStatus` stayed `BLOCKED` due to the ruleset requiring check names that were never emitted | Auto-merge fires only when all required status checks pass; a permanently absent check is treated the same as a permanently failing one — the PR stays blocked indefinitely |
| Attempt 3 | Checked classic branch protection to understand which checks were required | `GET /repos/{owner}/{repo}/branches/main/protection` returned 404 because the repo uses branch rulesets, not classic protection | When classic branch protection returns 404, always check `/rulesets` and `/rules/branches/{branch}` — the enforcement mechanism is different but equally binding |

## Results & Parameters

**Deadlock signature (all three signals must be present):**

```text
mergeStateStatus: BLOCKED
failing_count: 0          (no checks are failing — they simply don't exist)
workflow_on_base: false   (the new workflow file is absent from main)
```

**Detection command:**

```bash
gh pr view $PR --repo $REPO --json mergeStateStatus,statusCheckRollup \
  --jq '{
    status: .mergeStateStatus,
    failing_count: ([.statusCheckRollup[] | select(.conclusion != "SUCCESS" and .conclusion != "SKIPPED" and .conclusion != null)] | length)
  }'
# status=BLOCKED + failing_count=0 = ruleset bootstrap deadlock
```

**Ruleset inspection commands:**

```bash
# List rulesets (NOT classic branch protection)
GET /repos/{owner}/{repo}/rulesets

# Get required check context names
GET /repos/{owner}/{repo}/rulesets/{ruleset_id}

# See active rules enforced on a specific branch
GET /repos/{owner}/{repo}/rules/branches/{branch}

# Classic branch protection (returns 404 when only rulesets are active)
GET /repos/{owner}/{repo}/branches/{branch}/protection
```

**How this differs from related ruleset issues:**

| Issue | Symptom | Root Cause |
| ------- | --------- | ------------ |
| Bootstrap deadlock (this skill) | BLOCKED, 0 failing, no CI runs at all | Required check names only exist in the PR being blocked |
| Matrix context mismatch | BLOCKED, checks "waiting" forever after all jobs pass | Ruleset uses bare job ID but matrix jobs emit `job (value)` format |
| Missing code scanning | BLOCKED, 0 checks emitted, no CI configured | Ruleset requires CodeQL/code-quality but repo has no source to scan |

**Resolution decision tree:**

```
Is mergeStateStatus=BLOCKED AND failing_count=0?
  └─ Yes: Does the workflow exist on main?
       ├─ No (bootstrap deadlock) → Pick resolution:
       │     ├─ Need it merged TODAY?         → Option 1: Admin bypass
       │     ├─ Have ruleset write access?     → Option 2: Temporarily remove checks
       │     └─ Want governance continuity?   → Option 3: Transitional workflow PR
       └─ Yes (different issue) → Check matrix contexts or code scanning config
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/ProjectCharybdis | PRs #4 and #5, 2026-04-28 | New `_required.yml` adding granular job names (`lint`, `unit-tests`, `integration-tests`, `security/dependency-scan`); ruleset already required those names; both PRs blocked with 0 failing checks; resolved via admin bypass |
