---
name: diverged-branch-cherry-pick-fix
description: 'Fix a diverged feature branch by resetting to remote and cherry-picking
  specific fix commits. Use when: local branch has diverged from remote, fix commits
  exist locally but remote has additional commits.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# diverged-branch-cherry-pick-fix

Workflow for recovering when a local feature branch has diverged from its remote counterpart
and you need to apply a specific fix commit on top of the updated remote state.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-05 |
| Objective | Apply a local fix commit onto a remote branch that has diverged |
| Outcome | Success |
| Project | ProjectOdyssey |
| Context | PR #3197 (issue #3088) — BF16 test skip fix |

## When to Use

- `git push` fails with "non-fast-forward" on a feature branch
- `git status` shows "Your branch and 'origin/<branch>' have diverged"
- A fix commit exists locally but the remote has accumulated additional commits
- A fix plan assumed the remote was behind, but it actually has more commits than local
- You need to land a minimal targeted fix (one file) on top of an updated remote state

## Verified Workflow

### Step 1: Diagnose the divergence

```bash
# Check local vs remote state
git log --oneline -6
git status

# Show commits unique to local (ahead of remote)
git log --oneline origin/<branch>..HEAD

# Show commits unique to remote (behind locally)
git log --oneline HEAD..origin/<branch>

# Find common ancestor
git merge-base HEAD origin/<branch>
```

### Step 2: Understand what each side changed

```bash
# See what the remote-only commits changed in the target file
git show origin/<branch>:path/to/file.ext | grep -n "relevant pattern"

# See what the local fix commit changes
git show <fix-commit-sha> --stat
git diff <merge-base>..<fix-commit-sha> -- path/to/file.ext
```

### Step 3: Reset local to remote tip

Only do this after confirming your fix applies cleanly on top of the remote state.

```bash
git reset --hard origin/<branch>
```

### Step 4: Cherry-pick the fix commit

```bash
git cherry-pick <fix-commit-sha>
```

If conflicts arise, resolve them manually, then `git cherry-pick --continue`.

### Step 5: Verify

```bash
# Should show exactly 1 commit ahead
git status

# Confirm fix is present
git show HEAD --stat
sed -n '<start>,<end>p' path/to/fixed/file.ext
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct push after local commits | Assumed local was ahead of remote | Branches had diverged; remote had 13 additional commits not present locally | Always check `HEAD..origin/<branch>` not just `origin/<branch>..HEAD` before pushing |
| Treating fix plan at face value | Fix plan said "2 commits ahead, just push" | Plan was written before remote accumulated additional commits | Verify actual remote state with `git log --oneline HEAD..origin/<branch>` before acting |
| Keeping local commits and merging | Would merge unrelated cleanup commit with remote's version of same | Remote already had an equivalent cleanup commit; merge would create duplicate | Use cherry-pick of the minimal fix only, not the full local commit stack |

## Results & Parameters

The fix involved only 1 file changed (test file BF16 test body replaced with `pass` + docstring).
Cherry-pick applied with zero conflicts because the remote's version of the file differed only
in the same function body that the fix commit modifies.

Key diagnostic commands:

```bash
# Full divergence diagnosis
git log --oneline origin/<branch>..HEAD       # local-only commits
git log --oneline HEAD..origin/<branch>       # remote-only commits
git merge-base HEAD origin/<branch>           # common ancestor SHA

# Safe reset + cherry-pick
git reset --hard origin/<branch>              # absorb all remote commits
git cherry-pick <fix-sha>                     # apply only the targeted fix

# Verify result
git log --oneline -3                          # should show fix as single HEAD commit
git status                                    # should show "ahead by 1 commit"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #3197, issue #3088 — BF16 test skip | [notes.md](../../references/notes.md) |
