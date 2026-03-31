---
name: pixi-lock-rebase-regenerate
description: "Correctly resolve pixi.lock staleness after git rebase or when main advances. Use when: (1) CI fails with 'lock-file not up-to-date with the workspace', (2) multiple PRs all fail identical CI jobs after a version bump on main, (3) git rebase causes pixi.lock conflicts."
category: ci-cd
date: 2026-03-30
version: "1.1.0"
user-invocable: true
verification: verified-local
history: pixi-lock-rebase-regenerate.history
tags: []
---
# Pixi Lock Rebase Regenerate

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Correctly resolve `pixi.lock` staleness after `git rebase` or main-branch advancement without producing an invalid lock file |
| **Outcome** | Eliminates `lock-file not up-to-date` CI failures; multi-branch parallel fix completes 5 PRs in ~1 minute |
| **Verification** | verified-local |
| **History** | [changelog](./pixi-lock-rebase-regenerate.history) |

## When to Use

- CI fails with `lock-file not up-to-date with the workspace` on one or more PRs
- Multiple open PRs all fail identical CI jobs (lint, pre-commit, dep-scan) after a version bump landed on main
- Running `git rebase` on a branch that includes `pixi.lock` and a conflict occurs
- The branch modifies `pixi.toml` (adds/removes dependencies or tasks)
- All test matrix jobs pass but infrastructure jobs (lock-check, pre-commit, dep-scan) uniformly fail

**Do NOT use `--ours` or `--theirs`** to resolve a `pixi.lock` conflict — either side will be stale
relative to the rebased branch's actual `pixi.toml`.

## Verified Workflow

### Quick Reference

```bash
# Triage: confirm lock staleness across multiple PRs
gh run view <run-id> --log-failed | grep "lock-file"

# Single-branch fix
git fetch origin
git rebase origin/main          # clean rebase (no pixi.lock conflict? run pixi install anyway)
pixi install                    # regenerates pixi.lock in place
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>
gh pr merge <pr-number> --auto --rebase

# Multi-branch parallel fix (5 PRs simultaneously)
REPO_DIR="/path/to/local/repo"
BRANCHES=(branch1 branch2 branch3 branch4 branch5)
git -C "$REPO_DIR" fetch origin
for branch in "${BRANCHES[@]}"; do
  dir="/tmp/fix-pr-${branch}"
  git -C "$REPO_DIR" worktree remove "$dir" --force 2>/dev/null || rm -rf "$dir"
  git -C "$REPO_DIR" worktree add "$dir" "origin/${branch}"
  (cd "$dir" && git rebase origin/main && pixi install && git add pixi.lock && \
   git commit -m "fix(deps): regenerate pixi.lock after rebase" && \
   git push --force-with-lease "origin/${branch}" && \
   PR=$(gh pr list --head "${branch}" --json number --jq '.[0].number') && \
   gh pr merge "$PR" --auto --rebase && echo "Done: ${branch}") &
done
wait
```

### Phase 0: Triage — Confirm It Is Lock Staleness

When multiple PRs fail simultaneously with identical errors, this is the fastest diagnosis:

```bash
# Pick any one failing run
gh pr list --state open --json number,headRefName
gh run view <run-id> --log-failed | head -40
```

**Confirming signals:**
- Error message: `lock-file not up-to-date with the workspace`
- All affected PRs were cut before a recent commit on main (version bump, new subpackage, dep change)
- All *test matrix* jobs pass — only infrastructure jobs (lock-check, pre-commit, dep-scan) fail
- The failing SHA256 in the lock message is the old main hash, not the branch's source hash

### Phase 1: Root Cause — Why Pixi.lock Goes Stale

`pixi.lock` encodes the exact resolved dependency graph plus a SHA256 hash of the local
editable package. When main advances:

1. If `pyproject.toml` or `pixi.toml` changed on main (version bump, new dep, new subpackage), the
   lock hash diverges from any branch cut before that commit
2. Even without `pixi.toml` changes, the local package hash changes when source files change
3. Accepting `--ours` or `--theirs` during rebase produces a hash that doesn't match the rebased state
4. `pixi install --locked` (what CI runs) then fails because the hash is wrong

### Phase 2: Single-Branch Fix

```bash
git fetch origin
git checkout <branch>
git rebase origin/main
# If pixi.lock shows as conflicted during rebase:
#   rm pixi.lock && git add pixi.lock && git rebase --continue

# Always regenerate the lock file after rebase
pixi install              # reads pixi.toml, resolves deps, rewrites pixi.lock
git add pixi.lock
git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
git push --force-with-lease origin <branch>

# Re-enable auto-merge (force-push clears it silently)
gh pr merge <pr-number> --auto --rebase
```

