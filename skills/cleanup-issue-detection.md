---
name: cleanup-issue-detection
description: 'Detect when a cleanup issue has already been implemented before starting
  work. Use when: implementing a cleanup/removal issue, checking if a branch already
  has the fix, or verifying prior auto-implementation state.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | tooling |
| **Trigger** | Implementing a cleanup issue (removal of dead code, NOTE markers, unimplemented stubs) |
| **Key insight** | Check `git log main..HEAD` before any exploration — prior automation may have already done the work |
| **Time saved** | Avoids full exploration and re-implementation when work is already done |

## When to Use

- Assigned a `[Cleanup]` labeled GitHub issue
- The issue involves removing test stubs, NOTE markers, or unimplemented placeholders
- Working in a pre-created worktree branch (e.g., `3083-auto-impl`)
- The issue description references a specific file+line with a marker to remove

## Verified Workflow

1. **Check if work is already done first** — before any file exploration:
   ```bash
   git log main..HEAD --oneline
   ```
   If a relevant commit appears, the implementation may already be complete.

2. **Verify the remote branch state**:
   ```bash
   git fetch origin <branch>
   git log --oneline origin/<branch> -5
   ```
   The remote branch may have additional commits from prior automation runs.

3. **Check for existing PR**:
   ```bash
   gh pr list --head <branch>
   ```
   If a PR exists and has auto-merge enabled, no further action is needed.

4. **If work is NOT done**: find the marker in the main-branch version of the file:
   ```bash
   grep -n "NOTE\|RotatingFileHandler\|not yet implemented" tests/shared/utils/test_logging.mojo
   ```
   Then remove the function and its call from `main()`.

5. **If work IS done**: skip to push/PR step, checking if remote has diverged:
   ```bash
   git push -u origin <branch>
   # If rejected: fetch remote and check if it already has the fix
   git fetch origin <branch> && git log --oneline origin/<branch> -5
   ```

6. **Confirm PR exists with auto-merge**:
   ```bash
   gh pr view <pr-number>
   ```
   Look for `auto-merge: enabled`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching worktree for NOTE marker | Grepped `tests/shared/utils/test_logging.mojo` in the worktree for `RotatingFileHandler` | Worktree already had the fix applied; grep returned no results | Check `git log main..HEAD` FIRST — searching for removed code in an already-fixed worktree gives false "not found" |
| Checking line 208 from issue description | Issue said "File: test_logging.mojo, Line: 208" — tried to read that line | Line numbers had shifted since issue was filed | Issue line numbers are approximate; search by pattern not line number |
| Pushing to remote | Ran `git push -u origin 3083-auto-impl` | Remote branch had diverged (forced update from prior automation) | Always `git fetch` first; if remote is ahead, check if fix is already there |

## Results & Parameters

### Detection Commands (copy-paste)

```bash
# Step 1: Check if already implemented in this worktree
git log main..HEAD --oneline

# Step 2: Check remote state
git fetch origin $(git branch --show-current)
git log --oneline origin/$(git branch --show-current) -5

# Step 3: Check for existing PR
gh pr list --head $(git branch --show-current)

# Step 4: If PR exists, view auto-merge status
gh pr view $(gh pr list --head $(git branch --show-current) --json number -q '.[0].number')
```

### Pattern for Cleanup Issues (removal of test stubs)

When a cleanup issue asks to remove a `NOTE: X not yet implemented` test:

1. Find the function in the **main branch** file (not worktree):
   ```bash
   grep -n "fn test_.*\|NOTE.*not yet\|pass$" /path/to/file.mojo | head -20
   ```

2. The removal pattern is:
   - Delete the entire `fn test_xxx():` function body
   - Delete the `test_xxx()` call from `main()`
   - Verify no remaining references: `grep -n "test_xxx" file.mojo`

3. Commit message format:
   ```
   cleanup(scope): remove unimplemented X placeholder

   Closes #NNNN
   ```
