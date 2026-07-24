---
name: automation-review-authorization-ci-boundary
description: "Keep automation-loop source-review authorization independent of CI/CD. Use when: (1) a strict PR review is mistakenly implemented as a required CI check, (2) an agent loop cannot observe or control the external workflow that is supposed to authorize it, (3) loop approval must survive restart using only loop-owned PR state, (4) a direct `--prs` review run must prove its closing-issue requirements before consuming a reviewer-model job, (5) a downstream rerun must short-circuit on a merged PR because GitHub clears autoMergeRequest after merge, or (6) merge_wait treats an externally armed open PR as success or lets pending auto-merge polling run without distinguishing the current run's arm from an external one."
category: architecture
date: 2026-07-24
version: "1.7.0"
user-invocable: false
verification: verified-ci
history: automation-review-authorization-ci-boundary.history
tags:
  - automation-loop
  - pr-review
  - ci-independent
  - authorization-boundary
  - implementation-go
  - restart-safety
  - state-label
  - source-review
  - merge-wait
  - external-auto-merge
  - pending-poll-budget
  - blocked-open-pr
  - in-memory-reseed
  - docs-review
---

# Automation Review Authorization: CI Boundary

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-24 |
| **Objective** | Keep a code-automation loop's strict source-review decision inside that loop rather than delegating its authorization to CI/CD, and enforce it at the auto-merge boundary. |
| **Outcome** | ProjectHephaestus moved strict-review proof, workflow triggers, artifacts, leases, and CI-status contracts out of the authorization path. The loop's own CI-free PR review applies `state:implementation-go` after a GO verdict; its review-local payload is then reduced to a fixed non-authorizing context before `merge_wait` can consume the label. PR #2347 showed the complete path: a B/GO review reported its own sandbox verification gap, applied the label, and merged after the repository's independent required checks passed. PR #2357 confirmed the complementary admission behavior: a direct `--prs 2357` run with `reviewer-model=sol` and medium effort produced zero agent jobs because the PR had no standalone `Closes #N` requirement link. PR #2418 / issue #2386 closed the merge-wait gap: an externally armed open PR is blocked, while only the current run's own pending arm consumes a bounded poll budget. |
| **Verification** | verified-ci — PR #2418's non-skipped checks, including `pr-policy`, `auto-merge-policy`, and `required-checks-gate`, passed before merge; the review decision itself remained source-review-only. |
| **Latest verified lesson** | PR #2421 / issue #2420: restart reseeds normally without recovering per-run ownership; other-run arms remain untouched, and docs review uses source links plus existing Markdown/link validation instead of prose snapshots. |

## When to Use

- A strict source review has been added as a required CI check even though the automation loop, not CI, is expected to decide whether implementation may advance.
- The loop is blocked by a workflow artifact, status, lease, or trigger that it cannot start, observe reliably, or repair.
- A restart path needs to determine whether a PR may proceed without reconstructing a CI-run proof artifact.
- You need to retire an external review-proof system while preserving historical ADRs and making the active contract unambiguous.
- A direct `--prs` discovery route can create an issue-less work item that reaches merge-wait with a stale or externally applied GO label.
- You are about to launch a direct `--prs` review run and need to know whether a selected reviewer model will actually be invoked, rather than merely selected by CLI configuration.
- A process-local strict-review mutex is released at a stage handoff even though the successor has not yet confirmed the live head and armed auto-merge.
- Review-local head, verdict, or evidence data remains in a work item after the label has been applied, where a later stage could accidentally turn it into a second authorization requirement.
- A downstream rerun evaluates a PR after merge and must short-circuit on PR state instead of expecting `autoMergeRequest` to still be present; GitHub clears `autoMergeRequest` on merged PRs.
- `merge_wait` returns success merely because an open PR already has an external auto-merge request, or a pending arm can retry forever without distinguishing the current run's arm from an externally owned one.

- A restart/recovery description invents durable merge-wait state instead of documenting the in-memory queue and ordinary reseeding contract.
- A docs-only implementation plan proposes tests that freeze prose, headings, or identifier absence instead of validating source links and executable behavior.

## Verified Workflow

### Quick Reference

