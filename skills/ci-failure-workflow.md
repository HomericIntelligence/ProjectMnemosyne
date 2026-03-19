---
name: ci-failure-workflow
description: "Complex workflow for analyzing and fixing CI failures"
category: ci-cd
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: analyze
description: "Parse and analyze CI failure logs to identify root causes and error patterns"
user-invocable: false
---

# Analyze CI Failure Logs

Parse CI failure logs to identify root causes and categorize errors.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Systematic log analysis | Faster root cause identification |

## When to Use

- (1) CI builds fail and you need to understand why
- (2) Analyzing test failures from GitHub Actions
- (3) Extracting error messages from build artifacts
- (4) Identifying patterns in recurring failures

## Verified Workflow

1. **Collect logs**: Download CI artifacts or view workflow run output
2. **Extract errors**: Filter for error patterns (FAILED, ERROR, PANIC)
3. **Identify type**: Categorize error (compilation, test, timeout, dependency)
4. **Find root cause**: Trace back to source (line numbers, stack traces)
5. **Check context**: Compare with recent changes in PR
6. **Create summary**: Report findings with actionable next steps

## Results

Copy-paste ready commands:

```bash
# Download CI logs from artifact
gh run download <run-id> -D /tmp/ci-logs

# Extract from workflow run
gh run view <run-id> --log > /tmp/ci-output.log

# Grep for error patterns
grep -i "error\|failed\|panic\|exception" /tmp/ci-output.log

# Get summary of failures
tail -100 /tmp/ci-output.log | grep -A 5 "FAILED\|ERROR"

# View failed job output only
gh run view <run-id> --log-failed
```

### Error Category Patterns

**Compilation Errors**:
- Look for: `error:`, `undefined`, `type mismatch`
- Check: Syntax, imports, type annotations

**Test Failures**:
- Look for: `FAILED`, `AssertionError`, `ValueError`
- Check: Test logic, expected vs actual values

**Timeout Issues**:
- Look for: `timeout`, `timed out`, `hanging`
- Check: Long-running loops, infinite recursion

**Dependency Issues**:
- Look for: `not found`, `import failed`, `version conflict`
- Check: Package versions, environment setup

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Only looked at last 10 lines | Root cause was earlier in log | Search entire log for first occurrence of error |
| Grepped for "error" only | Missed "FAILED" and "panic" patterns | Use comprehensive pattern: `error\|failed\|panic\|exception` |
| Used `gh run view` for large logs | Output truncated | Download full artifact instead |
| Analyzed wrong workflow run | Fixed unrelated issue | Verify run-id matches the failing PR check |

## Output Format

Provide analysis with:

1. **Error Category** - Type of failure (compilation, test, timeout, dependency, environmental)
2. **Root Cause** - What line/code caused the failure
3. **Context** - Full error message and stack trace
4. **Related Changes** - Which PR changes might have caused it
5. **Remediation** - Recommended fix or investigation steps

## Error Handling

| Problem | Solution |
|---------|----------|
| Logs not accessible | Use `gh run view` to check permissions |
| Truncated logs | Download full artifact instead of view |
| Large log files | Use grep to extract relevant sections |
| Encoded artifacts | Unzip and decompress before analysis |

## Related Skills

- **fix** - Implement fixes after analysis

## References

- See batch-pr-ci-fix for fixing multiple PRs
- GitHub Actions docs: https://docs.github.com/en/actions

---
name: fix
description: "Diagnose and fix CI/CD failures systematically"
user-invocable: false
---

# Fix CI Failures

Diagnose and fix CI failures systematically.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Systematic CI debugging | Faster resolution of CI issues |

## When to Use

- (1) CI checks fail on PR
- (2) Tests pass locally but fail in CI
- (3) Need to debug CI issues
- (4) Workflow runs fail unexpectedly

## Verified Workflow

1. **Check status** - View failed PR checks
2. **Get logs** - Download or view failure details
3. **Reproduce** - Run same commands locally
4. **Fix issue** - Apply necessary changes
5. **Verify** - Test passes locally
6. **Push** - Commit and push fix
7. **Monitor** - Check CI passes

## Results

Copy-paste ready commands:

```bash
# 1. View CI status
gh pr checks <pr-number>

# 2. Get failure details
gh run view <run-id> --log-failed

# 3. Download logs for analysis
gh run download <run-id>

# 4. Reproduce issue locally
# Run the same commands that failed in CI

# 5. Push fix
git add .
git commit -m "fix: address CI failure"
git push

# 6. Monitor CI
gh pr checks <pr-number> --watch
```

### Common Failures

| Failure | Command | Fix |
|---------|---------|-----|
| Trailing whitespace | `pre-commit run --all-files` | Stage and re-commit |
| Test failure | `mojo test tests/` or `pytest` | Fix code, re-run tests |
| Markdown lint | `markdownlint --fix "**/*.md"` | Commit fixes |
| Build error | Check imports/deps | Update and rebuild |

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Fixed only one of multiple failures | PR still blocked on other failures | Address ALL failures before pushing |
| Assumed local pass means CI pass | Different environments caused mismatch | Always verify environment parity |
| Pushed fix without testing locally | Introduced new failure | Test locally before every push |
| Ignored flaky test | Flaky test caused future failures | Fix or skip flaky tests properly |

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| "Cannot find module" | Missing import or broken path | Fix import, check file structure |
| "Syntax error" | Invalid code | Correct syntax, test compile |
| "Test failed" | Logic error | Debug test, fix implementation |
| "Hook failed" | Formatting/whitespace | Run formatters, re-commit |

## Prevention

- Run pre-commit before pushing
- Run tests locally
- Check formatting before commit
- Review CI logs regularly

## Related Skills

- **analyze** - Parse CI logs to identify root cause

## References

- See batch-pr-ci-fix for fixing multiple PRs at once
- See run-precommit for running hooks locally
- See gh-check-ci-status for monitoring CI
