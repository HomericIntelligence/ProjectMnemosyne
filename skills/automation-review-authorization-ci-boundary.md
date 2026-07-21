---
name: automation-review-authorization-ci-boundary
description: "Keep automation-loop source-review authorization independent of CI/CD. Use when: (1) a strict PR review is mistakenly implemented as a required CI check, (2) an agent loop cannot observe or control the external workflow that is supposed to authorize it, (3) loop approval must survive restart using only loop-owned PR state, or (4) a downstream rerun must short-circuit on a merged PR because GitHub clears autoMergeRequest after merge."
category: architecture
date: 2026-07-20
version: "1.4.0"
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
---

# Automation Review Authorization: CI Boundary

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-20 |
| **Objective** | Keep a code-automation loop's strict source-review decision inside that loop rather than delegating its authorization to CI/CD, and enforce it at the auto-merge boundary. |
| **Outcome** | ProjectHephaestus moved strict-review proof, workflow triggers, artifacts, leases, and CI-status contracts out of the authorization path. The loop's own CI-free PR review applies `state:implementation-go` after a GO verdict; its review-local payload is then reduced to a fixed non-authorizing context before `merge_wait` can consume the label. PR #2347 showed the complete path: a B/GO review reported its own sandbox verification gap, applied the label, and merged after the repository's independent required checks passed. |
| **Verification** | verified-ci — PR #2347's full CI suite and required-checks gate passed before merge; the review decision itself remained source-review-only. |

## When to Use

- A strict source review has been added as a required CI check even though the automation loop, not CI, is expected to decide whether implementation may advance.
- The loop is blocked by a workflow artifact, status, lease, or trigger that it cannot start, observe reliably, or repair.
- A restart path needs to determine whether a PR may proceed without reconstructing a CI-run proof artifact.
- You need to retire an external review-proof system while preserving historical ADRs and making the active contract unambiguous.
- A direct `--prs` discovery route can create an issue-less work item that reaches merge-wait with a stale or externally applied GO label.
- A process-local strict-review mutex is released at a stage handoff even though the successor has not yet confirmed the live head and armed auto-merge.
- Review-local head, verdict, or evidence data remains in a work item after the label has been applied, where a later stage could accidentally turn it into a second authorization requirement.
- A downstream rerun evaluates a PR after merge and must short-circuit on PR state instead of expecting `autoMergeRequest` to still be present; GitHub clears `autoMergeRequest` on merged PRs.

## Verified Workflow

### Quick Reference

```text
automation loop owns source-review authorization
  1. read the live PR source, diff, and loop-owned state
  2. run the strict PR review in the loop (CI-free)
  3. if and only if the review returns GO, apply state:implementation-go
  4. merge_wait consumes that loop-owned label and the live PR head

merge-wait is also the authorization boundary of last resort
  1. reject an item without required issue/requirements context before any arm
  2. durably defer any existing auto-merge request and re-read its state
  3. only then terminally fail the orphaned item
  4. retain the strict-review guard until the first successful arm confirmation

CI/CD is outside this decision:
  - do not query checks, workflow runs, artifacts, or deployments
  - do not create review-proof workflows or triggers on review/implementation-go
  - do not make an external CI result a prerequisite for loop progress
```

### Detailed Steps

1. Establish a single decision owner. Source-review authorization belongs to the automation loop when that loop is responsible for planning, implementation, review, and advancement. CI/CD may validate a repository independently, but it is not evidence the loop can depend on for this decision.

2. Run the strict PR review as an in-loop, CI-free operation against the live PR diff. Require an explicit GO result before transition; a missing, ambiguous, or NO-GO result must not apply the approval label.

3. Report review evidence precisely. A reviewer may issue GO from sufficient source and local evidence even when its sandbox cannot independently rerun every claimed test, but it must name the gap, avoid claiming those tests passed, and grade the evidence accordingly. Do not turn that disclosure into a CI dependency for the loop decision.

4. Record the completed loop decision with one loop-owned state marker such as `state:implementation-go`. `merge_wait` should consume that marker and the live PR head when it restarts; it must not require a workflow artifact, lease, status context, or an external proof document.

