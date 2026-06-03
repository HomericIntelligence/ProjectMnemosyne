# Implementation Notes: github-branch-protection-api-validation

## ProjectNestor Issue #54 Context

**Issue**: Enforce `required_approving_review_count >= 1` on main branch protection
**Repository**: HomericIntelligence/ProjectNestor
**PR**: #108
**Branch**: 54-auto-impl
**Commit**: b0d5e77 (fix(#54): require ≥1 approving review on main branch)

## Implementation Details

### Files Modified

1. **`.github/branch-protection/main.json`**
   - Added JSON configuration file to version control
   - Single-field approach: only specified `required_pull_request_reviews.required_approving_review_count: 1`
   - Minimal payload reduces API surface risk

2. **`scripts/apply-branch-protection.sh`**
   - Read-back validation implemented immediately after PUT
   - Fetches live state from `repos/{owner}/{repo}/branches/main/protection` endpoint
   - Compares `live_count` to `expected_count` from config
   - Exits non-zero if PUT silently failed

3. **`scripts/verify-branch-protection.sh`**
   - Environment variable hook for synthetic testing: `VERIFY_RULES_FIXTURE`
   - If set, reads from fixture file (for testing)
   - If unset, calls `gh api repos/{owner}/{repo}/rules/branches/main` (production)
   - Uses `>= 1` assertion to allow future tightening (1→2→3)

### API Field Name Mapping

The GitHub REST API for branch protection uses these field names in responses:
- Endpoint: `GET|PUT /repos/{owner}/{repo}/branches/{branch}/protection`
- Response field: `.required_pull_request_reviews.required_approving_review_count`

**Critical**: When setting the field via PUT, use same structure as GET response to ensure API recognizes it.

### Synthetic Testing Pattern

```bash
# Extract API fetch into overridable function
fetch_protection_rules() {
  if [ -n "${VERIFY_RULES_FIXTURE:-}" ]; then
    cat "$VERIFY_RULES_FIXTURE"
  else
    gh api "repos/${REPO}/branches/main/protection"
  fi
}

# Usage in test
fixture=$(mktemp)
jq -n '{required_pull_request_reviews:{required_approving_review_count:1}}' > "$fixture"
VERIFY_RULES_FIXTURE="$fixture" bash scripts/verify-branch-protection.sh
```

### Why This Matters

1. **Silent Failures**: GitHub API may accept PUT requests that ignore unknown fields or misspelled keys, returning HTTP 200 but not applying changes. Read-back validation is the only way to detect this.

2. **Forward Compatibility**: Using `>= 1` instead of `== 1` allows branch protection settings to be tightened (1→2 required reviews) without breaking drift detection scripts.

3. **Testability**: Environment variable injection allows bash governance scripts to be tested without network access, accelerating CI/CD feedback.

## Verification Criteria (All Passed)

1. **Syntax Check**: JSON config is valid, jq can parse it
2. **API Acceptance**: gh api PUT accepts config without errors
3. **Read-back Match**: Live setting matches config value
4. **Synthetic Test Pass**: Positive test case exits 0
5. **Synthetic Test Fail**: Negative test case exits non-zero

## Lessons for Future Branch Protection Changes

| Scenario | Pattern | Evidence |
|----------|---------|----------|
| Adding new field to branch protection | Use single-field change in separate PR | Issue #54: `required_approving_review_count` only, deferred `require_last_push_approval` |
| Changing existing enforcement | Use read-back validation + synthetic tests | apply-branch-protection.sh: GET immediately after PUT; verify-branch-protection.sh: env hook |
| Detecting drift on tightening rules | Use >= comparisons, not exact equality | verify-branch-protection.sh: `.required_approving_review_count >= 1` allows 1→2→3 |
| Testing governance scripts in CI | Inject fixture via environment variable | VERIFY_RULES_FIXTURE injected by test harness, script uses fixture-aware function |

## Related Commits in ProjectNestor

- **b0d5e77**: fix(#54): require ≥1 approving review on main branch (implements the pattern)
- **36cc497**: fix: Address CI failures for PR ProjectNestor#86 (earlier attempt with unverified fields)
- **cdcb08a**: ci(branch-protection): read effective rules instead of admin endpoint (API endpoint selection)

## References

- GitHub API: [Update branch protection](https://docs.github.com/en/rest/branches/branch-protection?apiVersion=2022-11-28#update-branch-protection)
- ProjectNestor governance: `docs/governance/branch-protection.md`
- gh CLI docs: [gh api](https://cli.github.com/manual/gh_api)
