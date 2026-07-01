---
name: git-branch-state-triage-and-recovery
description: >-
  Diagnose and recover branches that have entered an invalid or obsolete state. Use when:
  (1) a branch is many commits behind main and its remote tracking ref is gone,
  (2) a branch has no common ancestor with main and needs content extraction,
  (3) stacked or diverged PR fixes must be cherry-picked onto the correct tip,
  (4) a branch has many HEAD-only files after main-side consolidation,
  (5) a squash-merged branch looks unmerged because git cherry/ahead counts lie,
  (6) an auto-merge PR already merged, its remote head ref is gone or stale, and a
  validated local amended commit must be converted into a clean follow-up branch from
  current trunk using git diff --binary plus git apply --index, (7) the current branch has an already-merged PR but contains uncommitted follow-up work, so stash it, create a fresh branch from current trunk, pop the stash, re-verify, sign, push, and open a new linked PR, or (8) an issue has a closed unmerged PR whose branch can be rebased and force-with-lease updated, but GitHub refuses `gh pr reopen`, so you need a replacement PR from the same recovered branch.
category: tooling
date: 2026-07-01
version: "1.5.0"
user-invocable: false
verification: verified-local
history: git-branch-state-triage-and-recovery.history
tags: [git, branch, triage, recovery, stale, superseded, orphan, diverged, merge-base, cherry-pick, fork-point, diff-filter, unrelated-histories, non-fast-forward, consolidation, three-way-diff, count-diff, hard-reset, stash, auto-merge, follow-up-branch, force-with-lease, git-apply, current-branch, merged-pr, closed-pr, replacement-pr, uncommitted-follow-up, signed-commit]
---

# Git Branch State Triage and Recovery

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-01 |
| **Objective** | Diagnose what state a branch is in (stale/superseded, orphaned/unrelated history, or diverged from remote) and recover it cleanly |
| **Outcome** | Success — unified triage tree: confirm-and-discard superseded branches, extract+recreate orphan branches, reset+cherry-pick diverged branches, convert validated local amended commits from already-merged PRs into clean follow-up branches, move uncommitted follow-up work off a branch whose prior PR is already merged, and recover closed unmerged PR branches into replacement PRs when GitHub refuses reopen |
| **Verification** | verified-local |

## When to Use

Use this skill whenever a branch is in an unexpected or unmergeable state. The root question
is always: **what state is this branch in, and how do I recover it?** Six distinct states:

**State A — Stale / superseded by main:**
- A branch is many commits behind main **and** its remote tracking ref is gone (`[gone]` in `git branch -vv`)
- The task is "get all open PRs merged" — check `gh pr list --state open` first; if zero open PRs the premise has changed
- A `git diff origin/main...HEAD` shows a large file count difference but you suspect most of it is merge noise
- Staged files with AD status in `git status --short` (added in index, deleted from working dir)
- Hundreds or thousands of HEAD-only files exist vs main, and main has commit messages like "consolidate N skills into X" or "absorb C086" — this is a **corpus consolidation** divergence, not unique unmerged work
- A branch **looks unmerged but is actually subsumed by a squash-merge**: `git cherry origin/main <branch>` shows every commit with a `+` prefix, `git rev-list --count origin/main..<branch>` reports commits "ahead", and an auto-rebase onto main **conflicts** — yet the branch's PR was already squash-merged. Squash gives the merged work a brand-new patch-id, so `git cherry` never matches and these signals are **false positives**. Disambiguate with message-search on main, **not** git cherry / ahead-counts (see "Squash-merge false positive" below). A worktree showing "uncommitted modified files" can be the same false alarm — verify with a 0-unique-lines diff against main

**State B — Orphan / unrelated history:**
- `git merge-base` returns nothing between branch and main
- Error: "fatal: refusing to merge unrelated histories"
- Branch appears to have a completely different commit history (suspect: pushed from wrong repo)
- PR shows massive unexpected file changes

**State C — Diverged from remote:**
- `git push` fails with "non-fast-forward" on a feature branch
- `git status` shows "Your branch and 'origin/<branch>' have diverged"
- A fix commit exists locally but the remote has accumulated additional commits (e.g. after a rebase or stacked-PR retarget)
- A fix plan assumed the remote was behind, but it actually has more commits than local

**State D — Already-merged PR; old head ref stale/gone; local amended commit has follow-up work:**
- `git push --force-with-lease origin <branch>` rejects as stale after auto-merge had been enabled
- `git fetch origin <branch>` fails with "couldn't find remote ref" because the PR head branch was deleted after merge
- `gh pr view <pr>` shows `state: MERGED` and an old `headRefOid`, while current trunk contains the merged work under a new squash/rebase commit SHA
- You have a local amended commit that was already validated, but the old PR branch is no longer the correct target
- The right recovery is to diff current trunk to the validated local commit, apply that binary patch on a fresh branch from trunk, prove the new tree matches the validated commit, then open a follow-up PR

**State E — Current branch's old PR is already merged, but the worktree has uncommitted follow-up work:**
- `gh pr view` for the current branch reports `state: MERGED`.
- The branch may still exist on origin, but its PR identity is spent; pushing more commits to it will not update an open PR.
- `git status --short` shows real uncommitted follow-up work that should become a new PR.
- The correct recovery is: stash including untracked files, fetch current trunk, create a fresh branch from `origin/<trunk>`, pop the stash, re-run verification, sign a new commit, push, and create a new issue-linked PR.

**State F — Closed unmerged PR; branch ref recovered; GitHub refuses reopen:**
- The issue is still open, but its old PR is `CLOSED` rather than `MERGED`.
- `gh pr reopen <old-pr>` fails even after you rebase and force-with-lease push the old branch, for example `GraphQL: Could not open the pull request`.
- `gh pr view` / `gh pr list --head` can keep showing stale closed-PR `headRefOid` metadata, while `git ls-remote --heads origin <branch>` proves the branch ref moved.
- The correct recovery is: create a detached `/tmp` worktree from the remote branch, rebase onto current `origin/main`, resolve conflicts semantically against current main, push `HEAD:<branch>` with `--force-with-lease`, try reopen once, then create a replacement PR from the same updated branch and link the old closed PR in the body if reopen is refused.

## Verified Workflow

### Quick Reference

