---
name: gh-batch-merge-by-labels
description: Batch merge multiple PRs by label matching
category: tooling
date: 2025-12-30
version: 1.0.0
---
# Batch Merge PRs by Label

Merge multiple PRs at once based on label matching.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Automate merging of multiple ready PRs | Reduced manual merge overhead |

## When to Use

- (1) Multiple PRs are ready for merge with same status label
- (2) End-of-sprint or release batch merges needed
- (3) Automating merge of dependent chain of PRs
- (4) Reducing manual merge overhead across team

## Verified Workflow

1. **Query PRs**: Find all PRs with target label
2. **Verify each**: Check CI status and approvals for each PR
3. **Check dependencies**: Ensure no conflicts between PRs to merge
4. **Sort by order**: Merge in dependency order if applicable
5. **Execute merges**: Merge each PR in sequence
6. **Verify success**: Confirm all PRs merged successfully
7. **Report results**: Summary of merged PRs

## Results

Copy-paste ready commands:

```bash
# List PRs with specific label
gh pr list --label "ready-to-merge" --state open

# Merge single PR
gh pr merge <pr> --squash --delete-branch

# Get PR numbers for batch merge
gh pr list --label "ready-to-merge" --json number --jq '.[].number'

# Merge all PRs with label (requires loop)
for pr in $(gh pr list --label "ready-to-merge" --json number --jq '.[].number'); do
  echo "Merging PR #$pr"
  gh pr merge "$pr" --squash --delete-branch
done
```

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Merge Options

**Squash Merge** (recommended):
- Combines all commits into single commit
- Clean git history
- `--squash` flag enables this

**Create Merge Commit**:
- Preserves all commits
- Clear merge history
- Default behavior without `--squash`

**Rebase and Merge**:
- Linear history
- `--rebase` flag enables this
- Good for feature branches

## Safety Checks

Before batch merging:

1. **CI Status**: All checks passing
2. **Approvals**: Required number of approvals met
3. **Conflicts**: No merge conflicts detected
4. **Dependencies**: No blocked dependencies
5. **Protected rules**: All branch protection rules satisfied

## Error Handling

| Problem | Solution |
|---------|----------|
| CI failing | Skip that PR, use analyze-ci-failure-logs |
| Merge conflict | Resolve manually, cannot batch merge |
| No permissions | Check gh auth status and repo access |
| Branch protection | Verify all required rules met |
| Network error | Retry with exponential backoff |

## References

- See gh-check-ci-status for CI verification
- See verify-pr-ready for pre-merge validation
- GitHub CLI docs: https://cli.github.com/manual/gh_pr_merge
