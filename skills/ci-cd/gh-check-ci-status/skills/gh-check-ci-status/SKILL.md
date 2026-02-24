---
name: gh-check-ci-status
description: "Check CI/CD status of a pull request including workflow runs and test results"
category: ci-cd
date: 2025-12-30
---

# Check CI Status

Verify CI/CD status of a pull request and investigate failures.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Efficiently monitor and debug CI status | Faster identification of CI failures |

## When to Use

- (1) Verifying PR checks are passing before merge
- (2) Investigating CI failures
- (3) Monitoring long-running CI jobs
- (4) Checking before pushing changes

## Verified Workflow

1. **Check status**: Run `gh pr checks <pr>` to see all checks
2. **Identify failures**: Look for X (failed) or O (pending)
3. **View logs**: Use `gh run view` to see failure details
4. **Fix locally**: Reproduce issue locally and test
5. **Push fix**: Commit and push changes
6. **Verify**: Watch CI with `--watch` flag

## Results

Copy-paste ready commands:

```bash
# Check PR CI status
gh pr checks <pr>

# Watch CI in real-time
gh pr checks <pr> --watch

# Get detailed status
gh pr view <pr> --json statusCheckRollup

# View failed logs
gh run view <run-id> --log-failed

# Rerun failed checks
gh run rerun <run-id>
```

### Status Indicators

- `PASS` - Check passed
- `FAIL` - Check failed
- `PENDING` - In progress
- `SKIPPED` - Check was skipped

### Common CI Failures

**Pre-commit issues** (formatting/linting):
```bash
just pre-commit-all  # Fix locally
git add . && git commit --amend --no-edit
git push --force-with-lease
```

**Test failures**:
```bash
mojo test tests/          # Run locally
pytest tests/             # Python tests
# Fix code and retest
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `gh pr checks` without `--watch` | Got stale status, checks were still running | Use `--watch` for real-time status updates |
| Checked status immediately after push | CI hadn't started yet, showed no checks | Wait 10-30 seconds or poll for workflow start |
| Looked only at summary status | Missed which specific check failed | Always drill down with `gh run view <id> --log-failed` |
| Reran all checks when one failed | Wasted CI time | Use `gh run rerun <id> --failed` to rerun only failed jobs |

## Error Handling

| Problem | Solution |
|---------|----------|
| No checks found | PR may not trigger CI (check workflow) |
| Pending forever | Check logs for stuck jobs |
| Auth error | Verify `gh auth status` |
| API rate limit | Wait or authenticate properly |

## Pre-Merge Verification

Before merging:

- [ ] All required checks passing
- [ ] No pending checks
- [ ] Latest commit has checks
- [ ] Branch up-to-date with base

```bash
gh pr checks <pr>          # All passing?
gh pr view <pr>            # Up-to-date?
gh pr diff <pr>            # Changes correct?
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | CI status monitoring workflow | Generic patterns applicable to any GitHub project |

## References

- See verify-pr-ready for complete pre-merge checklist
- See analyze-ci-failure-logs for debugging failures
- GitHub CLI docs: https://cli.github.com/manual/gh_pr_checks