```bash
# === Triage: which state am I in? ===
git branch -vv | grep "$(git rev-parse --abbrev-ref HEAD)"   # [gone] = remote ref deleted
git merge-base HEAD origin/main || echo "ORPHAN: no common ancestor"  # empty = State B
git status                                                    # "diverged" = State C

# === State A: stale / superseded by main ===
gh pr list --state open                          # check premise FIRST
FORK=$(git merge-base HEAD origin/main)           # fork point
git ls-tree --name-only -r HEAD skills/ | sort > /tmp/head.txt
git ls-tree --name-only -r origin/main skills/ | sort > /tmp/main.txt
comm -23 /tmp/head.txt /tmp/main.txt              # HEAD-only files (maybe new, maybe old)
git log --diff-filter=D --oneline origin/main -- <path> | head -1  # how main disposed of it
# staged-index no-op check:
git ls-files --stage | awk '{print $1, $4}' | sort > /tmp/staged.txt
git ls-tree -r origin/main | awk '{print $3, $4}' | sort > /tmp/mainh.txt
comm -23 /tmp/staged.txt /tmp/mainh.txt           # staged files NOT on main = true new work

# === State A: squash-merge FALSE POSITIVE — do NOT trust git cherry / ahead-counts ===
# These LIE on squash repos (squash = new patch-id, cherry never matches):
git cherry origin/main <branch>                   # every commit shows '+' even when subsumed
git rev-list --count origin/main..<branch>        # >0 "ahead" even when subsumed
# Reliable disambiguator — message-search on main for the squash commit (PR number / subject):
git log origin/main --oneline | grep -iE '<distinctive phrase or (#PRnum)>'
# found on main  => branch is SUBSUMED: safe to discard, no rebase/PR. Cross-check PR state:
gh pr list --head <branch> --state all --json number,state   # MERGED/CLOSED corroborates
# rebase conflicts on a subsumed branch are EXPECTED (squash content on main collides with the
# original un-squashed commits). Report "subsumed" and STOP — do not resolve, do not auto-delete.

# === State A: worktree "uncommitted modified files" 0-unique-lines redundancy check ===
# A modified working-tree file can be byte-for-byte already on main (it shipped via a merged PR):
diff <(git show origin/main:<path>) <(cat <worktree>/<path>) | grep -c '^>'  # 0 = no unique lines
# 0 unique lines on ALL modified files => the "uncommitted work" already merged; safe to discard.

# === State A (large-scale): three-way count diff for consolidation divergence ===
MERGE_BASE=$(git merge-base HEAD origin/main)
git ls-tree -r --name-only "$MERGE_BASE" skills/ | grep '\.md$' | sort > /tmp/base.txt
git ls-tree -r --name-only HEAD skills/ | grep '\.md$' | sort > /tmp/branch.txt
git ls-tree -r --name-only origin/main skills/ | grep '\.md$' | sort > /tmp/main2.txt
wc -l /tmp/base.txt /tmp/branch.txt /tmp/main2.txt  # counts: base→branch grew? base→main shrank?
comm -23 /tmp/branch.txt /tmp/main2.txt | wc -l     # branch-only (pre-consolidation originals?)
comm -13 /tmp/branch.txt /tmp/main2.txt | wc -l     # main-only (new canonical merged skills?)
# if main shrank (consolidation) and branch-only are old originals absorbed by main:
git log --oneline origin/main | grep -iE 'consolidat|absorb|merge.*skill|cluster' | head -10
# safety: stash before any hard-reset (recoverable snapshot)
git stash push -u -m "pre-reset snapshot $(date +%Y%m%d)"
git log --oneline origin/main..HEAD                  # confirm only superseded commits

# === State B: orphan / unrelated history ===
git fetch origin <branch>
git merge-base origin/main origin/<branch>        # empty = orphan
git log --oneline origin/<branch> | tail -10      # oldest commits reveal origin repo
git ls-tree --name-only origin/<branch> | head    # unexpected files = wrong repo
git show origin/<branch>:<path> > /tmp/extracted   # extract before deleting
git log --oneline origin/main -- <path>           # CHECK: already merged on main?
git push origin --delete <branch>                 # delete broken branch

# === State C: diverged from remote ===
git log --oneline origin/<branch>..HEAD           # local-only commits
git log --oneline HEAD..origin/<branch>           # remote-only commits (often forgotten!)
git merge-base HEAD origin/<branch>               # common ancestor
git reset --hard origin/<branch>                  # absorb remote, AFTER confirming fix applies
git cherry-pick <fix-sha>                         # apply only the targeted fix

# === State D: old PR merged; remote branch deleted; preserve validated local delta ===
# Use the repository's real trunk: origin/main for most repos, origin/master for Inference360.
TRUNK=origin/master
VALIDATED_SHA=<validated-local-amended-sha>
PATCH=/tmp/<topic>-followup.patch
git fetch origin master
gh pr view <old-pr> --json state,headRefName,headRefOid,autoMergeRequest,mergeCommit
git fetch origin <old-branch>                     # expected failure if the branch was deleted
git diff --stat "$TRUNK" "$VALIDATED_SHA"         # inspect the intended incremental delta
git diff --binary "$TRUNK" "$VALIDATED_SHA" --output="$PATCH"
git switch -c <followup-branch> "$TRUNK"
git apply --index "$PATCH"
git diff --quiet "$VALIDATED_SHA" -- .            # proves worktree matches validated commit
git commit -m "<follow-up message>"
git push -u origin <followup-branch>

# === State E: current branch PR is MERGED but uncommitted follow-up work exists ===
gh pr view --json number,state,title,url,headRefName,baseRefName
# If state == MERGED, do not commit/push more work to that branch for a new PR.
git stash push -u -m <topic>-before-fresh-pr
git fetch origin <trunk>
git checkout -b <fresh-branch> origin/<trunk>
git stash pop
./.venv/bin/python -m ruff check radiance scripts tests --no-cache
./.venv/bin/pytest -q
git add -A
git commit -S -m "<message>"
git log --show-signature -1 --oneline
git push -u origin <fresh-branch>
gh issue create --title "<tracking issue>" --body "<kickoff/scope>"
gh pr create --base <trunk> --head <fresh-branch> --title "<title>" --body "Closes #<issue>"

# === State F: CLOSED unmerged PR branch recovery; reopen refused ===
ISSUE=<issue>
OLD_PR=<closed-pr>
BRANCH=<old-branch>
git ls-remote --heads origin "$BRANCH"              # authoritative branch ref
git worktree add --detach /tmp/<issue>-recovery "origin/$BRANCH"
git -C /tmp/<issue>-recovery fetch origin main
git -C /tmp/<issue>-recovery rebase origin/main
# Resolve conflicts semantically; keep current-main architecture where stale branch intent is obsolete.
git -C /tmp/<issue>-recovery push --force-with-lease origin HEAD:"$BRANCH"
gh pr reopen "$OLD_PR" --repo OWNER/REPO            # try once
gh pr create --repo OWNER/REPO --base main --head "$BRANCH" \
  --title "<replacement title>" \
  --body "$(printf 'Replaces closed PR #%s after rebasing the recovered branch.\\n\\nCloses #%s\\n' "$OLD_PR" "$ISSUE")"
git log origin/main..HEAD --format='%h %G? %GS'     # signatures
python3 scripts/check_conventional_commit.py -
python3 scripts/check_dco_signoff.py -
```