5. Discard review-local state after the label's post-write current-head confirmation and before transition to `merge_wait`. Use a fixed allowlist of ordinary issue/implementation context, the cleanup worktree path, and the process-local handoff mutex. Do not retain review heads, verdicts, attempts, artifacts, leases, evidence, or a dynamically captured ingress-key list. A denylist cannot anticipate aliases; a dynamic ingress list can preserve a forged or stale proof after a retry. The current-head check must precede sanitization so a concurrent head change still follows the normal containment path with the original review state available.

6. Enforce the requirements-context invariant at `merge_wait.on_enter`, not only at strict review. An unlinked direct PR may have an externally retained GO label, and a stage-routing regression can otherwise bypass the strict-stage orphan check. Before recovery, label consumption, or arming, invoke the same fail-closed helper used for unsafe arm state: request auto-merge deferral, re-read live PR state to confirm it is disarmed, then return terminal failure. This makes stale labels non-authoritative when the work item lacks its required context.

7. Treat the strict-review guard as a handoff mutex, not merely a strict-stage mutex. Keep it held after strict review advances to merge-wait. Release it only when merge-wait's first arm operation has returned its successful continuation after live-label/head verification and arm confirmation. Preserve ownership through fail-back/retry to strict review; release idempotently on terminal finish, shutdown parking, or exception handling.

8. Keep the boundary mechanically enforceable. Delete CI workflows and automatic tasks that trigger from review or implementation-go solely to produce authorization proof. Remove their references from active documentation, agent directions, prompt contracts, and tests.

9. Cover direct PR discovery as well as issue-driven discovery. If the strict stage needs issue/comment context, pass the PR number as its work-item context for a PR discovered without a closing issue. Passing `None` converts a valid PR into a terminal strict-review failure. If direct PRs deliberately remain issue-less, they must stop at merge-wait under step 6; never treat a label alone as enough to compensate for missing requirements context.

10. Preserve ADR history. Do not rewrite accepted historical decisions just to erase obsolete policy. Add a new superseding ADR and update the ADR index so active readers find the current contract while audits retain the original record.

11. Validate the source-only behavior locally: resolve the PR identity and exact head, inspect the source diff and active contracts, run targeted stage/documentation tests, and run `git diff --check`. Tests must cover (a) an orphaned merge-wait item with GO label: defer is attempted, no arm occurs, terminal failure; (b) a competing strict reviewer remains blocked during merge-wait arm and proceeds only after the successful arm continuation; and (c) known, unknown, and forged review-proof aliases do not cross the successful GO handoff. State clearly that this is not CI evidence.

12. Short-circuit downstream reruns on terminal PR state. If a later workflow or review pass reruns after the PR has merged, fetch PR `state` first and exit 0 when it is not `OPEN`. GitHub clears `autoMergeRequest` on merged PRs, so a null arm is expected and not a blocker.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Put strict-review proof in CI/CD | A required workflow generated proof artifacts and gated progress. | The automation loop did not control the CI loop, so it could neither make progress nor make a trustworthy decision from that external state. | The component that owns the review decision must execute and persist it; make strict source review an in-loop CI-free operation. |
| Restart from external proof data | `merge_wait` depended on workflow artifacts, leases, and status records. | Those records were external coupling, could be absent or stale after restart, and were unnecessary once loop-owned approval existed. | Restart from the loop-owned approval label and live PR state only. |
| Preserve strict-review ingress fields dynamically | A review pass snapshotted its ingress payload keys and kept those keys after GO. | An unknown alias or forged snapshot entry could preserve review evidence; after a NOGO retry, the stale snapshot could drop fresh implementation context. | At the GO boundary, retain a small fixed set of non-authorizing context keys instead of trying to classify or remember review fields. |
| Treat a repository-wide PR as an issue-less strict review | Direct PR discovery constructed a work item with `issue=None`. | The strict stage requires issue/comment context and rejected the work item as terminal. | For direct PR review, use the PR number as the work-item context unless the design supplies an equivalent explicit context. |
| Trust strict review as the only orphan check | An unlinked direct PR with a stale `state:implementation-go` label was routed around strict review and into merge-wait. | The strict-stage check never ran on that path, so merge-wait could otherwise arm auto-merge without requirements context. | Repeat the invariant at the irreversible side-effect boundary: defer, confirm deferral, and fail before merge-wait reads labels or arms. |
| Release strict guard at the stage transition | The guard was released as soon as strict review routed to merge-wait. | A competing strict reviewer could enter while the first item was between review approval and confirmed arming. | Retain ownership through merge-wait's first successful arm and release on its `POLL` continuation; all finish/park/exception paths remain idempotent releases. |
| Treat `autoMergeRequest` as a post-merge signal | A rerun checked `autoMergeRequest` after the PR had already merged. | GitHub clears `autoMergeRequest` on merged PRs, so the rerun misread a terminal PR as still pending. | Post-merge consumers must check `state` and short-circuit on non-`OPEN` instead of treating `autoMergeRequest` as durable. |
| Rewrite accepted ADRs to remove obsolete instructions | Historical ADR text was modified in place. | It obscured the decision record and broke the repository's ADR immutability convention. | Preserve accepted ADRs verbatim; add a superseding ADR and make the index point to the active policy. |

