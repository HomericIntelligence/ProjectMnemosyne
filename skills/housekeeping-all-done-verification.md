---
name: housekeeping-all-done-verification
description: 'Verify external state for pure housekeeping issues where all cleanup
  may already be complete. Use when: issue describes git branch/worktree/GitHub closure
  tasks, all target artifacts may already be cleaned up, and an empty verification
  PR is needed to close the issue.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Housekeeping All Done Verification

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-07 |
| **Objective** | Implement GitHub issue #3377 — clean up `issue-2722` worktree/branch after PR #3372 merged |
| **Outcome** | All cleanup already complete; created verification comment + empty commit + PR to close issue |
| **Root Cause** | Housekeeping was done out-of-band (by the system that merged PR #3372); issue just needed formal closure |
| **Key Learning** | Pure housekeeping issues need external state verification (GitHub API + git ls-remote), not code changes |

## When to Use

Use this workflow when an issue describes **pure housekeeping** with no code deliverables:

- Issue asks to delete a git branch or remove a worktree
- Issue asks to close another GitHub issue
- Issue asks to verify a PR was merged and artifacts cleaned up
- The issue body says "clean up", "close", "remove", or "delete" referring to git/GitHub artifacts
- No source code files are created or modified

## Verified Workflow

### Step 1: Confirm Prerequisites

```bash
# Confirm the prerequisite PR is merged
gh pr view <PR-number> --json state,mergedAt,mergeCommit

# Update local refs
git fetch origin
```

If the prerequisite PR is not yet merged, **stop** and post a comment explaining the dependency.

### Step 2: Check All Target Artifacts

```bash
# Check worktree existence
git worktree list | grep <issue-name>

# Check local branch existence
git branch -a | grep <branch-name>

# Check remote branch existence
git ls-remote --heads origin <branch-name>

# Check GitHub issue state
gh issue view <issue-number> --json state
```

Collect results for each artifact. Document which are already gone.

### Step 3: Perform Any Remaining Cleanup

If any artifact still exists, clean it up following the plan:

```bash
# Remove worktree (if present)
git worktree remove .worktrees/<name>
git worktree prune

# Delete local branch (if present)
git branch -d <branch-name>

# Delete remote branch (if present)
git push origin --delete <branch-name>
git remote prune origin

# Close GitHub issue (if open)
gh issue close <number> --comment "Closing as superseded by ..."
```

### Step 4: Post Verification Comment

Always post a summary comment on the tracking issue:

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Cleanup Verification

- ✅ PR #<N> merged — <description>
- ✅ Issue #<N> closed — <reason>
- ✅ `<branch-name>` branch deleted — confirmed absent
- ✅ `<worktree-path>` worktree removed — not present in worktree list

No further action required.
EOF
)"
```

### Step 5: Create Empty Verification Commit + PR

Since there are no code changes, use an empty commit to have something to push:

```bash
# Create empty commit
git commit --allow-empty -m "chore(cleanup): verify <description>

<summary of what was verified>

Closes #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and create PR
git push -u origin <branch-name>

gh pr create \
  --title "chore(cleanup): verify <description>" \
  --body "$(cat <<'EOF'
## Summary

Verification task for issue #<N>. All cleanup was already complete:

- <artifact 1> — <status>
- <artifact 2> — <status>

No code changes were required.

Closes #<N>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" \
  --label "cleanup"

gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Searching for code to change | Initially looked for source files related to `__hash__` | No code changes needed — pure git/GitHub cleanup task | Read issue category first; "clean up worktree/branch" = no code |
| Trying to delete the branch locally | Ran `git branch -d issue-2722` | Branch didn't exist locally — already gone | Check `git branch -a` AND `git ls-remote` for both local + remote |

## Results & Parameters

### Exact Commands Used (Issue #3377)

```bash
# Step 1: Verify PR #3372 state
gh pr view 3372 --json state,mergedAt,mergeCommit
# Result: {"state":"MERGED","mergedAt":"2026-03-07T07:10:46Z","mergeCommit":{"oid":"cad626a4..."}}

# Step 2: Check worktree
git worktree list | grep 2722
# Result: (empty — worktree already removed)

# Step 3: Check branches (local + remote)
git fetch origin
git branch -a | grep issue-2722
git ls-remote --heads origin issue-2722
# Result: (empty — branch already deleted everywhere)

# Step 4: Check GitHub issue state
gh issue view 2722 --json state
# Result: {"state":"CLOSED"}

# Step 5: Post verification comment
gh issue comment 3377 --body "## Cleanup Verification..."
# Result: https://github.com/.../issues/3377#issuecomment-4017741494

# Step 6: Empty commit + PR
git commit --allow-empty -m "chore(cleanup): verify issue-2722 branch cleanup post PR #3372 merge..."
git push -u origin 3377-auto-impl
gh pr create --title "chore(cleanup): verify ..." --body "..."
gh pr merge --auto --rebase 4044
```

### Total Steps

- 6 verification commands
- 0 code changes
- 1 empty commit (required to have something to push)
- 1 PR created with auto-merge

### Key Insight: `--allow-empty` Commit

When a housekeeping issue has no code deliverables, use `git commit --allow-empty` to create
a commit for the PR. This is the correct pattern for tracking-only work. Pre-commit hooks
will skip all checks (no files to check = Skipped for all hooks).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3377, branch `3377-auto-impl`, PR #4044 | Verifying cleanup of `issue-2722` worktree/branch after PR #3372 merged |

## Related Skills

- `cleanup-task-already-done-on-branch` — When a deletion task was already done in a prior git commit
- `worktree-prompt-already-done` — When auto-impl pipeline already ran for this branch
- `issue-completion-verification` — Close orphaned GitHub issues
- `git-worktree-cleanup` — Manual worktree removal workflow