### Detailed Steps

#### State A — Stale-branch-superseded-by-main diagnosis

1. **Check the premise**: run `gh pr list --state open` before any branch archaeology. If
   there are zero open PRs, the task "get all PRs merged" is already done — report and stop.
2. **Find the fork point**: `git merge-base HEAD origin/main` gives the SHA where the branch
   diverged. All analysis is relative to this point.
3. **Three-way file inventory**: compare `git ls-tree` outputs for HEAD and origin/main on
   the relevant directories, piped through `sort` then `comm` → three sets: HEAD-only,
   main-only, both.
4. **For each HEAD-only file**: run `git log --diff-filter=D --oneline origin/main -- <path>`.
   A commit message containing "consolidate", "merge", or "absorb" means main intentionally
   deleted it via a consolidation PR. An empty result means the file genuinely never reached
   main (rare for an old branch).
5. **For each file in both**: compare `version:` frontmatter. If main's version number is
   strictly greater, main has the newer copy and the branch's change is stale.
6. **Staged index check**: if `git status --short` shows many AD-status files (added in index,
   deleted in working tree), hash-compare `git ls-files --stage` against `git ls-tree
   origin/main`. If every staged hash matches a main hash, the staged index is a no-op.
7. **Apply the three-condition test** — a branch is fully superseded when **all three** hold:
   - Its deletions are already absent from main, AND
   - Its modified files have lower version numbers than main's, AND
   - Its "new" files are already present on main.

   When all three hold the branch has zero net contribution and can be discarded.

#### State A (squash-merge) — `git cherry` false positive, message-search disambiguator

On repos where PRs are **squash-merged** (the default on many repos), the commit-level
"is this on main?" tools cannot be trusted:

- `git cherry origin/main <branch>` shows **every** branch commit with a `+` prefix (its
  meaning is "this patch is not on main"), so a fully-merged branch looks entirely unmerged.
- `git rev-list --count origin/main..<branch>` reports the branch is N commits **ahead**.

Both are **false positives**. The reason: squash-merge collapses the branch's commits into a
single brand-new commit on main with a **different patch-id**. `git cherry`'s patch-id
matching never matches the branch's original commits, and the original commits are genuinely
not reachable from main, so the ahead-count is non-zero. **Neither signal means the work is
unmerged.**

The reliable disambiguator is **message-search on main**. Take a distinctive phrase from the
branch's commit subject (or the PR title), and grep main's history:

```bash
git log origin/main --oneline | grep -iE '<distinctive phrase or (#PRnum)>'
```

If the squash commit is found on main, the branch is **subsumed** — safe to discard, no
rebase and no PR required. Cross-check the PR state to corroborate:

```bash
gh pr list --head <branch> --state all --json number,state   # MERGED / CLOSED corroborates
```

Important consequence: when you try to auto-rebase a subsumed branch onto main it will
**conflict**, *precisely because* the same changes already exist on main as a squash commit
and the branch's original un-squashed commits collide with them. **A rebase conflict on a
subsumed branch is expected and is NOT evidence of unmerged work.** Correct action:

- Report "subsumed" and **stop**. Do **not** spawn a conflict-resolution swarm — every
  resolution would be "take main's side" on every file, producing an empty branch with zero
  net benefit.
- Do **not** auto-delete the branch. Branch deletion is left to the user / gh-tidy's own
  y/N prompts (and is Safety-Net-blocked anyway — see below).

**Worktree-redundancy variant.** A worktree reporting "uncommitted modified files" can be the
same false alarm. Diff each working-tree file against `origin/main` and count unique lines:

```bash
diff <(git show origin/main:<path>) <(cat <worktree>/<path>) | grep -c '^>'
```

`0` unique lines on **all** modified files means the "uncommitted work" is byte-for-byte
already on main (it shipped via a merged PR); the worktree is safe to discard. Real example:
worktree `agent-a7fe2df2b7f6e658b` had 3 modified files all showing 0 unique lines vs main —
the `log_on_error` changes had already merged via PR #1372.

**Destructive ops are Safety-Net-blocked — hand them to the user.** Once safety is proven
(subsumed / 0-unique-lines), the *recovery* commands are blocked by the CC Safety Net hook
even with in-conversation user approval; the assistant cannot override the hook and must print
the exact command for the **user** to run manually:

- `git checkout -- <file>` (discards tracked changes) — "use `git stash` first", then hand to user
- `git worktree remove --force <path>` (can discard uncommitted work) — hand to user
- `git tag -d <tag>` (deletes tags) — hand to user
- `git branch -D <branch>` — branch deletion is gh-tidy's job anyway
- `git stash drop` and `rm -rf .worktrees/` are likewise blocked

Workflow shape: **prove** safety (subsumed / 0-unique-lines), **then print** the precise
`--force` / `-d` / `checkout --` command for the user to execute.

#### State A (large-scale) — Three-way count diff for corpus-consolidation divergence

When a branch has **hundreds or thousands** of HEAD-only files vs main AND main shows
consolidation commit messages, spot-checking a few file versions is not sufficient — the
branch and main may have diverged in *opposite* directions simultaneously.

1. **Find the merge-base**: `MERGE_BASE=$(git merge-base HEAD origin/main)`. All counts are
   relative to this ancestor.
