---
name: batch-review-plan-implementation
description: 'Implements multiple automated review plans for PRs, handling OPEN PRs
  via rebase+push and skipping MERGED PRs with only transient CI failures. Use when:
  automated implementer generated review-plan-*.md files with phase=failed in review
  JSON, need to process 10+ stale PR branches at once.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Objective** | Process all failed automated review plans to unblock stale PRs |
| **Input** | `.issue_implementer/review-plan-{N}.md` + `review-{N}.json` files |
| **Output** | All OPEN PRs rebased/fixed and pushed with auto-merge enabled |
| **Time** | ~20-30 min for 14 OPEN PRs, mostly parallel rebase operations |

## When to Use

- After `scylla.automation.implementer` creates PRs and review phase fails with `git push` errors
- When `review-{N}.json` shows `"phase": "failed"` with `git push` or `git add` errors
- When many PR branches are stale (10+ commits behind main) causing CI flakes
- When local worktrees have unpushed fix commits that need to be pushed

## Verified Workflow

### Step 1: Triage — Identify Failed Reviews and PR States

```bash
# Get phase and error for all review JSON files
for f in .issue_implementer/review-*.json; do
  issue=$(echo $f | grep -o '[0-9]*' | tail -1)
  python3 -c "
import json
d=json.load(open('$f'))
print('$issue', d.get('phase','unknown'), d.get('pr_number','?'), repr(d.get('error',''))[:80])
"
done | sort -n

# Check which failed PRs are still OPEN vs MERGED
gh pr list --state all --json number,state --limit 200 | python3 -c "
import json, sys
prs = json.load(sys.stdin)
pr_map = {p['number']: p['state'] for p in prs}
for pr_num in [3263, 3269, ...]:  # list of failed PR numbers
    print(f'PR #{pr_num}: {pr_map.get(pr_num, \"NOT_FOUND\")}')
"
```

**Decision rules:**
- `phase=failed` + OPEN PR → Process (rebase or apply fix)
- `phase=failed` + MERGED PR → Read review plan; if "pre-existing CI flake" → skip; if code fix → check if fix already on main
- `phase=completed` → Skip

### Step 2: Check for Existing Local Fix Commits

Many worktrees already have fix commits that were never pushed (the push was what failed):

```bash
for issue in 3066 3077 3085 3140 3162 3163; do
  wt=".worktrees/issue-$issue"
  if [ -d "$wt" ]; then
    behind=$(git -C "$wt" rev-list --count origin/${issue}-auto-impl..HEAD 2>/dev/null)
    echo "issue-$issue: $behind commits ahead of remote"
  fi
done
```

If `N commits ahead of remote` → branch has local fix commit. Just rebase onto main and push.

### Step 3: Handle "Corrupted Files" Pattern

The automated implementer had a bug: when `git add EADME.md` failed (typo), it left `README.md` and `docs/dev/release-process.md` in a truncated/corrupted state in the worktree. Detect and fix:

```bash
git -C .worktrees/issue-NNNN diff README.md | head -10
# If shows deletions of real content → corrupted
git -C .worktrees/issue-NNNN checkout -- README.md docs/dev/release-process.md
```

### Step 4: Create Missing Worktrees for Rebase-Only Issues

```bash
cd /path/to/repo
for issue in 3071 3087 3112 3148 3152 3158; do
  git worktree add .worktrees/issue-$issue $issue-auto-impl
done
```

### Step 5: Rebase All Stale Branches

```bash
for issue in 3071 3087 3112 3148 3152 3158; do
  git -C .worktrees/issue-$issue rebase origin/main
done

# Push all (force-with-lease for rebases)
for issue in 3071 3087 3112 3148 3152 3158; do
  git -C .worktrees/issue-$issue push --force-with-lease origin ${issue}-auto-impl
done
```

### Step 6: Handle Merge Conflicts During Rebase

If `git rebase origin/main` fails with conflicts:

```bash
# Check which files conflict
git -C .worktrees/issue-NNNN diff --name-only --diff-filter=U

# Resolve: take the branch's version of intentional changes
# Edit the file to remove conflict markers (<<<, ===, >>>)
git add <file>
GIT_EDITOR=true git rebase --continue
```

**Key**: The conflict markers `<<<<<<< HEAD` and `>>>>>>> <hash>` are at the start of lines. The `=====` separators in YAML echo commands are NOT conflict markers.

### Step 7: Enable Auto-Merge on All Fixed PRs

```bash
for pr in 3263 3269 3232 3177 3231 3193 3214 3224 3335 3343 3354 3363 3371 3372; do
  gh pr merge $pr --auto --rebase
done
```

### Step 8: Verify

```bash
for pr in 3263 3269 3232 3177 3231 3193 3214 3224 3335 3343 3354 3363 3371 3372; do
  s=$(gh pr view $pr --json state,autoMergeRequest | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['state'], 'auto:', d.get('autoMergeRequest') is not None)")
  echo "PR #$pr: $s"
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sequential worktree creation | Creating worktrees one at a time before checking local state | Wasted time — many branches already had local fix commits that just needed pushing | Check `git rev-list --count origin/branch..HEAD` first to detect unpushed commits |
| Running `git rebase` without checking for existing fix commits | Assumed all failures were "no local changes, just stale" | Some worktrees had 1-2 unpushed fix commits that rebase would reorder or complicate | Always inspect local worktree state before choosing rebase vs push strategy |
| Trying to push MERGED PR fix commits | Read review plan saying "push failed" without checking PR state first | MERGED PRs can't receive new pushes to update the PR (it's closed) | Always check PR state (OPEN vs MERGED) before any push attempt |
| Using `grep -c "<<<<<"` to detect conflict markers | Counted `=====` separator lines in YAML as conflict markers | YAML workflows use `=====` legitimately in echo commands | Use `grep -n "^<<<<<<\|^=======\|^>>>>>>>"` (anchored to line start) |

## Results & Parameters

### Typical Distribution (51 total review plans)

- `phase=completed`: ~27 — skip
- `phase=failed` + MERGED PR + pre-existing CI flake: ~12 — skip
- `phase=failed` + OPEN PR + rebase-only fix: ~8 — `git rebase origin/main && push --force-with-lease`
- `phase=failed` + local fix commit unpushed: ~6 — `git checkout -- corrupted_files && push`
- `phase=failed` + merge conflict during rebase: ~1 — manual conflict resolution

### Review JSON Structure

```json
{
  "issue_number": 3066,
  "pr_number": 3263,
  "phase": "failed",
  "worktree_path": "/path/.worktrees/issue-3066",
  "branch_name": "3066-auto-impl",
  "plan_path": "/path/.issue_implementer/review-plan-3066.md",
  "error": "Command ['git', 'push', 'origin', '3066-auto-impl'] returned non-zero exit status 1."
}
```

### Common Error Patterns in review JSON

| Error Pattern | Root Cause | Fix |
|--------------|-----------|-----|
| `git push ... returned non-zero exit status 1` | Branch diverged from remote after rebase | `git rebase origin/main && push --force-with-lease` |
| `git add EADME.md ... returned non-zero exit status` | Typo in filename — `git add` failed silently | Restore corrupted files with `git checkout --`, then push |
| `Analysis session failed for PR ...` | Review analysis couldn't complete | Read plan file manually to determine action |
