---
name: fix-ci-failures
description: "Diagnose and fix CI/CD failures systematically"
category: ci-cd
source: ProjectOdyssey
date: 2025-12-30
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

## References

- See run-precommit for running hooks locally
- See analyze-ci-failure-logs for log analysis
- See gh-check-ci-status for monitoring CI
