---
name: gh-create-pr-linked
description: "Create linked GitHub PRs"
category: ci-cd
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: gh-create-pr-linked
description: "Create a pull request properly linked to a GitHub issue using gh pr create. Use when creating a PR that implements or addresses a specific issue."
category: github
---

# Create PR Linked to Issue

Create a pull request with automatic issue linking.

## When to Use

- After completing implementation work
- Ready to submit changes for review
- Need to link PR to GitHub issue

### Quick Reference

```bash
# Create PR linked to issue (preferred)
gh pr create --title "Title" --body "Closes #<issue-number>"

# Verify link appears
gh issue view <issue-number>  # Check Development section
```

## Workflow

1. **Verify changes committed**: `git status` shows clean
2. **Push branch**: `git push -u origin branch-name`
3. **Create PR**: `gh pr create --title "Title" --body "Closes #<number>"`
4. **Verify link**: Check issue's Development section on GitHub
5. **Monitor CI**: Watch checks with `gh pr checks`

## PR Requirements

- PR must be linked to GitHub issue
- All changes committed and pushed
- Branch has upstream tracking
- Clear, descriptive title
- Do NOT create PR without issue link

## Error Handling

| Problem | Solution |
|---------|----------|
| No upstream branch | `git push -u origin branch-name` |
| Issue not found | Verify issue number exists |
| Auth failure | Run `gh auth status` |
| Link not appearing | Add "Closes #ISSUE-NUMBER" to body |

## Branch Naming Convention

Format: `<issue-number>-<description>`

Examples:

- `42-add-bracket-parser`
- `73-fix-graph-layout`

## References

- See CLAUDE.md for complete git workflow
