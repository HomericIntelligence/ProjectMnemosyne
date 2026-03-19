---
name: pr-review-fix-stale-branch
description: 'Fix CI failures when a PR''s remote branch was rebased and lost a fix
  commit. Use when: pre-commit CI fails but fix was already applied locally, local
  and remote branches have diverged after force-push, mojo format violations appear
  in CI but not in local files.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | pr-review-fix-stale-branch |
| **Category** | ci-cd |
| **Trigger** | PR pre-commit CI fails; local branch has fix but remote doesn't |
| **Root Cause** | Remote branch force-pushed/rebased, dropping the fix commit |
| **Resolution** | Reset local to remote, re-apply fix, commit, push |

## When to Use

- A `.claude-review-fix-<issue>.md` plan says "no fixes needed" but CI still fails pre-commit
- `git log main..<branch>` shows a fix commit locally but CI shows the unfixed code
- `git fetch` output shows `(forced update)` for the PR branch
- `gh run view <run-id> --log-failed` reveals `mojo format` line-length violations in files
  the PR touched (but differently worded than expected)
- Local worktree and remote branch have diverged with incompatible histories

## Verified Workflow

### Step 1: Read the review fix plan

```bash
cat .claude-review-fix-<issue>.md
```

Note: "no fixes needed" plans may be outdated if CI is still failing.

### Step 2: Identify actual CI failures

```bash
gh pr view <pr-number> --json statusCheckRollup | python3 -c "
import json,sys
for c in json.load(sys.stdin)['statusCheckRollup']:
    if c.get('conclusion') == 'FAILURE':
        print(c['name'], c['detailsUrl'])
"
```

Then fetch the actual failure log:

```bash
gh run view <run-id> --log-failed 2>&1 | grep -E "ERROR|error|FAIL" | head -40
```

### Step 3: Determine if failures are pre-existing vs PR-caused

```bash
# Check if the same CI check fails on main
gh run list --branch main --workflow "<workflow-name>" --limit 3 \
  --json conclusion,databaseId,createdAt | python3 -c "
import json,sys; [print(r['databaseId'], r['conclusion'], r['createdAt']) for r in json.load(sys.stdin)]
"
```

Pre-existing = same failure on main = no fix needed for those checks.
PR-caused = passes on main but fails on PR = must fix.

### Step 4: Identify the PR branch and create/reset worktree

```bash
# Find the actual PR branch (may differ from your current worktree branch)
gh pr view <pr-number> --json headRefName

# Fetch the remote branch
git fetch origin <head-branch>

# Create a worktree for it (or reset existing)
git worktree add .worktrees/issue-<n> <head-branch>

# If worktree already exists but is diverged, reset to remote
cd .worktrees/issue-<n>
git reset --hard origin/<head-branch>
```

### Step 5: Verify the remote still has the unfixed code

```bash
git show origin/<head-branch>:<path/to/file.mojo> | grep -n "long line pattern"
```

Confirm the line is still too long (>88 chars for mojo format).

### Step 6: Apply the fix

For mojo format line-length violations, split long `print()` strings:

```mojo
# Before (>88 chars):
print("STATUS: Very long string that exceeds the 88 char limit set by mojo format.")

# After (mojo format style):
print(
    "STATUS: Very long string that exceeds the 88 char"
    " limit set by mojo format."
)
```

### Step 7: Commit (do NOT push — the calling script pushes)

```bash
git add <files>
git commit -m "fix: Address review feedback for PR #<pr-number>

<Brief description of what was fixed>.

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the review plan | Plan said "no fixes needed" so stopped | CI was still failing pre-commit due to mojo format violations | Always verify actual CI status even when plan says no fixes needed |
| Work in current worktree | Tried to fix files in `issue-3181` worktree | Wrong branch — PR was on `3084-auto-impl`, not `3181-auto-impl` | Always confirm the PR's `headRefName` before editing files |
| Apply fix to local branch as-is | Local `3084-auto-impl` had fix commit but was diverged from remote | Remote was force-pushed and had 13 newer commits; local fix was on old history | Must reset local to remote before re-applying fix |
| Assume fix commit exists on remote | Saw fix commit locally (`1be9b841`) and assumed it was pushed | `git fetch` showed `(forced update)` — remote had dropped the commit | Check remote state explicitly with `git show origin/<branch>:<file>` |

## Results & Parameters

**Key metrics**:

- Files fixed: 3 Mojo files with `print()` strings >88 chars
- CI check fixed: `pre-commit` (mojo format)
- Pre-existing failures (not fixed, correctly identified): `link-check`, 5 test groups

**mojo format line length rule**: 88 characters (configured in `pyproject.toml` or `mojo.toml`)

**Identifying the right branch**:

```bash
gh pr view <number> --json headRefName,baseRefName
```

**Checking if a fix commit survived a rebase**:

```bash
# Local has it:
git log --oneline main..<branch> | grep "fix"

# Remote may not:
git log --oneline origin/main..origin/<branch> | grep "fix"
```

If local has it but remote doesn't: the commit was dropped in a force-push.
Always reset local to remote before applying fixes to avoid working on stale history.
