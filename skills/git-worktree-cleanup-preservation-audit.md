---
name: git-worktree-cleanup-preservation-audit
description: "Systematic 3-method audit for cleaning up stale git worktrees, branches, and stashes
  with a strong preservation bias. Use when: (1) asked to clean up stale branches/worktrees/stashes
  and told to 'err on the side of keeping', (2) git cherry shows '+' for commits on a PR that was
  MERGED (squash-merge false positive), (3) a branch is far behind main but unclear if work is
  truly on main, (4) a stash exists but unclear if its content is already committed, (5) cleanup
  request comes with no explicit 'it is safe to destroy' confirmation."
category: tooling
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, worktree, cleanup, stash, branch, preservation, audit, squash-merge, cherry, patch-id]
---

# Git Worktree Cleanup — Preservation-Biased Audit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Safely clean up stale git artifacts (worktrees, branches, stashes) while proving — not assuming — each one is redundant before discarding |
| **Outcome** | Audit methodology executed end-to-end in ProjectHermes; all artifacts verified as redundant via multi-method evidence before discard |
| **Verification** | verified-local — audit methodology executed locally; cleanup was evidence-backed |

## When to Use

- User says "clean up stale branches/worktrees/stashes" AND asks to preserve work or "err on the side of keeping"
- `git cherry origin/main <branch>` shows `+` commits on a branch whose PR was MERGED (squash-merge false positive)
- A branch is many commits behind main but unclear whether its unique content is already incorporated
- A stash exists but it is unclear whether its changes are already in main
- Safety Net blocks `git stash drop`, `git worktree remove --force`, or `rm -rf .worktrees/`
- Cleanup is requested without explicit "it is safe to destroy" confirmation

## Verified Workflow

### Quick Reference

```bash
# Step 1: Full inventory
git worktree list
git branch -vv
git stash list
gh pr list --state all --json number,title,headRefName,state | jq -r '.[] | "\(.state) \(.headRefName) #\(.number)"'

# Step 2: PR-state classification for each branch/worktree
gh pr list --head <branch> --state all --json number,state,title

# Step 3: Patch-ID check
git cherry origin/main <branch>
# "-" prefix = commit equivalent in main (same patch-id) — safe to discard
# "+" prefix = commit NOT equivalent — need further verification

# Step 4: For "+" commits — find squash-merge equivalent by message
git log origin/main --oneline | grep -i "<first-4-words-of-commit-msg>"

# Step 5: Tree diff — verify content presence in main
git diff <worktree-sha> <main-sha> --stat
# If main has NET MORE insertions than the worktree SHA → worktree is the seed not the divergence

# Step 6: Uncommitted work check
git -C <worktree-path> status --short
grep -rn "<key-symbol>" src/

# Step 7: Silent-drop check for branches
git log origin/main..HEAD --oneline
# Empty output = branch fully subsumed by rebase → safe to discard

# Step 8: Stash audit
git stash show -p stash@{N}
grep -r "def <key-function>" src/
```

### Detailed Steps

#### Phase 1 — Full Inventory

```bash
# Worktrees
git worktree list

# Branches with tracking info
git branch -vv

# Stashes
git stash list

# All PRs (open + merged + closed) — the most reliable classification signal
gh pr list --state all --json number,title,headRefName,state \
  | jq -r '.[] | "\(.state) | \(.headRefName) | #\(.number) | \(.title)"'
```

#### Phase 2 — Classify by PR Status

For each worktree/branch:

```bash
gh pr list --head <branch> --state all --json number,state,title
```

| PR State | Initial Verdict | Next Step |
|----------|-----------------|-----------|
| `MERGED` | Candidate for discard | Still run cherry + diff verification |
| `CLOSED` | Candidate for discard | Check if cherry has unique commits |
| `OPEN` | KEEP | No further action |
| No PR | Investigate | Run silent-drop + cherry check |

#### Phase 3 — Patch-ID Check (git cherry)

```bash
git cherry origin/main <branch>
```

**Critical interpretation:**
- `-` prefix: commit is equivalent in main (identical patch-id). Definitively safe.
- `+` prefix: commit is NOT equivalent. This does NOT mean the work is missing from main — squash merges ALWAYS produce `+` because squashing changes the patch context. Proceed to Phase 4.

#### Phase 4 — Squash-Merge Detection for "+" Commits

When `git cherry` shows `+` on a MERGED PR:

```bash
# Get the commit message from the branch
git log origin/main..<branch> --oneline

# Search for it on main by the first few words
git log origin/main --oneline | grep -i "<first-4-words>"
```

If main has a commit with matching message words, the work was squash-merged. Confirm with:

```bash
# Tree diff — if main commit has significantly more insertions, branch was the seed
git diff <branch-tip-sha> <main-squash-sha> --stat

# If main's commit shows net MORE lines than branch tip → branch content is fully in main
```

#### Phase 5 — Uncommitted Work Check

A worktree that is many commits behind main will appear to have hundreds of dirty files — but most are just "drift" from main's newer state, not real WIP.

```bash
# Check actual uncommitted changes (not drift from main)
git -C <worktree-path> status --short

# If status is empty or only shows known artifacts → no real uncommitted work
# Key artifact patterns to discard:
# __pycache__/ .pyc .coverage .pytest_cache .mypy_cache
```