## Results & Parameters

| Item | Result |
|------|--------|
| Decision marker | `state:implementation-go` is the sole loop-owned authorization after a current review GO. |
| Prohibited dependencies | CI checks, workflow runs, artifacts, deployments, external status contexts, and review-proof leases. |
| Review-state handoff | After the label's current-head readback, retain only fixed non-authorizing context, cleanup, and the ephemeral handoff mutex; discard all review result and proof aliases. |
| Direct-PR correction | Use the PR number as strict-review work-item context rather than `None`. |
| Defense in depth | `merge_wait.on_enter` rejects `issue=None` before consuming labels or arming; deferral is confirmed by a fresh PR-state read. |
| Guard lifetime | Strict-review ownership covers the strict-to-merge-wait handoff and first successful arm; it is released only after that arm confirms continuation to polling. |
| Post-merge terminality | PR #2306 / issue #2177 merged at `2026-07-21T01:53:35Z` with `state=MERGED`; `autoMergeRequest` is `null` and `mergeStateStatus` was `UNKNOWN` after merge. Downstream reruns must key off PR state and treat terminal PRs as complete. |
| Review evidence boundary | PR #2347's reviewer passed `diff --check`, Ruff, formatting, mypy, and direct probes but could not rerun pytest or artifact builds in its sandbox. It reported a B/GO without overclaiming those tests; source review authorized the label, while the independent required-checks gate completed before merge. |
| Local validation example | `uv run pytest` over pipeline stage/coordinator and active-documentation/ADR tests: 85 passed; `git diff --check` passed. |
| Historical-policy migration | Preserve accepted ADRs; record the new label-only rule in a superseding ADR and its index entry. |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2280 / issues #2053 and #2276 | CI-free source review and loop-owned `state:implementation-go` authorization. The direct repository-wide PR route now supplies PR context to strict review. Local swarm review then found that dynamic review-payload preservation could retain an aliased proof or survive a NOGO retry; a fixed allowlist removes those fields only after the label's current-head readback. Local verification only; no CI/CD state was queried. |
| ProjectHephaestus | PR #2306 / issue #2177 | Docs PR that reached merged state through the normal review-to-merge path: review GO, loop-owned `state:implementation-go`, and merge_wait. Post-merge `gh pr view` showed `state=MERGED` with `autoMergeRequest=null`, confirming reruns must short-circuit on terminal PR state. |
| ProjectHephaestus | PR #2347 / issue #2283 | The review posted B/GO at `ecba01d9`, explicitly recorded that its sandbox could not rerun pytest or artifact builds, and applied `state:implementation-go` at `2026-07-21T04:35:08Z`. `merge_wait` completed the merge at `2026-07-21T04:44:01Z` as `fde855ad`, after the independent required-checks gate succeeded. |
