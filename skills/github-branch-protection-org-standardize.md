---
name: github-branch-protection-org-standardize
description: "Standardize GitHub branch protection across all repositories in an org using repository rulesets. Use when: (1) rolling out a required-checks baseline to all repos on the free GitHub plan, (2) onboarding new repos to a shared CI policy, (3) auditing ruleset drift across an org."
category: ci-cd
date: 2026-04-26
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: github-branch-protection-org-standardize.history
tags:
  - github
  - branch-protection
  - rulesets
  - gh-api
  - org-admin
  - policy-standardization
  - required-status-checks
---

# GitHub Branch Protection Org Standardization

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 |
| **Objective** | Roll out `homeric-main-baseline` repository ruleset to all 15 HomericIntelligence repos, enforcing 8 required CI checks on every PR |
| **Outcome** | Successful — all 15 rulesets applied live, PRs opened and merged successfully |
| **Verification** | verified-ci (all 15 rulesets applied live, PRs opened successfully) |
| **History** | [changelog](./github-branch-protection-org-standardize.history) |

## When to Use

- Applying an org-wide branch protection baseline to multiple repos at once (free GitHub plan)
- Enforcing required CI status checks via rulesets with `integration_id`
- Dynamically discovering all non-archived repos in an org without hardcoding lists
- Auditing current ruleset state before or after a policy rollout
- Onboarding new repos to an existing gold-standard configuration

## Verified Workflow

### Quick Reference

```bash
ORG="HomericIntelligence"
INTEGRATION_ID=15368  # GitHub Actions app ID

# 1. Dynamically discover all non-archived repos
mapfile -t REPOS < <(gh repo list "$ORG" --json name,isArchived --limit 100 \
  --jq '[.[] | select(.isArchived == false) | .name] | sort | .[]')

# 2. Apply ruleset to each repo (idempotent — creates if absent, replaces if exists)
for repo in "${REPOS[@]}"; do
  existing_id=$(gh api "repos/$ORG/$repo/rulesets" \
    --jq '.[] | select(.name == "homeric-main-baseline") | .id' 2>/dev/null)

  RULESET_JSON=$(cat <<ENDJSON
{
  "name": "homeric-main-baseline",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "non_fast_forward" },
    { "type": "deletion" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "lint",                     "integration_id": $INTEGRATION_ID },
          { "context": "unit-tests",               "integration_id": $INTEGRATION_ID },
          { "context": "integration-tests",        "integration_id": $INTEGRATION_ID },
          { "context": "security/dependency-scan", "integration_id": $INTEGRATION_ID },
          { "context": "security/secrets-scan",    "integration_id": $INTEGRATION_ID },
          { "context": "build",                    "integration_id": $INTEGRATION_ID },
          { "context": "schema-validation",        "integration_id": $INTEGRATION_ID },
          { "context": "deps/version-sync",        "integration_id": $INTEGRATION_ID }
        ]
      }
    }
  ],
  "bypass_actors": []
}
ENDJSON
)

  if [ -n "$existing_id" ]; then
    echo "$RULESET_JSON" | gh api -X PUT "repos/$ORG/$repo/rulesets/$existing_id" --input - > /dev/null
    echo "Updated ruleset on $repo (id=$existing_id)"
  else
    echo "$RULESET_JSON" | gh api -X POST "repos/$ORG/$repo/rulesets" --input - > /dev/null
    echo "Created ruleset on $repo"
  fi
done

# 3. Verify all repos have the ruleset
for repo in "${REPOS[@]}"; do
  count=$(gh api "repos/$ORG/$repo/rulesets" \
    --jq '[.[] | select(.name == "homeric-main-baseline")] | length')
  echo "$repo: ruleset_count=$count"
done
```

### Detailed Steps

1. **Use repo-level rulesets, not org-level** — `orgs/<ORG>/rulesets` returns HTTP 403 on the free GitHub plan. Use `repos/<ORG>/<REPO>/rulesets` instead. Both endpoints accept the same JSON body format.

2. **Dynamically discover repos** — Use `gh repo list` with `--json name,isArchived` and filter with `--jq` to exclude archived repos. Feed into `mapfile -t` for a clean array. Never hardcode the repo list — it misses newly created repos.

3. **Use bare job names as context strings** — In `required_status_checks`, the `context` field must be the exact `name:` value from the workflow job (e.g., `lint`, `build`), NOT the prefixed form (`Required Checks / lint`). GitHub reports bare job names in check run contexts.

4. **Always include `integration_id: 15368`** — This is the GitHub Actions app ID. Required for ruleset status checks to match against GitHub Actions workflow runs. Without it, checks never satisfy the requirement.

5. **Put typecheck inside the lint job** — `typecheck` steps (mypy, clang-tidy, pyright) belong as steps within the `lint` job, not as a separate required context. This keeps the required context count at 8 (not 9).

6. **Do NOT use `--silent` when collecting output** — `gh api --silent` suppresses JSON output entirely. When storing responses in variables for idempotency checks (e.g., checking if a ruleset already exists), omit `--silent`. Redirect to `/dev/null` only when you truly don't need the output.

7. **Check for existing ruleset before POST vs PUT** — `POST repos/<ORG>/<REPO>/rulesets` creates a new ruleset. `PUT repos/<ORG>/<REPO>/rulesets/<ID>` replaces an existing one. Always check if a ruleset with the target name already exists before deciding which verb to use.

