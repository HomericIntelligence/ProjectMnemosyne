---
name: cleanup-task-already-done-on-branch
description: 'Detect when a cleanup/deletion task was already completed in a prior
  commit on the current branch. Use when: working on a cleanup issue in an auto-impl
  worktree, the target file is already missing, or a PR exists but the commit history
  shows the work already happened.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Cleanup Task Already Done on Branch

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Implement GitHub issue #3066 - delete deprecated `benchmarks/__init__.mojo` |
| **Outcome** | File already deleted in commit `98f5ce44` on the branch; PR #3263 already open |
| **Root Cause** | Auto-impl worktree was created after the deletion commit was already made |
| **Key Learning** | For deletion/cleanup tasks, check `git log` and file existence BEFORE attempting implementation |

## When to Use

Use this pre-flight check for cleanup/deletion issues when:

- Working in an auto-impl worktree (branch named `<issue-number>-auto-impl`)
- Issue asks to delete a file, remove deprecated code, or clean up artifacts
- The target file is not found in the working tree
- A PR already exists for the branch

## Verified Workflow

### Step 1: Check if Target Already Gone

```bash
# For file deletion tasks - check if file exists
ls <target-file>
# OR
cat .claude-prompt-<issue>.md   # read the issue to find the target path

# Then check:
ls path/to/deprecated/file.mojo
# If "No such file" -> it may already be deleted
```

### Step 2: Check Git History for the Deletion

```bash
# Check recent commits on current branch
git log --oneline -10

# Search for commits mentioning the file or issue
git log --oneline --all --grep="<filename>"
git log --oneline --all --grep="#<issue-number>"
```

If a commit message like `chore: delete deprecated <file>` appears, the work is done.

### Step 3: Verify No Remaining References

```bash
# Ensure nothing still imports or references the deleted file
# (adjust extension and path as needed)
grep -r "benchmarks/__init__" . --include="*.mojo"
grep -r "from benchmarks import" . --include="*.mojo"
```

Zero matches confirms the deletion is complete and safe.

### Step 4: Check for Existing PR

```bash
# Check if a PR already exists for this branch
gh pr list --head <branch-name>
# OR
gh pr list --search "<issue-number>"
```

If a PR exists and the commit is already on the branch, the task is complete.

### Step 5: Report and Stop

Once confirmed:
1. Report findings to the user — the issue is already resolved
2. Do NOT create a new commit (nothing to commit)
3. The existing PR just needs CI to pass and then merge

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| None - fast detection | Checked file existence and git log immediately after reading the prompt | N/A - correct approach | Checking git history first saves all implementation effort |

## Results & Parameters

### Exact Commands Used (Issue #3066)

```bash
# Read the prompt to understand the task
cat .claude-prompt-3066.md

# Check if target file exists and what else is in benchmarks/
# (Used Glob tool)
# Result: benchmarks/__init__.mojo NOT present

# Check for imports of the deleted file
grep -r "benchmarks/__init__" . --include="*.mojo"
# Result: 0 matches (only .claude-prompt-3066.md contained the string)

# Check git history
git log --oneline -5
# Result: 98f5ce44 chore(benchmarks): delete deprecated benchmarks/__init__.mojo

# Confirm PR exists
gh pr list --head 3066-auto-impl
# Result: PR #3263 OPEN
```

### Total Tool Calls to Detect

- 4 tool calls to confirm task already complete
- 0 implementation needed
- No new commits created

### Decision Tree

```text
Is the target file/artifact missing from the working tree?
YES -> Check git log for deletion commit
  Found deletion commit? YES -> Check for imports/references
    Zero references? YES -> Check for existing PR
      PR exists? YES -> Task complete, report to user
      PR exists? NO -> Determine if PR needs to be created
    References exist? YES -> Still need to fix remaining references
  Found deletion commit? NO -> Check if never existed (wrong path?)
NO -> Proceed with deletion as normal
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3066, branch `3066-auto-impl`, PR #3263 | `benchmarks/__init__.mojo` deleted in commit `98f5ce44` |

## Related Skills

- `verify-issue-before-work` - Check issue state before starting any implementation
- `issue-completion-verification` - Close orphaned issues when auto-close fails
- `gh-implement-issue` - End-to-end implementation workflow (when work is NOT done)
