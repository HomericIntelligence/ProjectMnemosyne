---
name: ci-github-ruleset-matrix-status-context
description: "GitHub matrix jobs emit expanded context names (job-id (matrix-value)) that must be registered verbatim in branch rulesets. Use when: (1) a required status check shows 'Expected — Waiting for status to be reported' forever even after all matrix jobs pass, (2) a ruleset uses the bare job ID for a matrix job and the PR merge box is permanently blocked, (3) debugging why classic branch protection returns 404 but the PR is still blocked."
category: ci-cd
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github
  - rulesets
  - matrix
  - status-checks
  - branch-protection
  - github-actions
---

# GitHub Ruleset: Matrix Job Expanded Context Names

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-26 |
| **Objective** | Fix permanently blocked PR caused by ruleset requiring a bare job ID that GitHub Actions never emits for matrix jobs |
| **Outcome** | Successful — ruleset PUT succeeded, all four expanded matrix contexts confirmed via API |
| **Verification** | verified-local (ruleset PUT succeeded and confirmed via API; CI run in progress) |

## When to Use

- A required status check shows "Expected — Waiting for status to be reported" on every PR even after all matrix jobs pass
- A branch ruleset has an entry like `Required Checks / integration-tests` but the workflow uses `strategy.matrix`
- `GET /repos/{owner}/{repo}/branches/{branch}/protection` returns 404 but the PR is still merge-blocked
- Debugging which API to use for rulesets vs. classic branch protection

## Verified Workflow

### Quick Reference

```bash
# 1. Find the ruleset ID
gh api repos/{owner}/{repo}/rulesets --jq '.[].id'

# 2. Fetch the full ruleset
gh api repos/{owner}/{repo}/rulesets/{RULESET_ID} > /tmp/ruleset.json

# 3. Rewrite — replace bare job ID with N expanded matrix context names
python3 << 'EOF'
import json

with open("/tmp/ruleset.json") as f:
    ruleset = json.load(f)

for rule in ruleset["rules"]:
    checks = rule.get("parameters", {}).get("required_status_checks")
    if checks is None:
        continue
    new_checks = []
    for c in checks:
        if c["context"] == "Required Checks / integration-tests":
            new_checks.extend([
                {"context": "Required Checks / integration-tests (asan)"},
                {"context": "Required Checks / integration-tests (ubsan)"},
                {"context": "Required Checks / integration-tests (tsan)"},
                {"context": "Required Checks / integration-tests (lsan)"},
            ])
        else:
            new_checks.append(c)
    rule["parameters"]["required_status_checks"] = new_checks

with open("/tmp/ruleset_updated.json", "w") as f:
    json.dump(ruleset, f, indent=2)
EOF

# 4. Apply and confirm
gh api -X PUT repos/{owner}/{repo}/rulesets/{RULESET_ID} \
  --input /tmp/ruleset_updated.json \
  --jq '.rules[].parameters.required_status_checks[].context'
```

### Detailed Steps

1. Confirm the problem is a ruleset (not classic branch protection):
   ```bash
   gh api repos/{owner}/{repo}/branches/{branch}/protection
   # Expect: 404 when only rulesets are active
   gh api repos/{owner}/{repo}/rules/branches/{branch}
   # Expect: list of active ruleset rules including required_status_checks
   ```

2. Identify the required status check context that will never be emitted:
   ```bash
   gh api repos/{owner}/{repo}/rulesets --jq '.[].id'
   gh api repos/{owner}/{repo}/rulesets/{RULESET_ID} \
     --jq '.rules[].parameters.required_status_checks[].context'
   ```
   Look for bare job IDs such as `Required Checks / integration-tests` without parenthesized matrix values.

3. Verify what GitHub Actions actually emits for a matrix job. In the workflow YAML:
   ```yaml
   integration-tests:
     name: integration-tests (${{ matrix.sanitizer }})
     strategy:
       matrix:
         sanitizer: [asan, ubsan, tsan, lsan]
   ```
   GitHub emits four check contexts:
   - `Required Checks / integration-tests (asan)`
   - `Required Checks / integration-tests (ubsan)`
   - `Required Checks / integration-tests (tsan)`
   - `Required Checks / integration-tests (lsan)`

   The bare `Required Checks / integration-tests` is NEVER emitted.

4. Fetch the ruleset JSON, rewrite the `required_status_checks` array (see Quick Reference above), and PUT it back. Verify with `--jq '.rules[].parameters.required_status_checks[].context'`.

5. Check the PR again — each expanded context should now appear in the checks list and resolve when the corresponding matrix job completes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Queried classic branch protection (`/branches/{branch}/protection`) to find the required check | Returns 404 when only rulesets are used; no policy visible | When classic branch protection returns 404, check `/rulesets` and `/rules/branches/{branch}` instead |
| Attempt 2 | Left the bare job ID `integration-tests` in the ruleset, expecting GitHub to match matrix children | GitHub has no wildcard or parent-child matching for required contexts; the bare name is never emitted by matrix jobs | Register each expanded matrix context verbatim — one entry per matrix value |
| Attempt 3 (not attempted, documented) | Adding a roll-up job (`needs: integration-tests`, `name: integration-tests`) to produce the bare context | Adds a phantom job to every run, doubles required check count, and creates confusing debugging surface | Prefer updating the ruleset to match what the workflow emits, not restructuring the workflow to match an inflexible ruleset |

## Results & Parameters

**Context name format rules:**

```text
"{workflow-name} / {job-name}"
```

Where `job-name` matches the `name:` field in the YAML, NOT the YAML job key. For a matrix job:

```text
"{workflow-name} / {job-name} ({matrix-value})"
```

Examples:
- YAML key `integration-tests:`, `name: integration-tests (${{ matrix.sanitizer }})`, sanitizer = asan
  → context: `Required Checks / integration-tests (asan)`
- YAML key `security-dependency-scan:`, `name: security/dependency-scan`
  → context: `Required Checks / security/dependency-scan`

**APIs used for rulesets (not classic branch protection):**

```bash
# List all rulesets
GET /repos/{owner}/{repo}/rulesets

# Get a specific ruleset by ID
GET /repos/{owner}/{repo}/rulesets/{ruleset_id}

# Update a ruleset
PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}

# See active rules for a specific branch
GET /repos/{owner}/{repo}/rules/branches/{branch}

# Classic branch protection (returns 404 when only rulesets are used)
GET /repos/{owner}/{repo}/branches/{branch}/protection
```

**Expected output after successful PUT:**

```text
Required Checks / integration-tests (asan)
Required Checks / integration-tests (ubsan)
Required Checks / integration-tests (tsan)
Required Checks / integration-tests (lsan)
```

**N matrix values = N required_status_checks entries.** GitHub provides no wildcard matching.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | PR #451, branch `fix/security-scan-gitleaks-jq` | Ruleset ID 15556488, four sanitizer matrix values; PUT confirmed via API |