```text
automation loop owns source-review authorization
  1. read the live PR source, diff, and loop-owned state
  2. run the strict PR review in the loop (CI-free)
  3. if and only if the review returns GO, apply state:implementation-go
  4. merge_wait consumes that loop-owned label and the live PR head

merge-wait is also the authorization boundary of last resort
  1. reject an item without required issue/requirements context before label use or arm
  2. leave any observed auto-merge request untouched; its owner is external or ambiguous
  3. terminally fail the orphaned item without a label or auto-merge mutation
  4. retain the strict-review guard only through operations the current queue actually owns

merge-wait terminal-state contract
  1. an externally armed OPEN PR is BLOCKED, not FINISH_PASS; do not mutate it
  2. a CLOSED or unavailable PR fails before consuming the merge budget
  3. only pending polls of the current run's own arm consume `merge`
  4. positive-budget exhaustion returns `merge_wait_exhausted` without changing labels

CI/CD is outside this decision:
  - do not query checks, workflow runs, artifacts, or deployments
  - do not create review-proof workflows or triggers on review/implementation-go
  - do not make an external CI result a prerequisite for loop progress
```

### Restart/review contract
  1. queue state is in memory; restart reseeds through the ordinary classifier
  2. do not reconstruct per-run merge-wait ownership from durable recovery records
  3. other-run auto-merge arms are BLOCKED without adoption, mutation, or re-arming
  4. for docs-only changes, prefer direct source links and existing Markdown/link validation over prose or identifier-absence snapshots

### Direct-PR admission preflight

```bash
PR=2357
REPO=HomericIntelligence/Hephaestus

# `--prs` selects a target; it does not override the requirements-context invariant.
gh pr view "$PR" --repo "$REPO" --json number,body,closingIssuesReferences \
  --jq '{number, closingIssuesReferences, body}'

# Require exactly one standalone closing line before spending a reviewer-model job.
gh pr view "$PR" --repo "$REPO" --json body --jq .body \
  | rg -x 'Closes #[0-9]+'
```

If this preflight has no exact closing line or no usable linked requirement, stop and repair the
PR metadata first. Do not retry with a different reviewer model or reasoning effort: model
selection is downstream of deterministic admission, so it cannot turn an orphaned PR into a
reviewable one.

### Detailed Steps

1. Establish a single decision owner. Source-review authorization belongs to the automation loop when that loop is responsible for planning, implementation, review, and advancement. CI/CD may validate a repository independently, but it is not evidence the loop can depend on for this decision.

2. Run the strict PR review as an in-loop, CI-free operation against the live PR diff. Require an explicit GO result before transition; a missing, ambiguous, or NO-GO result must not apply the approval label.

   For direct `--prs` operation, first verify the requirements context deterministically. `--prs`
   identifies the PR but does not waive the exact standalone `Closes #N` contract or synthesize
   acceptance criteria from prose such as `Addresses #N`. When the preflight fails, the correct
   result is a fail-closed terminal record with zero reviewer jobs; changing `--reviewer-model` or
   its reasoning effort must not bypass that result. This is admission control, not a duplicate
   LLM policy check and not a CI dependency.

3. Report review evidence precisely. A reviewer may issue GO from sufficient source and local evidence even when its sandbox cannot independently rerun every claimed test, but it must name the gap, avoid claiming those tests passed, and grade the evidence accordingly. Do not turn that disclosure into a CI dependency for the loop decision.

4. Record the completed loop decision with one loop-owned state marker such as `state:implementation-go`. `merge_wait` should consume that marker and the live PR head when it restarts; it must not require a workflow artifact, lease, status context, or an external proof document.

5. Discard review-local state after the label's post-write current-head confirmation and before transition to `merge_wait`. Use a fixed allowlist of ordinary issue/implementation context, the cleanup worktree path, and the process-local handoff mutex. Do not retain review heads, verdicts, attempts, artifacts, leases, evidence, or a dynamically captured ingress-key list. A denylist cannot anticipate aliases; a dynamic ingress list can preserve a forged or stale proof after a retry. The current-head check must precede sanitization so a concurrent head change still follows the normal containment path with the original review state available.

