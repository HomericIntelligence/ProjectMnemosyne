# PR Review Workflow - Notes

## Plugin Overview

This plugin consolidates 3 related PR review skills into a single coherent workflow:

1. **get-comments** - Fetch all review comments from a PR
2. **reply-comment** - Reply to individual review comments
3. **fix-feedback** - Complete workflow to address and reply to all feedback

## Typical Workflow

```
1. gh api repos/OWNER/REPO/pulls/PR/comments   (get-comments)
2. [make fixes to address each comment]
3. git add . && git commit -m "fix: address review feedback"
4. gh api .../comments/ID/replies -f body="Fixed - ..." (reply-comment)
5. git push && gh pr checks PR                  (fix-feedback completes)
```

## Key Insight

There are TWO types of PR comments:
- **PR-level comments**: Use `gh pr comment <pr>`
- **Review comment replies**: Use GitHub API `/pulls/PR/comments/ID/replies`

NEVER confuse these - the API endpoints are completely different.

## Consolidated From

This plugin was created by merging:
- `tooling/gh-get-review-comments`
- `tooling/gh-reply-review-comment`
- `tooling/gh-fix-pr-feedback`

## Source

- ProjectOdyssey development workflow
- Date: 2025-12-30
