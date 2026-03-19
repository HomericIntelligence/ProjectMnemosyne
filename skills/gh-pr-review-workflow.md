---
name: gh-pr-review-workflow
description: "GitHub PR review workflow"
category: tooling
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: get-comments
description: "Retrieve all review comments from a pull request using GitHub API"
user-invocable: false
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

---
name: fix-feedback
description: "Address PR review feedback by making changes and replying to comments"
user-invocable: false
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

## Related Skills

- **get-comments** - Fetch all review comments first
- **reply-comment** - Reply syntax for individual comments

## References

- GitHub API docs: https://docs.github.com/en/rest/pulls/comments

---
name: reply-comment
description: "Reply to PR review comments using correct GitHub API endpoint"
user-invocable: false
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

## Related Skills

- **get-comments** - Fetch all review comments first
- **fix-feedback** - Full workflow to address all feedback

## References

- GitHub API docs: https://docs.github.com/en/rest/pulls/comments
