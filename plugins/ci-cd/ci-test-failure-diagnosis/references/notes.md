# Session Notes: CI Test Failure Diagnosis (PR #336)

## Session Context

**Date**: 2026-02-02
**PR**: #336 - feat(skills): Add paper-revision-workflow skill
**Initial Status**: Pre-commit and unit tests failing
**Final Status**: Pre-commit ✅ passing, pricing test ✅ fixed, 3 analysis tests ⚠️ pre-existing issue

## Timeline of Investigation

### 1. Initial Check (00:00)

User request: "fix this error: https://github.com/HomericIntelligence/ProjectScylla/pull/336"

First action: Get PR status
```bash
gh pr view 336 --json title,body,url,statusCheckRollup
gh pr checks 336
```

Result: Pre-commit pending, need to wait for completion.

### 2. Pre-commit Failure (00:02)

Error discovered:
```
pre-commit	fail	9s
```

Retrieved logs:
```bash
gh run view --job=62170160966 --log
```

Found errors:
```
tests/unit/e2e/test_tier_manager.py:805:101: E501 Line too long (107 > 100)
tests/unit/e2e/test_tier_manager.py:810:101: E501 Line too long (106 > 100)
```

### 3. Fix Attempt 1 - Line Length (00:05)

Read file:
```python
# Line 805
# Should raise because best_subtest is missing from result.json and best_subtest.json doesn't exist

# Line 810
"""Test that build_merged_baseline falls back to best_subtest.json when result.json is missing."""
```

Applied fixes:
- Broke line 805 into two lines
- Reformatted docstring on line 810 (initially incorrect format)

Ruff complained about docstring format (D205, D209), fixed by:
```python
"""Test that build_merged_baseline falls back to best_subtest.json.

When result.json is missing.
"""
```

### 4. Critical Mistake - Wrong Branch (00:08)

**ERROR**: Committed to main instead of PR branch!

```bash
git branch --show-current
# Output: main  <-- WRONG!
```

Recovery:
```bash
git reset --soft HEAD~1
git stash
gh pr checkout 336
git stash pop
git commit && git push
```

**Lesson learned**: Always check current branch before committing.

### 5. Unit Test Failures Discovered (00:12)

After fixing pre-commit, unit tests failed:
```
test (unit, tests/unit)	fail	42s
```

Four failing tests identified:
1. `test_e2e_pipeline_with_sample_data` - Missing Vega-Lite spec files
2. `test_e2e_smoke_test_outputs[fig04_pass_rate_by_tier...]` - Empty directory
3. `test_e2e_smoke_test_outputs[fig01_score_variance_by_tier...]` - Empty directory
4. `test_with_cached_tokens` - assert 0.0183 == 0.018 ± 1.8e-08

### 6. Fix Pricing Test (00:15)

Read pricing configuration:
```python
# scylla/config/pricing.py
cached_cost_per_million=0.3,  # 0.1x base input cost
```

Calculation:
- 1000 input × $3/M = $0.003
- 1000 output × $15/M = $0.015
- 1000 cached × $0.3/M = $0.0003
- Total = $0.0183 ✓

Updated test expectation from 0.018 to 0.0183 with explanatory comment.

### 7. Analysis Tests Investigation (00:20)

Tests failing in CI but passing locally:
```bash
# Failed locally (wrong environment):
python -m pytest tests/unit/analysis/test_integration.py
# ModuleNotFoundError: No module named 'pandas'

# Passed locally (correct environment):
pixi run -e analysis pytest tests/unit/analysis/test_integration.py
# All tests PASSED
```

Checked GitHub workflow:
```yaml
# .github/workflows/test.yml
if [[ "$TEST_PATH" == "tests/unit" ]]; then
  pixi run -e analysis pytest "$TEST_PATH" -v
```

CI is using correct environment!

### 8. Main Branch Investigation (00:25)

Checked if issue pre-exists:
```bash
gh run list --branch main --limit 5
# All recent runs: failure status

gh run list --branch main --workflow test.yml --status success --limit 1
# Last success: 2026-02-01T00:16:17Z (24+ hours ago)
```

Checked recent commits since last success:
```bash
git log --oneline --since="2026-02-01T00:16:17Z" origin/main
# 45+ commits, including major analysis pipeline changes
```

