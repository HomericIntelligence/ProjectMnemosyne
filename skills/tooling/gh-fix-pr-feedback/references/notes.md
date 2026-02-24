# References: gh-fix-pr-feedback

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR review workflow | Imported from ProjectOdyssey .claude/skills/gh-fix-pr-feedback |

## Source

Originally created for ProjectOdyssey to address PR review feedback systematically.

## Additional Context

This skill provides a complete workflow for:
1. Fetching all review comments using GitHub API
2. Analyzing feedback to understand requested changes
3. Making code changes
4. Committing changes with descriptive message
5. Replying to EACH comment individually
6. Pushing and verifying CI status

## Critical Points

- Must reply to review comments using the GitHub API (not `gh pr comment`)
- Reply format should be concise: `✅ Fixed - [brief description]`
- Must reply to EACH comment individually

## Related Skills

- gh-get-review-comments: For retrieving comments
- gh-reply-review-comment: For replying to specific comments
