---
name: github-auto-merge-ci-gating-merge-method
description: "Use when: (1) a PR has mergeStateStatus CLEAN or MERGEABLE but auto-merge never fires despite all checks passing, (2) gh pr merge --auto --rebase or --squash returns an error or silently fails on a squash-only repo, (3) a PR is BLOCKED because required CI status contexts never post (workflow never triggered, paths filter excluded PR, required check name mismatch), (4) GPG-signing failures or mismatched committer emails cause commits to be unsigned and block the pr-policy gate, (5) branch protection rulesets and classic branch protection disagree and their union blocks merge, (6) a CI ruleset chicken-and-egg deadlock blocks a PR that introduces a new workflow, (7) an advisory check should not block merge but currently does because it lives in the required gate, (8) deciding which merge method a repo supports before arming auto-merge, (9) auditing required-check names after adding or removing CI jobs, (10) state:implementation-go label or pr-policy gates auto-merge arming, (11) per-issue arming-state machine is triggered on the wrong event (optimistic point vs detected merge), (12) mergeStateStatus=BLOCKED with all CI green and auto-merge armed - unresolved review threads are the PRIMARY blocker to check FIRST before assuming CI failure, (13) stale failed status-rollup entries must be distinguished from current-head required checks before deciding a PR is blocked or complete"
category: ci-cd
date: 2026-06-26
version: "1.5.0"
user-invocable: false
history: github-auto-merge-ci-gating-merge-method.history
tags:
  - auto-merge
  - github
  - ci-cd
  - merge-method
  - squash
  - branch-protection
  - rulesets
  - required-checks
  - pr-policy
  - implementation-go
  - gpg-signing
  - arming-state-machine
  - review-threads
  - resolveReviewThread
  - current-head-checks
  - status-rollup
  - dco-signoff
---