**If pixi.lock conflict during rebase** (branch has explicit pixi.toml changes):

```bash
# During git rebase, when pixi.lock is conflicted:
rm pixi.lock
git add pixi.lock
git rebase --continue
# After rebase finishes:
pixi install
git add pixi.lock
```

### Phase 3: Multi-Branch Parallel Fix (3+ PRs)

When many PRs share the same staleness root cause, fix them all simultaneously using git worktrees.
Each worktree is fully isolated — zero branch conflicts, zero interaction.

```bash
REPO_DIR="/path/to/local/repo"
git -C "$REPO_DIR" fetch origin

BRANCHES=(127-auto-impl 128-some-feature 129-other-feature 130-another 131-last)

for branch in "${BRANCHES[@]}"; do
  dir="/tmp/fix-pr-${branch}"
  # Remove any stale worktree at that path
  git -C "$REPO_DIR" worktree remove "$dir" --force 2>/dev/null || rm -rf "$dir"
  # Create isolated worktree on the branch
  git -C "$REPO_DIR" worktree add "$dir" "origin/${branch}"
  (
    cd "$dir"
    git rebase origin/main                           # clean: no pixi.lock conflicts
    pixi install                                     # regenerate pixi.lock
    git add pixi.lock
    git commit -m "fix(deps): regenerate pixi.lock after rebase on main"
    git push --force-with-lease "origin/${branch}"
    # Get PR number from branch name and re-enable auto-merge
    PR=$(gh pr list --head "${branch}" --json number --jq '.[0].number')
    gh pr merge "$PR" --auto --rebase
    echo "Done: ${branch}"
  ) &
done
wait
echo "All branches fixed"

# Clean up worktrees
for branch in "${BRANCHES[@]}"; do
  git -C "$REPO_DIR" worktree remove "/tmp/fix-pr-${branch}" --force 2>/dev/null || true
done
git -C "$REPO_DIR" worktree prune
```

**Observed timing**: 5 branches in parallel → ~1 minute total (vs ~10 minutes sequential).

### Phase 4: Verify

```bash
# Check CI is re-triggered and passing
for pr in <list>; do
  gh pr checks "$pr" 2>&1 | grep -E "(fail|pass|pending)"
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git checkout --theirs pixi.lock` | Accept main's lock during rebase | Main's lock hash is for main's source tree, not the branch | Always delete and regenerate — never accept either side |
| `git checkout --ours pixi.lock` | Accept branch's lock during rebase | Branch's lock is pre-rebase; doesn't reflect rebased state | Always regenerate with `pixi install` after rebase |
| `--no-verify` to skip pre-commit | Attempted to bypass lock-file check | Critical violation of repo policy; hook exists to protect CI | Always fix the root cause — the lock file IS wrong, fix it |
| Sequential per-branch fixes | Fixed branches one at a time | 5x longer than parallel; each pixi install takes ~15s | Use git worktrees for parallel execution when 3+ branches share the same fix |

## Results & Parameters

### Key Commands

```bash
# Diagnose lock staleness
gh run view <run-id> --log-failed | grep "lock-file"

# Regenerate lock
pixi install              # regenerate pixi.lock (reads pixi.toml, resolves all deps)
pixi install --locked     # verify lock file is consistent (what CI runs) — use for verification

# Check if pixi.toml diverges between branch and main
git diff origin/main..HEAD -- pixi.toml

# Re-enable auto-merge after force-push (GitHub clears it silently)
gh pr merge <pr-number> --auto --rebase
gh pr view <pr-number> --json autoMergeRequest  # verify: should NOT be null
```

### When to Expect Clean Rebase vs. Conflict

| Scenario | What Happens | Action |
|----------|-------------|--------|
| Branch cut before version bump on main; branch has no pixi.toml changes | Rebase is clean — no pixi.lock conflict | Run `pixi install` anyway; the hash is stale |
| Branch has pixi.toml changes AND main has pixi.toml changes | Conflict in pixi.lock | Delete pixi.lock, stage, continue rebase, then `pixi install` |
| Branch has no pixi.toml changes, main has no pixi.toml changes | Rebase clean; pixi.lock may still be stale if any source changed | Run `pixi install` to be safe |

### Timing Reference

| Approach | PRs | Time |
|----------|-----|------|
| Sequential single-branch | 5 | ~10 min |
| Parallel worktrees | 5 | ~1 min |
| Break-even point | 3 | Parallel wins at 3+ branches |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Multiple PRs on 2026-02-22 with pixi.lock conflicts and CI failures | v1.0.0 |
| ProjectHephaestus | 5 PRs failed after version bump 0.5.0 to 0.6.0 + resilience subpackage; all fixed via parallel worktrees, 2026-03-30 | v1.1.0 |
