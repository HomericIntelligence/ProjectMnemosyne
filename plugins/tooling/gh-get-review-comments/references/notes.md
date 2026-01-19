# References: gh-get-review-comments

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR review workflow | Imported from ProjectOdyssey .claude/skills/gh-get-review-comments |

## Source

Originally created for ProjectOdyssey to retrieve PR review comments using GitHub API.

## Additional Context

This skill uses the GitHub API to retrieve review comments with:
- Comment ID (for replies)
- File path (where comment was made)
- Line number
- Comment body
- Reviewer username
- Parent comment ID (for threading)

## API Endpoint

```bash
gh api repos/OWNER/REPO/pulls/PR/comments
```

## Filtering Examples

- Filter by file: `.[] | select(.path == "src/file.mojo")`
- Filter by reviewer: `.[] | select(.user.login == "reviewer")`
- Only top-level comments: `.[] | select(.in_reply_to_id == null)`

## Related Skills

- gh-reply-review-comment: For replying to comments
- gh-fix-pr-feedback: For complete feedback workflow
