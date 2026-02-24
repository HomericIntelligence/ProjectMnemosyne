---
name: verify-pr-ready
description: "Verify PR is ready for merge with all requirements met"
category: ci-cd
date: 2025-12-30
---

# Verify PR Ready for Merge

Check that PR meets all requirements before merging.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Pre-merge validation checklist | Prevent broken merges |

## When to Use

- (1) Before merging a PR manually
- (2) Validating PR readiness in batch merge operations
- (3) Checking branch protection rule compliance
- (4) Before requesting final approval

## Verified Workflow

1. **View PR**: Get full PR details with `gh pr view <pr>`
2. **Check CI**: Verify all checks passing with `gh pr checks <pr>`
3. **Check reviews**: Confirm approvals with `gh pr view --json reviews`
4. **Check conflicts**: Test mergeability (mergeable field)
5. **Verify rules**: Check branch protection satisfaction
6. **Final validation**: Confirm all requirements met
7. **Report status**: Merge or identify blocking issues

## Results

Copy-paste ready commands:

```bash
# Check PR status
gh pr view <pr>

# Check CI status
gh pr checks <pr>

# View PR review status
gh pr view <pr> --json reviews

# Check for conflicts
gh pr view <pr> --json mergeable --jq '.mergeable'

# Get PR details as JSON
gh api repos/OWNER/REPO/pulls/<pr> --jq '{mergeable, merged, title}'

# Full readiness check
gh pr view <pr> --json state,mergeable,statusCheckRollup,reviews
```

## Readiness Checklist

Before merging, verify:

- [ ] All CI checks passing (no failures or pending)
- [ ] Required number of approvals received
- [ ] No requested changes from reviewers
- [ ] PR is linked to issue
- [ ] No merge conflicts detected
- [ ] Branch is up to date with main
- [ ] All branch protection rules satisfied
- [ ] Code review completed

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Merged with pending checks | CI failed after merge, broke main | Wait for ALL checks to complete, not just pass |
| Checked mergeable once at start | Conflict appeared from parallel merge | Re-check mergeable immediately before merge |
| Ignored "requested changes" status | Reviewer blocked merge | Address all requested changes before attempting merge |
| Merged stale branch | Introduced bugs already fixed in main | Ensure branch is up-to-date with base branch |

## Blocking Issues

PR cannot merge if:

- CI checks failing (pipeline errors or test failures)
- Merge conflicts exist (requires manual resolution)
- Required approvals not met (check branch protection rules)
- Requested changes pending (from required reviewers)
- Branch is stale (needs rebase on main)
- Protected rule violations (size, format, etc.)

## Error Handling

| Problem | Solution |
|---------|----------|
| Mergeable check fails | Rebase on main and resolve conflicts |
| CI pending | Wait for checks to complete |
| Approvals missing | Request review from required reviewers |
| Auth error | Check `gh auth status` permissions |
| PR not found | Verify PR number exists |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR merge validation workflow | Generic patterns applicable to any GitHub project |

## References

- See gh-check-ci-status for detailed CI verification
- See gh-batch-merge-by-labels for batch merge workflow
- GitHub CLI docs: https://cli.github.com/manual/gh_pr_view
