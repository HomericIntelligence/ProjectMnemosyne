---
name: gh-fix-pr-feedback
description: "Address PR review feedback by making changes and replying to comments"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Fix PR Review Feedback

Address PR review comments by implementing fixes and responding to each comment.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Efficiently address reviewer feedback | Faster PR approval cycles |

## When to Use

- (1) PR has open review comments requiring responses
- (2) Ready to implement reviewer's requested changes
- (3) Need to notify reviewers of fixes
- (4) PR is blocked on feedback

## Verified Workflow

1. **Fetch review comments**: List all comments requiring response
2. **Analyze feedback**: Understand all requested changes
3. **Make changes**: Edit code to address each comment
4. **Run tests**: Verify fixes pass locally
5. **Commit changes**: Create single focused commit
6. **Reply to comments**: Reply to EACH comment individually (critical!)
7. **Push and verify**: Push changes and check CI status

## Results

Copy-paste ready commands:

```bash
# 1. Get all review comments
gh api repos/OWNER/REPO/pulls/PR/comments --jq '.[] | {id: .id, path: .path, body: .body}'

# 2. Make fixes to code
# [edit files, test, format]

# 3. Commit changes
git add . && git commit -m "fix: address PR review feedback"

# 4. Reply to EACH comment
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  --method POST -f body="Fixed - [brief description]"

# 5. Push and verify
git push
gh pr checks PR
```

Reply format (keep SHORT):
- `Fixed - Updated conftest.py to use real repository root`
- `Fixed - Removed duplicate test file`
- `Fixed - Added error handling for edge case`

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `gh pr comment` for inline replies | Created new general comment, not a reply to the review comment | Use GitHub API `POST /repos/.../pulls/.../comments/.../replies` for inline replies |
| Replied with long explanations | Cluttered the PR, harder to track fixes | Keep replies to 1 line: "Fixed - [what changed]" |
| Pushed before replying to comments | Reviewer didn't know which comments were addressed | Reply to each comment THEN push |
| Addressed only some comments | PR still blocked, wasted review cycle | Address ALL comments before requesting re-review |

## Error Handling

| Problem | Solution |
|---------|----------|
| Comment ID invalid | Verify ID using API |
| Auth failure | Run `gh auth status` |
| Reply not appearing | Check API endpoint syntax |
| CI fails after push | Review logs and fix issues |

## Critical: Two Types of Comments

**PR-level comments** (general timeline):
```bash
gh pr comment <pr> --body "Response"
```

**Review comment replies** (inline code feedback):
```bash
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  --method POST -f body="Fixed - description"
```

NEVER confuse these - use the correct API for review comments.

## References

- See gh-get-review-comments for fetching comments
- See gh-reply-review-comment for reply syntax
- GitHub API docs: https://docs.github.com/en/rest/pulls/comments
