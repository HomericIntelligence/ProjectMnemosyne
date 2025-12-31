---
name: get-comments
description: "Retrieve all review comments from a pull request using GitHub API"
---

# Get PR Review Comments

Retrieve and analyze all review comments from a pull request.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Fetch and parse PR review comments | Structured feedback for efficient fixes |

## When to Use

- (1) Checking for unresolved review feedback
- (2) Analyzing reviewer feedback before fixing
- (3) Verifying all comments have been addressed
- (4) Getting comment IDs for replies

## Verified Workflow

1. **Fetch comments**: Use API to list all comments
2. **Parse output**: Extract IDs and feedback
3. **Analyze feedback**: Understand what needs fixing
4. **Plan fixes**: Decide how to address each comment
5. **Apply fixes**: Make the requested changes

## Results

Copy-paste ready commands:

```bash
# Get all review comments
gh api repos/OWNER/REPO/pulls/PR/comments

# Get comments with formatting
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | {id: .id, path: .path, body: .body}'

# Filter by reviewer
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | select(.user.login == "username")'

# Get only unresolved comments (top-level, not replies)
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | select(.in_reply_to_id == null)'

# Comments on specific file
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | select(.path == "src/file.mojo")'
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `gh pr view --comments` | Only shows PR timeline comments, not inline review comments | Use `gh api` with `/pulls/PR/comments` endpoint |
| Forgot to filter out replies | Got duplicate information, harder to track what needs addressing | Filter with `select(.in_reply_to_id == null)` for top-level only |
| Didn't extract comment IDs | Couldn't reply to specific comments later | Always include `.id` in jq output |
| Used wrong repo format in API | 404 error | Use `repos/OWNER/REPO` format, not just repo name |

## Output Format

Comments include:

- `id` - Comment ID (use for replies)
- `path` - File where comment was made
- `line` - Line number of comment
- `body` - Comment text
- `user` - Reviewer username
- `in_reply_to_id` - Parent comment ID (null if top-level)

## Error Handling

| Problem | Solution |
|---------|----------|
| PR not found | Verify PR number |
| Auth failure | Check `gh auth status` |
| No comments | API returns empty array (not an error) |
| Permission denied | Check authentication scopes |

## Related Skills

- **reply-comment** - Reply to individual comments
- **fix-feedback** - Full workflow to address all feedback

## References

- GitHub API docs: https://docs.github.com/en/rest/pulls/comments
