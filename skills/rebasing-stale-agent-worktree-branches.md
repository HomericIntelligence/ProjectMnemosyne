---
name: rebasing-stale-agent-worktree-branches
description: "Use when: (1) multiple locked `.claude/worktrees/agent-*` worktrees from sub-agent runs need reconciling against main, (2) agent-generated `worktree-agent-*` branches have commits whose work has already been re-done on main with polished wording, (3) `git cherry main <branch>` reports commits as missing even though content is semantically equivalent, (4) plain `git rebase main` produces hundreds of semantic-reword conflict hunks across many branches, (5) you need to determine which agent branches still carry unique content vs. which are redundant duplicates, (6) many agent branches share identical residual diffs and can be collapsed, (7) rebase artifacts (duplicated paragraphs, misplaced sections) need to be distinguished from legitimate unique content"
category: tooling
date: 2026-04-21
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [git, rebase, worktree, agent, stale, cleanup, -X-ours, residual-diff, sub-agent]
---
# Rebasing Stale Agent Worktree Branches

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-21 |
| **Objective** | Reconcile agent-generated worktree branches whose commits have been re-done on main with slightly different wording, without grinding through 1000+ semantic-reword conflicts |
| **Outcome** | Use `git rebase -X ours` to auto-collapse reword conflicts, then hash-compare residual diffs to cluster duplicates and isolate branches with genuine unique content |

## When to Use

- 10+ locked git worktrees under `.claude/worktrees/agent-*` left over from sub-agent runs
- Each worktree has a `worktree-agent-*` branch with 1-2 commits
- `git log --oneline main..<branch>` shows commits whose subjects match commits already on main (via `git log main --grep=`)
- `git cherry main <branch>` reports commits as missing despite content being semantically equivalent
- Plain `git rebase main` produces 30+ conflicted files / 100+ hunks on the FIRST commit of the FIRST branch
- Conflicts are uniformly minor rewords of the same paragraph (e.g., "Net TPOT speedup estimate" vs "Corrected TPOT speedup estimate")
- Manual per-hunk resolution would degrade into pattern-matching "keep main" across hundreds of hunks

**Common trigger phrases:**
- "I have a bunch of locked agent worktrees left over"
- "These agent branches look like they duplicate what's already on main"
- "Rebase is producing conflicts on every file"
- "Which of these worktree-agent branches still has unique work?"

## Key Pattern Recognition

### "Audit already re-done on main"

Signals that the branch's work has been re-done on main with edits (so plain rebase will conflict uselessly):

1. `git log --oneline main..<branch>` shows fix commits whose messages match commits already on main
2. `git log main --grep="<branch commit subject>"` returns a match
3. Rebase conflicts on nearly every file, each being a trivial reword of the same paragraph
4. `git cherry main <branch>` misses commits because main's re-done versions have slightly different content (patch-id mismatch)

When all four signals are present, **do not** attempt a plain rebase or manual per-hunk review.

## Verified Workflow

### 1. Inventory

```bash
git worktree list
git branch --list 'worktree-agent-*'
```

### 2. Check for uncommitted work

```bash
for wt in .claude/worktrees/agent-*; do
  echo "== $wt =="
  git -C "$wt" status --short
done
```

### 3. Audit each branch's commits vs. main

```bash
for b in $(git branch --list 'worktree-agent-*' --format='%(refname:short)'); do
  echo "== $b =="
  git log --oneline main.."$b"
done

# Spot-check: does main already have a commit with that subject?
git log main --oneline | head -200
git log main --grep="<branch commit subject>"
```

### 4. Rebase all with prefer-main conflict resolution

```bash
for b in <branches>; do
  git checkout "$b"
  git rebase -X ours main
done
```

**Why `-X ours` is correct here:** During rebase, HEAD starts as main (the rebase target), and branch commits are replayed on top. So `ours` = main = the side you want to keep. Commits that are fully redundant get dropped as "patch contents already upstream"; commits with genuinely new content survive with a small, analyzable residual diff.

**Why this is not just "slow Option C":** Manually resolving 1000+ reword hunks devolves into pattern-matching "keep main" anyway — that's `-X ours` in disguise while pretending to do careful review. Automating it frees attention for the small residual where real judgment matters.

### 5. Hash-compare residual diffs

```bash
for b in <rebased-branches>; do
  h=$(git diff main.."$b" | sha256sum | cut -c1-12)
  echo "$h  $b"
done | sort
```

Identical hashes = duplicate branches. Keep one, drop the rest.

### 6. Per-file stat analysis for near-duplicates

```bash
for b in <branches>; do
  echo "== $b =="
  git diff --stat main.."$b"
done
```

Identical `--stat` output across a group reveals clusters even when hashes differ slightly.

### 7. Manual inspection of outliers

For each uniquely-stat'd branch, read the diff end-to-end. Look specifically for:

- **Duplicate-paragraph artifact:** 2-line additions whose content is a verbatim copy of an immediately preceding line already on main. Happens when a branch's small non-conflicting change sits adjacent to a hunk where main has the same paragraph, so `-X ours` inserts the branch's line *next to* main's identical line.
- **Structural placement breakage:** A branch's non-conflicting block lands at a position that conflicted with restructured content on main. `-X ours` resolves the conflict but the block ends up effectively replacing main's content. Diff stats can't flag this — only reading the diff can.

Example (observed): `worktree-agent-a1babe44` inserted its §Accuracy section at a location that conflicted with main's §6.3 Experimental Path. The rebase succeeded but the branch's block displaced main's content in the residual diff — discard.

### 8. Per-hunk keep/drop decisions on the small residual

Once clusters are collapsed and outliers classified, cherry-pick or commit only the hunks that carry genuine new content.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Plain `git rebase main` on first branch | 39 files x ~107 conflict hunks in the first commit alone; projected ~1000+ hunks across 13 branches | Plain rebase is impractical when main has re-done the same audit with polished rewording |
| 2 | Manually resolve each conflict hunk by "understanding intent" | Every hunk was a trivial reword of the same sentence; real resolution devolves into pattern-matching "keep main" across hundreds of hunks | Manual per-hunk review isn't "doing the work properly" when the work is 95% identical rewording — it's just slow Option-C |
| 3 | `git cherry main <branch>` to detect redundancy | Patch-id matching missed most branch commits because main's re-done versions had slightly different content | `git cherry` works for clean cherry-picks, not for "re-done from scratch with edits" |

## Results & Parameters

- 13 branches reduced to analyzable small diffs
- 7 branches collapsed to byte-identical residual diffs (keep 1, drop 6)
- 4 branches had real unique content worth cherry-picking
- 2 branches produced pure garbage (duplicate paragraphs from `-X ours` artifacts)
- 1 branch had a broken structural placement (discard)

## Gotchas

- **`ours` vs `theirs` in rebase is inverted from merge.** In a merge, `ours` = your current branch. In a rebase, the current branch is detached onto the target, so `ours` = the target (main). If you confuse them, you'll silently keep the stale agent wording and lose main's polish.
- **Diff stats are necessary but not sufficient.** 7 branches had identical stats (4 files, 68 insertions) and were true duplicates, but 1 branch also had clean-looking stats yet contained a broken structural placement. Always read outlier diffs.
- **Locked worktrees must be unlocked or force-removed** before cleanup: `git worktree unlock <path>` then `git worktree remove <path>`, or `git worktree remove --force <path>`.
