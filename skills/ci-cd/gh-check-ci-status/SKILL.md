---
name: gh-check-ci-status
description: "Check CI/CD status of a pull request including workflow runs and test results."
category: github
user-invocable: false
---

# Check CI Status

Verify CI/CD status of a pull request and investigate failures.

## When to Use

- Verifying PR is ready to merge
- Investigating CI failures
- Monitoring long-running CI jobs

### Quick Reference

```bash
# Check PR CI status
gh pr checks <pr>

# Watch CI in real-time
gh pr checks <pr> --watch

# View failed logs
gh run view <run-id> --log-failed

# Rerun failed checks
gh run rerun <run-id>
```

## Status Indicators

- `✓` - Passing
- `✗` - Failed
- `○` - Pending/In progress
- `-` - Skipped

## References

- See `.github/workflows/` for CI configuration
