---
name: "CI Test Failure Diagnosis"
description: "Systematic approach to diagnosing and fixing CI test failures in PRs"
category: ci-cd
date: 2026-02-02
user-invocable: false
---
# CI Test Failure Diagnosis

Systematic approach to diagnosing and fixing CI test failures in pull requests.

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-02 |
| **Objective** | Fix CI test failures in PR #336 |
| **Outcome** | ✅ Fixed pre-commit and pricing test failures<br>⚠️ Identified pre-existing CI environment issues |
| **Verified On** | PR #336 (paper-revision-workflow skill) |
| **Key Lesson** | Always distinguish PR-specific failures from pre-existing main branch issues |

## When to Use

Use this skill when:
- PR checks are failing in GitHub Actions
- Tests pass locally but fail in CI
- Need to determine if failures are caused by PR changes or pre-existing
- Multiple types of checks failing (pre-commit, unit tests, integration tests)

## Verified Workflow

### Phase 1: Initial Investigation (5 steps)

1. **Get PR check status**
   ```bash
   gh pr checks <PR_NUMBER>
   ```
   Identifies which checks are failing and provides direct links to logs.

2. **View detailed logs**
   ```bash
   gh run view --job=<JOB_ID> --log
   ```
   Downloads complete CI logs for analysis.

3. **Extract error messages**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -E "FAILED|ERROR|error" | head -20
   ```
   Quickly surfaces actual failure points.

4. **Search for specific error context**
   ```bash
   gh run view --job=<JOB_ID> --log | grep -B 10 -A 10 "<error_message>"
   ```
   Gets surrounding context for error understanding.

5. **Check if issue exists on main branch**
   ```bash
   gh run list --branch main --limit 5
   ```
   Determines if this is a PR-specific or pre-existing issue.

### Phase 2: Fix PR-Specific Issues

**Pre-commit failures (linting/formatting)**:

1. Extract exact violations from logs:
   ```bash
   grep -E "E501|D205|D209" <log_file>
   ```

2. Read the offending file:
   ```bash
   # Use Read tool to view lines around the error
   ```

3. Fix violations locally:
   - Line too long → Split into multiple lines
   - Docstring format → Add blank line, move closing quotes

4. Verify fix locally:
   ```bash
   ruff check <file_path>
   pre-commit run --all-files
   ```

5. Commit and push to PR branch (NOT main):
   ```bash
   git checkout <PR_BRANCH>
   git add <files>
   git commit -m "fix: <description>"
   git push
   ```

**Test assertion failures**:

1. Identify the specific test and assertion:
   ```
   tests/unit/config/test_pricing.py::test_with_cached_tokens - assert 0.0183 == 0.018
   ```

2. Read the test file to understand expectations:
   ```python
   # Look for pytest.approx() comparisons
   # Check what values are being asserted
   ```

3. Determine root cause:
   - Has the source code changed? (e.g., pricing values updated)
   - Are test expectations outdated?
   - Is this a precision/rounding issue?

4. Update test expectations or fix source code:
   ```python
   # Update expected values to match new behavior
   assert cost == pytest.approx(0.0183)  # Updated expectation
   ```

5. Run test locally to verify:
   ```bash
   pixi run pytest <test_path> -v
   # OR with specific environment:
   pixi run pytest <test_path> -v
   ```

### Phase 3: Identify Pre-Existing Issues

**Tests passing locally but failing in CI**:

1. Compare local vs CI environment:
   - Check pixi environment configuration in workflow file
   - Verify dependencies are installed in CI
   - Look for environment-specific configuration

2. Run tests with exact CI environment:
   ```bash
   pixi run -e <environment_name> pytest <test_path>
   ```

3. Check recent commits on main:
   ```bash
   git log --oneline --since="<last_success_date>" origin/main
   ```

4. Find last successful CI run:
   ```bash
   gh run list --branch main --workflow <workflow> --status success --limit 1
   ```

5. Document as pre-existing if:
   - Tests pass locally with correct environment
   - Main branch is also failing same tests
   - Issue exists before PR changes
   - Last successful run was days/weeks ago

## Failed Attempts & Lessons
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Committing directly to main

**What happened**: Accidentally committed fix to main branch instead of PR branch.

**Why it failed**:
- Main branch is protected and requires PR
- Would bypass code review
- Violates project workflow

**Fix applied**:
```bash
git reset --soft HEAD~1  # Undo commit
git stash                # Save changes
gh pr checkout <PR>      # Switch to PR branch
git stash pop            # Apply changes
git commit && git push   # Commit to PR branch
```

**Lesson**: Always verify current branch before committing:
```bash
git branch --show-current  # Check before commit
```

### ❌ Running tests without correct environment

**What happened**: Tests failed with `ModuleNotFoundError: No module named 'pandas'`

**Why it failed**:
- Analysis tests require `analysis` environment
- Default environment doesn't include numpy/pandas dependencies

**Fix applied**:
```bash
# Wrong:
pytest tests/unit/analysis/

