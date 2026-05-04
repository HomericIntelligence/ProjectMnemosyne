---
name: rebasing-stale-agent-worktree-branches
description: "Use when: (1) multiple locked `.claude/worktrees/agent-*` worktrees from sub-agent runs need reconciling against main, (2) agent-generated `worktree-agent-*` branches have commits whose work has already been re-done on main with polished wording, (3) `git cherry main <branch>` reports commits as missing even though content is semantically equivalent, (4) plain `git rebase main` produces hundreds of semantic-reword conflict hunks across many branches, (5) you need to determine which agent branches still carry unique content vs. which are redundant duplicates, (6) many agent branches share identical residual diffs and can be collapsed, (7) rebase artifacts (duplicated paragraphs, misplaced sections) need to be distinguished from legitimate unique content, (8) user says 'rebase all branches' but `gh pr list --state open` returns 0 results — full batch is actually cleanup not rebase, (9) `git branch -vv` shows many branches 'ahead 1, behind N' after a myrmidon swarm session — squash-merge artifact pattern not stale branches needing rebase, (10) all branches with open PRs show the same MERGED PR ID in `gh pr list --head <branch> --state all` — squash-merge wave completed, nothing to rebase, (11) `hephaestus-tidy` or `gh tidy` identifies orphaned `worktree-agent-*` branches with rebase conflicts after `git pull` advanced main, (12) need to decide whether to delete or rebase a cherry=1 no-PR branch — check whether target file still exists on main first"
category: tooling
date: 2026-05-03
version: "1.2.0"
user-invocable: false
verification: verified-local
history: rebasing-stale-agent-worktree-branches.history
tags: [git, rebase, worktree, agent, stale, cleanup, -X-ours, residual-diff, sub-agent, squash-merge, cherry, pre-flight, orphan, conflict-markers, union-merge, history-file]
---
# Rebasing Stale Agent Worktree Branches

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Reconcile agent-generated worktree branches whose commits have been re-done on main with slightly different wording, without grinding through 1000+ semantic-reword conflicts; also determine which orphaned cherry=1 no-PR branches are safe to delete vs. require actual rebase |
| **Outcome** | Use `git rebase -X ours` to auto-collapse reword conflicts, then hash-compare residual diffs to cluster duplicates and isolate branches with genuine unique content; use file-existence check to safely prune orphaned branches already absorbed by consolidation PRs |
| **Verification** | verified-local |
| **History** | [changelog](./rebasing-stale-agent-worktree-branches.history) |

## When to Use

- 10+ locked git worktrees under `.claude/worktrees/agent-*` left over from sub-agent runs
- Each worktree has a `worktree-agent-*` branch with 1-2 commits
- `git log --oneline main..<branch>` shows commits whose subjects match commits already on main (via `git log main --grep=`)
- `git cherry main <branch>` reports commits as missing despite content being semantically equivalent
- Plain `git rebase main` produces 30+ conflicted files / 100+ hunks on the FIRST commit of the FIRST branch
- Conflicts are uniformly minor rewords of the same paragraph (e.g., "Net TPOT speedup estimate" vs "Corrected TPOT speedup estimate")
- Manual per-hunk resolution would degrade into pattern-matching "keep main" across hundreds of hunks
- **User says "rebase all branches"** but `gh pr list --state open` returns 0 results — full batch is actually cleanup, not rebase
- **`git branch -vv` shows many branches "ahead 1, behind N"** after a myrmidon swarm session — this is the squash-merge artifact pattern, not stale branches needing rebase
- **All branches with open PRs show the same MERGED PR ID** in `gh pr list --head <branch> --state all` — implies squash-merge wave completed, nothing to rebase
- **`hephaestus-tidy` or `gh tidy` reports orphaned `worktree-agent-*` branches with rebase conflicts** — need to decide delete vs. rebase per-branch before agents handle them
- **cherry=1, no PR branches** — must check whether the target file still exists on main before attempting any rebase