6. Enforce the requirements-context invariant at `merge_wait.on_enter`, not only at strict review. An unlinked direct PR may have an externally retained GO label, and a stage-routing regression can otherwise bypass the strict-stage orphan check. The orphan entry path terminally rejects it before label use or arming. In the normal ARM flow, a fresh live-state read treats a present or ambiguous auto-merge request as externally owned, leaves it untouched, and blocks with no label mutation. This makes stale labels non-authoritative when the work item lacks its required context.

7. Treat the strict-review guard as a handoff mutex, not merely a strict-stage mutex. Keep it held after strict review advances to merge-wait. Release it only when merge-wait's first arm operation has returned its successful continuation after live-label/head verification and arm confirmation. Preserve ownership through fail-back/retry to strict review; release idempotently on terminal finish, shutdown parking, or exception handling.

8. Keep the boundary mechanically enforceable. Delete CI workflows and automatic tasks that trigger from review or implementation-go solely to produce authorization proof. Remove their references from active documentation, agent directions, prompt contracts, and tests.

9. Cover direct PR discovery as well as issue-driven discovery. First distinguish a PR with a valid closing requirement from an orphan: only the former may reach strict review. For that valid PR, if the strict stage needs issue/comment context, pass the PR number as its work-item context rather than `None`. Passing `None` converts a valid PR into a terminal strict-review failure. If direct PRs deliberately remain issue-less, they must stop at admission/merge-wait under step 6; never treat a label alone, the `--prs` selector, or reviewer-model configuration as enough to compensate for missing requirements context.

10. Preserve ADR history. Do not rewrite accepted historical decisions just to erase obsolete policy. Add a new superseding ADR and update the ADR index so active readers find the current contract while audits retain the original record.

11. Validate the source-only behavior locally: resolve the PR identity and exact head, inspect the source diff and active contracts, run targeted stage/documentation tests, and run `git diff --check`. Tests must cover (a) an orphaned merge-wait item with GO label: any existing arm is left untouched, no queue arm occurs, and the item terminates; (b) a competing strict reviewer remains blocked during an owned merge-wait operation; and (c) known, unknown, and forged review-proof aliases do not cross the successful GO handoff. State clearly that this is not CI evidence.

12. Short-circuit downstream reruns on terminal PR state. If a later workflow or review pass reruns after the PR has merged, fetch PR `state` first and exit 0 when it is not `OPEN`. GitHub clears `autoMergeRequest` on merged PRs, so a null arm is expected and not a blocker.

13. Bound the merge-wait poll contract. Treat an `autoMergeRequest` observed before or outside the current run as operator-owned: return `BLOCKED`, do not arm, retry, consume the `merge` budget, or change labels. For the arm created by this run, increment the `merge` attempt only while the PR remains open and pending; retry until the strictly positive budget is exhausted, then return `FINISH_FAIL` with `merge_wait_exhausted` and leave labels unchanged. Terminal `CLOSED` or unavailable PR state must fail before arm handling and before budget consumption.

14. Treat coordinator queues as in-memory. On restart, reseed PRs through the ordinary classifier and current live state; do not reconstruct merge_wait entries or per-run arm ownership from retired durable recovery symbols. An auto-merge request created by another run remains external and requires operator handling.