2. **Count artifacts at all three points**:
   ```bash
   git ls-tree -r --name-only "$MERGE_BASE" skills/ | grep '\.md$' | sort > /tmp/base.txt
   git ls-tree -r --name-only HEAD            skills/ | grep '\.md$' | sort > /tmp/branch.txt
   git ls-tree -r --name-only origin/main     skills/ | grep '\.md$' | sort > /tmp/main2.txt
   wc -l /tmp/base.txt /tmp/branch.txt /tmp/main2.txt
   ```
   Interpret: if `base→branch` grew (new skills added on branch) but `base→main` shrank
   (consolidation on main), the branch has old originals that main absorbed into canonical
   merged skills. The branch-only files are the **pre-consolidation originals**, not new work.
3. **Compute three comm sets**:
   - `comm -23 branch main` (branch-only): would be deleted by reset — are these old originals or new skills?
   - `comm -13 branch main` (main-only): canonical merged skills the branch is missing.
   - `comm -12 branch main` (intersection): files present in both — compare versions.
4. **Confirm consolidation on main**: `git log --oneline origin/main | grep -iE 'consolidat|absorb|cluster' | head -10`.
   Messages like "consolidate 50-cluster 516->291" confirm main ran systematic consolidation
   after the branch diverged. Branch-only files matching the pre-consolidation count at
   merge-base are the absorbed originals, not unique work.
5. **Safety: stash before any destructive reset**:
   ```bash
   git stash push -u -m "pre-reset snapshot $(date +%Y%m%d)"
   ```
   The stash is a recoverable snapshot. Confirm `git log --oneline origin/main..HEAD` contains
   only commits superseded by main's consolidation PRs before running `git reset --hard origin/main`.
6. **Surface the finding to the human** when branch-only file count is large (e.g. >500).
   The decision to hard-reset is irreversible without the stash — it's the human's data and
   they should confirm the conclusion explicitly.

#### State B — Orphan-branch recovery (no common ancestor)

1. **Diagnose**: `git fetch origin <branch>` then `git merge-base origin/main
   origin/<branch>`. No output (exit 1) = no common ancestor.
2. **Understand the divergence**: `git log --oneline origin/main..origin/<branch>` (commits
   on branch not in main) and the reverse. Then `git log --oneline origin/<branch> | tail -10`
   — unfamiliar "Initial commit" lines reveal the branch was created from a different repo.
3. **Inspect contents**: `git ls-tree --name-only origin/<branch> | head` — unexpected files
   (e.g. `.mojo-version` in a Python project) confirm a wrong-repo push.
4. **Extract valuable content** before any deletion:
   ```bash
   git show origin/<branch>:plugins/cat/name/SKILL.md > /tmp/SKILL.md
   ```
5. **Check if already merged**: `git log --oneline origin/main -- <path>`. Often the real
   content already landed via a correct PR and the orphan is just a stale duplicate — then no
   recreation is needed, just delete.
6. **Delete and (if needed) recreate**:
   ```bash
   git push origin --delete <branch>
   git checkout main && git pull origin main
   git checkout -b <branch>
   cp /tmp/extracted <path>/ && git add . && git commit -m "feat: recreated from broken branch"
   git push -u origin <branch>
   ```

   **Root cause / prevention**: orphan branches typically come from running `/learn` (or any
   commit-and-push flow) from one project's working directory while pushing to another's
   remote. Always verify `git remote -v` matches the expected repository before pushing.

#### State C — Diverged-branch cherry-pick fix

1. **Diagnose the divergence**: `git status` shows "diverged, N and M different commits". Run
   both `git log --oneline origin/<branch>..HEAD` (local-only) AND `git log --oneline
   HEAD..origin/<branch>` (remote-only). The remote-only side is the one usually forgotten —
   a fix plan may claim "just push" while the remote has accumulated commits since.
2. **Understand each side**: `git show origin/<branch>:path/to/file` to see the remote's
   current version; `git show <fix-sha> --stat` to see exactly what the local fix touches.
   Confirm the fix applies cleanly on top of the remote tip.
3. **Reset local to remote tip** (only after confirming the fix applies):
   `git reset --hard origin/<branch>`.
4. **Cherry-pick the minimal fix**: `git cherry-pick <fix-sha>`. Resolve any conflicts, then
   `git cherry-pick --continue`. Cherry-pick the targeted fix only — never the full local
   commit stack, which may duplicate an equivalent commit already on the remote.
5. **Verify**: `git status` should show "ahead by 1 commit"; `git show HEAD --stat` confirms
   the fix is present. Then push (fast-forward now succeeds).

   This same pattern recovers stacked-PR fix commits: when a stacked PR is retargeted and
   lint/CI fix commits made after the retarget become orphaned from the prerequisite, reset to
   the correct remote tip and cherry-pick the orphaned fix commits onto it.

#### State D — Already-merged PR with deleted head ref; recover follow-up delta

Use this when the PR merged before you could update it, the remote PR branch is gone or stale,
and you have a local amended commit that contains exactly the validated follow-up work. Do not
try to keep force-pushing the old branch; after merge, the correct target is current trunk.

1. **Confirm the old PR is no longer writable as a PR update target.** A stale lease rejection
   plus a missing remote ref means this is not a normal rebase push:
   ```bash
   git push --force-with-lease origin <old-branch>  # rejected as stale
   git fetch origin <old-branch>                    # fatal: couldn't find remote ref
   gh pr view <old-pr> --json state,headRefName,headRefOid,autoMergeRequest,mergeCommit
   ```
   If `state` is `MERGED`, stop targeting `<old-branch>`. The PR content is already on trunk,
   usually as a new squash/rebase commit SHA that does not equal the old PR head SHA.
2. **Refresh trunk and compare the validated local tree to trunk.** Use the repo's real trunk
   branch (`origin/master` for Inference360, `origin/main` for most HomericIntelligence repos):
   ```bash
   git fetch origin master
   TRUNK=origin/master
   VALIDATED_SHA=<validated-local-amended-sha>
   git diff --stat "$TRUNK" "$VALIDATED_SHA"
   ```
   The diff must show only the intended follow-up changes. If it includes the already-merged PR
   body again, your trunk ref is stale or you picked the wrong validated SHA.
3. **Save a binary patch from trunk to the validated local commit.** Binary mode preserves
   renames, mode bits, and binary files:
   ```bash
   PATCH=/tmp/<repo>-<topic>-followup.patch
   git diff --binary "$TRUNK" "$VALIDATED_SHA" --output="$PATCH"
   ```
