---
name: git-rebase-signing-ci
description: "Rebase and sign commits to pass CI pr-policy checks. Use when: (1) CI pr-policy fails on unsigned commits, (2) need to re-sign all PR commits after rebase, (3) force push signed commits to update a PR, (4) a rebase using --exec stops on a real conflict and you need to resume it correctly instead of hand-invoking the exec command, (5) pr-policy fails with 'commit signature is missing or invalid' immediately after GitHub's Update branch button or gh pr update-branch --rebase — the server-side rebase re-creates every commit UNSIGNED, so never use it on a signed-commits repo, (6) git push --force-with-lease is rejected with 'stale info' after a server-side branch update — fetch the branch to refresh the remote-tracking ref, verify the remote head is the expected rewrite, then push, (7) branch protection requires strictly up-to-date branches AND signed commits and NO merge queue is enabled — every merge to main invalidates sibling PRs and each needs its own local re-signed rebase + force-push, one PR per cycle (server-side update is never usable), (8) a stacked PR's base branch was squash-merged — rebase with git rebase --onto origin/main <old-base-head> to shed the base's commits before pushing, (9) a GitHub merge queue IS enabled — do NOT prepare a local re-signed rebase + force-push cycle at all; a green PR queued for merge is rebuilt and merged server-side (merge-signed by GitHub) and lands MERGED without any author force-push, so check pr state before rebasing."
category: tooling
date: 2026-07-17
version: "1.3.0"
user-invocable: false
verification: verified-ci
history: git-rebase-signing-ci.history
tags: [git, signing, rebase, ci, gpg, exec, conflict-resolution, update-branch, force-with-lease, stale-info, branch-protection, up-to-date, stacked-pr, squash-merge, merge-queue]
---

# Git Rebase Signing for CI

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-16 |
| **Objective** | Sign all PR commits to pass CI pr-policy checks that require GPG signatures, avoid commit corruption when a `--exec` rebase stops on a real conflict, and avoid the server-side branch updater that silently strips signatures |
| **Outcome** | Successful — all commits show 'G' (good signature) after rebase; corrupted-commit failure mode documented with a safe recovery + redo procedure; server-side `update-branch` signature-stripping confirmed red-then-green in CI across two PRs |
| **Verification** | verified-ci |
| **History** | [changelog](./git-rebase-signing-ci.history) |

## When to Use

- CI `pr-policy` check fails with "every commit is signed" requirement
- Commits were created without `-S` flag and need to be retroactively signed
- After rebasing, need to verify all commits are signed
- A `git rebase --exec ...` run stops with a real content conflict and you
  need to resume it without corrupting the in-progress commit
- `git reflog` shows an amend landed directly on a `rebase (start): checkout`
  entry with no intervening pick — signals the corruption described below
- `pr-policy` fails with `commit signature is missing or invalid` right after the PR branch was
  updated via GitHub's **Update branch** button or `gh pr update-branch --rebase`
- `git push --force-with-lease` is rejected with `stale info` after a server-side branch update
- The repository requires strictly up-to-date branches AND signed commits, no merge queue is
  enabled, and several PRs must merge in sequence
- A GitHub merge queue IS enabled — before preparing any re-signed rebase, confirm the PR is not
  simply queueable (the queue makes the local rebase unnecessary)
- A stacked PR's base branch was squash-merged and the branch now shows CONFLICTING

## Verified Workflow

### Quick Reference

```bash
# Rebase all PR commits onto latest base with signing (no conflicts expected)
git rebase --exec 'git commit --amend --no-edit -S' origin/main

# Verify all commits are signed (G = good)
git log --format='%h %G? %s' origin/main..HEAD

# Force push to update PR
git push --force-with-lease origin <branch>
```

> **Critical — if the `--exec` rebase stops on a real conflict, do NOT
> hand-invoke the exec command.** After resolving the conflict
> (`git add <file>`), always run `git rebase --continue` — never run
> `git commit --amend ...` yourself to "help it along," even though the
> rebase reports "Next command to do: exec ...". At that pause point the
> conflicted commit has **not yet been created** as a commit object; `git
> rebase` is still mid-`pick`. Manually running `git commit --amend` amends
> whatever HEAD currently is — the rebase's "onto" checkout (the base branch
> tip) — instead of finalizing the pick. `git rebase --continue` correctly
> sequences "finalize the pick as a real commit" BEFORE "run the queued exec
> command against it." This applies to any `--exec` script, not just
> amend/sign (e.g. `--exec "pytest"` has the same risk).

### Detailed Steps

1. **Identify unsigned commits**: `git log --format='%h %G? %s' origin/main..HEAD` — look for `N` (no signature) or `U` (unknown validity).
2. **Rebase with signing**: `git rebase --exec 'git commit --amend --no-edit -S' origin/main` — this replays each commit and re-signs it with your GPG key.
3. **If it stops on a conflict**: resolve the conflict per-hunk, `git add <file>`, then run `git rebase --continue` (NOT `git commit --amend` by hand — see warning above). `--continue` finalizes the pick as a commit and then automatically fires the queued `--exec` command against that new commit.
4. **Verify**: Re-run `git log --format='%h %G? %s' origin/main..HEAD` — all should show `G`.
5. **Force push**: `git push --force-with-lease origin <branch>` — the `--force-with-lease` is safer than `--force` as it rejects if the remote has changes you haven't fetched.