**Common trigger phrases:**
- "I have a bunch of locked agent worktrees left over"
- "These agent branches look like they duplicate what's already on main"
- "Rebase is producing conflicts on every file"
- "Which of these worktree-agent branches still has unique work?"
- "Rebase all branches against main"
- "These branches show ahead 1, behind N — are they stale?"
- "hephaestus-tidy found 10 branches with rebase conflicts"

## Key Pattern Recognition

### "Audit already re-done on main"

Signals that the branch's work has been re-done on main with edits (so plain rebase will conflict uselessly):

1. `git log --oneline main..<branch>` shows fix commits whose messages match commits already on main
2. `git log main --grep="<branch commit subject>"` returns a match
3. Rebase conflicts on nearly every file, each being a trivial reword of the same paragraph
4. `git cherry main <branch>` misses commits because main's re-done versions have slightly different content (patch-id mismatch)

When all four signals are present, **do not** attempt a plain rebase or manual per-hunk review.

### "Squash-merge artifact" — ahead-1 branches

When a repo uses squash merges for PRs, every branch that was merged will appear as "ahead 1, behind N" in `git branch -vv`. This is **not** evidence of unmerged work. The branch's original commit SHA was never reused — only the squashed commit on main carries the content. `git cherry origin/main <branch>` will return 0 for every such branch.

### "Orphaned agent branch" — cherry=1, no PR (NEW in v1.2.0)

When `gh tidy` classifies a branch as `cherry=1` (one unique commit) and no open PR exists, it does **not** automatically mean the branch should be rebased. The consolidation PR may have already absorbed the branch's target file. Always check file existence on main before rebasing.

### "Orphaned conflict markers" (NEW in v1.2.0)

Files can contain leftover `<<<<<<<` / `=======` / `>>>>>>>` markers from prior PRs that were merged without being cleaned up. These look like rebase artifacts but are actually committed content. The discarded half of such a marker may contain real content that should be committed. Always inspect both halves of the marker before discarding either.

## Verified Workflow

### Quick Reference

```bash
# Step 0: check if anything to rebase
gh pr list --state open --json number,headRefName,mergeStateStatus

# Decision tree for orphaned cherry=1 no-PR branch
git show "origin/main:<file>" > /dev/null 2>&1 && echo EXISTS || echo DELETED
# DELETED → consolidation PR already absorbed this; delete the branch safely
# EXISTS  → conflict needs real resolution; proceed to worktree rebase below

# Per-branch worktree rebase (safe isolation)
git worktree add /tmp/wt-rebase-<short-hash> <branch>
cd /tmp/wt-rebase-<short-hash>
git rebase origin/main
# resolve conflict (see file-type rules below)
git add <file> && git rebase --continue
git push --force-with-lease origin <branch>
git -C <repo-root> worktree remove /tmp/wt-rebase-<short-hash>

# Union merge for .history files (append-only changelogs)
# Keep ALL content from both sides, newest first — never discard either half

# .md skill file conflict
# Base: take main as the authoritative version
# Add: any code blocks, table rows, Verified On entries from the branch that are NOT already on main
```

### Step 0: Pre-flight rebase gate

Before doing any rebase work, confirm there is actually something to rebase.

```bash
# Are there even open PRs to rebase?
gh pr list --state open --json number,headRefName,mergeStateStatus
# If 0 results → nothing to rebase; pivot to branch cleanup, not rebase
```

If open PRs exist, classify every "ahead" branch before touching it:

```bash
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/ | grep -v '^main$'); do
  cherry=$(git cherry origin/main "$b" 2>/dev/null | grep -c '^+')
  pr_info=$(gh pr list --head "$b" --state all --json number,state --jq '.[0] | "\(.number)|\(.state)"' 2>/dev/null)
  pr_num=$(echo "$pr_info" | cut -d'|' -f1)
  pr_state=$(echo "$pr_info" | cut -d'|' -f2)
  if [ "$cherry" = "0" ] && [ "$pr_state" = "MERGED" ]; then verdict="DONE-squash-merged"
  elif [ "$cherry" = "0" ] && [ "$pr_state" = "CLOSED" ]; then verdict="DONE-closed-superseded"
  elif [ "$pr_state" = "OPEN" ]; then verdict="REBASE_NEEDED"
  elif [ "$cherry" = "0" ]; then verdict="DONE-ancestor-of-main"
  else verdict="INVESTIGATE"
  fi
  echo "$b | cherry=$cherry | PR#${pr_num:-none} $pr_state | $verdict"
done
```