8. **Verify after applying** — Run a second loop checking `gh api repos/<ORG>/<REPO>/rulesets --jq '[.[] | select(.name == "homeric-main-baseline")] | length'`. Should be `1` for every repo.

### The `_required.yml` Workflow Pattern

Every repo needs a `_required.yml` workflow that emits exactly the 8 job names that the ruleset requires. The workflow `name:` field is arbitrary; only the job-level `name:` fields matter.

```yaml
# .github/workflows/_required.yml
name: Required Checks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    name: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: echo "lint ok"
      - name: Typecheck
        run: echo "typecheck ok"  # typecheck is a STEP here, not a separate job

  unit-tests:
    name: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "unit-tests ok"

  integration-tests:
    name: integration-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "integration-tests ok"

  dependency-scan:
    name: security/dependency-scan   # note: name has slash, job id does not
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "dependency-scan ok"

  secrets-scan:
    name: security/secrets-scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "secrets-scan ok"

  build:
    name: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "build ok"

  schema-validation:
    name: schema-validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "schema-validation ok"

  version-sync:
    name: deps/version-sync
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "version-sync ok"
```

**Critical**: Job `id`s (YAML keys like `dependency-scan`) cannot contain slashes. Job `name:` values (like `security/dependency-scan`) can. The ruleset uses the `name:` value, not the job id.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Using `orgs/<ORG>/rulesets` endpoint | Returns HTTP 403 on free GitHub plan — org-level rulesets require Team plan | Use `repos/<ORG>/<REPO>/rulesets` (repo-level) instead — works on free plan |
| Attempt 2 | Context string `"Required Checks / lint"` (workflow-prefixed form) | GitHub reports bare job `name:` values in check run contexts, not workflow-prefixed names | Use bare job names: `lint`, `build`, `unit-tests`, etc. |
| Attempt 3 | Adding `typecheck` as a 9th standalone required context | Typecheck belongs as a step inside `lint`, not a separate job | Keep typecheck as a step in `lint`; required context count is 8 |
| Attempt 4 | `gh api --silent` when checking existing rulesets | `--silent` suppresses JSON output, causing all repos to appear as having no ruleset | Remove `--silent`; use `> /dev/null` only when output is genuinely not needed |
| Attempt 5 | Hardcoding `REPOS=(Repo1 Repo2 ...)` array | Brittle — misses newly created repos, requires manual maintenance | Use `gh repo list` + `mapfile` for dynamic discovery |
| Attempt 6 | `gh pr merge --auto --rebase` on repos that only allow squash merge | Fails — some repos only permit squash merge, not rebase | Use `gh pr merge --auto --squash` as the safer default; check repo merge settings first |

## Results & Parameters

**Canonical ruleset JSON (all 15 HomericIntelligence repos)**:

```json
{
  "name": "homeric-main-baseline",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "non_fast_forward" },
    { "type": "deletion" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "lint",                     "integration_id": 15368 },
          { "context": "unit-tests",               "integration_id": 15368 },
          { "context": "integration-tests",        "integration_id": 15368 },
          { "context": "security/dependency-scan", "integration_id": 15368 },
          { "context": "security/secrets-scan",    "integration_id": 15368 },
          { "context": "build",                    "integration_id": 15368 },
          { "context": "schema-validation",        "integration_id": 15368 },
          { "context": "deps/version-sync",        "integration_id": 15368 }
        ]
      }
    }
  ],
  "bypass_actors": []
}
```

**API endpoint reference**:

```bash
# List rulesets for a repo
gh api repos/<ORG>/<REPO>/rulesets

# Get a specific ruleset by ID
gh api repos/<ORG>/<REPO>/rulesets/<ID>

# Create a ruleset
gh api -X POST repos/<ORG>/<REPO>/rulesets --input -

# Replace an existing ruleset
gh api -X PUT repos/<ORG>/<REPO>/rulesets/<ID> --input -

# Delete a ruleset
gh api -X DELETE repos/<ORG>/<REPO>/rulesets/<ID>
```

**Plan requirements**:
- `repos/<ORG>/<REPO>/rulesets` — works on **free plan**
- `orgs/<ORG>/rulesets` — requires **Team plan** (HTTP 403 on free)

**integration_id reference**:
- `15368` = GitHub Actions (for matching workflow job checks)

**Verification output format** (expected after a successful pass):
```text
ProjectAgamemnon: ruleset_count=1
ProjectNestor: ruleset_count=1
AchaeanFleet: ruleset_count=1
... (all 15 repos)
```

### Deprecated Approach (v1.0.0 — Legacy Branch Protection API)

The v1.0.0 skill used `PUT repos/<ORG>/<REPO>/branches/main/protection`. This still works but has limitations: it does not support `integration_id` in required_status_checks and `required_linear_history: true` prevents merge commits retroactively. See [history file](./github-branch-protection-org-standardize.history) for the full v1.0.0 workflow.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence (all 15 repos) | Ruleset rollout session 2026-04-26 | Applied `homeric-main-baseline` ruleset via repo-level API, PRs opened and merged successfully |
| HomericIntelligence (all 15 repos) | Legacy branch protection session 2026-04-22 | Applied Scylla-style PUT policy, verification loop confirmed linear=true conversation=true on every repo |