4. **Create the follow-up branch from current trunk and apply the patch into the index.**
   ```bash
   git switch -c <followup-branch> "$TRUNK"
   git apply --index "$PATCH"
   ```
5. **Prove the new branch tree matches the already-validated local commit.**
   ```bash
   git diff --quiet "$VALIDATED_SHA" -- .
   ```
   This is the key guardrail: it proves the patch-applied branch has the same tree as the
   local commit you already validated. If this diff is non-empty, fix the mismatch before
   committing.
6. **Commit, push, and open a normal follow-up PR.** Enable auto-merge on the new PR; the old
   merged PR should remain untouched.
   ```bash
   git commit -m "<follow-up message>"
   git push -u origin <followup-branch>
   gh pr create --base <trunk-branch> --head <followup-branch> --title "<title>" --body "<body>"
   gh pr merge <new-pr> --auto --squash --repo <owner/repo>
   ```

#### State E — Current branch's previous PR is merged; move uncommitted follow-up work to a fresh PR branch

Use this when `gh pr view` on the current branch points to a merged PR, but `git status` shows
new uncommitted work that should become its own review. This is different from State D: the
follow-up exists as a worktree/staged diff, not as a validated local commit that needs a binary
patch.

1. **Confirm the current branch's PR is already merged.**
   ```bash
   git status --short --branch
   gh pr view --json number,state,title,url,headRefName,baseRefName
   ```
   If `state` is `MERGED`, treat the current branch name as historical. Do not create a new PR
   from that same branch, because GitHub will associate it with the closed/merged PR context.
2. **Stash the follow-up diff, including untracked files.**
   ```bash
   git stash push -u -m <topic>-before-fresh-pr
   ```
3. **Refresh the real trunk and create a fresh branch from it.** Use the repo's actual default
   branch (`master` for Radiance in June 2026; `main` for most repos).
   ```bash
   git fetch origin <trunk>
   git checkout -b <fresh-branch> origin/<trunk>
   ```
4. **Restore the diff and resolve any base drift immediately.**
   ```bash
   git stash pop
   git status --short
   ```
   If conflicts appear, resolve them against current trunk before committing. If it applies
   cleanly, still re-run the relevant focused tests because the base changed.
5. **Re-run local verification on the fresh branch, then sign the commit.**
   ```bash
   ./.venv/bin/python -m ruff check radiance scripts tests --no-cache
   ./.venv/bin/pytest -q
   git add -A
   git commit -S -m "refactor: reduce duplicate code"
   git log --show-signature -1 --oneline
   ```
6. **Push the fresh branch and create a new linked PR.** If the repository requires one issue per
   PR, create the tracking issue before the PR and include `Closes #<issue>` in the body.
   ```bash
   git push -u origin <fresh-branch>
   gh issue create --title "<issue title>" --body "<scope and validation>"
   gh pr create --base <trunk> --head <fresh-branch> --title "<title>" --body "Closes #<issue>"
   gh pr checks <new-pr>
   ```

#### State F — Closed unmerged PR branch recovery; replacement PR when reopen is refused

Use this when an issue is still open but its old implementation PR is closed and unmerged. The
branch may still exist and may be the right carrier for recovered work, but the closed PR object
can remain stale even after the branch ref moves. Treat GitHub PR metadata as advisory and the
remote branch ref as authoritative.

1. **Confirm the old PR is closed, not merged, and inspect both PR metadata and the branch ref.**
   ```bash
   gh pr view <old-pr> --json number,state,headRefName,headRefOid,title,url
   gh pr list --head <branch> --state all --json number,state,headRefName,headRefOid,url
   git ls-remote --heads origin <branch>
   ```
   If `gh pr view` keeps reporting the old `headRefOid` after the branch moves, do not conclude
   that the push failed. `git ls-remote` is the ground truth for the ref.
2. **Recover in a detached `/tmp` worktree from the remote branch.**
   ```bash
   git worktree add --detach /tmp/<issue>-recovery origin/<branch>
   git -C /tmp/<issue>-recovery fetch origin main
   git -C /tmp/<issue>-recovery rebase origin/main
   ```
   A detached worktree prevents the user's current checkout from switching branches and keeps the
   recovery disposable after the PR is opened.
3. **Resolve conflicts semantically, not by preserving stale branch intent literally.** The stale
   branch may delete files or introduce abstractions that current main has already evolved past.
   Preserve the live architecture on `origin/main` and carry only the still-valid delta.

   ProjectHephaestus examples:
   - For issue #1442, do not delete `_interfaces.py` just because the stale branch did. Current
     main had grown `_interfaces.py` into the broader protocol-contract home. Keep it and carry
     only the still-valid tiny-module consolidation: move `work_report` into `_review_utils`,
     secret constants into `pr_manager`, and `ReviewerProtocol` into `protocol.py`.
   - For issue #1432, current main already had the broader `StateStoreProtocol` union. Skip the
     stale extra `StateStore` class commit and carry only the remaining persistence change:
     `ArmingStateStore.load()` routes through `load_state_file`.
4. **Push the recovered branch with a lease, then try reopening once.**
   ```bash
   git -C /tmp/<issue>-recovery push --force-with-lease origin HEAD:<branch>
   gh pr reopen <old-pr> --repo OWNER/REPO
   ```
   If reopen succeeds, continue with the old PR. If it fails with `GraphQL: Could not open the pull
   request`, do not keep fighting the old PR object.
5. **Create a replacement PR from the same updated branch.** Link the old PR in the body and keep
   the issue-closing line exact:
   ```bash
   gh pr create --repo OWNER/REPO --base main --head <branch> \
     --title "<title>" \
     --body "$(printf 'Replaces closed PR #%s after rebasing the recovered branch.\\n\\nCloses #%s\\n' <old-pr> <issue>)"
   ```
   The line must be exactly `Closes #N` with no trailing period for repositories whose `pr-policy`
   checks parse the body literally.
6. **If body-only edits do not re-trigger policy checks, create a synchronize event.** Amend the
   commit message or otherwise push a no-content metadata update only after confirming the repo's
   policy needs a new push. Do not stack unrelated workflow fixes into the feature PR just to turn
   CI green.