# GitHub Auto-Merge: CI Gating, Branch Protection, and Merge Method

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-06-07 | Consolidated canonical for why GitHub auto-merge does not fire and how to arm it correctly: wrong merge method, missing/required CI status contexts, two-layer branch protection, GPG-signing blockers, ruleset bootstrap deadlock, the `state:implementation-go` arming-state machine, and advisory-vs-required gate split | Each failure mode has a verified diagnosis + fix; verified across many HomericIntelligence repos in live CI |
| 2026-06-14 | Add the classic-vs-ruleset review-count UNION hard gate (a required human approval automation cannot provide), the keystone-PR self-introduced-required-context merge-train deadlock (merge keystone first, then re-rebase the queue), and duplicate check-run resolution after a re-run | Diagnosed live across 13 open ProjectHephaestus PRs during a `/myrmidon-swarm` drive (verified-local; the PRs had not yet merged at capture, the review-union gate was confirmed by API inspection) |
| 2026-06-14 | Expanded unresolved review thread diagnostic to verified-ci status: PR #1282 was BLOCKED despite all CI green and auto-merge armed; the stated "lint failure" was stale; the real blockers were 2 unresolved review threads. Resolving via `resolveReviewThread` GraphQL mutation immediately triggered auto-merge (merged 2026-06-15T03:05:38Z by app/github-actions). Added full GraphQL copy-paste workflow for thread query + reply + resolve. | verified-ci — PR #1282 ProjectHephaestus merged within seconds of thread resolution |
| 2026-06-15 | Folded v1.3.0 improvements from the briefly-reintroduced `squash-only-repo-merge-method-docs` standalone (PR #2546) back into this consolidated skill, then re-removed the standalone duplicate (restoring the #2200 consolidation): the f-string regression-test pattern (`inspect.getsource(_make_agent_prompt)`, not a `_AGENT_PROMPT_TEMPLATE` constant), the explicit per-block `<!-- merge-method-allowed: example -->` lint-exemption marker replacing a brittle 10-line look-back heuristic, the plain-`jq -r` form (not `gh api --jq -` over stdin), and tiered helper sourcing for cross-repo callers | verified-ci (shipped in ProjectHephaestus PR #1069); standalone duplicate re-removed |
| 2026-06-26 | Added a ProjectHephaestus PR-completion checklist for label-gated auto-merge: create a PR with literal `Closes #N`, verify signed/DCO commits, apply `state:implementation-go` before relying on auto-merge policy, arm `gh pr merge --auto --squash`, watch the current-head Test matrix, and distinguish stale failed rollup entries from later successful current runs before declaring completion. | verified-ci — ProjectHephaestus PR #1646 closed issue #1645 and merged after Test workflow run 28256151963 and Required Checks run 28256238895 succeeded |

GitHub auto-merge is **stricter than branch protection** and fires only when EVERY check (required and non-required) reaches a clean terminal state, the chosen merge method is allowed, every required status context has actually posted, all commits are verified-signed, and BOTH protection layers (ruleset + classic) are satisfied. A PR that looks ready (`mergeStateStatus: CLEAN`/`MERGEABLE`) can sit forever when any one of those is silently unmet. This skill covers the merge-blocking mechanics; it does NOT cover general CI failure diagnosis, rebase-conflict resolution, review-loop orchestration, or PR enumeration.

**Verification: verified-ci** (most failure modes observed and fixed live; the advisory-split and per-issue arming refinements are verified-local where noted).

## When to Use

- A PR is `CLEAN`/`MERGEABLE` with auto-merge armed but never merges (after minutes to hours).
- `gh pr merge --auto --rebase`/`--squash` errors or silently fails to arm on a squash-only repo.
- A PR is `BLOCKED` because a required status context never posts: workflow never triggered, a `paths:` filter excluded the PR, or the required-check NAME does not match the emitted job name.
- GPG-signing failures or mismatched committer emails leave commits unsigned and block the `pr-policy` gate (or the ruleset's `required_signatures`).
- A ruleset and classic branch protection disagree; their UNION blocks merge.
- A PR introducing a NEW workflow is permanently BLOCKED because the ruleset requires check names that only exist in the workflow being added (bootstrap deadlock).
- An advisory/timing-sensitive sub-check should report but not block, yet currently gates merge because it lives in the required `pr-policy` gate.
- Deciding which merge method a repo supports before arming auto-merge; auditing required-check names after adding/removing CI jobs.
- `pr-policy` fails on premature auto-merge: `Auto-merge is enabled before implementation review GO` (or the inverse, label present but auto-merge off).
- A post-CI `/learn` (or any capture step) fires on the optimistic point (auto-merge armed) instead of the truth (detected merge), polluting downstream state.
- **A PR is `BLOCKED` with all CI checks green and auto-merge already armed** — unresolved review threads are the PRIMARY blocker to check FIRST (verified-ci: PR #1282 merged immediately after thread resolution).
- Completing a ProjectHephaestus PR where `pr-policy` / auto-merge policy depends on a literal issue-closing line, signed DCO commits, the `state:implementation-go` label, and current-head required checks rather than stale failed status-rollup entries.

## Verified Workflow

### Quick Reference

```bash
# 1. WHY isn't auto-merge firing? Full state snapshot.
gh pr view <PR> --json number,mergeStateStatus,mergeable,autoMergeRequest,statusCheckRollup

# 2. Zero CI runs on the branch => auto-merge will NEVER fire (no check event ever posts)
gh run list --branch "$(gh pr view <PR> --json headRefName --jq .headRefName)"   # [] = stalled

# 3. Which merge method does the TARGET repo allow? (detect, do not hardcode)
gh api repos/<OWNER>/<REPO> --jq '{rebase:.allow_rebase_merge, squash:.allow_squash_merge, merge:.allow_merge_commit}'

# 4. Arm with the correct flag, then verify it actually armed
gh pr merge <PR> --auto --squash         # squash-only repos REJECT/ignore --rebase
gh pr view <PR> --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'   # expect SQUASH

# 5. What does branch protection ACTUALLY require? (check BOTH layers)
gh api repos/<O>/<R>/branches/main/protection --jq .required_status_checks.contexts  # classic (may 404)
gh api repos/<O>/<R>/rulesets/<RID> --jq '.rules[]|select(.type=="required_status_checks")|.parameters.required_status_checks[].context'

# 6. Unresolved bot review threads block merge with all checks green (required_review_thread_resolution)
gh api graphql -f query='{repository(owner:"O",name:"R"){pullRequest(number:N){reviewThreads(first:50){nodes{isResolved}}}}}' \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[]|select(.isResolved==false)]|length'

# 7. pr-policy "Auto-merge enabled before GO": un-arm, rerun, let the label workflow arm it
gh run view <run-id> --log-failed | grep '::error::'
gh pr merge <PR> --disable-auto && gh run rerun <run-id> --failed

# 8. Bulk batch: list ALL open PRs (default limit is 30 — silently omits older PRs)
gh pr list -R <O>/<R> --state open --limit 200 --json number,mergeStateStatus,autoMergeRequest

# 9. ProjectHephaestus PR completion: policy + current-head checks
git log --show-signature -1 --format=fuller
gh issue create --repo HomericIntelligence/ProjectHephaestus --title "..." --body "..."
gh issue view <ISSUE> --repo HomericIntelligence/ProjectHephaestus
gh pr create --repo HomericIntelligence/ProjectHephaestus --title "..." --body $'...\n\nCloses #<ISSUE>'
gh issue edit <PR> --repo HomericIntelligence/ProjectHephaestus --add-label state:implementation-go
gh pr merge <PR> --repo HomericIntelligence/ProjectHephaestus --auto --squash
gh pr checks <PR> --repo HomericIntelligence/ProjectHephaestus --watch --interval 30
gh pr view <PR> --repo HomericIntelligence/ProjectHephaestus \
  --json state,mergedAt,mergeCommit,mergeStateStatus,statusCheckRollup
```

### Detailed Steps

#### Squash-only merge-method detection

Some repos set `allow_rebase_merge: false` (the HomericIntelligence default — `{"rebase":false,"squash":true,"merge":false}`). The wrong method hides in THREE places: docs/CLAUDE.md, code (`pr.merge(merge_method="rebase")`), and skill/plugin instruction files (`/learn`, `/finish-branch`). Symptoms differ by form: the CLI `gh pr merge --auto --rebase` **silently fails to arm** (no error), while a PyGithub/API call **fails loudly** with `GraphQL: Rebase merges are not allowed on this repository (mergePullRequest)` / `(enablePullRequestAutoMerge)`.

The robust fix is **settings-aware selection**, not swapping one hardcoded flag for another (that just breaks on a rebase-only or merge-only target). Detect and pick by preference order `rebase` (linear history) -> `squash` -> `merge`:

```bash
choose_merge_flag() {
  gh api "repos/$1" --jq '[
    (if .allow_rebase_merge then "--rebase" else empty end),
    (if .allow_squash_merge then "--squash" else empty end),
    (if .allow_merge_commit then "--merge"  else empty end)
  ] | .[0] // ""'
}
MERGE_FLAG=$(choose_merge_flag "HomericIntelligence/Mnemosyne")   # -> --squash here
gh pr merge "$PR" --auto "$MERGE_FLAG" --repo HomericIntelligence/Mnemosyne
```

Audit for the bug in all forms, and add a source-inspection unit test as a durable guard:

```bash
grep -rn 'merge_method="rebase"\|--auto --rebase\|gh pr merge.*--rebase' .
```

```python
import inspect
from hephaestus.github import pr_merge
def test_pr_merge_uses_squash_not_rebase():
    src = inspect.getsource(pr_merge)
    assert 'merge_method="rebase"' not in src and 'merge_method="squash"' in src
```

#### Arm-time GraphQL status errors (retry, do not treat as fatal)

`gh pr merge --auto --squash` (the `enablePullRequestAutoMerge` mutation) can reject the arm with a transient GraphQL status error tied to the PR's current `mergeStateStatus`. These are NOT fatal — back off and retry, do not give up or force-merge:

- **"Pull request is in clean status"** — API internal state has not caught up on a freshly-CLEAN PR. **Retry immediately**; the second call seconds later succeeds with no other change.
- **"Pull request is in unstable status"** — checks are still actively settling. **Wait a few seconds, then retry**; the PR commonly resolves to `UNKNOWN` mergeStateStatus, which DOES accept the arm call.

```bash
arm_auto_merge() {  # retry through transient clean/unstable arm-time GraphQL errors
  local pr="$1" repo="$2" i out
  for i in 1 2 3 4 5; do
    if out=$(gh pr merge "$pr" --repo "$repo" --auto --squash 2>&1); then return 0; fi
    case "$out" in
      *"clean status"*)    continue ;;            # retry immediately
      *"unstable status"*) sleep 5; continue ;;   # let it resolve to UNKNOWN, then retry
      *) printf '%s\n' "$out" >&2; return 1 ;;    # anything else IS fatal
    esac
  done
  return 1
}
```

#### Required-check name management

GitHub uses `jobs.<id>.name:` (falling back to the job id) as the status-check CONTEXT string; the ruleset's `required_status_checks.context` must match EXACTLY. Use the bare job name (`lint`, `build`, `unit-tests`) — NOT the workflow-prefixed form `"Required Checks / lint"`. A slash is valid in `name:` but not in a job id, so `name: security/dependency-scan` is the correct way to emit a slashed context.

Required-check membership lives in repo settings / ruleset, OUTSIDE the workflow file. Always include `"integration_id": 15368` (the GitHub Actions app id) in `required_status_checks`, or the contexts never match a run. Audit alignment between what is required and what is emitted:

```bash
gh api repos/<O>/<R>/branches/main/protection --jq '.required_status_checks.contexts[]' | sort > /tmp/required.txt
grep -rh "name:" .github/workflows/*.yml | sed 's/.*name: //' | sort -u > /tmp/emitted.txt
comm -23 /tmp/required.txt /tmp/emitted.txt   # required but NOT emitted => blocks every PR
```

When a required context never posts because the workflow did not trigger: a path-filtered `on: pull_request` workflow sees zero changed files; **force-push after rebase** (`git fetch origin && git rebase origin/main && git push --force-with-lease`) re-evaluates path filters against the new tip SHA. Do NOT use empty `--allow-empty` commits (no path diff), `workflow_dispatch` (does NOT satisfy required checks), or close+reopen (unreliable). The ONE exception: a dropped downstream `workflow_run` gate (real tests green, gates stuck `pending:0`, zero runs created) is recovered by a single empty **signed** `chore:` commit — that re-evaluates trigger scheduling. (Note these are inverse fixes — diagnose which event was dropped first.)

A PR that touches only paths excluded by every workflow's `paths:` filter (`pods/**`, `**/*.md`, `scripts/**`, `justfile`) generates ZERO check events; auto-merge then waits forever even with no required checks. Fix per-PR with a manual merge, or permanently by broadening `paths:`.

#### `strict_required_status_checks_policy: false` merges on stale CI

The common HomericIntelligence default `strict: false` means a required context is satisfied by ANY passing run, including one recorded on a PRIOR commit SHA — GitHub does NOT require the check to have passed on the LATEST commit. Consequence: after a force-push/new commit, the newest commit's CI can still be `QUEUED`/`IN_PROGRESS` at the moment auto-merge fires, and auto-merge can merge BEFORE that newest CI finishes (the gate is green courtesy of the older SHA). This is not a bug to fix per-PR; it is the configured behavior, but be aware that "auto-merge fired" does NOT guarantee the merged tip's CI ran. Check which mode a repo uses:

```bash
gh api repos/OWNER/REPO/branches/main/protection/required_status_checks --jq .strict
# false => prior-SHA passing checks satisfy the gate; latest commit's CI may still be QUEUED at merge
# true  => the required checks must have passed on the PR's most recent commit (no stale-CI merge)
```

#### Two-layer branch protection (ruleset + classic)

HomericIntelligence `main` protection is split across TWO layers and GitHub enforces their UNION (stricter wins). A rule reported as `0`/absent in the ruleset can still be enforced by classic protection, and vice-versa — so always audit BOTH.

- **RULESET = shared baseline** (identical across repos): `deletion, non_fast_forward, pull_request (required_approving_review_count=0), required_linear_history, required_signatures, required_status_checks`. Canonical contexts: `lint, unit-tests, integration-tests, security/dependency-scan, security/secrets-scan, build, schema-validation, deps/version-sync`.
- **CLASSIC = repo-specific ADDITIONS only**: `required_conversation_resolution: true` (all repos) plus each repo's EXTRA contexts not already in the ruleset. NO reviews, NO linear-history in classic.

Critical gotchas:
- `required_conversation_resolution` is **classic-only**; putting `{"type":"required_conversation_resolution"}` in a ruleset PUT returns `HTTP 422: data matches no possible input`. (`required_linear_history`/`non_fast_forward` ARE valid ruleset types.)
- A ruleset PUT is a **full replace** of `.rules` — fetch, dedup the same type, append, then PUT the full object. Never PUT only the new rule.
- `GET branches/main/protection` on an unprotected repo returns a 404 BODY `{"message":"Branch not protected","status":"404"}`. Guard `.status=="404"` before extracting contexts, or its top-level keys (`documentation_url`/`message`/`status`) become FAKE required contexts that permanently block merges.
- All-checks-green + `MERGEABLE` can still sit `BLOCKED` on `required_review_thread_resolution: true` — unresolved `@github-advanced-security` (CodeQL) review threads gate merge. Detect via the GraphQL `reviewThreads` query (REST field is empty); READ each `path:line` and classify false-positive vs genuine, document accept-rationale, then `resolveReviewThread`. A force-push amend re-runs CodeQL and can post NEW threads — re-check the count after amending.
- A `branch-protection-drift` required check that fails in ~4s with empty `--log-failed` is failing at the `gh api` call itself: `Resource not accessible by integration (HTTP 403)` from hitting the admin `branches/main/protection` endpoint with the default `GITHUB_TOKEN`. Switch to `rules/branches/main` (readable with `contents: read`; field names differ — `dismiss_stale_reviews` -> `dismiss_stale_reviews_on_push`). Fixing the 403 EXPOSES real drift — survey the ecosystem (count:0, dismiss:false, thread-resolution:true) to decide which side is authoritative.

#### Classic-vs-ruleset review-count UNION (a required human approval automation cannot clear)

A repo can carry BOTH a classic branch-protection AND an org/repo ruleset, each with its own
`required_approving_review_count`. GitHub enforces their UNION — the STRICTER count wins. So a
classic protection with `required_approving_review_count: 1` is NOT overridden by a ruleset that
sets `0` (even with `required_review_thread_resolution: true`); every PR still needs 1 human
APPROVING review. No automated actor can satisfy this: a bot, a GitHub App, or the PR author who
armed auto-merge CANNOT approve their own PR, and a `COMMENTED` review does NOT count — only an
`APPROVED` review increments the satisfied-count. This is a HARD gate: the swarm/automation cannot
bypass it; a human with approve rights must approve.

Diagnostic signature (all true at once): `mergeable=MERGEABLE`, `mergeStateStatus=BLOCKED`, ALL
required status checks `SUCCESS`, NOT behind main, auto-merge armed, `reviewDecision=null` (or
`REVIEW_REQUIRED`), and critically `viewerCanEnableAutoMerge=false` via GraphQL. Diagnose precisely:

```bash
# Classic layer review-count
gh api repos/OWNER/REPO/branches/main/protection/required_pull_request_reviews \
  --jq '{required_approving_review_count, require_code_owner_reviews}'
# Ruleset layer review params (take the UNION — the stricter count wins)
gh api repos/OWNER/REPO/rules/branches/main \
  --jq '[.[]|select(.type=="pull_request").parameters]'
# Per-PR decision (COMMENTED != APPROVED; only APPROVED satisfies the count)
gh pr view N --json reviewDecision,mergeable,mergeStateStatus
# If false, no automated actor can clear this — a human must approve
gh api graphql -f query='query{repository(owner:"OWNER",name:"REPO"){pullRequest(number:N){viewerCanEnableAutoMerge}}}'
```

Lesson: when auto-merge will not fire with everything green, check BOTH protection layers'
review-count, take the UNION (stricter wins), and recognize a required human approval is a hard gate
automation cannot bypass.

#### Keystone-PR self-introduced required context (a serial merge-train deadlock)

A required status context that does NOT yet exist in any workflow on `main` — because it is
INTRODUCED by ONE open PR — deadlocks the WHOLE queue. Example: branch protection requires
`required-checks-gate`, but that context is produced by an `if: always()` aggregator job (with a
large `needs:` list) living in `.github/workflows/_required.yml` on a single "harden CI" PR. Every
OTHER open PR is missing that never-posted context and sits `BLOCKED`. The keystone PR can
self-satisfy because its OWN branch carries the gate workflow.

Diagnostic — the required context is configured but not on main:

```bash
gh api repos/OWNER/REPO/branches/main/protection/required_status_checks --jq .contexts
git grep -c "required-checks-gate" origin/main -- .github/   # 0 / not-on-main => producer is in an unmerged PR
```

Resolution: merge the KEYSTONE PR FIRST (it is the unblock-everything PR); then every other PR must
be RE-REBASED onto the new `main` to inherit the gate workflow so the context actually posts on
their HEAD. This is the chicken-and-egg ruleset deadlock — distinct from the bootstrap deadlock above
(there the gate blocks its OWN introducing PR; here the keystone self-satisfies but blocks the rest
of the queue until they rebase to inherit the producer workflow).

#### Duplicate check-runs after re-running a cancelled run

Re-running a failed/cancelled CI run can leave DUPLICATE check-runs of the same required-context name
on a single HEAD sha (one stale, one fresh):

```bash
gh api repos/OWNER/REPO/commits/SHA/check-runs \
  --jq '[.check_runs[]|{name,conclusion}]|group_by(.name)[]|{name:.[0].name,count:length,conclusions:[.[].conclusion]}'
# e.g. required-checks-gate appearing twice
```

If BOTH copies are `success` it is harmless to branch protection. If one is a stale `FAILURE` from a
cancelled duplicate run, re-run the FAILED run (`gh run rerun <id> --failed`) so the name resolves to
a single success. Beware: a rerun re-evaluates `changes-gate` and may flip most NON-required jobs to
`SKIPPED` (fine — only the named required contexts matter). Do NOT chase `SKIPPED` non-required jobs.

#### Unresolved review threads as primary BLOCKED diagnostic (verified-ci)

**FIRST check when `mergeStateStatus=BLOCKED` with all CI green and auto-merge armed.** A PR can be
stuck in BLOCKED even though every status check shows SUCCESS, `reviewDecision` is not CHANGES_REQUESTED,
and auto-merge is armed. The hidden cause: the repo has `required_review_thread_resolution: true` in
classic branch protection, and one or more review threads (from bots, CodeQL, or human reviewers)
are unresolved. GitHub silently blocks the merge engine.

**Critical diagnostic order:**
1. `gh pr checks <PR>` — verify all checks are genuinely green NOW (not reading stale UI)
2. `gh pr view <PR> --json mergeStateStatus,autoMergeRequest,reviewDecision` — confirm BLOCKED+armed
3. Query threads (see below) — look for `isResolved: false` entries

**Stale UI trap**: GitHub's PR page can display an error message (e.g. "lint failure") from a prior
run that has since been fixed. Always verify the CURRENT CI state via `gh pr checks` or
`gh api .../commits/SHA/check-runs` before investigating CI jobs.

```bash
# Step 1 — Verify current CI state (not the UI which may show stale errors)
gh pr checks <PR_NUMBER>

# Step 2 — Check merge state
gh pr view <PR_NUMBER> --json mergeStateStatus,autoMergeRequest,reviewDecision

# Step 3 — List all review threads and find unresolved ones
gh api graphql -f query='
query($owner:String!,$name:String!,$num:Int!){
  repository(owner:$owner,name:$name){
    pullRequest(number:$num){
      reviewThreads(first:50){
        nodes{
          isResolved
          id
          comments(first:10){
            nodes{
              author{login}
              body
              path
              line
            }
          }
        }
      }
    }
  }
}' -F owner=HomericIntelligence -F name=ProjectHephaestus -F num=<PR_NUMBER>

# Step 4 — Reply to thread citing fixing commit (do this before resolving)
gh api graphql -f query='
mutation($threadId:ID!,$body:String!){
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId,body:$body}){
    comment{id}
  }
}' -F threadId="PRRT_<id>" -F body="Addressed in commit <SHA>: <brief explanation>"

# Step 5 — Resolve the thread
gh api graphql -f query='
mutation($id:ID!){
  resolveReviewThread(input:{threadId:$id}){
    thread{isResolved}
  }
}' -F id="PRRT_<id>"

# Step 6 — Verify (mergeStateStatus briefly goes UNKNOWN, then auto-merge fires)
gh pr view <PR_NUMBER> --json mergeStateStatus,state
```

**After resolving all unresolved threads**: `mergeStateStatus` transitions `BLOCKED` → `UNKNOWN` →
auto-merge fires within seconds. The UNKNOWN state is transient and expected — do NOT re-arm
auto-merge during this window.

**Rules for resolving threads:**
- Only resolve a thread where the concern is GENUINELY addressed by committed code. Cite the fixing commit SHA in your reply.
- Do NOT resolve threads that represent open issues or open questions as a workaround.
- If a thread is from `@github-advanced-security` (CodeQL), classify as false-positive vs genuine before resolving. Note: `dismissed_comment` max length is 280 chars (HTTP 422 otherwise).
- A force-push amend re-runs CodeQL and can post NEW threads — re-check thread count after any amend.

**Verification:** PR #1282 ProjectHephaestus (branch `1315-harden-ci-required-gate`): 2 unresolved threads, all CI green, auto-merge armed. Resolved both threads via `resolveReviewThread`; PR merged at 2026-06-15T03:05:38Z by `app/github-actions` within seconds. **verified-ci.**

#### GPG-signing as a blocker

The ruleset's `required_signatures` silently blocks unsigned commits, and a `pr-policy` gate often re-checks signatures via GraphQL `verified: true`. Mismatched committer emails or a missing `-S` produce unsigned commits that block merge with no obvious failing test. `git log --show-signature` showing `U` (good signature, untrusted local key) is FINE — GitHub verifies against the REGISTERED key. Always sign with `-S`; an empty re-trigger commit must also be signed or it is rejected by the same gate it is trying to unblock.

#### Ruleset bootstrap deadlock

A PR adding a new CI workflow can be permanently `BLOCKED` with `failing_count=0` because the ruleset requires check names that exist ONLY in the workflow being added — and GitHub runs workflows from the BASE branch, so the new workflow never runs against its own PR. Signature: `mergeStateStatus=BLOCKED` + `failing_count=0` + workflow absent from `main`.

```bash
gh pr view $PR --repo $REPO --json mergeStateStatus,statusCheckRollup \
  --jq '{status:.mergeStateStatus, failing_count:([.statusCheckRollup[]|select(.conclusion!="SUCCESS" and .conclusion!="SKIPPED" and .conclusion!=null)]|length)}'
```

Resolve via: Option 1 admin "Merge without waiting for requirements" (fastest); Option 2 temporarily REMOVE the entire `required_status_checks` rule entry from `rules[]` (NOT `[]` — that returns HTTP 422 "Expected at least 1 elements, got 0"), merge, then restore; Option 3 a transitional PR that adds the workflow alongside the old aggregate check first.

#### Advisory-vs-required gate split

A timing-sensitive sub-check bundled into a REQUIRED gate (e.g. the auto-merge ↔ `state:implementation-go` state machine inside `pr-policy`) blocks correct PRs. The fix is to SPLIT it into its own job (e.g. `auto-merge-policy`) whose name is NOT in the ruleset — making it advisory (reports red as a signal, never blocks). The new job needs its OWN `gh pr view --json autoMergeRequest,labels,state` fetch and the SAME triggers (re-run on `auto_merge_enabled`/`auto_merge_disabled`/`labeled`/`unlabeled`, no `needs:`); trim the parent's fetch to `--json body`. Required-check membership lives in the ruleset, OUTSIDE the YAML — a new job is non-required BY DEFAULT until an operator adds its name. Update any text-based workflow tests that asserted the old bundled fetch string.

#### Arming-state machine (`state:implementation-go` + detected-merge)

Two distinct state machines gate arming:

1. **pr-policy label gate (#899).** The label and auto-merge state must MATCH: (`state:implementation-go` + auto-merge ON) or (no GO label + auto-merge OFF). Any mismatch fails `pr-policy` Check 2. Distinguish the error strings — `Auto-merge is not enabled on this PR` is the OLD propagation race (enable fast / rely on the `auto_merge_enabled` self-heal); `Auto-merge is enabled before implementation review GO` is the NEW gate where re-running alone does nothing. Fix by aligning the label (`gh pr edit <PR> --add-label state:implementation-go`, which re-runs `pr-policy` green with no new commit) OR disabling premature auto-merge (`gh pr merge <PR> --disable-auto`). Automate the GO transition with a `pull_request_target` `labeled` workflow that does NOT checkout PR code, re-fetches server-side metadata, validates a numeric `PR_NUMBER`, and arms `--auto --squash`. A workflow added by a PR is not active on `main` until that PR merges, so validate it on a follow-up PR. Guard `pr-policy` for terminal state: after merge GitHub clears `autoMergeRequest`, so fetch PR `state` and exit 0 for non-`OPEN` PRs.

2. **Capture on detected-merge, per-issue (#844).** Post-CI `/learn` (or any capture step) must fire on the TRUTH (`gh pr view --json mergedAt` confirms MERGED), not the optimistic point (`_enable_auto_merge` returned True) — otherwise captures pollute from PRs that armed but never shipped. Replace the optimistic call with a per-issue arming record (`state_dir/drive-green-armed-<issue>.json`: `pr_number`, `pr_head_branch`, `head_sha_at_arming`, `armed_at`, `learn_captured_at`). Fan out one record per sibling via the shared-PR dedupe map (`shared_pr_issues = {pr: [issues]}`) so a 9-issue shared PR yields 9 captures. Resolve at drive-start:

   | GH state | `learn_captured_at` | Head SHA | Action |
   |----------|--------------------|--------|--------|
   | any | not null | any | success, no capture (already done) |
   | MERGED | null | any | fire capture once, set `learn_captured_at` (always, even on failure), success |
   | OPEN | null | same | success, no capture (still in flight) |
   | OPEN | null | different | drop record, re-enter drive (force-pushed) |
   | CLOSED (not merged) | null | any | drop record, re-enter drive (abandoned) |

   Set `learn_captured_at` even on capture FAILURE (gating it on success loops forever). Fall back to `repo_root` for cwd when the post-merge worktree is gone.

#### ProjectHephaestus PR completion: policy first, current-head checks second

ProjectHephaestus PRs can look blocked when older failed check-rollup entries remain visible after
a later current run has already passed. Treat the PR as complete only after the policy prerequisites
are satisfied and the current-head required checks reach terminal success.

Policy prerequisites:

1. The PR body contains a literal issue-closing line such as `Closes #<issue>`.
2. Commits are signed and include DCO sign-off; verify locally with `git log --show-signature`.
3. The PR has the `state:implementation-go` label before auto-merge policy is expected to pass.
4. Auto-merge is armed with an allowed merge method (`--squash` for ProjectHephaestus).

Current-head verification:

1. Use `gh pr checks --watch --interval 30` to wait for the active Test matrix to reach a terminal
   state. Do not declare completion while the matrix is queued or in progress.
2. Use `gh pr view --json state,mergedAt,mergeCommit,mergeStateStatus,statusCheckRollup` as the
   final state snapshot.
3. If `statusCheckRollup` includes an older failed Required Checks entry, compare it against the
   later current run. A stale failed auto-merge-policy entry from before the GO label is evidence of
   an earlier policy mismatch, not necessarily a current blocker.

Public evidence: ProjectHephaestus PR #1646 was created for issue #1645 with literal
`Closes #1645`. Applying `state:implementation-go` allowed the later auto-merge policy to pass.
`gh pr merge --auto --squash` armed auto-merge. The PR merged on 2026-06-26 after Test workflow
run 28256151963 and Required Checks run 28256238895 succeeded; an earlier Required Checks run with
failed auto-merge-policy did not block the later merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Waited for auto-merge to fire on CLEAN PRs with zero CI | Left CLEAN+armed PRs for 9+ hours | Auto-merge needs at least one check EVENT; zero CI runs (path-excluded PR) means it never fires | `CLEAN` + `statusCheckRollup: []` is the stall signal; manual-merge or broaden `paths:` |
| Assumed no required checks => immediate merge | Verified protection had no required checks | GitHub still waits for a check event signal | Auto-merge != "merge when CLEAN" |
| `gh pr merge --auto --rebase` on a squash-only repo | Followed stale CLAUDE.md / hardcoded `--rebase` | `allow_rebase_merge: false` — CLI silently fails to arm; API fails loudly with GraphQL "Rebase merges are not allowed" | Detect allowed methods via `gh api repos/<repo>`; pick rebase->squash->merge; guard with a source-inspection test |
| Swapped a hardcoded `--rebase` for a hardcoded `--squash` | Reactive one-flag fix | Still wrong on a rebase-only/merge-only target | Settings-aware `choose_merge_flag`, not a new hardcode |
| `gh pr list` without `--limit` | Listed open PRs to arm a backlog | Default limit is 30 — 31+ open PRs silently omit the older ones | Always `--limit 200` when sweeping a backlog |
| Ran `gh pr create` then `gh pr merge --auto` sequentially | Two sequential commands | `pr-policy` read `autoMergeRequest` ~4s later, before enablement propagated → `Auto-merge is not enabled` | Enable fast; add the `auto_merge_enabled` trigger so the gate self-heals; else re-run after the run completes |
| Edited the PR body to add `Closes #N` expecting a re-run | Edited body, waited | `pull_request` does not fire on `edited` | Re-run the failed job; body edits never re-trigger |
| Treated `cancelled` sibling jobs as real failures | Counted every non-success rollup entry | One `pr-policy` race failure tore down the run via the `concurrency` group, cancelling all siblings; a green re-run superseded them | Filter by `conclusion=="FAILURE"` AND `startedAt` later than open+60s; cross-check `state` (may be MERGED); never force-merge to escape |
| Ran `--auto --squash` right after create on a #899 repo | Old habit | `pr-policy` Check 2 fails `Auto-merge is enabled before implementation review GO` | Match the label to the auto-merge state; add `state:implementation-go` OR `--disable-auto` |
| Enabled auto-merge before the implementation GO label | `gh pr merge --auto --squash` before `state:implementation-go` existed on the PR | The auto-merge-policy/pr-policy gate saw auto-merge armed before review approval state and failed the earlier Required Checks run | Apply `state:implementation-go` first, then rely on auto-merge policy; if a stale pre-label failure remains in the rollup, verify the later current run |
| Treated stale failed Required Checks rollup entries as current blockers | Read a failed Required Checks entry from before the GO label as if it described the current HEAD | A later Required Checks run passed after the label and did not block the merge | Check current-head `gh pr checks --watch` and the later Required Checks run before deciding the PR is blocked |
| Claimed completion before the Test matrix reached a terminal state | Saw auto-merge armed and policy prerequisites in place, then stopped watching | Auto-merge only merges after the active required checks finish; queued or in-progress matrix jobs can still fail | Keep `gh pr checks --watch --interval 30` running until the current-head Test matrix is terminal, then confirm `state=MERGED` / `mergedAt` |
| Added `{"type":"required_conversation_resolution"}` to a ruleset | PUT it into `rules[]` | `HTTP 422: data matches no possible input` — it is classic-only | Keep convo-resolution in classic; `required_linear_history`/`non_fast_forward` ARE valid ruleset types |
| PUT a ruleset with only the new rule in `{"rules":[...]}` | Partial PUT | Ruleset PUT is a FULL REPLACE — drops the entire baseline | Fetch, dedup same type, append, PUT the full object |
| Parsed `branches/main/protection` on an unprotected repo | Treated the 404 body as data | Top-level keys became fake contexts (`message`/`status`) that block all merges if PUT back | Guard `.status=="404"` before extracting contexts |
| Assumed ruleset `required_approving_review_count=0` meant no review gate | Ignored the classic layer | Classic independently required 1 review, blocking ~18 signed PRs | Audit BOTH layers; the union wins |
| Read `--log-failed` for a 4s `branch-protection-drift` failure | Assumed transient | It was `HTTP 403 Resource not accessible by integration` at the admin endpoint | Read the full `--log`; switch to `rules/branches/main`; fixing the 403 exposes real drift |
| Set `required_status_checks` to `[]` to unblock a bootstrap deadlock | Empty array PUT | `HTTP 422: Expected at least 1 elements, got 0` | Remove the entire rule ENTRY from `rules[]`, not patch it to `[]` |
| Re-triggered CI for a PR adding a new workflow | `gh workflow run` / push triggers | GitHub runs workflows from the BASE branch; the new workflow is absent on `main` | Bootstrap deadlock: admin-bypass, remove-rule-merge-restore, or a transitional PR |
| Kept the timing-sensitive auto-merge check inside required `pr-policy` | Operator workaround (disable-auto, rerun) | The check depends on a label-triggered workflow; a correct PR still failed and BLOCKED | Split orchestration/timing concerns into a non-required advisory job (name out of the ruleset) |
| Fired `/learn` on `_enable_auto_merge` returning True | Captured at the optimistic point | PRs arm then get blocked/cancelled; captures from PRs that never shipped pollute state | Capture only on detected-merge; use a per-issue arming record resolved by `gh pr view --json state,mergedAt` |
| One capture per PR for shared-PR groups | Dedupe collapsed N issues to 1 worker | Each issue is a distinct lesson; 8 siblings got none | Fan out via `shared_pr_issues` map: dedupe at the worker layer, fan out at the lesson layer |
| Pushed an unsigned empty commit to re-trigger CI | `git commit --allow-empty` without `-S` | The same `pr-policy`/`required_signatures` gate blocks unsigned commits | Sign re-trigger commits with `-S`; `U` (untrusted local key) is fine, GitHub verifies the registered key |
| `workflow_dispatch` to satisfy required checks | `gh workflow run <wf> --ref <branch>` | Dispatch runs do NOT satisfy branch-protection required contexts | CI must be triggered by `pull_request`; force-push after rebase to re-fire path filters |
| Trusted `mergeStateStatus` right after force-push | Checked immediately | It lags several minutes — shows BLOCKED while CI is passing | Verify via `actions/runs?branch=<branch>` matching `head_sha` |
| Treated an arm-time GraphQL "clean status" / "unstable status" error as fatal | Aborted (or force-merged) when `enablePullRequestAutoMerge` rejected the arm | These are transient: "clean status" is API lag on a fresh-CLEAN PR; "unstable status" is checks still settling (PR resolves to `UNKNOWN`, which accepts the arm) | "clean" → retry immediately; "unstable" → wait a few seconds and retry; only OTHER GraphQL errors are fatal |
| Assumed auto-merge waits for the LATEST commit's CI under `strict: false` | Trusted that a fired auto-merge meant the merged tip's CI had passed | `strict_required_status_checks_policy: false` accepts passing checks from a PRIOR commit SHA, so the newest commit's CI can still be QUEUED when auto-merge fires and merges | Check `gh api .../branches/main/protection/required_status_checks --jq .strict`; under `false`, stale-CI merges are expected behavior, not a fault |
| Assumed all-green + auto-merge armed ⇒ will merge | Left ~13 MERGEABLE+armed PRs expecting them to fire | A CLASSIC protection `required_approving_review_count: 1` (UNION with a ruleset's `0`) requires 1 human APPROVING review the automation cannot provide; `viewerCanEnableAutoMerge=false` | Check BOTH protection layers' review-count and take the UNION; a required human approval is a hard gate — only an `APPROVED` (not `COMMENTED`) human review clears it |
| Treated a never-posting required context as a CI flake | Re-ran CI / waited for `required-checks-gate` to post on every queued PR | The context was introduced by an unmerged keystone PR and is not on `main`; `git grep -c <ctx> origin/main -- .github/` returns 0 | Merge the keystone PR FIRST, then RE-REBASE the queue onto new `main` so each PR inherits the producer workflow and the context posts |
| Assumed CI failure based on stale UI message when BLOCKED with green checks | Took "lint failure" message at face value; investigated lint jobs; re-ran CI | Lint had already been fixed in prior commits; CI was already green; the UI message was stale from an older run | Always run `gh pr checks <PR>` and `gh pr view --json mergeStateStatus` to get current state; do not trust the web UI error text |
| Waited for auto-merge to self-trigger after CI passed (BLOCKED) | Expected auto-merge to fire on its own once CI was green | Two unresolved review threads were silently blocking the merge engine (`required_review_thread_resolution: true`) | `mergeStateStatus=BLOCKED` + all CI green + auto-merge armed = QUERY REVIEW THREADS FIRST via GraphQL `reviewThreads`; `resolveReviewThread` immediately unblocks |
| Regression test asserted `template = mod._AGENT_PROMPT_TEMPLATE` for an f-string template | The hardcoded `gh pr merge --auto --merge` lived inside an f-string built at call time by `_make_agent_prompt()` in `hephaestus/github/tidy.py`, not a module-level constant | `AttributeError: module 'hephaestus.github.tidy' has no attribute '_AGENT_PROMPT_TEMPLATE'` | For f-string templates, assert on `inspect.getsource(mod._make_agent_prompt)` (the f-string analogue of the `inspect.getsource(pr_merge)` PyGithub guard), not on a presumed module-level template constant |
| Used a 10-line look-back heuristic to exempt instructional `choose_merge_flag` example blocks from the merge-method lint | The lint exempted any hardcoded-flag hit within 10 lines of a `choose_merge_flag` mention | Brittle: re-orderings or a long preface broke the heuristic; a skill author could not predict whether their example would lint-clean | Replace with an explicit per-block marker `<!-- merge-method-allowed: example -->` on the immediately preceding non-blank line of the fenced block; the lint walks fence -> first non-blank and checks exact-string equality (concrete, file-local, predictable) |
| `gh api --jq '...' -` to process a stdin-piped response body | `printf '%s' "$raw" \| gh api --jq '...' -` to chain a second jq pass over a captured response | Non-standard usage; `gh api --jq` is documented to operate on the response of its OWN API call, not stdin. Some `gh` versions silently fail | Use plain `jq -r '...' 2>/dev/null` directly on the captured response body — the conventional, unsurprising form |

## Results & Parameters

### Auto-merge non-firing decision tree

```text
auto-merge armed but not merged
├── statusCheckRollup == []  AND  gh run list --branch <head> == []
│      → zero CI events; auto-merge will NEVER fire → manual merge or broaden paths:
├── mergeStateStatus == BLOCKED, failing_count == 0, workflow absent from main
│      → ruleset bootstrap deadlock → admin-bypass / remove-rule-merge-restore / transitional PR
├── all required checks green but BLOCKED  ← CHECK REVIEW THREADS FIRST (verified-ci: PR #1282)
│      → STEP 1: query unresolved review threads via GraphQL reviewThreads (isResolved==false)
│                reply with addPullRequestReviewThreadReply citing fixing commit
│                then resolveReviewThread — auto-merge fires within seconds
│      → STEP 2 (if threads all resolved): NON-required check still red/pending → fix it
│      → STEP 3: required context name mismatch / never posted → align name + integration_id 15368
├── pr-policy red: "Auto-merge is enabled before implementation review GO"
│      → label/auto-merge mismatch → add state:implementation-go OR --disable-auto
├── autoMergeRequest.mergeMethod absent after --rebase
│      → squash-only repo → re-arm with detected --squash
└── unsigned commit / email mismatch
       → required_signatures / pr-policy signature gate → re-sign with -S (registered key verified)
```

### Tiered helper sourcing for cross-repo callers

Prefer **sourcing the helper** over re-defining `choose_merge_flag` inline. The helper exists as
a real, sourceable file in ProjectHephaestus: `scripts/choose_merge_flag.sh`. A sub-agent running
a Hephaestus skill from inside *another* repo (e.g. running `/finish-branch` against a
Mnemosyne worktree) cannot see that file via the current worktree's
`git rev-parse --show-toplevel`. Use a three-candidate tiered lookup with `--squash` as the
org-wide-correct fallback (every HomericIntelligence repo is squash-only):

```bash
HELPER=""
for cand in \
    "${HEPHAESTUS_REPO_ROOT:-}/scripts/choose_merge_flag.sh" \
    "$(git rev-parse --show-toplevel 2>/dev/null)/scripts/choose_merge_flag.sh" \
    "$HOME/Projects/ProjectHephaestus/scripts/choose_merge_flag.sh"; do
    if [ -r "$cand" ]; then HELPER="$cand"; break; fi
done
if [ -n "$HELPER" ]; then
    . "$HELPER"
    MERGE_FLAG=$(choose_merge_flag "$(gh repo view --json nameWithOwner --jq .nameWithOwner)") \
        || MERGE_FLAG="--squash"   # safe org-wide default per HomericIntelligence policy
else
    MERGE_FLAG="--squash"
fi
gh pr merge --auto "$MERGE_FLAG"
```

The helper itself uses plain `jq -r` on the captured response body — NOT the `gh api --jq -`
stdin-pipe trick, which is non-standard and silently fails on some `gh` versions.

### Marker-based lint exemption for instructional code blocks

The companion lint (`hephaestus/validation/skill_merge_method.py` in ProjectHephaestus) scans
skill files for hardcoded `gh pr merge --auto --(rebase|squash|merge)` and would otherwise flag
any "do-not-copy" example. The exemption is an explicit per-block marker on the immediately
preceding non-blank line of the fenced code block:

```text
<!-- merge-method-allowed: example -->
\`\`\`bash
gh pr merge --auto --rebase   # OLD: do not copy
\`\`\`
```

The lint walks backward from the matching line to the fence open, then to the first non-blank
line, and checks exact-string equality. The marker exempts only the *immediately following*
block; a second hardcoded flag in a *later* block is still flagged. This replaced an earlier
fragile 10-line look-back heuristic ("is this hit near a `choose_merge_flag` mention?") because
the marker is concrete, file-local, and predictable for skill authors.

### Regression-test pattern for f-string templates

When the hardcoded merge flag lives inside an f-string built at call time (not a module-level
constant), an `inspect.getsource` assertion is the durable regression guard. Example for
`hephaestus/github/tidy.py:_make_agent_prompt`:

```python
import inspect
import re
from hephaestus.github import tidy

def test_agent_prompt_does_not_hardcode_merge_method() -> None:
    source = inspect.getsource(tidy._make_agent_prompt)
    assert not re.search(r"--auto\s+--(rebase|squash|merge)\b", source), \
        "tidy._make_agent_prompt still hardcodes a merge method; use choose_merge_flag instead."
    assert "choose_merge_flag" in source
```

This is the f-string analogue of the `inspect.getsource(pr_merge)` test for the PyGithub
call-site bug. Asserting on `_AGENT_PROMPT_TEMPLATE` (assuming a module constant) raises
`AttributeError` because the template is constructed inside the function — a common gotcha.

### Confirmed HomericIntelligence settings

```json
{"rebase": false, "squash": true, "merge": false}
```

| Parameter | Value |
| --------- | ----- |
| Merge method (HI repos) | `--squash` (rebase disabled; detect, don't hardcode) |
| GitHub Actions app id for `required_status_checks.integration_id` | `15368` |
| Baseline ruleset contexts | `lint, unit-tests, integration-tests, build, schema-validation, security/dependency-scan, security/secrets-scan, deps/version-sync` |
| HI `pull_request` ruleset params | count `0`, `dismiss_stale_reviews_on_push false`, `require_last_push_approval false`, `required_review_thread_resolution true`, `require_code_owner_review false` |
| Review-count UNION (observed ProjectHephaestus) | classic `required_approving_review_count=1` UNION ruleset `required_approving_review_count=0` (+ `required_review_thread_resolution true`) ⇒ effective 1 human approval required; automation cannot clear it |
| Required status contexts (observed ProjectHephaestus) | `'test (ubuntu-latest, 3.12, integration)'`, `'test (ubuntu-latest, 3.12, unit)'`, `required-checks-gate` |
| `required-checks-gate` producer | an `if: always()` aggregator job in `.github/workflows/_required.yml`; a PR lacking that workflow version never gets the context |
| `dismissed_comment` (CodeQL dismiss) max length | 280 chars (HTTP 422 otherwise) |
| Required-check context format | bare job `name:` (e.g. `lint`), NOT `"Required Checks / lint"` |
| GO label set | `state:plan-go`, `state:plan-no-go`, `state:needs-plan`, `state:implementation-go`, `state:implementation-no-go` |
| Arming record path | `state_dir/drive-green-armed-<issue>.json` |
| `gh pr list` default limit | 30 — use `--limit 200` for backlogs |

### Label-gated auto-merge workflow constraints

| Constraint | Value |
| --------- | ----- |
| Event | `pull_request_target` with `types: [labeled]` |
| Condition | label is `state:implementation-go`, PR `open`, not draft |
| Permissions | `contents: write`, `pull-requests: write` |
| Forbidden | `actions/checkout` (do not execute PR-controlled code) |
| Input guard | numeric-only `PR_NUMBER` |
| Metadata | re-fetch `gh pr view --json autoMergeRequest,isDraft,labels,state` (event payload is stale) |
| Arm | `gh pr merge "$PR" --repo "$REPO" --auto --squash` |

### ProjectHephaestus current-head PR-policy completion checklist

Use this sequence when finishing a ProjectHephaestus PR by hand or verifying that automation did it
correctly:

```bash
# Verify the commit identity and signature before pushing or before trusting the PR policy gate.
git log --show-signature -1 --format=fuller

# Create and inspect the linked issue.
gh issue create --repo HomericIntelligence/ProjectHephaestus --title "..." --body "..."
gh issue view <ISSUE> --repo HomericIntelligence/ProjectHephaestus

# The PR body must include the literal closing line.
gh pr create --repo HomericIntelligence/ProjectHephaestus --title "..." --body $'Summary...\n\nCloses #<ISSUE>'

# Policy ordering: apply GO state, then arm auto-merge.
gh issue edit <PR> --repo HomericIntelligence/ProjectHephaestus --add-label state:implementation-go
gh pr merge <PR> --repo HomericIntelligence/ProjectHephaestus --auto --squash

# Wait for the current-head Test matrix, not a stale rollup entry.
gh pr checks <PR> --repo HomericIntelligence/ProjectHephaestus --watch --interval 30
gh pr view <PR> --repo HomericIntelligence/ProjectHephaestus \
  --json state,mergedAt,mergeCommit,mergeStateStatus,statusCheckRollup
```

If a failed Required Checks entry predates the GO label but a later Required Checks run on the
current head succeeds, do not treat the stale failure as a blocker. The completion signal is the
later successful required run plus `state=MERGED`, `mergedAt`, and `mergeCommit` populated.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| AchaeanFleet | 11 CLEAN+armed PRs stuck 9+ hours with zero CI | Path filter broadened; remaining merged manually |
| ProjectCharybdis | 32 armed PRs; review requirement relaxed but 23 did not auto-fire; bootstrap deadlock on PRs #4/#5 | Swept armed state with `gh pr merge --squash`; deadlock resolved via admin bypass |
| ProjectScylla | Ruleset 15556492 — empty-array PUT returned 422 | Remove-rule PUT succeeded, PR merged, ruleset restored |
| ProjectKeystone / ProjectAgamemnon | Pure-transport refactor — pixi-lock, just.systems flake, CodeQL pack, auto-merge-on-non-required (Keystone #577–#581, Agamemnon #419–#421, merged 2026-05-31) | All traps fixed in live CI |
| ProjectNestor | Unresolved CodeQL review threads gated #101/#97; `branch-protection-drift` 403 | Resolving threads flipped BLOCKED→merged 2026-06-02; switched to rules endpoint + ecosystem reconcile |
| ProjectHephaestus | `pr-policy` label-gate (#899/#901/#903/#904/#906/#908/#910), `pull_request_target` arming workflow (#915/#917), squash-only docs/code fix (#668/#904/#911), per-issue arming-state machine (#844, builds on #835), pre-armed auto-merge trap (#1073/#1075/#1077), advisory split (#1081 closes #1080) | Label alignment re-ran `pr-policy` green; settings-aware merge selection shipped; `/learn` capture keyed on detected-merge; advisory split verified-local (107 `tests/unit/ci` pass) |
| HomericIntelligence (all 15 repos) | Two-layer protection audited + applied live; `homeric-main-baseline` ruleset rollout | Union confirmed; Keystone 404-body fake-context trap corrected; Nestor classic count:1 patched to 0 |
| ProjectHephaestus | 2026-06-14: drove 13 open PRs toward mergeable during a `/myrmidon-swarm` run — hit the classic-vs-ruleset review-count UNION hard gate (`viewerCanEnableAutoMerge=false`), a `required-checks-gate` keystone PR (`_required.yml` `if: always()` aggregator) blocking the whole queue, and duplicate check-runs after a re-run | verified-local: the union gate was confirmed by API inspection (classic count=1 UNION ruleset count=0); keystone-first + re-rebase identified as the queue unblock; PRs had not yet merged at capture |
| ProjectHephaestus | 2026-06-14: PR #1282 (`1315-harden-ci-required-gate`) BLOCKED with all CI green and auto-merge armed; stated "lint failure" was stale; root cause was 2 unresolved review threads; resolved via `resolveReviewThread` GraphQL mutation | **verified-ci**: PR merged at 2026-06-15T03:05:38Z by `app/github-actions` auto-merge within seconds of thread resolution; `mergeStateStatus` transitioned BLOCKED → UNKNOWN → MERGED |
| ProjectHephaestus | 2026-06-26: PR #1646 for issue #1645 completed with literal `Closes #1645`, signed DCO commit, `state:implementation-go`, `gh pr merge --auto --squash`, and current-head Test/Required Checks verification | **verified-ci**: PR merged after Test workflow run 28256151963 and Required Checks run 28256238895 succeeded; an earlier pre-label Required Checks failure was stale and did not block the merge |
