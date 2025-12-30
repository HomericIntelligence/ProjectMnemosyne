---
name: gh-create-pr-linked
description: "Create PRs properly linked to GitHub issues"
category: tooling
source: ProjectOdyssey
date: 2025-12-30
---

# Create PR Linked to Issue

Create a pull request with automatic issue linking using `gh pr create --issue`.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2025-12-30 | Automate PR creation with proper issue linking | Consistent PR-issue relationships |

## When to Use

- (1) After completing implementation work for an issue
- (2) Ready to submit changes for review
- (3) Need to link PR to GitHub issue automatically
- (4) Starting from a feature branch named after the issue

## Verified Workflow

1. **Verify changes committed**: `git status` shows clean
2. **Push branch**: `git push -u origin branch-name`
3. **Create PR**: `gh pr create --issue <number>`
4. **Verify link**: Check issue's Development section on GitHub
5. **Monitor CI**: Watch checks with `gh pr checks`

## Results

Copy-paste ready commands:

```bash
# Create PR linked to issue (preferred)
gh pr create --issue <issue-number>

# With custom title and body
gh pr create --title "Title" --body "Closes #<issue-number>"

# Verify link appears
gh issue view <issue-number>  # Check Development section

# After creating PR
gh pr view <pr-number>
gh pr checks <pr-number>
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Used `--body "Closes #N"` without HEREDOC | Special characters broke the command | Use `gh pr create --body "$(cat <<'EOF'..."` for multiline |
| Created PR without pushing branch first | `gh pr create` failed with "no upstream" | Always `git push -u origin branch` before creating PR |
| Used issue number that didn't exist | PR created but not linked | Verify issue number with `gh issue view` first |
| Forgot to include "Closes #N" in any field | PR not linked to issue, didn't auto-close | Always use `--issue` flag or include "Closes #N" in body |

## Error Handling

| Problem | Solution |
|---------|----------|
| No upstream branch | `git push -u origin branch-name` |
| Issue not found | Verify issue number exists |
| Auth failure | Run `gh auth status` |
| Link not appearing | Add "Closes #ISSUE-NUMBER" to body |

## PR Requirements

- PR must be linked to GitHub issue
- All changes committed and pushed
- Branch has upstream tracking
- Clear, descriptive title
- Summary in description
- Do NOT create PR without issue link

## References

- GitHub CLI docs: https://cli.github.com/manual/gh_pr_create
- See gh-read-issue-context for getting issue details first
