# Issue Completion Verification

| **Attribute** | **Value** |
|---------------|-----------|
| **Date** | 2026-02-15 |
| **Objective** | Verify GitHub issue completion and manually close when PR auto-close automation fails |
| **Outcome** | Success - Issue #594 properly closed after detecting completed work |
| **Category** | workflow |
| **Confidence** | High |

## Overview

When working on GitHub issues, sometimes the automation that automatically closes issues when PRs are merged fails to trigger, leaving completed work marked as "open". This skill provides a systematic workflow to detect this situation and properly close the issue.

## When to Use This Skill

Use this skill when:

1. **Prompt file indicates work on an issue** (e.g., `.claude-prompt-594.md`)
2. **Branch name suggests issue number** (e.g., `594-auto-impl`)
3. **You suspect work may already be completed** but issue is still open
4. **Issue status doesn't match actual completion state**

## Trigger Conditions

- User provides a prompt file referencing an issue number
- Working directory is a git worktree for an issue branch
- Branch tracking shows "up to date with origin/main" but work seems done

## Verified Workflow

### 1. Read Issue Context

```bash
# Read the prompt file
cat .claude-prompt-594.md

# Get full issue details with all comments
gh issue view 594 --comments
```

**Key insight**: Issue comments often contain implementation plans and completion summaries that reveal if work is done.

### 2. Check Git History

```bash
# Check recent commits on current branch
git log --oneline -10

# Search for commits mentioning the issue
git log origin/main --oneline --grep="594" -5

# Check if specific commit is on main
git log origin/main --stat <commit-hash>
```

**Key insight**: If commits with "Closes #594" are already on `origin/main`, the work is complete.

### 3. Check for Merged PRs

```bash
# Search for PRs related to the issue
gh pr list --search "594" --state all --limit 10 --json number,title,state,mergedAt

# Check specific PR for issue linking
gh pr view 680 --json body,closingIssuesReferences
```

**Key insight**: The `closingIssuesReferences` field confirms GitHub detected the "Closes #594" syntax, even if automation failed to close it.

### 4. Verify Issue State

```bash
# Check current issue state
gh issue view 594 --json state,closedAt
```

**Expected**: If `state: "OPEN"` but PR merged with `closingIssuesReferences`, automation failed.

### 5. Manually Close Issue

```bash
gh issue close 594 --comment "All HIGH priority fixes from the code quality audit have been implemented and merged via PR #680.

**Completed in PR #680:**
- ✅ Created tracking issues #670-679
- ✅ Increased test coverage threshold to 80%
- ✅ Fixed model config naming inconsistencies

**Remaining Work:**
- Issues #670-679 track MEDIUM and LOW priority items

This tracking issue is now complete."
```

**Key insight**: Include summary of completed work and reference to tracking issues for remaining items.

### 6. Clean Up

```bash
# Remove prompt file
rm .claude-prompt-594.md

# Verify clean state
git status
```

## Failed Attempts

### ❌ Attempting to Create PR for Already-Merged Work

**Tried**: Creating a new PR from the branch when commits were already on main

**Why it failed**:

- Branch tracking showed `[origin/main]` instead of `[origin/594-auto-impl]`
- The work had already been merged via PR #680
- Creating a duplicate PR would fail with "no changes to merge"

**Lesson**: Always check git history and search for merged PRs **before** attempting to create a new PR.

### ❌ Assuming Issue Auto-Closes from Commit Message

**Tried**: Assuming "Closes #594" in commit message would auto-close the issue

**Why it failed**:

- GitHub's auto-close only triggers when PRs are merged via the GitHub UI
- Direct pushes to main (bypassing PR) don't trigger auto-close
- Sometimes GitHub's automation simply fails for unknown reasons

**Lesson**: Always verify issue state after PR merge, even if "Closes #XXX" syntax was used correctly.

## Results & Parameters

### Commands Used

```bash
# Issue investigation
gh issue view 594 --comments
gh issue view 594 --json state,closedAt

# Git history analysis
git log --oneline -10
git log origin/main --grep="594"
git show --stat 9c9b911

# PR analysis
gh pr list --search "594" --state all --limit 10 --json number,title,state,mergedAt
gh pr view 680 --json body,closingIssuesReferences

# Issue closure
gh issue close 594 --comment "<summary>"

# Cleanup
rm .claude-prompt-594.md
```

### Success Indicators

- ✅ Issue state changed from `OPEN` to `CLOSED`
- ✅ `closedAt` timestamp populated
- ✅ Closing comment documents completion
- ✅ Working directory clean (prompt file removed)

## Edge Cases

1. **Work done but not pushed**: Check `git status` and local commits before searching main
2. **Multiple PRs for same issue**: Use `--state all` when searching PRs
3. **Issue intentionally kept open**: Check issue comments for tracking/epic status
4. **Worktree cleanup needed**: The branch may still exist as a worktree even after merge

## Related Skills

- `commit-commands:commit-push-pr` - Creating PRs (when work isn't done)
- `commit-commands:clean_gone` - Cleaning up merged branches and worktrees
- `github-issue-workflow` - Reading and updating GitHub issues

## Integration with Existing Workflows

This skill complements the standard PR workflow documented in `.claude/shared/pr-workflow.md`. Use it as a **pre-flight check** before starting work on an issue:

```bash
# 1. Check if work is already done
gh issue view <number> --comments
git log origin/main --grep="<number>"

# 2. If not done, proceed with normal workflow
git checkout -b <number>-description
# ... implement changes ...

# 3. If already done, close issue and clean up
gh issue close <number> --comment "..."
rm .claude-prompt-<number>.md
```

## Confidence Level

**High** - This workflow successfully identified completed work, verified PR merge, and properly closed the orphaned issue. The pattern is reproducible for any situation where GitHub's auto-close automation fails.

## Tags

`github`, `workflow`, `automation`, `issue-tracking`, `pr-management`, `git-history`