### Recovery if you already hand-invoked the exec command mid-conflict

If `git commit --amend` was run by hand while paused on a conflict and the
result looks wrong (see Failed Attempts below for the corruption symptoms):

1. Verify the working tree is clean/matches your target state:
   `git status` + `git diff <target-sha> HEAD`.
2. If `git rebase --abort` is unavailable (e.g. blocked by a safety-net
   policy) and deleting `.git/**/rebase-merge` directly is also blocked as an
   unsafe path deletion, use the non-destructive combo instead:
   `git reset --keep <pre-rebase-sha>` followed by `git rebase --quit`.
   `--quit` clears only the rebase bookkeeping directory — unlike `--abort`,
   it does **not** touch HEAD or the working tree — so it is safe once HEAD
   is already back at the pre-rebase commit via `reset --keep`.
3. Redo the rebase in two explicit, separate passes instead of `--exec`:
   (a) plain `git rebase origin/main`, resolve conflicts by hand per-hunk
   (verify with `git ls-files --stage <file>` that stage `:2:` = ours/base and
   `:3:` = theirs/your-branch — rebase inverts the usual merge meaning),
   `git add <file>`, `git rebase --continue` through to completion (git
   prints "Successfully rebased..."); (b) only then run
   `git commit --amend --no-edit -s -S` once, standalone, over the final HEAD
   to add signing/DCO. This decouples conflict-resolution-continuation from
   the signing amend and avoids the whole bug class.

See also `pr-rebase-conflict-resolution-patterns.md` § re-signing replayed
commits for the general `--exec` signing pattern on conflict-heavy rebase
chains — this skill's warning applies there too whenever a pick in that
chain conflicts.

### Server-side branch updates strip signatures (v1.2.0)

GitHub's **Update branch** button and `gh pr update-branch --rebase` perform the rebase
server-side: every commit is re-created by GitHub **without your GPG signature**, so a
signed-commits `pr-policy` gate that was green goes red on the next run with
`<sha>: commit signature is missing or invalid`. On a repo that requires signed commits,
NEVER update a PR branch server-side. Instead:

```bash
# Local re-signed rebase (commit.gpgsign re-signs each replayed commit)
git fetch origin main <branch>          # refresh BOTH refs; stale tracking ref => lease 'stale info'
git -c commit.gpgsign=true rebase origin/main
git log --show-signature -2             # expect 'Good signature' on every replayed commit
git push --force-with-lease --force-if-includes origin <branch>
```

