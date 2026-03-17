---
name: gh-fix-pr-feedback
description: "Address PR review feedback by making changes and replying to comments."
category: github
---

# Fix PR Review Feedback

Address PR review comments by implementing fixes and responding to each comment.

## When to Use

- PR has open review comments requiring responses
- Ready to implement reviewer's requested changes
- PR is blocked on feedback

### Quick Reference

```bash
# 1. Get all review comments
gh api repos/OWNER/REPO/pulls/PR/comments --jq '.[] | {id: .id, path: .path, body: .body}'

# 2. Make fixes to code, then test
pixi run test

# 3. Commit changes
git add . && git commit -m "fix: address PR review feedback"

# 4. Reply to EACH comment
gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies \
  --method POST -f body="Fixed - [brief description]"

# 5. Push and verify
git push
gh pr checks PR
```

## Reply Format

Keep responses SHORT (1 line preferred):

- `Fixed - Updated parser to handle negative IDs`
- `Fixed - Removed duplicate test`
- `Fixed - Added error handling for edge case`

## Verification

After addressing feedback:

- [ ] All review comments have replies
- [ ] Changes committed and pushed
- [ ] CI checks passing
- [ ] No new issues introduced

## References

- See CLAUDE.md for PR workflow
