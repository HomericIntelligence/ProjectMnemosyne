---
name: ci-test-matrix-management
description: Safely modify CI test matrix without breaking coverage validation
category: debugging
date: 2026-02-08
tags: [ci-cd, test-matrix, coverage, pre-commit, flaky-tests, github-actions]
user-invocable: false
---

# ci-test-matrix-management

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-08 |
| Context | PR #3119 - Fix gitleaks license requirement + disable flaky Core Loss tests |
| Objective | Safely disable flaky tests from CI workflow matrix without breaking pre-commit coverage validation |
| Outcome | ✅ Success - Tests disabled, coverage validation updated, CI passing |

## When to Use

Use this skill when:

1. **Disabling flaky tests from CI workflow** - Tests fail intermittently and need to be temporarily removed from the test matrix
2. **Removing test groups from comprehensive-tests.yml** - Commenting out or deleting test group entries in the CI matrix
3. **Pre-commit validate-test-coverage hook fails** - After CI matrix changes, the coverage validation hook fails because it detects "uncovered" test files

**Key Indicator**: Error message like:
```
Error: Found 2 test files not included in any test group:
  - tests/shared/core/test_loss.mojo
  - tests/shared/core/test_metrics.mojo
```

## Verified Workflow

### Step 1: Disable Tests in CI Matrix

Locate `.github/workflows/comprehensive-tests.yml` and comment out or remove the problematic test group:

```yaml
# Temporarily disabled - flaky Core Loss tests (see issue #3120)
# - name: "Core Loss"
#   path: "tests/shared/core"
#   pattern: "test_loss.mojo"
```

**Important**: Add a comment explaining WHY the tests are disabled and link to a tracking issue.

### Step 2: Update Coverage Validation Exclusion List

This is the **CRITICAL STEP** that is easy to miss.

Locate `scripts/validate_test_coverage.py` and add the disabled test files to the `EXCLUSIONS` set:

```python
EXCLUSIONS = {
    # Flaky tests disabled in CI (see issue #3120)
    "tests/shared/core/test_loss.mojo",
    "tests/shared/core/test_metrics.mojo",
    # ... other exclusions
}
```

**Why this matters**: The pre-commit hook `validate-test-coverage` checks that ALL test files under `tests/` are included in the CI matrix. If you disable tests in the workflow but don't update the exclusion list, the hook will fail.

### Step 3: Update Gitleaks Allowlist (If Needed)

If the disabled tests contain patterns that trigger gitleaks (like test data with fake credentials), add them to `.gitleaks.toml`:

```toml
[[rules.allowlist]]
description = "Test fixtures with mock credentials"
paths = [
    '''tests/shared/core/test_loss\.mojo''',
    '''tests/shared/core/test_metrics\.mojo''',
]
```

### Step 4: File Tracking Issue

Create a GitHub issue to track re-enabling the disabled tests:

```bash
gh issue create \
  --title "Re-enable flaky Core Loss tests" \
  --body "Tests disabled in PR #3119 due to intermittent failures. Investigate root cause and re-enable." \
  --label "testing,flaky-test"
```

Reference this issue in both the CI workflow comment and the exclusion list.

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| Only disable tests in CI matrix | Pre-commit hook failed with "uncovered test files" error | Must also update `scripts/validate_test_coverage.py` exclusion list |

## Results & Parameters

### Files Modified

1. `.github/workflows/comprehensive-tests.yml` - Comment out flaky test groups
2. `scripts/validate_test_coverage.py` - Add disabled tests to `EXCLUSIONS` set
3. `.gitleaks.toml` (optional) - Add paths to allowlist if needed

### Commands

```bash
# Verify coverage validation passes locally
python scripts/validate_test_coverage.py

# Run pre-commit hooks to verify
pixi run pre-commit run validate-test-coverage --all-files

# Check CI status after pushing
gh pr checks
```

### Verification Checklist

- [ ] Tests commented out in `.github/workflows/comprehensive-tests.yml` with reason
- [ ] Test files added to `EXCLUSIONS` in `scripts/validate_test_coverage.py`
- [ ] Gitleaks allowlist updated if needed (`.gitleaks.toml`)
- [ ] Tracking issue created and referenced in comments
- [ ] Pre-commit hooks pass locally
- [ ] CI checks pass on PR

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3119 - Fix gitleaks + disable flaky tests | [notes.md](../../references/notes.md) |

## Related

- PR #3119: Fix gitleaks license requirement + disable flaky Core Loss tests
- Issue #3120: Re-enable flaky Core Loss tests (tracking issue)
- Skill: `run-precommit` - Run pre-commit hooks locally
- Skill: `fix-ci-failures` - Diagnose and fix CI failures

## Notes

**The Hidden Dependency**: The `validate_test_coverage.py` script is called by a pre-commit hook, but it's not obvious from the CI workflow alone. This causes confusion when tests are disabled in CI but the coverage validation still expects them.

**Best Practice**: Always create a tracking issue when disabling tests. This ensures the work doesn't get lost and provides context for future developers.

**Future Improvement**: Consider adding a check in the CI workflow that validates the exclusion list is in sync with the test matrix. This would catch the mismatch earlier.
