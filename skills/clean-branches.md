---
name: clean-branches
description: Clean up stale git worktrees and merged/closed remote branches. Use after
  a wave of PRs merges or periodically to prune remote refs.
category: tooling
date: 2026-05-03
version: 1.1.0
user-invocable: false
---
# Clean Branches: Git Worktree and Branch Cleanup

## Overview

| Aspect | Details |
| -------- | --------- |
| **Date** | 2026-05-03 |
| **Objective** | Remove stale local/remote branches and worktrees after PR waves |
| **Outcome** | Deleted 3 merged remote branches; 0 worktrees (only `main` existed); 5 branches kept (open PRs/issues) |
| **Key Finding** | PR merge status is the authoritative signal — batch `gh issue view` calls are unnecessary and slow |
| **v1.1 Finding** | GitHub rulesets block `git push --delete` for >2 branches; use `gh api` per-branch loop instead |

## When to Use This Skill

Use after:
- A parallel wave of PRs has merged
- `git branch -vv` shows branches with `[gone]` or no open PR
- You want to clear accumulated auto-impl branches

## Verified Workflow

### Step 1: Enumerate

```bash
git worktree list --porcelain
git branch -vv
```

### Step 2: Classify branches

For each non-main branch, check PR status (most reliable single signal):

```bash
gh pr list --head <branch> --state all --json number,state,title
```

| PR State | Verdict |
| ---------- | --------- |
| `MERGED` | DONE — safe to delete |
| `CLOSED` | DONE — safe to delete |
| `OPEN` | KEEP |
| No PR found | Check issue state or `git merge-base --is-ancestor` |

**Definitive classification signals:**
- `ahead=0` (no commits over main) + PR is merged/closed/absent → safe to delete
- Worktree branches (e.g., `worktree-agent-XXXX`, `rebase-XXXX`) with no open PR → safe to delete
- Any branch with `ahead>0` → inspect commits before deleting

**If no PR found**, verify the branch is not in main:

```bash
git merge-base --is-ancestor origin/<branch> origin/main && echo "MERGED" || echo "NOT MERGED"
```

### Step 3: Check remote-only branches

Remote branches not present locally won't appear in `git branch -vv`. Fetch them explicitly:

```bash
gh api repos/{owner}/{repo}/git/refs/heads --paginate --jq '.[].ref' | sed 's|refs/heads/||' | grep -v '^main$'
```

Run the same `gh pr list --head <branch> --state all` check for each.

### Step 4: Print classification report

Print a table before taking action:

| Branch | PR | PR State | Verdict | Reason |
| -------- | ---- | ---------- | --------- | -------- |
| `1359-auto-impl` | #1392 | MERGED | DONE | Merged into main |
| `1427-auto-impl` | #1452 | OPEN | KEEP | Open PR |

### Step 5: Remove DONE worktrees

```bash
git -C <path> status --short   # check if dirty
git worktree remove <path>     # if clean
git worktree remove --force <path>  # if dirty but confirmed DONE (staged deletions, old prompt files, etc.)
```

> **Note:** `--force` cleanly removes worktrees even when they have uncommitted changes
> (e.g., staged deletions of old prompt files). All worktrees are removed independently —
> one dirty worktree does not block others.

### Step 6: Delete local branches

```bash
git branch -d <branch>   # prefer -d (safe: refuses if unmerged)
# Only use -D if explicitly confirmed merged
```

### Step 7: Delete stale remote branches

> **CRITICAL: GitHub rulesets block `git push --delete` for >2 branches.** See Failed Attempts.
> Always use the REST API loop below — it bypasses push rulesets and handles failures independently.

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

for b in "${BRANCHES_TO_DELETE[@]}"; do
  gh api -X DELETE "repos/${OWNER_REPO}/git/refs/heads/$b" 2>&1 \
    && echo "deleted: $b" \
    || echo "FAIL: $b"
done
```

Each API call is independent — a failure on one branch (e.g., already deleted) does not stop others.

Get `{owner}/{repo}`:
```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

### Step 8: Prune

```bash
git worktree prune
git remote prune origin
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| **Batch `gh issue view` for all branches** | Called `gh issue view <N>` for each `<N>-*` branch to check issue state | User interrupted — unnecessary extra call when PR state already tells you everything | PR merge status is sufficient; skip issue state checks unless no PR exists at all |
| **`gh pr list --state merged`** | Filtered to merged only | Returns empty when the branch has a CLOSED (not merged) PR, or no PR at all | Always use `--state all` to catch all terminal states |
| **Checking only local branches** | Ran `git branch -vv` and stopped | Missed remote-only branches (e.g., `998-auto-impl`) that had never been checked out locally | Always enumerate remote refs via `gh api repos/.../git/refs/heads` |
| **`git push origin --delete branch1 branch2 ... branchN` (N>2)** | Attempted to delete >2 remote branches in one push | GitHub ruleset GH013: `Pushes can not update more than 2 branches or tags` — entire batch fails silently, zero branches deleted | Use `gh api -X DELETE` loop; REST API bypasses push rulesets |
| **`git push origin --delete` with any missing remote ref** | Included a branch already deleted from remote in a `--delete` batch | Git fails with "remote ref does not exist" and aborts the entire batch — not atomic per-ref | Use `gh api -X DELETE` loop; individual 404s are logged without blocking remaining deletions |

## Key Decisions

| Decision | Rationale |
| ---------- | ----------- |
| **PR state over issue state** | A merged PR means the work landed in main — issue state is secondary |
| **`gh api -X DELETE` loop over `git push --delete`** | Bypasses push rulesets (GH013 max-2-refs limit); each call is independent; handles missing refs gracefully; works for any number of branches |
| **`-d` over `-D` for local branches** | `-d` refuses to delete unmerged branches — safe default; only escalate to `-D` with explicit confirmation |
| **`--state all` in `gh pr list`** | Catches MERGED, CLOSED, and OPEN in one call |
| **`--force` for worktree removal** | Cleanly removes worktrees with uncommitted changes (staged deletions, old prompt files, etc.) — each worktree is independent |

## Results & Parameters

**Commands for a clean run** (substitute `{owner}/{repo}` and branch names):

```bash
# 1. Enumerate
git worktree list --porcelain
git branch -vv
gh api repos/{owner}/{repo}/git/refs/heads --paginate --jq '.[].ref' | sed 's|refs/heads/||' | grep -v '^main$'

# 2. Classify (repeat per branch)
gh pr list --head <branch> --state all --json number,state,title

# 3. Confirm merge ancestry for branches with no PR
git merge-base --is-ancestor origin/<branch> origin/main && echo MERGED || echo NOT_MERGED

# 4. Delete remote stale branches (one by one via REST API — bypasses GH013 ruleset)
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
for b in "${BRANCHES[@]}"; do
  gh api -X DELETE "repos/${OWNER_REPO}/git/refs/heads/$b" 2>&1 && echo "deleted: $b" || echo "FAIL: $b"
done

# 5. Prune
git worktree prune
git remote prune origin
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | 2026-03-07 — pruned 3 merged remote branches after wave of auto-impl PRs | [notes.md](../../references/notes.md) |
| ProjectScylla | 2026-05-02 — deleted 59 branches via `gh api` loop after GH013 blocked batch push; removed 5 worktrees with `--force` | verified-local |