**Only proceed to Steps 1–8 for branches classified as `REBASE_NEEDED` or `INVESTIGATE`.** All `DONE-*` branches should be deleted locally (after confirming no uncommitted changes), not rebased.

### Step 0b: Decision tree for orphaned no-PR branches (cherry=1) — NEW in v1.2.0

For branches with `cherry=1` and no open PR, run this decision tree **before** attempting any rebase:

```bash
# 1. Identify the file the branch touches
git diff origin/main...<branch> --name-only

# 2. Check if that file still exists on main
git show "origin/main:<file>" > /dev/null 2>&1 && echo EXISTS || echo DELETED
```

**If DELETED**: The consolidation PR already absorbed this branch's work into main (the file was merged into a canonical location). The branch is safe to delete — its content lives on main under a different path or in a merged skill.

```bash
git branch -d <branch>
git push origin --delete <branch>
```

**If EXISTS**: The conflict is real. Classify the file type and resolve accordingly:

- **`.history` file** (append-only changelog): union merge — keep ALL content from both sides, newest entry first. Never discard either half.
- **`.md` skill file**: take main as the authoritative base, then cherry-pick additions from the branch (new code blocks, new table rows, new "Verified On" entries) that are not already present on main.

### Step 0c: Scan for orphaned conflict markers — NEW in v1.2.0

Before starting rebase work, scan for files that already contain committed conflict markers from prior merges:

```bash
grep -rl "^<<<<<<< " skills/ | grep -v ".history"
```

If any files are found, they contain committed conflict markers — these are **not** rebase artifacts. Both halves of the marker may contain real content. Inspect the diff and commit the real content from both sides before any rebase work.

```bash
# For a file with orphaned markers:
git diff HEAD -- <file>   # see what's in the file
# Manually merge both halves, remove the marker lines, commit
git add <file>
git commit -m "fix: resolve orphaned conflict markers in <file>"
```

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

**For orphaned branches where you need manual per-file resolution**, use a fresh worktree per branch to avoid polluting the main workspace:

```bash
git worktree add /tmp/wt-rebase-<short-hash> <branch>
cd /tmp/wt-rebase-<short-hash>
git rebase origin/main
# resolve conflict per file-type rules (see Step 0b)
git add <file> && git rebase --continue
git push --force-with-lease origin <branch>
git -C <repo-root> worktree remove /tmp/wt-rebase-<short-hash>
```

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
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Plain `git rebase main` on first branch | 39 files x ~107 conflict hunks in the first commit alone; projected ~1000+ hunks across 13 branches | Plain rebase is impractical when main has re-done the same audit with polished rewording |
| 2 | Manually resolve each conflict hunk by "understanding intent" | Every hunk was a trivial reword of the same sentence; real resolution devolves into pattern-matching "keep main" across hundreds of hunks | Manual per-hunk review isn't "doing the work properly" when the work is 95% identical rewording — it's just slow Option-C |
| 3 | `git cherry main <branch>` to detect redundancy | Patch-id matching missed most branch commits because main's re-done versions had slightly different content | `git cherry` works for clean cherry-picks, not for "re-done from scratch with edits" |
| 4 | Mass rebase of all "ahead" branches without cherry check | All 57 branches were squash-merged; `git cherry origin/main` = 0 for every single branch; rebasing would have produced empty commits or reword conflicts with no useful output | Always run `git cherry origin/main <branch>` before rebasing; "ahead N" in `git branch -vv` is a squash-merge artifact, not evidence of unmerged work |
| 5 | Letting `hephaestus-tidy` swarm handle 10 orphaned branch rebases automatically | All swarm agents crashed with `rate_limit_event` before completing any rebases | Do not dispatch a swarm for serial rebase operations that hit per-minute API limits — handle manually or with sequential per-branch worktrees |
| 6 | `git checkout -- <file>` to clear rebase conflict artifacts | Safety Net blocks this command even when the changes are pure conflict markers; the file may also contain real content in the discarded half | Inspect `git diff HEAD -- <file>` first; commit real content rather than discarding it with checkout |
| 7 | Assuming all cherry=1 / no-PR branches are safe to delete | 5 of 10 branches had a target file that still EXISTS on main — their conflicts were real and required per-file resolution | Always run `git show "origin/main:<file>"` before deleting a cherry=1 no-PR branch; file deletion on main is the only safe-delete signal |

