---
name: verify-pr-ready
description: "Verify a PR is ready for merge (CI passing, approvals, no conflicts). Use before merging to ensure all requirements met."
category: github
---

# Verify PR Ready for Merge

Check that PR meets all requirements before merging.

## When to Use

- Before merging a PR manually
- Checking if PR is ready for automated merge
- Before requesting final approval

## Quick Reference

```bash
# Check PR status
gh pr view <pr>

# Check CI status
gh pr checks <pr>

# View PR review status
gh pr view <pr> --json reviews

# Check for conflicts
gh pr view <pr> --json mergeable
```

## Readiness Checklist

Before merging, verify:

- [ ] All CI checks passing (no failures or pending)
- [ ] Required number of approvals received
- [ ] No requested changes from reviewers
- [ ] PR is linked to issue
- [ ] No merge conflicts detected
- [ ] Branch is up to date with main

## Blocking Issues

PR cannot merge if:

- CI checks failing
- Merge conflicts exist
- Required approvals not met
- Requested changes pending
- Branch is stale (needs rebase on main)

## References

- See CLAUDE.md for PR workflow
