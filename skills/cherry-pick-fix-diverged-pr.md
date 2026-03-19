---
name: cherry-pick-fix-diverged-pr
description: 'Apply a local fix commit to a remote PR branch when histories have diverged
  (same-content commits with different SHAs). Use when: fix exists locally but can''t
  fast-forward push to PR branch due to diverged history from rebase.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | cherry-pick-fix-diverged-pr |
| **Category** | ci-cd |
| **Trigger** | Fix commit exists locally but `git push` is rejected as non-fast-forward |
| **Root Cause** | Local and remote branch have diverged: same file content, different commit SHAs (caused by rebase) |
| **Resolution** | Create temp branch from remote PR branch, cherry-pick the fix commit, push to PR branch, clean up |

## When to Use

- `git push origin <fix-commit>:refs/heads/<pr-branch>` fails with "non-fast-forward"
- `git diff <local-parent> <remote-tip> -- <files>` shows no diff (identical content, different SHAs)
- `git merge-base <local-commit> <remote-commit>` points to the same ancestor — confirming diverged parallel histories
- A review fix plan says "branch already has the fix" but the fix is on a local branch with a different parent than the remote PR branch
- Re-triggering CI via `gh run rerun` still fails because the fix commit was never pushed to the remote

## Verified Workflow

### Step 1: Identify the divergence

```bash
# Get the PR's actual remote branch
gh pr view <pr-number> --json headRefName,headRefOid

# Find your local fix commit
git log --oneline <local-branch> -5

# Compare parents: same content, different SHAs?
git diff <local-parent-sha> <remote-tip-sha> -- <path/to/file>
# If no diff: diverged history — cherry-pick is needed
```

### Step 2: Verify the fix commit content

```bash
git show <fix-commit-sha> --stat
# Confirm it only touches the files you intend to fix
```

### Step 3: Create a temp branch from the remote PR branch

```bash
git fetch origin <pr-branch>
git checkout -b <pr-branch>-fix origin/<pr-branch>
# This puts you exactly at the remote PR branch tip
```

### Step 4: Cherry-pick the fix

```bash
git cherry-pick <fix-commit-sha>
# Verify it applied cleanly
git log --oneline -3
```

### Step 5: Push to the PR branch (fast-forward)

```bash
git push origin <pr-branch>-fix:<pr-branch>
# This is a fast-forward push — no force required
```

### Step 6: Clean up the temp branch

```bash
git checkout main
git branch -d <pr-branch>-fix
```

### Step 7: Verify CI is triggered on the new commit

```bash
gh pr view <pr-number> --json headRefOid,statusCheckRollup | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print('HEAD:', d['headRefOid'][:12]); [print(c['name'], c['conclusion'] or c['status']) for c in d['statusCheckRollup'][:5]]"
# Confirm HEAD SHA matches your pushed commit and checks are queued/running
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Re-trigger CI via `gh run rerun` | Re-ran the failing CI run on the old commit | CI ran against the unfixed commit SHA — still failed mojo format | Re-triggering doesn't help if the fix was never pushed to the remote branch |
| Direct push fix commit to PR branch | `git push origin <fix-sha>:refs/heads/<pr-branch>` | Rejected as non-fast-forward — local fix had a different parent SHA than the remote tip | When histories diverge (same content, different SHAs), a direct push always fails |
| Trust "no changes needed" in review plan | Plan said fix was on the branch already | Plan was generated against a local branch with diverged history; remote never had the fix | Always verify the fix is on `origin/<pr-branch>` not just locally |
| Check if contents are identical | Ran `git diff <local-parent> <remote-tip>` | No diff — but that confirmed diverged histories, not that fix was pushed | Same content + different SHAs = diverged history; cherry-pick onto remote tip is the fix |

## Results & Parameters

**Key pattern — detecting diverged histories**:

```bash
# Both show the same diff as their parent — content is identical:
git show <local-sha>  # shows same changes as...
git show <remote-sha>  # ...this remote commit

# But they can't be merged without cherry-pick:
git merge-base <local-sha> <remote-sha>
# => their common ancestor is NEITHER of them
```

**When `git diff` shows no difference but push is rejected**:

This is the signature of a rebase that created two parallel "versions" of the same commit
with different SHAs. The local branch's commit history is not a superset of the remote's —
it's a parallel branch that happened to produce the same files.

**Cherry-pick is safe here because**:

- The fix commit is small and isolated (only touches the files you care about)
- The cherry-pick is a clean fast-forward onto the remote tip
- No force-push needed — no risk of overwriting others' work

**mojo format line length**: 88 chars. Check with:

```bash
git show <remote-tip>:<path/to/file> | awk '{if(length>88) print NR, length, $0}' | head -10
```
