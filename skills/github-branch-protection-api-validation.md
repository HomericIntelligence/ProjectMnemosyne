---
name: github-branch-protection-api-validation
description: "GitHub branch protection API enforcement with response validation and synthetic testing. Use when: (1) implementing new branch protection rules, (2) adding API PUT calls that need validation, (3) testing bash scripts with environment fixtures."
category: ci-cd
date: 2026-06-03
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github, branch-protection, api, bash-testing, validation]
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Objective** | Enforce GitHub branch protection rules with response validation to detect silent API failures, and enable synthetic testing of branch protection scripts |
| **Outcome** | Successfully implemented for ProjectNestor main branch; all verification criteria passed |
| **Verification** | verified-ci (PR #108 CI checks passed) |

## When to Use

- Implementing new GitHub branch protection rules via API
- Adding PUT/PATCH calls to `repos/{owner}/{repo}/branches/{branch}/protection` endpoint
- Detecting silent failures when API ignores PUT fields (API field names differ from request payload keys)
- Testing bash governance scripts without hitting live GitHub API
- Need to allow future tightening of branch protection settings (e.g., 1→2 required reviews) without breaking drift detection

## Verified Workflow

### Quick Reference

**1. Minimize API payload to single field change:**
```json
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1
  }
}
```

**2. Apply with read-back validation:**
```bash
#!/usr/bin/env bash
set -euo pipefail
REPO="HomericIntelligence/ProjectNestor"
CONFIG=".github/branch-protection/main.json"

expected_count=$(jq -r '.required_pull_request_reviews.required_approving_review_count' "$CONFIG")

echo "Applying branch protection..."
gh api --method PUT "repos/${REPO}/branches/main/protection" --input "$CONFIG" >/dev/null

# READ-BACK: Verify the live state matches expected
live_count=$(gh api "repos/${REPO}/branches/main/protection" \
  --jq '.required_pull_request_reviews.required_approving_review_count // 0')

if [ "$live_count" != "$expected_count" ]; then
  echo "ERROR: PUT ignored field; live=$live_count, expected=$expected_count" >&2
  exit 1
fi
echo "OK: live setting = ${live_count}"
```

**3. Support synthetic testing via environment variable hook:**
```bash
#!/usr/bin/env bash
# In your verification script
fetch_rules() {
  if [ -n "${VERIFY_RULES_FIXTURE:-}" ]; then
    cat "$VERIFY_RULES_FIXTURE"  # Test mode: use injected fixture
  else
    gh api "repos/${REPO}/rules/branches/main"  # Production: call API
  fi
}
rules=$(fetch_rules)
```

**4. Use >= comparisons for forward-compatible drift detection:**
```bash
# Allows 1→2→3 tightening without breaking drift checks
if ! jq -e '.required_approving_review_count >= 1' <<<"$pr_params" >/dev/null 2>&1; then
  echo "ERROR: required_approving_review_count must be >= 1"
  exit 1
fi
```

### Detailed Steps

1. **Scope API changes narrowly**: Only change field whose semantics are verified by existing code or prior testing. Defer unverified fields (e.g., `require_last_push_approval`) to separate PR with dedicated API validation.

2. **Add GET read-back after PUT**: On same endpoint (`repos/{owner}/{repo}/branches/{branch}/protection`), immediately after PUT, call GET and compare live value to expected config using jq.

3. **Use defensive jq syntax**: Include fallback operator (`// 0` or `// "default"`) to handle missing fields gracefully.

4. **Extract rules-fetch into overridable function**: For bash governance scripts, expose the API call as a function that can be injected via env variable, enabling synthetic testing without network.

5. **Create synthetic test fixtures**: Use `jq -n` to generate test payloads matching the API response format. Example: `[{type:"pull_request",parameters:{required_approving_review_count:1}}]`

6. **Test both pass and fail paths**: Verify script exits 0 with valid payload, exits non-zero with invalid payload.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| No read-back after PUT | Apply script called gh api PUT and exited | Silent failures: API ignores unknown/misspelled fields, script exits 0 but live state unchanged | Always read-back immediately after PUT to detect silent failures |
| Direct jq assertions in CI | Verified workflow used bare `jq ... < output.json` expression | Doesn't exercise full script logic; synthetic test wasn't executing the actual code path | Extract API calls into overridable functions; inject fixtures via env hooks |
| Bundled unverified fields | Tried to tighten both `required_approving_review_count` and `require_last_push_approval` in one JSON change | API field name mapping unknown for `require_last_push_approval`; risk of silent failure | Single-field changes only; defer unverified fields to separate PR with explicit API validation |
| Exact equality for drift detection | Used `required_approving_review_count == 1` assertion | Blocks future tightening to 2 (drift check would fail on valid tightening) | Use `>= min_threshold` instead of `== exact_value` to allow forward evolution |

## Results & Parameters

**Example JSON config** (`.github/branch-protection/main.json`):
```json
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": false,
    "contexts": ["All Build/Test Checks", "branch-protection-drift"]
  },
  "enforce_admins": false,
  "required_conversation_resolution": true,
  "required_linear_history": true
}
```

**Synthetic test fixture** (pass case):
```bash
fixture=$(mktemp)
jq -n '[{type:"pull_request",parameters:{required_approving_review_count:1,required_review_thread_resolution:true}},{type:"required_status_checks",parameters:{required_status_checks:[{context:"x"}]}}]' > "$fixture"
VERIFY_RULES_FIXTURE="$fixture" bash scripts/verify-branch-protection.sh
# Expected: exit 0
```

**Synthetic test fixture** (fail case):
```bash
fixture=$(mktemp)
jq -n '[{type:"pull_request",parameters:{required_approving_review_count:0}}]' > "$fixture"
VERIFY_RULES_FIXTURE="$fixture" bash scripts/verify-branch-protection.sh
# Expected: exit 1, error message about count < 1
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | Issue #54: Required approving review count | Implemented main branch protection fix; verified with 4 synthesis criteria; PR #108 CI passed |