15. Keep docs-only review evidence maintainable. If a plan proposes assertions about exact prose, headings, or retired-identifier absence, replace them with direct source links and the repository's existing Markdown/link validation unless executable behavior is actually being tested. Record the review correction and keep runtime scope unchanged.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Put strict-review proof in CI/CD | A required workflow generated proof artifacts and gated progress. | The automation loop did not control the CI loop, so it could neither make progress nor make a trustworthy decision from that external state. | The component that owns the review decision must execute and persist it; make strict source review an in-loop CI-free operation. |
| Restart from external proof data | `merge_wait` depended on workflow artifacts, leases, and status records. | Those records were external coupling, could be absent or stale after restart, and were unnecessary once loop-owned approval existed. | Restart from the loop-owned approval label and live PR state only. |
| Preserve strict-review ingress fields dynamically | A review pass snapshotted its ingress payload keys and kept those keys after GO. | An unknown alias or forged snapshot entry could preserve review evidence; after a NOGO retry, the stale snapshot could drop fresh implementation context. | At the GO boundary, retain a small fixed set of non-authorizing context keys instead of trying to classify or remember review fields. |
| Treat a repository-wide PR as an issue-less strict review | Direct PR discovery constructed a work item with `issue=None`. | The strict stage requires issue/comment context and rejected the work item as terminal. | For direct PR review, use the PR number as the work-item context unless the design supplies an equivalent explicit context. |
| Retry an orphaned direct PR with a different reviewer setting | Launched `hephaestus-automation-loop --prs 2357 --reviewer-model sol --reviewer-reasoning-effort medium` without first proving an exact closing requirement. | The admission gate found no standalone `Closes #N` line, completed with `agent jobs: 0`, and no reviewer model was invoked; `Addresses #2138 and #2223` was not usable requirements context. | Preflight direct PR metadata before dispatch. `--prs` and model flags select work only after the deterministic requirements-context invariant passes. |
| Trust strict review as the only orphan check | An unlinked direct PR with a stale `state:implementation-go` label was routed around strict review and into merge-wait. | The strict-stage check never ran on that path, so merge-wait could otherwise act on a stale label without requirements context. | Repeat the invariant at the irreversible side-effect boundary: leave an observed auto-merge request untouched, block it as external, and fail before merge-wait reads labels or arms. |
| Release strict guard at the stage transition | The guard was released as soon as strict review routed to merge-wait. | A competing strict reviewer could enter while the first item was between review approval and confirmed arming. | Retain ownership through merge-wait's first successful arm and release on its `POLL` continuation; all finish/park/exception paths remain idempotent releases. |
| Treat `autoMergeRequest` as a post-merge signal | A rerun checked `autoMergeRequest` after the PR had already merged. | GitHub clears `autoMergeRequest` on merged PRs, so the rerun misread a terminal PR as still pending. | Post-merge consumers must check `state` and short-circuit on non-`OPEN` instead of treating `autoMergeRequest` as durable. |
| Treat an externally armed open PR as successful merge-wait completion | `merge_wait` returned `FINISH_PASS` for an auto-merge request created before or outside the current run. | The PR remained open, so the loop reported completion without owning or observing the arm; it also made an operator-owned setting look like loop progress. | External arms are `BLOCKED` and untouched. Only a current-run arm may enter bounded pending polling. |
| Reuse the old drive-green retry budget for merge-wait | The option and route treated the budget as generic per-issue attempts, allowing invalid values and conflating review/implementation retries with merge polls. | A merge-wait poll could be unbounded or consume budget on an external arm; a zero budget could also make the contract meaningless. | Name the budget for current-run pending merge polls, validate it as strictly positive, and consume it only in the own-arm `POLL` state. |
| Reintroduce durable merge-wait recovery prose | A later documentation consolidation restored references to `pending_drive_green_arms`, `_pending_arm_recovery_entries`, and `merge_wait_recovery` after the durable recovery flow had been removed. | The documented APIs and state no longer exist; the current coordinator owns only in-memory queues and ordinary classifier reseeding. | Derive restart documentation from the live implementation: reseed normally and never adopt, mutate, or re-arm another run's auto-merge request. |
| Freeze docs prose or retired identifiers in regression tests | The initial #2420 plan requested wording/absence assertions for the replacement documentation. | Athena review identified these as prohibited prose-string/documentation snapshots that would couple tests to editorial text rather than behavior. | Use direct source links plus existing Markdown/link validation for docs-only corrections; add executable tests only for computable behavior. |
| Rewrite accepted ADRs to remove obsolete instructions | Historical ADR text was modified in place. | It obscured the decision record and broke the repository's ADR immutability convention. | Preserve accepted ADRs verbatim; add a superseding ADR and make the index point to the active policy. |

## Results & Parameters

