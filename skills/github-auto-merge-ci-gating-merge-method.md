---
name: github-auto-merge-ci-gating-merge-method
description: "Use when: (1) a PR has mergeStateStatus CLEAN or MERGEABLE but auto-merge never fires despite all checks passing, (2) gh pr merge --auto --rebase or --squash returns an error or silently fails on a squash-only repo, (3) a PR is BLOCKED because required CI status contexts never post (workflow never triggered, paths filter excluded PR, required check name mismatch), (4) GPG-signing failures or mismatched committer emails cause commits to be unsigned and block the pr-policy gate, (5) branch protection rulesets and classic branch protection disagree and their union blocks merge, (6) a CI ruleset chicken-and-egg deadlock blocks a PR that introduces a new workflow, (7) an advisory check should not block merge but currently does because it lives in the required gate, (8) deciding which merge method a repo supports before arming auto-merge, (9) auditing required-check names after adding or removing CI jobs, (10) state:implementation-go label or pr-policy gates auto-merge arming, (11) per-issue arming-state machine is triggered on the wrong event (optimistic point vs detected merge)"
category: ci-cd
date: 2026-06-14
version: "1.2.0"
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
---

# GitHub Auto-Merge: CI Gating, Branch Protection, and Merge Method

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-06-07 | Consolidated canonical for why GitHub auto-merge does not fire and how to arm it correctly: wrong merge method, missing/required CI status contexts, two-layer branch protection, GPG-signing blockers, ruleset bootstrap deadlock, the `state:implementation-go` arming-state machine, and advisory-vs-required gate split | Each failure mode has a verified diagnosis + fix; verified across many HomericIntelligence repos in live CI |
| 2026-06-14 | Add the classic-vs-ruleset review-count UNION hard gate (a required human approval automation cannot provide), the keystone-PR self-introduced-required-context merge-train deadlock (merge keystone first, then re-rebase the queue), and duplicate check-run resolution after a re-run | Diagnosed live across 13 open ProjectHephaestus PRs during a `/myrmidon-swarm` drive (verified-local; the PRs had not yet merged at capture, the review-union gate was confirmed by API inspection) |

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
MERGE_FLAG=$(choose_merge_flag "HomericIntelligence/ProjectMnemosyne")   # -> --squash here
gh pr merge "$PR" --auto "$MERGE_FLAG" --repo HomericIntelligence/ProjectMnemosyne
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

## Results & Parameters

### Auto-merge non-firing decision tree

```text
auto-merge armed but not merged
├── statusCheckRollup == []  AND  gh run list --branch <head> == []
│      → zero CI events; auto-merge will NEVER fire → manual merge or broaden paths:
├── mergeStateStatus == BLOCKED, failing_count == 0, workflow absent from main
│      → ruleset bootstrap deadlock → admin-bypass / remove-rule-merge-restore / transitional PR
├── all required checks green but BLOCKED
│      → unresolved review threads (required_review_thread_resolution) → GraphQL reviewThreads, assess, resolve
│      → OR a NON-required check still red/pending (auto-merge is stricter than branch protection) → fix it
│      → OR required context name mismatch / never posted → align name + integration_id 15368
├── pr-policy red: "Auto-merge is enabled before implementation review GO"
│      → label/auto-merge mismatch → add state:implementation-go OR --disable-auto
├── autoMergeRequest.mergeMethod absent after --rebase
│      → squash-only repo → re-arm with detected --squash
└── unsigned commit / email mismatch
       → required_signatures / pr-policy signature gate → re-sign with -S (registered key verified)
```

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
