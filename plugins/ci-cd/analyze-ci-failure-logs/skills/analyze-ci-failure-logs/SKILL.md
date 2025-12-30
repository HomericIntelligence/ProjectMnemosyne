---
name: analyze-ci-failure-logs
description: "Parse and analyze CI failure logs to identify root causes and error patterns"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-30
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

## References

- See fix-ci-failures for implementing fixes
- See gh-check-ci-status for monitoring CI status
- GitHub Actions docs: https://docs.github.com/en/actions
