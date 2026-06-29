---
name: automation-multi-repo-pr-sweep-rebase-resolve
description: "Driving a large backlog of author-scoped PRs to green+merged across many repos. Use when: (1) hephaestus-review-prs runs but leaves PRs unmerged / BLOCKED-all-green, (2) deciding between a rebase-resolve sweep and the plain automation loop, (3) diagnosing why armed auto-merge PRs sit BLOCKED (unresolved review threads vs. CI backlog vs. red main), (4) a merge train of file-overlapping PRs keeps re-conflicting as siblings merge, (5) you need force-with-lease + resolveReviewThread after rebasing PR branches onto a moved main."
category: tooling
date: 2026-06-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - multi-repo
  - pr-sweep
  - rebase-resolve
  - hephaestus-review-prs
  - merge-train-cascade
  - ci-throughput
  - red-main-first
  - auto-merge
  - github
  - homericintelligence
  - worktree-per-pr
  - resolveReviewThread
---

# Multi-Repo PR Sweep: Rebase + Resolve to Drive a Backlog Green and Merged

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-28 |
| **Objective** | Drive a large backlog of author-scoped (mvillmow) PRs to green + merged across many HomericIntelligence repos in one session, when `hephaestus-review-prs` alone leaves them unmerged. |
| **Outcome** | Successful. One session resolved ~97/108 mvillmow PRs across 13 repos; 89 merged. Remaining were regressive PRs left for manual re-authoring or CI-throughput-throttled (merged as runners freed). |
| **Verification** | verified-ci (PRs went green in CI and squash-merged on `main`; commit signatures verified `verified==true`). |

## When to Use

- `hephaestus-review-prs` (the automation loop) ran but PRs are still open / `BLOCKED` with all checks green.
- You have a big backlog of PRs **authored by one account** spread across many repos and want them merged, not just reviewed.
- You need to decide between a **rebase-resolve sweep** (this skill) and the plain drive-prs-green loop.
- An armed `--auto --squash` PR sits `BLOCKED` and you must tell apart: unresolved review threads vs. CI runner backlog vs. a red `main` blocking every PR.
- A **merge train** of PRs touching shared files (CHANGELOG, pixi.lock, `_required.yml`, coverage.xml) keeps re-conflicting as siblings merge.
- After rebasing a PR branch onto a moved `main`, a plain `git push` is rejected non-fast-forward.

## Verified Workflow

The core insight: **`hephaestus-review-prs` has 3 gaps, so do not rely on it alone.**

1. It does **not rebase** branches onto the current `main` -> PRs fail any required check that `main` has moved past.
2. It pushes fix **commits** but does **not resolve the GitHub review-THREAD objects** -> with `required_review_thread_resolution=true` (the `homeric-main-baseline` ruleset) PRs stay `BLOCKED` with everything green.
3. It does a plain `git push` after a history-rewriting rebase -> non-fast-forward rejection, **and** its worktrees auto-clean on exit, so the rebase fix is **lost**.
4. It has **no `--repo` flag** — it operates on the CWD repo, so it must be invoked from inside each submodule/clone (not the Odysseus meta-repo root).

The working pattern is the **rebase + resolve sweep**: dispatch **one sub-agent per repo** into a **fresh `/tmp/sweep-<repo>` clone** (never the shared submodule, whose branch state and worktrees are shared). Per PR the sub-agent:

1. `git fetch origin`
2. Rebase the PR branch onto `origin/main`, **re-signing every replayed commit** via `--exec 'git commit --amend --no-edit -S -s --reset-author'`.
3. Resolve conflicts **semantically** (understand both sides; do not blindly take theirs/ours).
4. Fix any residual CI failures the rebase surfaces.
5. `git push --force-with-lease` (NOT plain push; NOT `--force`).
6. Resolve the GitHub review-thread objects via the GraphQL `resolveReviewThread` mutation.
7. Verify the tip commit is signed: `gh api repos/<o>/<r>/commits/<sha> --jq .commit.verification.verified` returns `true`.

The orchestrator then **strict-verifies** each PR and arms auto-merge:

- Strict-verify = `mergeStateStatus` CLEAN **AND** 0 unresolved review threads **AND** all signatures valid **AND** no **REQUIRED**-context failure. Non-required checks (Trivy, docker-build, markdownlint) do **not** block.
- Arm `gh pr merge <n> --auto --squash` (these repos are squash-only). A fully-green PR merges immediately on arm.

**RED-MAIN-FIRST:** if a repo's `main` itself fails a **required** check (notably `security` / `dependency-scan` via `pip-audit`), **every** PR is blocked. Fix `main` FIRST with a dep-bump PR, then the whole queue unblocks. Seen on Hermes / Agamemnon / Proteus / Odysseus this session.