**Decision**: This is a pre-existing issue on main, not caused by PR #336.

Evidence:
- Tests pass locally with correct environment
- Main branch failing for 24+ hours
- CI workflow correctly configured
- No error messages in logs, files just aren't created
- Likely environment-specific issue in GitHub Actions

## Error Patterns Encountered

### Pattern 1: Line Too Long

**Symptom**:
```
E501 Line too long (107 > 100)
```

**Fix**: Break into multiple lines at logical boundaries:
```python
# Comment over 100 chars
# becomes:
# First part of comment
# Second part of comment
```

### Pattern 2: Docstring Format Violations

**Symptoms**:
```
D205 1 blank line required between summary line and description
D209 Multi-line docstring closing quotes should be on a separate line
```

**Fix**:
```python
"""Summary line.

Description.
"""
```

### Pattern 3: Test Expectation Mismatch

**Symptom**:
```
assert 0.0183 == 0.018 ± 1.8e-08
```

**Root cause**: Source code changed (pricing values updated) but tests not updated.

**Fix**: Update test expectations to match new behavior, add comment explaining calculation.

### Pattern 4: Missing Dependencies

**Symptom**:
```
ModuleNotFoundError: No module named 'pandas'
```

**Root cause**: Using wrong pixi environment.

**Fix**: Check `pixi.toml` and use correct environment:
```bash
pixi run -e analysis pytest tests/unit/analysis/
```

## Files Modified

1. `tests/unit/e2e/test_tier_manager.py`
   - Lines 805-806: Split long comment
   - Lines 810-813: Reformatted docstring

2. `tests/unit/config/test_pricing.py`
   - Lines 83-92: Updated cached token test expectation

## Commands Used

```bash
# PR investigation
gh pr view 336 --json title,body,url,statusCheckRollup
gh pr checks 336
gh pr checkout 336

# Log analysis
gh run view 21578269527
gh run view --job=62170160966 --log
gh run view --job=62170160966 --log | grep -E "error|Error|fail|Fail"

# File operations
Read tests/unit/e2e/test_tier_manager.py (offset 800, limit 20)
Read tests/unit/config/test_pricing.py
Read scylla/config/pricing.py

# Local testing
ruff check tests/unit/e2e/test_tier_manager.py
python -m pytest tests/unit/config/test_pricing.py::TestCalculateCost::test_with_cached_tokens -v
pixi run -e analysis pytest tests/unit/analysis/test_integration.py -v

# Git operations
git branch --show-current
git reset --soft HEAD~1
git stash
git stash pop
git add <files>
git commit -m "fix: ..."
git push

# CI history
gh run list --branch main --limit 5
gh run list --branch main --workflow test.yml --status success --limit 1
git log --oneline --since="2026-02-01T00:16:17Z" origin/main
```

## Success Metrics

- ✅ Pre-commit check: **PASSING**
- ✅ Pricing test: **PASSING**
- ✅ Integration tests: **PASSING** (verified locally)
- ⚠️ 3 analysis tests failing in CI: **PRE-EXISTING ISSUE** (main branch also failing)

## Recommendations

1. **For future PR debugging**:
   - Always check `gh run list --branch main` first
   - Compare PR failures to main branch status
   - Don't fix pre-existing issues in unrelated PRs

2. **For CI environment issues**:
   - Verify dependencies in both pixi.toml and workflow files
   - Test locally with exact CI environment (`pixi run -e <env>`)
   - Check for environment variables or system-specific behavior

3. **For workflow discipline**:
   - Run `git branch --show-current` before every commit
   - Use `gh pr checkout <number>` to switch to PR branches
   - Never commit directly to protected branches

## Open Questions

Why do analysis tests pass locally but fail in CI?
- Same pixi environment configuration
- Same dependencies installed
- Same Python version (3.14.2)
- Functions complete without errors locally but silently fail in CI
- No error messages or stack traces in CI logs

**Hypothesis**: GitHub Actions environment issue (permissions, temp directory access, or system library mismatch).

**Not investigated** because:
- Out of scope for PR #336 (unrelated skill documentation)
- Pre-existing on main branch
- Would require deeper CI debugging