# Correct:
pixi run pytest tests/unit/analysis/
```

**Lesson**: Check `pixi.toml` for feature-specific environments:
```toml
[feature.analysis.pypi-dependencies]
matplotlib = ">=3.8"
numpy = ">=1.24"
pandas = ">=2.0"

[environments]
analysis = { features = ["dev", "analysis"] }
```

### ⚠️ Trying to fix pre-existing main branch issues

**What happened**: Analysis tests failing in CI but passing locally.

**Investigation findings**:
- Tests pass: `pixi run pytest tests/unit/analysis/test_integration.py -v`
- CI uses correct environment (verified in `.github/workflows/test.yml`)
- Main branch has been failing for 24+ hours
- Functions don't write output files in CI but work locally

**Decision**: Document as pre-existing, don't attempt to fix in PR for unrelated changes.

**Lesson**:
- Distinguish PR-caused failures from pre-existing issues
- Check main branch CI history before spending time debugging
- Don't expand PR scope to fix unrelated issues

## Results & Parameters

### Successful Fixes

**1. Pre-commit (ruff) line length violations**

File: `tests/unit/e2e/test_tier_manager.py`

Before:
```python
# Line 805 (107 chars)
# Should raise because best_subtest is missing from result.json and best_subtest.json doesn't exist

# Line 810 (106 chars)
"""Test that build_merged_baseline falls back to best_subtest.json when result.json is missing."""
```

After:
```python
# Line 805-806
# Should raise because best_subtest is missing from result.json
# and best_subtest.json doesn't exist

# Line 810-813
"""Test that build_merged_baseline falls back to best_subtest.json.

When result.json is missing.
"""
```

Verification:
```bash
ruff check tests/unit/e2e/test_tier_manager.py
# Output: All checks passed!
```

**2. Pricing test cached token expectation**

File: `tests/unit/config/test_pricing.py:83-92`

Before:
```python
def test_with_cached_tokens(self) -> None:
    """Cost calculation with cached tokens (zero cost by default)."""
    cost = calculate_cost(
        tokens_input=1000,
        tokens_output=1000,
        tokens_cached=1000,
        model="claude-sonnet-4-5-20250929",
    )
    # Cached tokens have 0 cost by default
    assert cost == pytest.approx(0.018)
```

After:
```python
def test_with_cached_tokens(self) -> None:
    """Cost calculation with cached tokens (0.1x base cost)."""
    cost = calculate_cost(
        tokens_input=1000,
        tokens_output=1000,
        tokens_cached=1000,
        model="claude-sonnet-4-5-20250929",
    )
    # 1000 input * $3/M + 1000 output * $15/M + 1000 cached * $0.3/M
    # = $0.003 + $0.015 + $0.0003 = $0.0183
    assert cost == pytest.approx(0.0183)
```

Root cause: Pricing configuration was updated to include cached token costs ($0.3/M for Sonnet), but test expectations weren't updated.

Verification:
```bash
pixi run pytest tests/unit/config/test_pricing.py::TestCalculateCost::test_with_cached_tokens -v
# Output: PASSED
```

### Commands Cheat Sheet

```bash
# Get PR status
gh pr checks <PR_NUMBER>

# View workflow logs
gh run view <RUN_ID> --log
gh run view --job=<JOB_ID> --log

# Search logs for errors
gh run view --job=<JOB_ID> --log | grep -E "FAILED|ERROR"

# Check main branch CI history
gh run list --branch main --limit 5
gh run list --branch main --workflow test.yml --status success --limit 1

# Verify fixes locally
ruff check <file>
pre-commit run --all-files
pixi run pytest <test_path> -v
pixi run pytest tests/unit/analysis/ -v

# Fix workflow (when on wrong branch)
git branch --show-current
git reset --soft HEAD~1
git stash
gh pr checkout <PR>
git stash pop
git add <files> && git commit -m "fix: ..." && git push
```

## Key Takeaways

1. **Systematic investigation**: Don't jump to fixing - first understand what's failing and why
2. **Check main branch**: Always verify if issue exists on main before spending time debugging
3. **Use correct environment**: Check `pixi.toml` and workflow files for environment requirements
4. **Branch discipline**: Always verify current branch before committing
5. **Scope control**: Fix only issues caused by PR changes, document pre-existing issues
6. **Local verification**: Test all fixes locally before pushing to CI

## Related Skills

- `commit-commands:commit-push-pr` - Creating and managing PRs
- `pr-review-toolkit:review-pr` - Comprehensive PR review
- `safety-net:verify-custom-rules` - Pre-commit hook configuration