**MERGE-TRAIN CASCADE:** arming N file-overlapping PRs at once — each merge advances `main`, so siblings touching shared files (CHANGELOG, pixi.lock, `_required.yml`, coverage.xml, test dep-count assertions) **re-conflict**. This needs repeated re-rebase passes; it converges as the queue shrinks. Empty/superseded PRs auto-close on push — rebase+push them to confirm they are truly superseded rather than manually closing. **REGRESSIVE** PRs (which would revert `main`'s newer work) must be **left untouched** for manual re-authoring — never force-merged.

**CI-THROUGHPUT CEILING:** force-pushing ~80 PRs saturates GitHub's runner pool — armed PRs sit `BLOCKED` with all checks **QUEUED** (not stuck, just waiting); auto-merge fires as runners free up. This is the real rate limit once structural blockers are gone.

### Quick Reference

```bash
# --- Per-repo sweep (one sub-agent per repo, fresh clone) ---
REPO=ProjectHermes; ORG=HomericIntelligence
git clone "https://github.com/$ORG/$REPO" "/tmp/sweep-$REPO"
cd "/tmp/sweep-$REPO"
# hephaestus-review-prs has NO --repo flag — must run from inside the clone (CWD):
hephaestus-review-prs   # optional first pass; then fix its 3 gaps manually below

# --- Per PR: rebase onto moved main, re-sign every commit, force-with-lease ---
git fetch origin
git checkout <pr-branch>
git rebase origin/main --exec 'git commit --amend --no-edit -S -s --reset-author'
# ...resolve conflicts semantically, fix residual CI...
git push --force-with-lease

# --- Resolve the GitHub review THREAD objects (commits alone don't clear them) ---
gh api graphql -f query='
  query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
    pullRequest(number:$n){reviewThreads(first:50){nodes{id isResolved}}}}}' \
  -f o="$ORG" -f r="$REPO" -F n=<pr>
gh api graphql -f query='
  mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' \
  -f id=<threadId>

# --- Verify the tip commit signature is valid ---
gh api repos/$ORG/$REPO/commits/<sha> --jq .commit.verification.verified   # -> true

# --- Strict-verify (CLEAN + 0 unresolved threads + no required-check failure) then arm ---
gh pr view <pr> --repo $ORG/$REPO \
  --json mergeStateStatus,reviewThreads,statusCheckRollup
gh pr merge <pr> --auto --squash --repo $ORG/$REPO   # squash-only repos
```

### Detailed Steps

1. **Discover** the author-scoped PR backlog per repo: `gh pr list --repo <o>/<r> --author <user> --json number,mergeStateStatus`.
2. **Red-main-first:** check each repo's `main` for a failing **required** check; if red, land a dep-bump PR before touching the queue.
3. **Fan out** one sub-agent per repo into `/tmp/sweep-<repo>` (fresh clone — never the shared submodule).
4. Per PR: fetch -> rebase onto `origin/main` re-signing via `--exec` -> resolve conflicts semantically -> fix residual CI -> `git push --force-with-lease` -> `resolveReviewThread` -> verify signature.
5. **Orchestrator strict-verify + arm** `--auto --squash`; expect merge-train re-conflicts on shared files, so run repeated re-rebase passes until the queue drains.
6. Leave **regressive** PRs untouched for manual re-authoring; let CI-throughput-throttled armed PRs merge as runners free.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Ran `hephaestus-review-prs` alone and expected it to merge the backlog | 15/30 PRs "failed" — plain `git push` after rebase was rejected non-fast-forward, and the review THREADs were never resolved so PRs stayed BLOCKED-all-green; the loop's auto-cleaned worktrees LOST the fix | The loop has 3 gaps. Use `git push --force-with-lease` + the `resolveReviewThread` GraphQL mutation, and work in a persistent clone so the rebase survives. |
| 2 | Ran the loop from the wrong CWD (the Odysseus meta-repo root) | `hephaestus-review-prs` has NO `--repo` flag — it targeted the wrong repo's issues/PRs | Always invoke it from inside each individual repo clone (CWD = that repo). |
| 3 | Armed `--auto --squash` on all overlapping PRs simultaneously | Maximal merge-train cascade: every merge advanced `main`, re-conflicting siblings that touched shared files (CHANGELOG, pixi.lock, `_required.yml`, coverage.xml) | Serialize the arm, or expect and budget for multiple re-rebase passes; the cascade converges as the queue shrinks. |
| 4 | Treated `BLOCKED`-all-green PRs as broken/stuck | They were not broken — either unresolved review threads (review-gate) OR a CI runner backlog with all checks QUEUED | Before assuming broken, check `reviewThreads` for unresolved nodes AND check the check-run QUEUED status; a red `main` on a required check blocks every PR — fix `main` first. |

## Results & Parameters

- **Scale:** ~97/108 mvillmow PRs resolved across 13 HomericIntelligence repos in one session; **89 merged**.
- **Repos where `main` was red on a required check (fixed first):** Hermes, Agamemnon, Proteus, Odysseus (`security`/`dependency-scan` via `pip-audit`).
- **Required vs. non-required:** only **required** contexts block the arm. Non-required (Trivy, docker-build, markdownlint) are ignored for the merge decision.
- **Merge method:** all HI repos are **squash-only** -> `gh pr merge <n> --auto --squash`.
- **Ruleset:** `homeric-main-baseline` sets `required_review_thread_resolution=true` — this is exactly why pushing commits is not enough and `resolveReviewThread` is mandatory.
- **Signature email:** sign with the noreply email `4211002+mvillmow@users.noreply.github.com` so rewritten/re-signed commits stay `verified==true` and survive the GH007 email-privacy push block (see cross-link below).
- **Throughput ceiling:** force-pushing ~80 PRs saturates the runner pool; armed PRs sit BLOCKED/QUEUED and auto-merge as runners free — this is the rate limit, not a failure.

### Related skills (cross-links)

- `automation-reuse-repo-clone-with-worktree-per-pr` — the clone/worktree-per-PR reuse mechanics this sweep builds on.
- `github-auto-merge-ci-gating-merge-method` — auto-merge CI gating and the squash merge-method requirement.
- `automation-review-loop-unpushed-fix-oscillates` — narrower review-loop failure mode (unpushed fix oscillation).
- `dependabot-lockfile-rebase-regenerate-resign` — regenerating + re-signing lockfiles when rebasing dependency PRs (the pixl.lock / CHANGELOG re-conflict case).
- `multi-repo-pr-automation-loop-orchestration` — the driver-side honest-reporting / report-vs-live-state failures of the loop itself.
- `reference_signed_commits_email_privacy` (Odysseus memory) — the noreply email `4211002+mvillmow@users.noreply.github.com` that keeps signatures valid past GH007.
