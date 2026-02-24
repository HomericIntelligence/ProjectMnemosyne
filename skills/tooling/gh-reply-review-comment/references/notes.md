# References: gh-reply-review-comment

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR review workflow | Imported from ProjectOdyssey .claude/skills/gh-reply-review-comment |

## Source

Originally created for ProjectOdyssey to reply to PR review comments using the correct GitHub API.

## Additional Context

This skill emphasizes the critical distinction between:
1. PR-level comments (general timeline): Use `gh pr comment`
2. Review comment replies (inline code): Use GitHub API

## API Endpoint for Replies

```bash
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  --method POST -f body="✅ Fixed - brief description"
```

## Reply Format Guidelines

Keep responses SHORT and CONCISE (1 line preferred):
- Good: `✅ Fixed - Updated conftest.py to use real repository root`
- Bad: Long explanations, defensive responses, multiple paragraphs

## Related Skills

- gh-get-review-comments: For retrieving comment IDs
- gh-fix-pr-feedback: For complete feedback workflow
