---
name: gh-reply-review-comment
description: "Reply to PR review comments using correct GitHub API endpoint"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Reply to Review Comments

Reply to PR review comments using the correct GitHub API.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Reply to inline review comments correctly | Proper threaded discussions in PR |

## When to Use

- (1) Responding to inline code review feedback
- (2) Confirming fixes have been implemented
- (3) Need to reply to specific review comments (not general PR comments)
- (4) Updating reviewers on progress for specific feedback

## Verified Workflow

1. **Get comment IDs**: List all review comments
2. **Apply fixes**: Make the requested changes
3. **Reply to EACH comment**: Respond individually to each
4. **Verify replies**: Check they all posted successfully
5. **Monitor CI**: Ensure changes pass CI

## Results

Copy-paste ready commands:

```bash
# 1. Get comment ID
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | {id: .id, path: .path, body: .body}'

# 2. Reply to comment
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  --method POST -f body="Fixed - brief description"

# 3. Verify reply posted
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | select(.in_reply_to_id)'
```

Reply format (keep SHORT and CONCISE):
- `Fixed - Updated conftest.py to use real repository root`
- `Fixed - Deleted test file as requested`
- `Fixed - Removed markdown linting section`

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `gh pr comment <pr>` | Created new PR-level comment, not a reply thread | Must use API endpoint `/pulls/PR/comments/ID/replies` |
| Omitted `--method POST` | API returned error about method | Always include `--method POST` for creating replies |
| Used wrong comment ID format | 404 not found | Comment IDs are numeric, get from API response |
| Long multi-paragraph replies | Cluttered PR discussion | Keep to 1 line: "Fixed - [specific change]" |

## Critical: Two Types of Comments

**DO NOT confuse these**:

1. **PR-level comments** (general timeline): `gh pr comment`
2. **Review comment replies** (inline code): GitHub API (see above)

## Error Handling

| Problem | Solution |
|---------|----------|
| Comment ID invalid | Verify using API call |
| Permission denied | Check `gh auth status` |
| Reply fails | Verify PR and comment exist |
| Comment not found | Double-check ID format |

## Verification

After replying:

```bash
# Check replies appeared
gh api repos/OWNER/REPO/pulls/PR/comments \
  --jq '.[] | select(.in_reply_to_id) | {id: .id, body: .body}'

# Verify CI status
gh pr checks PR
```

## References

- See gh-get-review-comments for fetching comments first
- See gh-fix-pr-feedback for complete feedback workflow
- GitHub API docs: https://docs.github.com/en/rest/pulls/comments