7. **Verify local policy prerequisites before relying on GitHub.**
   ```bash
   git log origin/main..HEAD --format='%h %G? %GS'
   python3 scripts/check_conventional_commit.py -
   python3 scripts/check_dco_signoff.py -
   ```
   Focused tests still matter, but PRs can remain red for unrelated current-main CI problems. Keep
   the verification label at `verified-local` until full CI passes for the replacement PR itself.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Judging staleness by spot-checking a few file `version:` fields | Compared version numbers in ~5 files on branch vs main to determine which side was "newer" | Branch and main had diverged in opposite directions: branch grew (new skills added), main shrank (consolidation). A handful of version comparisons gave a misleading picture of the whole | Run a three-way file-count diff (branch vs main vs merge-base) before drawing any conclusion when hundreds of files are involved |
| Assuming "branch's PR already merged ⇒ all branch work is on main" | Saw that an early PR (#1572) was merged and concluded the branch had no remaining contribution | An early PR merged but the bulk of the branch's subsequent commits (hundreds of new skills added after the merge) never reached main — they were simply abandoned before the branch was last touched | PR-merge history answers only "did this PR's content land?" not "has every commit on this branch landed?" — check `git log --oneline origin/main..HEAD` for the full picture |
| Committing the large working-tree deletions | Working tree showed hundreds of deleted files; first instinct was to commit them as "cleanup" | The deletions were not intentional cleanup — they were the working tree reflecting pre-consolidation originals that the index still tracked but disk did not have. Committing would have reverted ~360 skills and downgraded canonicals main had since improved | Never commit large file-count deletions without first running the three-way count diff; if `comm -23 branch main` shows thousands of "branch-only" files that map to the pre-consolidation count at merge-base, the deletions are stale state, not new work |
| Treating HEAD-only files as unmerged value | Assumed "file present in HEAD but not in main" = "work not yet on main" | Most HEAD-only files were OLD files that main subsequently deleted or consolidated through later PRs after the branch diverged | Always check HOW a file left main (`--diff-filter=D`) before assuming it was never there |
| Using plain `git log` to find deletions | `git log --oneline origin/main -- <path>` showed nothing | Plain log only shows commits that touched the file; it does not surface the deletion commit reliably | `--diff-filter=D` is required to find the commit that removed a file |
| Treating AD status as uncommitted work | `git status --short` showed hundreds of AD lines and looked like staged changes needing attention | AD status is normal for branches created in worktrees not fully restored to disk — files exist in the index but not on disk | AD means "added in index, deleted from working dir"; verify hashes match main before treating as new work |
| Direct push after local commits (diverged) | Assumed local was ahead of remote and pushed | Branches had diverged; remote had 13 additional commits not present locally | Always check `HEAD..origin/<branch>` not just `origin/<branch>..HEAD` before pushing |
| Treating a fix plan at face value | Plan said "2 commits ahead, just push" | Plan was written before the remote accumulated additional commits | Re-diagnose actual remote state with `git log --oneline HEAD..origin/<branch>` before acting |
| Keeping local commits and merging (diverged) | Would merge the local cleanup commit with the remote's equivalent | Remote already had an equivalent cleanup commit; merge would create a duplicate | Cherry-pick the minimal fix only, not the full local commit stack |
| Deleting an orphan branch before extraction | Tempted to just `git push --delete` the broken branch | Risked losing valid skill content that lived only on the branch tip | Extract content (and check whether it is already on main) before deleting |
| Relied on `git cherry origin/main <branch>` to detect unmerged work | All commits showed `+` so branches looked unmerged | Squash-merge gives every original commit a new patch-id; cherry never matches | Use message-search (`git log origin/main --oneline \| grep '(#PR)'`) + `gh pr list --state all`, not git cherry, for squash repos |
| Considered spawning a rebase-conflict-resolution swarm for 7 conflicting branches | Conflicts existed only because the squash content already on main collides with original commits | Resolution would be "take main's side" everywhere → empty branch | Confirm subsumed first; report subsumed and stop — don't resolve, don't delete |
| Assistant tried `git worktree remove --force` / `git tag -d` / `git checkout --` | Blocked by CC Safety Net hook | Cannot override the hook even with user approval in-chat | Prove safety, then print the exact destructive command for the user to run manually |
| Force-pushed a follow-up amendment to an auto-merged PR's old branch | `git push --force-with-lease origin feat/simplify-control-interface` after PR #160 had auto-merge enabled | The PR had already merged and the lease was stale; the old branch was no longer the live PR update target | Check `gh pr view <pr> --json state,headRefOid,autoMergeRequest` before pushing follow-up amendments to an auto-merge PR |
| Fetched the old PR branch after merge | `git fetch origin feat/simplify-control-interface` | GitHub had deleted the merged PR head branch, so fetch failed with "couldn't find remote ref" | Treat missing remote ref plus `state: MERGED` as a signal to create a new follow-up branch from current trunk |
| Treated the local amended commit as a branch update after merge | Local commit `530bd3114d4ae62c01d4ac11729ff4a86fab6706` was validated, so the instinct was to force-push it to PR #160 | `origin/master` already contained the original simplification under new commit `61304b9`; the old PR head SHA was `858e302`, so the branch identity was obsolete | Diff current trunk to the validated commit, apply that patch on a fresh branch, and prove the resulting tree matches the validated commit before opening a follow-up PR |
| Reused the current branch after discovering its PR was already merged | `gh pr view` on `codex/test-architecture-layout` showed PR #906 as `MERGED`, but the worktree contained new cleanup changes | A merged PR branch is historical; pushing more commits there would not create the intended fresh review and would confuse branch/PR state | Stash the uncommitted work, fetch current trunk, create a fresh branch from `origin/<trunk>`, pop the stash, re-verify, sign, push, and create a new linked PR |
| Trusted closed-PR `headRefOid` after a branch force-with-lease update | `gh pr view` / `gh pr list --head` still showed old closed PR metadata after the recovered branch was pushed | Closed PR metadata can remain pinned to the old head SHA even when the branch ref moved | Confirm branch movement with `git ls-remote --heads origin <branch>` before deciding the push failed |
| Kept retrying `gh pr reopen` after GitHub refused | `gh pr reopen <old-pr>` failed with `GraphQL: Could not open the pull request` | GitHub can refuse to reopen a closed PR even when its head branch has been updated | Try reopen once; if refused, create a replacement PR from the same recovered branch and link the old PR |
| Preserved stale branch deletion of a now-important module | The stale #1442 branch deleted `_interfaces.py` during tiny-module consolidation | Current main had evolved `_interfaces.py` into the home for broader protocol contracts; deleting it would regress architecture | Resolve conflicts against current main semantics, not stale branch shape |
| Carried an obsolete class from the stale branch | The stale #1432 branch added an extra `StateStore` class | Current main already had the broader `StateStoreProtocol` union, so the stale class was no longer the right abstraction | Skip obsolete commits and carry only the still-valid persistence behavior change |
| Used `Closes #N.` with a trailing period | PR body contained a sentence-like closing line | `pr-policy` required an exact `Closes #N` line and rejected the body | Put `Closes #N` on its own line with no trailing punctuation |
| Added unrelated CI workflow fixes to recovered feature PRs | Considered stacking the pydantic CI install fix into replacement PRs whose code was otherwise locally verified | That would mix independent concerns and make the recovered feature PRs depend on unrelated workflow churn | Keep replacement feature PRs scoped; let the dedicated CI workflow PR merge first unless the user explicitly wants stacking |

## Results & Parameters

### State F — Closed unmerged PR branch recovery with replacement PR

| Parameter | Value |
| --------- | ----- |
| Old PR state | `CLOSED`, unmerged |
| Branch truth source | `git ls-remote --heads origin <branch>` |
| Recovery worktree | Detached `/tmp/<issue>-recovery` from `origin/<branch>` |
| Base refresh | Rebase onto current `origin/main` |
| Push | `git push --force-with-lease origin HEAD:<branch>` |
| Reopen attempt | `gh pr reopen <old-pr>` once |
| Reopen failure | `GraphQL: Could not open the pull request` |
| Fallback | Replacement PR from the same updated branch |
| PR body policy | Exact `Closes #N` line, no trailing period |
| Verification level | `verified-local` until replacement PR CI passes independently |

ProjectHephaestus examples:

```text
Issue #1442 / closed PR #1696 / branch 1442-auto-impl
Replacement PR: #1731
Focused verification:
pixi run pytest tests/unit/automation/test_interfaces.py tests/unit/automation/test_loop_runner_early_exit.py tests/unit/automation/test_secret_patterns.py -v --override-ini=addopts=
# 80 passed

Issue #1432 / closed PR #1687 / branch 1432-auto-impl
Replacement PR: #1732
Focused verification:
pixi run pytest tests/unit/automation/test_arming_state.py tests/unit/automation/test_interfaces.py -v --override-ini=addopts=
# 22 passed
```

Both replacement PRs were created and reached mergeable/policy-passing state. Full CI was still
red at capture time because those PRs depended on ProjectHephaestus PR #1730's pydantic
workflow install fix, so this State F addition is `verified-local`, not `verified-ci`.

### State E — Fresh PR branch from merged current branch with uncommitted work

| Parameter | Value |
| --------- | ----- |
| Current branch | Branch whose `gh pr view` reports `state: MERGED` |
| Follow-up work state | Uncommitted/staged/untracked diff in the worktree |
| Preservation command | `git stash push -u -m <topic>-before-fresh-pr` |
| Fresh base | `origin/<trunk>` after `git fetch origin <trunk>` |
| Fresh branch | New branch name that has not already been tied to a merged PR |
| Required verification | Re-run focused/full local tests after `git stash pop`; prior tests on old base do not count |
| Commit requirement | Signed commit (`git commit -S`) and signature verification with `git log --show-signature -1` |
| PR requirement | New issue-linked PR; include `Closes #<issue>` when repo policy requires it |
| Verification level | `verified-local` until GitHub checks pass |

Radiance example commands used:

```bash
gh pr view --json number,url,state,title,headRefName,baseRefName
git stash push -u -m codex-duplicate-cleanup-before-pr
git fetch origin master
git checkout -b codex/reduce-duplicate-code origin/master
git stash pop
./.venv/bin/python -m ruff check radiance scripts tests --no-cache
./.venv/bin/pytest -q
git add -A
git commit -S -m "refactor: reduce duplicate code"
git log --show-signature -1 --oneline
git push -u origin codex/reduce-duplicate-code
gh issue create --title "Reduce duplicate code in Radiance helpers" --body "..."
gh pr create --base master --head codex/reduce-duplicate-code --title "refactor: reduce duplicate helper code" --body "Closes #907"
```

### State A — Superseded decision matrix

| Condition | Check Command | "Stale" Verdict |
| --------- | ------------- | --------------- |
| Deletions already absent from main | `comm -23 head.txt main.txt` → each: `git log --diff-filter=D origin/main -- <path>` | consolidation commit found for all |
| Modified files have lower version | `grep "^version:" skills/<f>.md` vs `git show origin/main:skills/<f>.md \| grep "^version:"` | branch version < main version |
| "New" files already on main | `comm -23 staged_hashes.txt main_hashes.txt \| wc -l` | result = 0 |

Expected output for a fully superseded branch:

```text
# gh pr list --state open
No pull requests match your search
# comm -23 /tmp/head.txt /tmp/main.txt | wc -l
1193    ← looks alarming, but all are old deletions
# git log --diff-filter=D --oneline origin/main -- skills/old-skill.md | head -1
a3f2b1c feat(skill-merge): consolidate 12 skills into automation-bundle (C086)
# comm -23 staged_hashes.txt main_hashes.txt | wc -l
0       ← zero true new files; staged index is a no-op
```

### State A (large-scale) — Three-way count diff interpretation table

| Pattern | merge-base count | branch count | main count | Diagnosis |
| ------- | ---------------- | ------------ | ---------- | --------- |
| Branch grew, main shrank | 1661 | 1849 | 333 | main ran corpus consolidation post-diverge; branch-only files are pre-consolidation originals |
| Branch shrank, main grew | N | N-k | N+m | branch deleted files; check if intentional or if branch is behind main |
| Both grew from base | N | N+a | N+b | two independent workstreams; inspect `comm -23` and `comm -13` carefully |
| Branch == main count | N | N | N | files differ by content, not count; use hash comparison or version comparison |

**Confirmation command sequence** for the "branch grew, main shrank" pattern:

```bash
# 1. Get counts at all three points
MERGE_BASE=$(git merge-base HEAD origin/main)
git ls-tree -r --name-only "$MERGE_BASE" skills/ | grep '\.md$' | wc -l   # e.g. 1661
git ls-tree -r --name-only HEAD            skills/ | grep '\.md$' | wc -l   # e.g. 1849
git ls-tree -r --name-only origin/main     skills/ | grep '\.md$' | wc -l   # e.g. 333

# 2. Verify main ran consolidation
git log --oneline origin/main | grep -iE 'consolidat|absorb|cluster' | head -5
# Expected: "chore(triage): second-pass addendum (21 new clusters, 5 merges, C060-C080)"

# 3. Confirm branch-only count matches expected pre-consolidation originals
comm -23 /tmp/branch.txt /tmp/main2.txt | wc -l  # e.g. 970 (pre-consolidation originals)
comm -13 /tmp/branch.txt /tmp/main2.txt | wc -l  # e.g. 76 (canonical merged skills branch lacks)

# 4. Safety stash and confirm superseded commits
git stash push -u -m "pre-reset snapshot $(date +%Y%m%d)"
git log --oneline origin/main..HEAD | head -10  # should show only adds/updates now on main

# 5. Only then hard-reset
git reset --hard origin/main
```

### State B — Orphan signs and recovery checklist

Signs of a wrong-repo push: unfamiliar "Initial commit" at `git log <branch> | tail`;
unexpected files at `git ls-tree --name-only <branch>`; massive ahead/behind counts; commit
messages referencing a different project.

- [ ] Verify branch has no merge-base with main
- [ ] Identify valuable content on branch tip
- [ ] Check whether content is already on main (`git log origin/main -- <path>`)
- [ ] Extract files before deletion
- [ ] Delete remote branch
- [ ] Recreate from main only if content not already merged

### State C — Reset + cherry-pick recipe

```bash
git log --oneline origin/<branch>..HEAD       # local-only commits
git log --oneline HEAD..origin/<branch>       # remote-only commits
git merge-base HEAD origin/<branch>           # common ancestor SHA
git reset --hard origin/<branch>              # absorb all remote commits
git cherry-pick <fix-sha>                     # apply only the targeted fix
git log --oneline -3                          # fix should be single HEAD commit
git status                                    # "ahead by 1 commit"
```

Cherry-picks of small, focused single-file fixes rarely conflict, even on heavily diverged
branches, because they touch a narrow region the remote version differs in only slightly.

### State D — Follow-up branch from validated local amendment

Generic verified parameter map from the follow-up branch recovery:

| Parameter | Value |
| --------- | ----- |
| Old PR | `<repo> PR <old-pr-number>` |
| Old branch | `<old-branch>` |
| Local validated amended commit | `<validated-commit-sha>` |
| Old PR head SHA reported by GitHub | `<old-pr-head-sha>` |
| Trunk commit containing the merged work | `<trunk-commit-sha>` on `origin/<trunk>` |
| Patch file | `/tmp/<followup-topic>.patch` |
| Follow-up branch | `<followup-branch>` |
| Follow-up PR | `<repo> PR <followup-pr-number>` |
| Verification | `verified-ci` after follow-up PR checks passed |

Copy-paste sequence used:

```bash
TRUNK="master"
VALIDATED_COMMIT="<validated-commit-sha>"
FOLLOWUP_BRANCH="<followup-branch>"
PATCH_FILE="/tmp/<followup-topic>.patch"

git fetch origin "$TRUNK"
git diff --stat "origin/$TRUNK" "$VALIDATED_COMMIT"
git diff --binary "origin/$TRUNK" "$VALIDATED_COMMIT" --output="$PATCH_FILE"
git switch -c "$FOLLOWUP_BRANCH" "origin/$TRUNK"
git apply --index "$PATCH_FILE"
git diff --quiet "$VALIDATED_COMMIT" -- .
git commit -m "refactor: apply follow-up change"
git push -u origin "$FOLLOWUP_BRANCH"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | Branch `feature/myrmidon-merge-triage` (32 ahead, 730 behind, remote gone) — three-way count diff: merge-base=1661 skills, branch=1849 (grew), main=333 (shrank via consolidation). 970 branch-only files were pre-consolidation originals. Hard-reset to origin/main confirmed correct after stash. 107 PRs subsequently merged on main. | State A — large-scale corpus consolidation |
| ProjectMnemosyne | Branch `feature/myrmidon-merge-triage` (32 ahead, 525 behind, remote gone) — confirmed fully superseded; no PRs opened | State A |
| ProjectMnemosyne | Branch `skill/debugging/fixme-todo-cleanup-v2` pushed from ProjectOdyssey's history — no merge-base; content already on main; deleted | State B |
| ProjectOdyssey | PR #3197, issue #3088 — BF16 test skip; reset to remote (13 remote-only commits) + cherry-pick fix | State C |
| ProjectHephaestus | 7 local branches all failed auto-rebase with conflicts; `git cherry` showed every commit `+`. Message-search proved all subsumed: `999-fix-pr-thread-reply-mutation`→`187720a … (#1041)`, `fix-1282-work`→`22fc435 … (#1282)`, `rc2-conflict-gate`→`d3701b8 … (#1335)`. Reported subsumed; no swarm, no delete | State A — squash-merge false positive |
| ProjectHephaestus | Worktree `agent-a7fe2df2b7f6e658b` — 3 "uncommitted modified" files all 0 unique lines vs main (`log_on_error` changes already merged via PR #1372); safe to discard | State A — worktree 0-unique-lines |
| LLM360/Inference360 | An auto-merged PR merged before follow-up changes could be force-pushed; the old remote branch was gone, and a validated local amended commit was converted into a clean follow-up branch from current trunk; the follow-up PR auto-merged after CI passed | State D — already-merged PR follow-up branch |
| LLM360/Radiance | Current branch `codex/test-architecture-layout` had merged PR #906 but contained uncommitted duplicate-code cleanup work. Stashed, fetched `origin/master`, created `codex/reduce-duplicate-code`, popped, re-verified locally, signed commit `e772d982`, pushed, created issue #907 and PR #908. GitHub checks were pending at capture time. | State E — merged current branch with uncommitted follow-up work, verified-local |

## References

- [git-branch-state-triage-and-recovery.history](git-branch-state-triage-and-recovery.history) — superseded source skills (verbatim)