| Item | Result |
|------|--------|
| Decision marker | `state:implementation-go` is the sole loop-owned authorization after a current review GO. |
| Prohibited dependencies | CI checks, workflow runs, artifacts, deployments, external status contexts, and review-proof leases. |
| Review-state handoff | After the label's current-head readback, retain only fixed non-authorizing context, cleanup, and the ephemeral handoff mutex; discard all review result and proof aliases. |
| Direct-PR correction | Use the PR number as strict-review work-item context rather than `None`. |
| Direct-PR admission | Before launching reviewer work, require one exact standalone `Closes #N` line and a usable linked requirement. `Addresses #N` is not a substitute; failed admission means zero agent jobs by design. |
| Defense in depth | `merge_wait.on_enter` rejects `issue=None` before consuming labels or arming; the normal ARM flow blocks an observed external arm and leaves it untouched after a fresh PR-state read. |
| Guard lifetime | Strict-review ownership covers the strict-to-merge-wait handoff and first successful arm; it is released only after that arm confirms continuation to polling. |
| Merge-wait ownership and budget | PR #2418 / issue #2386: an external open arm returns `BLOCKED` with zero mutation and zero `merge` attempts; a current-run pending arm retries only until the positive `merge` budget, then returns `FINISH_FAIL` / `merge_wait_exhausted` without changing labels. |
| Restart/reseed contract | PR #2421 / issue #2420: queue state is in memory; restart uses ordinary classifier reseeding and never recovers per-run ownership. Other-run open arms remain blocked and untouched. |
| Post-merge terminality | PR #2306 / issue #2177 merged at `2026-07-21T01:53:35Z` with `state=MERGED`; `autoMergeRequest` is `null` and `mergeStateStatus` was `UNKNOWN` after merge. Downstream reruns must key off PR state and treat terminal PRs as complete. |
| Review evidence boundary | PR #2347's reviewer passed `diff --check`, Ruff, formatting, mypy, and direct probes but could not rerun pytest or artifact builds in its sandbox. It reported a B/GO without overclaiming those tests; source review authorized the label, while the independent required-checks gate completed before merge. |
| Docs review correction | PR #2421 / issue #2420: Athena review rejected prose/identifier-absence assertions; direct source links and the existing Markdown/link validation preserved a docs-only scope. |
| Local validation example | `uv run pytest` over pipeline stage/coordinator and active-documentation/ADR tests: 85 passed; `git diff --check` passed. |
| Historical-policy migration | Preserve accepted ADRs; record the new label-only rule in a superseding ADR and its index entry. |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2280 / issues #2053 and #2276 | CI-free source review and loop-owned `state:implementation-go` authorization. The direct repository-wide PR route now supplies PR context to strict review. Local swarm review then found that dynamic review-payload preservation could retain an aliased proof or survive a NOGO retry; a fixed allowlist removes those fields only after the label's current-head readback. Local verification only; no CI/CD state was queried. |
| ProjectHephaestus | PR #2306 / issue #2177 | Docs PR that reached merged state through the normal review-to-merge path: review GO, loop-owned `state:implementation-go`, and merge_wait. Post-merge `gh pr view` showed `state=MERGED` with `autoMergeRequest=null`, confirming reruns must short-circuit on terminal PR state. |
| ProjectHephaestus | PR #2347 / issue #2283 | The review posted B/GO at `ecba01d9`, explicitly recorded that its sandbox could not rerun pytest or artifact builds, and applied `state:implementation-go` at `2026-07-21T04:35:08Z`. `merge_wait` completed the merge at `2026-07-21T04:44:01Z` as `fde855ad`, after the independent required-checks gate succeeded. |
| ProjectHephaestus | PR #2357 | A scoped direct-PR run selected Sol at medium reasoning effort, but the deterministic admission gate found no exact `Closes #N` link and completed with `agent jobs: 0`. The independent strict review could still inspect the source, but the in-loop reviewer was correctly not invoked. Verified locally; no CI conclusion follows from this admission result. |
| ProjectHephaestus | PR #2418 / issue #2386 | The review/merge path reached `state:implementation-go`; one code-quality bot comment was non-blocking, all non-skipped CI checks passed (including `pr-policy`, `auto-merge-policy`, and `required-checks-gate`), and the PR merged at `2026-07-24T15:25:15Z`. The PR's three signed commits and merge-wait regression suite verified the bounded current-run poll behavior in CI. |