- **Lease rejection `stale info`:** after any server-side update the remote-tracking ref no
  longer matches the remote, and `--force-with-lease` (correctly) refuses. Fetch the branch,
  confirm the remote head is exactly the known server-side rewrite (not someone else's work),
  then push again.
- **Strict up-to-date + signed commits, NO merge queue = manual serial merges:** each merge
  advances `main` and flips every sibling PR to BEHIND, and the server-side updater is unusable, so
  each PR needs its own local re-signed rebase, force-push, and full CI cycle — plan merges one at a
  time and rebase the NEXT PR only after the previous one lands. This is the *no-queue* case; if a
  real GitHub merge queue is enabled, do the opposite (next bullet).
- **A real GitHub merge queue makes the local re-signed rebase UNNECESSARY:** when the repo has a
  merge queue enabled (branch protection "Require merge queue" / a `merge_group`-triggered required
  workflow), a green PR does NOT need to be brought up-to-date by hand. Queue it and the queue
  rebuilds the branch on the current base and merges it **server-side**, signing the resulting merge
  with GitHub's key — the PR lands MERGED with no author force-push. So before starting the
  serial re-sign-rebase cycle above, check `gh pr view <N> --json state,mergeStateStatus`: if the
  PR is already MERGED or is queueable, skip the rebase entirely. Note the queue's transient head
  can appear unsigned (`N`) and carry extra queue-machinery commits while it processes — that is
  ephemeral queue state, not the final signed merge commit, and it is not a signature failure to fix.
- **Stacked PR whose base was squash-merged:** the branch still carries the base's original
  commits (now absent from `main`'s history), so it shows CONFLICTING. Shed them with
  `git rebase --onto origin/main <old-base-head> <branch>`, then re-verify signatures and push.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git commit --amend -S` per commit | Manual signing of each commit | Tedious and error-prone with multiple commits | Use `--exec` flag to sign all commits in one rebase |
| `git push --force` | Force push without lease check | Could overwrite remote changes from other collaborators | Use `--force-with-lease` for safety |
| `gh pr update-branch --rebase` to satisfy a strict up-to-date branch-protection rule | Server-side rebase to bring two green PRs current with main | GitHub re-created every commit unsigned; the previously-green signed-commits `pr-policy` gate failed on both PRs with `commit signature is missing or invalid` | Never update a signed-commits PR server-side; do a local `git -c commit.gpgsign=true rebase origin/main` and force-push with lease |
| `git push --force-with-lease` immediately after a server-side branch update | Pushing the locally re-signed rebase over the server-side rewrite | Rejected with `stale info` — the local remote-tracking ref predated the server-side rewrite, so the lease check failed | Fetch the branch first, verify the remote head is the expected rewrite, then push; the rejection is the lease working as designed |
| Preparing a local re-signed rebase + user force-push cycle for a green PR on a repo with a merge queue enabled | Rebased the branch onto the new `main`, re-signed, ran full local gates, and waited on a user force-push to satisfy the strict up-to-date rule before merging | Unnecessary work: the merge queue rebuilt and merged the PR server-side (GitHub-signed merge commit) and it landed MERGED while the re-signed branch was still waiting to be pushed — the whole rebase cycle was moot | On a merge-queue repo, check `gh pr view <N> --json state,mergeStateStatus` first; if queueable, just let the queue merge it — do NOT prepare a serial re-sign-rebase cycle. The queue absorbs the up-to-date requirement itself |
| Hand-invoking the queued `--exec` command (`git add <file>` then `git commit --amend --no-edit -s -S`) after resolving a conflict, instead of `git rebase --continue` | Rebase paused mid-conflict showing "Next command to do: exec ..."; resolved the conflict then manually replicated the exec command to "help it along" | The conflicted commit had not yet been finalized as a commit object — `git rebase` was still mid-`pick`. `git commit --amend` amended the rebase's "onto" checkout (base branch tip, which was HEAD at that moment) instead of the picked change, producing a corrupted commit whose diff was the union of an unrelated upstream commit's changes plus the PR's own changes, under the wrong commit message/title. Diagnosed via `git reflog` showing `rebase (start): checkout <base>` immediately followed by `commit (amend): <wrong title>` with no intervening pick entry, plus `git diff <merge-base> <bad-commit> --stat` showing far more files than the original commit's own `git show <sha> --stat` | Always run `git rebase --continue` after resolving a conflict, even when the rebase reports a queued `exec` line next — never hand-invoke the exec command yourself. If already corrupted: recover via `git reset --keep <pre-rebase-sha>` + `git rebase --quit` (when `--abort` is blocked), then redo as a plain rebase followed by one standalone amend pass |

## Results & Parameters

- **Signing key**: GPG key configured in git (`git config user.signingkey`)
- **Base branch**: `origin/main` (or `origin/master` depending on repo)
- **Verification output**: `G` = good signature, `N` = no signature, `U` = unknown validity
- **Corruption diagnostic signals**: `git reflog` missing an intervening pick entry between `rebase (start): checkout` and `commit (amend)`; `git diff <merge-base> <bad-commit> --stat` showing more files than `git show <original-sha> --stat`; commit message inherited from an unrelated pre-existing commit rather than the picked change
- **Safe cancel-and-quit sequence** (when `--abort` is policy-blocked): `git reset --keep <pre-rebase-sha>` then `git rebase --quit` — verify clean state with `git status` first
- **Verified case**: Hephaestus PR #2099 (branch `2053-auto-impl`), 1 commit rebased onto ~38 new commits of `origin/main`, one real conflict in `docs/AUTOMATION_LOOP_ARCHITECTURE.md`; recovery + redo verified via `git diff origin/main --stat` matching the original commit's stat exactly, 892/892 tests passing in `tests/unit/automation/pipeline/`, pre-commit hooks green, correct signature and DCO trailer present

## Verified On

| Project | Context | Details |
|---------|---------|-------|
| HomericIntelligence/ProjectHephaestus | PR #1171 — show-prompt CLI | 4 commits rebased and signed, pr-policy passes |
| example-org/inference-service | PR #82 — Move inference_service module | Commits signed for pr-policy compliance |
| HomericIntelligence/ProjectHephaestus | PR #2099 — branch `2053-auto-impl`, rebase onto ~38 new commits with one real conflict; `--exec` hand-invocation corrupted a commit by merging in an unrelated upstream commit's diff; recovered via `reset --keep` + `rebase --quit`, redone as plain rebase + standalone amend | verified-local (not yet confirmed in this skill PR's own CI) |
| HomericIntelligence/Athena | PRs #35/#36 — `gh pr update-branch --rebase` stripped signatures on both (pr-policy red with `commit signature is missing or invalid`); recovered with local `git -c commit.gpgsign=true rebase origin/main` + lease push after a branch fetch (first push rejected `stale info`); #35 re-merged green | verified-ci (pr-policy observed red on the server-side rewrite and green on the re-signed heads) |
| HomericIntelligence/Athena | PR #45 — pytest GHSA bump; a local re-signed rebase (`9b0f1fd`) was prepared for the strict up-to-date rule, but the repo's merge queue rebuilt and merged the PR server-side (merge commit `93a2e7f`, GitHub-signed) and it landed MERGED before the re-signed branch was pushed — proving the merge queue makes the manual re-sign-rebase cycle unnecessary | verified-ci (PR observed MERGED via the queue with pytest 9.x on `main`, no author force-push) |