## Results & Parameters

- 13 branches reduced to analyzable small diffs (from the original rebase scenario)
- 7 branches collapsed to byte-identical residual diffs (keep 1, drop 6)
- 4 branches had real unique content worth cherry-picking
- 2 branches produced pure garbage (duplicate paragraphs from `-X ours` artifacts)
- 1 branch had a broken structural placement (discard)
- Session 2026-04-25: 57 branches all showing "ahead 1" — 0 open PRs, cherry=0 for every branch → entire batch was cleanup, not rebase
- Session 2026-05-03: 10 orphaned `worktree-agent-*` branches after `gh tidy` post-pull:
  - 5 deleted (target file DELETED on main — consolidation already absorbed): `a2de5d57`, `a6355b84`, `a6c7643e`, `a9085ab3`, `ae0c8445`
  - 5 rebased successfully (target file EXISTS): `a1e38373`, `a5b83835`, `a5c86f82`, `a77f8645`, `a8665a13`
  - 2 additional files with orphaned conflict markers fixed: `fix-stale-agent-crossrefs.md`, `mojo-bitcast-always-inline-crash-fix.md`

## Gotchas

- **`ours` vs `theirs` in rebase is inverted from merge.** In a merge, `ours` = your current branch. In a rebase, the current branch is detached onto the target, so `ours` = the target (main). If you confuse them, you'll silently keep the stale agent wording and lose main's polish.
- **Diff stats are necessary but not sufficient.** 7 branches had identical stats (4 files, 68 insertions) and were true duplicates, but 1 branch also had clean-looking stats yet contained a broken structural placement. Always read outlier diffs.
- **Locked worktrees must be unlocked or force-removed** before cleanup: `git worktree unlock <path>` then `git worktree remove <path>`, or `git worktree remove --force <path>`.
- **"ahead 1, behind N" is the squash-merge artifact.** After a squash-merge wave, every merged branch will show this pattern. It does not mean those branches need rebasing — it means they've been absorbed into main and should be deleted.
- **Always check open PRs first.** If `gh pr list --state open` returns 0 results, there is nothing to rebase. Pivot immediately to branch cleanup.
- **cherry=1 / no-PR does NOT mean delete.** Half of such branches may still have unique content. Run `git show "origin/main:<file>"` before deleting.
- **Orphaned conflict markers survive merges.** Two files in this session had committed `<<<<<<`/`=======`/`>>>>>>>` markers from prior PRs. The discarded half contained real content. Always inspect both halves.
- **Use per-branch worktrees for manual resolution.** Resolving conflicts inline in the shared clone pollutes the workspace if the session is interrupted. A worktree per branch is clean and disposable.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | Session 2026-04-25 — 57-branch squash-merge cleanup | v1.0.0 initial |
| ProjectMnemosyne | Session 2026-04-25 — pre-flight gate + squash-merge artifact pattern | v1.1.0 amendment |
| ProjectMnemosyne | Session 2026-05-03 — 10 orphaned `worktree-agent-*` branches after `gh tidy` post-pull | v1.2.0 amendment |