Also grep main for the key function/class to confirm it is present:

```bash
grep -rn "def <key_function>\|class <KeyClass>" src/
```

#### Phase 6 — Silent-Drop Detection

For branches with no PR (may have been silently subsumed by a rebase):

```bash
git log origin/main..HEAD --oneline
# Empty = branch is fully subsumed — all commits already in main via rebase
```

#### Phase 7 — Stash Audit

```bash
# See stash content
git stash show -p stash@{N}

# Cross-reference: does main have the key function/symbol from the stash?
grep -r "def <function-name>" src/
grep -r "<key-class-or-symbol>" src/
```

If main has the function/symbol the stash adds → stash is redundant.

**Note:** Safety Net blocks `git stash drop`. Ask user to run stash drops manually.

#### Phase 8 — Cleanup (after audit confirms safety)

```bash
# For unlocked worktrees:
git worktree remove <path>
git worktree prune

# For locked worktrees (Claude Code session-isolation):
# Safety Net blocks --force. Ask user to run manually:
for w in .claude/worktrees/agent-*; do
  git worktree unlock "$w" 2>/dev/null
  git worktree remove --force "$w"
done
git worktree prune

# For local branches (squash-merged branches refuse -d; use -D only after audit):
git branch -D <branch-name>

# For remote branches:
git push origin --delete <branch-name>
git remote prune origin

# For stashes (ask user — Safety Net blocks these):
git stash drop 'stash@{N}'  # drop in reverse-index order (highest N first)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusting git cherry as definitive | `git cherry origin/main <branch>` showed `+` → concluded work not in main | Squash merges always produce `+` because squashing changes the commit context/SHA even when content is identical | `git cherry` is not definitive for squash-merged branches; follow up with message search + tree diff |
| Assuming dirty worktree = real WIP | Worktree 95 commits behind main showed hundreds of dirty files | The "dirty" state was entirely drift — main had moved forward; the worktree had not | Check `git status --short` in the worktree itself; drift shows as many modifications, real WIP is a small targeted set |
| Running git stash drop directly | Agent executed `git stash drop stash@{4}` | Safety Net treats stash drop as a destructive operation and blocks it | Stash drops must be handed to user to run manually |
| Running git worktree remove --force | Agent tried `git worktree remove --force .claude/worktrees/agent-*` | Safety Net blocks `--force` on worktree remove | Provide the unlock + force-remove command for user to run; do not execute directly |
| Running rm -rf .worktrees/ | Agent tried to bulk-remove worktree directory | Safety Net blocks rm -rf on project directories | Same as above — hand to user or unlock first |
| Assuming MERGED PR means `-d` will work | After audit confirmed safety, ran `git branch -d <squash-merged-branch>` | `-d` refuses for squash-merged branches because git cannot verify ancestry | Use `git branch -D` (force-delete) only after audit proves the content is in main |

## Results & Parameters

### The 3-Method Verification Summary

For any artifact candidate, apply these checks in order — stop when confidence is established:

| Method | Command | Positive Signal (Safe to Discard) |
|--------|---------|-----------------------------------|
| **PR state** | `gh pr list --head <branch> --state all` | `MERGED` or `CLOSED` |
| **Patch-ID** | `git cherry origin/main <branch>` | All `-` prefix (skip if squash-merge suspected) |
| **Message match** | `git log origin/main --oneline \| grep -i "<subject>"` | Match found on main |
| **Tree diff** | `git diff <branch-sha> <main-sha> --stat` | Main has net more insertions |
| **Uncommitted check** | `git -C <wt> status --short` | Empty (only artifact noise) |
| **Symbol grep** | `grep -rn "<key-symbol>" src/` | Found in main |
| **Silent-drop** | `git log origin/main..HEAD --oneline` | Empty output |

### Stash Audit Pattern

```bash
# Full stash audit sequence
git stash list
for i in $(seq 0 <N>); do
  echo "=== stash@{$i} ==="
  git stash show -p stash@{$i} | head -30
done

# Cross-reference each stash's key changes against main
grep -rn "<function-or-class-from-stash>" src/
```

### Safety Net Bypass Commands (for user to run manually)

```bash
# Stash drops (reverse order — highest index first)
git stash drop 'stash@{4}'
git stash drop 'stash@{3}'
git stash drop 'stash@{2}'
git stash drop 'stash@{1}'
git stash drop 'stash@{0}'

# Locked worktree force-removal
for w in .claude/worktrees/agent-*; do
  git worktree unlock "$w" 2>/dev/null
  git worktree remove --force "$w"
done
git worktree prune
git branch -D $(git branch | grep '^[ +*]*worktree-agent-' | tr -d '* +') 2>/dev/null || true

# Bulk worktree dir removal (fallback)
rm -rf .claude/worktrees/

# Squash-merged branch cleanup
git branch -D <branch-name>
git push origin --delete <branch-name>
git remote prune origin
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | 2026-04-25 — branch `9-auto-impl`, cleaned up stale worktrees + stashes + branches after feature work, strong preservation bias | Audit methodology applied: squash-merge detection confirmed rate-limiting branch content on main; stash content cross-referenced via grep; locked worktrees identified as Safety Net-blocked |
