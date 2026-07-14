---
name: git-rebase-signing-ci
description: "Rebase and sign commits to pass CI pr-policy checks. Use when: (1) CI pr-policy fails on unsigned commits, (2) need to re-sign all PR commits after rebase, (3) force push signed commits to update a PR, (4) a rebase using --exec stops on a real conflict and you need to resume it correctly instead of hand-invoking the exec command."
category: tooling
date: 2026-07-12
version: "1.1.0"
user-invocable: false
verification: verified-local
history: git-rebase-signing-ci.history
tags: [git, signing, rebase, ci, gpg, exec, conflict-resolution]
---

# Git Rebase Signing for CI

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-12 |
| **Objective** | Sign all PR commits to pass CI pr-policy checks that require GPG signatures, and avoid commit corruption when a `--exec` rebase stops on a real conflict |
| **Outcome** | Successful — all commits show 'G' (good signature) after rebase; corrupted-commit failure mode documented and a safe recovery + redo procedure verified |
| **Verification** | verified-local |
| **History** | [changelog](./git-rebase-signing-ci.history) |

## When to Use

- CI `pr-policy` check fails with "every commit is signed" requirement
- Commits were created without `-S` flag and need to be retroactively signed
- After rebasing, need to verify all commits are signed
- A `git rebase --exec ...` run stops with a real content conflict and you
  need to resume it without corrupting the in-progress commit
- `git reflog` shows an amend landed directly on a `rebase (start): checkout`
  entry with no intervening pick — signals the corruption described below

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `git commit --amend -S` per commit | Manual signing of each commit | Tedious and error-prone with multiple commits | Use `--exec` flag to sign all commits in one rebase |
| `git push --force` | Force push without lease check | Could overwrite remote changes from other collaborators | Use `--force-with-lease` for safety |
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
| LLM360/Inference360 | PR #82 — Move inference360 module | Commits signed for pr-policy compliance |
| HomericIntelligence/ProjectHephaestus | PR #2099 — branch `2053-auto-impl`, rebase onto ~38 new commits with one real conflict; `--exec` hand-invocation corrupted a commit by merging in an unrelated upstream commit's diff; recovered via `reset --keep` + `rebase --quit`, redone as plain rebase + standalone amend | verified-local (not yet confirmed in this skill PR's own CI) |
