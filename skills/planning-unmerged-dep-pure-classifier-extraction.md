---
name: planning-unmerged-dep-pure-classifier-extraction
description: "Two entangled planning-phase disciplines for building a stage/module against an unmerged dependency AND making a blocking poll loop non-blocking. (1) PLAN-AGAINST-UNMERGED-DEPENDENCY: when planning issue N that depends on unmerged issue N-1 whose package does not exist on disk yet (`ls pkg/` → not found, `git branch -a | grep pkg` → empty, `gh pr list` does not list N-1), treat the EPIC's frozen contract (the full approved design pasted verbatim in the epic body) as the interface spec, and make implementation STEP 1 an explicit 'compatibility probe' that reads the real merged base/routing/work-item/jobs modules and pins exact imported names/constructors BEFORE writing stage code. Every `ctx.retry()`, `ctx.advance()`, `ctx.fail_back()`, `Route(next=…, fail_routes=…)`, `item.attempts[...]`, `item.state` name is an ASSUMED API from epic prose, unverified against merged code — list them for the reviewer. (2) EXTRACT-A-PURE-CLASSIFIER-TO-DE-BLOCK-A-POLL-LOOP: an in-stage `time.sleep` would freeze a single-threaded coordinator, so the sleep/backoff loop CANNOT move into the stage; instead extract ONLY the conclusion-classification logic as a pure `list-in / enum-out` function (`classify_ci_state(checks) -> CiConclusion` with GREEN/FAILING/PENDING/NO_CHECKS), leaving the impure sleep/backoff tail in the legacy method. The classifier takes ALREADY-FETCHED data (`checks: list[dict]`), NOT a PR number — the `gh` fetch stays in the caller, so the classifier is trivially unit-testable over fixtures and the stage module imports no gh/sleep. UN-COLLAPSE overloaded sentinels: a legacy `None`-for-both-NO_CHECKS-and-TIMEOUT return must become two distinct enum members (NO_CHECKS = advance/success, PENDING = timer-park, no timeout because the coordinator heap owns the deadline). Place the classifier in the module that ALREADY owns the loop (a cycle-free leaf) so the stage imports FROM it, never back. FLAG the semantic-change risk when converting a WALL-CLOCK-bounded sleep loop (`HEPH_PR_MERGE_MAX_WAIT` 1800s, exponential backoff) into a COUNT-bounded timer-park (N poll windows × backoff ≠ 1800s). Use when: (1) planning issue N against unmerged issue N-1 with no branch/PR, consuming an epic's frozen contract, (2) extracting a pure classifier so a blocking poll can be timer-heap-parked, (3) you catch a poll helper returning one `None` sentinel for two semantically-different outcomes, (4) refactoring a legacy poll loop to CALL a new classifier and claiming existing `patch.object` seams prove behavior preservation, (5) converting a time-bounded loop into a count-bounded one."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - pipeline-stages
  - unmerged-dependency
  - frozen-contract
  - pure-classifier
  - non-blocking-poll
  - timer-heap
  - sentinel-separation
  - semantic-change-risk
  - epic-serialized-issues
  - compatibility-probe
  - behavior-preservation
  - assumptions
  - nogo-revision
---

# Planning Against an Unmerged Dependency + Extracting a Pure Classifier to De-Block a Poll Loop

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Capture two entangled planning-phase disciplines from planning ProjectHephaestus issue #1816 (`feat(pipeline): ci drive-green and merge-wait stages`, part of epic #1809, depends on #1815): (1) authoring a stage/module against a dependency (#1815) whose package (`hephaestus/automation/pipeline/`) does NOT exist on disk yet, by consuming the epic's frozen contract and gating on a compatibility-probe step; and (2) extracting a PURE `list-in / enum-out` classifier from a blocking poll loop so the loop can become a non-blocking timer-heap park, while un-collapsing an overloaded `None` sentinel. |
| **Outcome** | PLANNING ARTIFACT ONLY — the plan was authored but NEVER implemented. No code was written, no tests ran, no CI validated it. The line counts / anchors cited below WERE measured from disk (AST/Read) during planning and are verified reads; the resulting PLAN was never executed. |
| **Verification** | unverified — no code executed, no tests ran, no CI. Every `pipeline/`-API name is assumed from epic prose (#1815 unmerged); the `ci_run_coordinator.py` / `ci_driver.py` / `github_api/checks.py` line anchors were Read from disk and are real. |
| **History** | v1.0.0 (2026-07-04): initial capture from the ProjectHephaestus #1816 plan (epic #1809, dep #1815 unmerged). Three core themes: plan-against-unmerged-dependency via frozen contract + compatibility probe; pure-classifier extraction to de-block a poll loop; and six named uncertain-assumption reviewer risks. |

> **Scope & sibling skills.** This skill covers the specific intersection of "plan against an
> unmerged dependency" AND "extract a pure classifier to make a blocking poll non-blocking."
> For the case where the dependency is ALREADY MERGED and just needs reading from `main`, see
> `planning-dependent-issue-unverified-upstream` (its lesson: delete conditional forks, read the
> merged code). For the Mojo/training-flavored "consume an approved parent PLAN comment + gate on a
> compile-smoke-test" variant, see `planning-unmerged-parent-contract-compile-smoke-gate` — this
> skill is its non-Mojo, pipeline-stage sibling and adds the pure-classifier-extraction angle.
> For the *counter-lesson* on the poll-helper sentinel, see `automation-pola-poll-helper-none-sentinel`:
> that skill KEEPS a single `None` sentinel for a data-only poll helper; THIS skill un-collapses that
> sentinel because a timer-heap model needs NO_CHECKS and TIMEOUT/PENDING distinguished.

## When to Use

- Planning issue N that depends on unmerged issue N-1 where N-1's package does not exist on disk yet:
  `ls <pkg>/` returns not-found, `git branch -a | grep <pkg>` is empty, and `gh pr list` does not
  list N-1. You cannot import or verify the real protocol/constructors/enum/route-table shape.
- The dependency's interface is only described in an **epic body's frozen contract** (the full
  approved design pasted verbatim in the epic issue), which is the single source of truth for the
  scaffolding.
- You are about to write stage/module code that references an API (`ctx.retry(delay_s=…)`,
  `ctx.advance()`, `Route(next=…, fail_routes=…)`, `item.attempts[...]`, `StageOutcome`,
  `Disposition`) that exists only in epic prose, not in any merged file.
- You need to make a blocking poll loop non-blocking under a single-threaded coordinator, and an
  in-stage `time.sleep` would freeze the whole coordinator — so the sleep/backoff loop cannot move
  into the stage.
- You catch a legacy poll helper returning ONE `None` sentinel for TWO semantically-different
  outcomes (e.g. "no checks configured" AND "timeout"), and a timer-heap model needs them
  distinguished.
- You are refactoring a legacy poll loop to CALL a newly-extracted classifier and are tempted to
  claim existing `patch.object` seams staying green proves behavior preservation.
- You are converting a WALL-CLOCK-bounded sleep loop into a COUNT-bounded timer-park loop
  (N poll windows × backoff vs a fixed second budget).

## Verified Workflow

<!-- The literal token "## Verified Workflow" is required by scripts/validate_plugins.py.
This skill's verification level is "unverified" — the PROPOSED WORKFLOW subsection below carries
the real semantics. Do not read this heading as an implicit warranty. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. No code was written or run; no tests
> ran; no CI validated it. It is the plan-authoring discipline distilled from an *unexecuted* plan
> (ProjectHephaestus #1816). The line anchors cited were Read from disk during planning and are real,
> but the resulting plan was never implemented. Treat every checklist item as a hypothesis until CI
> confirms. The single gate that would empirically discharge the "epic prose == merged API" assumption
> is the compatibility-probe step (Step 1 of implementation), which has NOT been run.

### Quick Reference

```bash
# ===== PLAN-AGAINST-UNMERGED-DEPENDENCY: prove the dependency is genuinely unmerged =====
# All three MUST be empty/not-found before you fall back to the epic's frozen contract.
ls hephaestus/automation/pipeline/                 # -> No such file or directory
git branch -a | grep -i pipeline                   # -> (empty)
gh pr list --repo <org>/<repo> --search "1815" --state all --json number,state  # -> []

# The epic's frozen contract is the ONLY interface spec you may consume:
gh issue view 1809 --repo <org>/<repo>             # read the pasted-verbatim design section

# ===== COMPATIBILITY PROBE (implementation STEP 1, run AFTER #1815 merges) =====
# Pin the EXACT imported names/constructors before writing a line of stage code.
Read hephaestus/automation/pipeline/stages/base.py    # StageOutcome / Disposition / ctx.* protocol
Read hephaestus/automation/pipeline/routing.py        # ROUTES table shape, Route(...) kwargs, StageName enum
Read hephaestus/automation/pipeline/work_item.py      # item.attempts[...], item.state
Read hephaestus/automation/pipeline/jobs.py           # worker JobRequest signature

# ===== EXTRACT-A-PURE-CLASSIFIER: verify the loop-owning module is a cycle-free leaf =====
grep -n "def poll_ci_until_concluded\|import" hephaestus/automation/ci_run_coordinator.py
# The classifier goes in the module that ALREADY owns the loop; the stage imports FROM it.
# Verify no import cycle: the stage must NOT be imported back into ci_driver.py / ci_run_coordinator.py.

# ===== SEMANTIC-CHANGE RISK: is the legacy bound WALL-CLOCK or COUNT? =====
grep -n "HEPH_PR_MERGE_MAX_WAIT\|max_wait\|2\*\*attempt\|max-merge-attempts" \
  hephaestus/automation/ci_driver.py
# _wait_for_pr_terminal bounds by SECONDS (HEPH_PR_MERGE_MAX_WAIT=1800, exp backoff), NOT poll count.
```

### Detailed Steps

1. **Prove the dependency is genuinely unmerged (all three signals), then consume the epic's frozen contract.**
   Run `ls <pkg>/` (not-found), `git branch -a | grep <pkg>` (empty), and
   `gh pr list --search "<N-1>" --state all` (`[]`). Only when ALL THREE are empty is this the
   "package does not exist on disk" case (distinct from `planning-dependent-issue-unverified-upstream`,
   where the dependency IS merged and must be read from `main`). The interface spec is then the
   **epic's frozen contract** — the full approved design pasted verbatim in the epic body — NOT the
   issue prose, NOT analogy to another framework. Transcribe the protocol/constructors from the epic
   contract; do NOT invent hedging fallbacks (that trap is covered by the sibling skills).

2. **Make implementation STEP 1 an explicit compatibility probe, and say so in the plan.**
   The FIRST implementation step (after #1815 merges) reads the real merged modules and pins the exact
   imported names/constructors BEFORE any stage code is written:
   `Read base.py` (the stage protocol, `StageOutcome`/`Disposition` constructors, the `ctx.*` methods),
   `Read routing.py` (the `ROUTES` table shape, `Route(...)` kwargs, the `StageName` enum),
   `Read work_item.py` (`item.attempts[...]`, `item.state`), `Read jobs.py` (the worker `JobRequest`
   signature). This is the ONLY gate that empirically discharges the "epic prose == merged API"
   assumption. Do not skip it in favor of "start writing and see what fails" — that pushes contract-drift
   discovery to the slowest feedback loop.

3. **List every assumed-from-epic-prose API in a dedicated reviewer section.**
   Every `ctx.retry(delay_s=…)`, `ctx.advance()`, `ctx.fail_back(reason)`, `ctx.finish_fail(reason)`,
   `ctx.continue_()`, `item.attempts[...]`, `item.state`, `Route(next=…, fail_routes=…, budgets=…)`,
   `StageOutcome`, `Disposition`, `StageName` name in the plan is ASSUMED — not verified against merged
   code because #1815 is unmerged. Put them in an "Unverified API Assumptions" table
   (Symbol | Assumed shape | Where cited | Verify with) so the reviewer has a targeted attack surface
   and the implementer has a pre-flight checklist for the compatibility probe.

4. **To de-block a blocking poll loop, extract ONLY the pure classifier — leave the sleep/backoff tail put.**
   An in-stage `time.sleep` would freeze a single-threaded coordinator, so the sleep/backoff loop
   CANNOT move into the stage. Extract ONLY the conclusion-classification logic as a pure
   `list-in / enum-out` function: `classify_ci_state(checks: list[dict]) -> CiConclusion` with members
   `GREEN / FAILING / PENDING / NO_CHECKS`. The impure sleep/backoff tail stays in the legacy method.

5. **The classifier takes ALREADY-FETCHED data, NOT a resource id — keep the fetch in the caller.**
   Pass `checks: list[dict]`, not a PR number. The `gh` fetch stays in the caller. This makes the
   classifier trivially unit-testable over fixtures and keeps the stage module free of any `gh`/`sleep`
   import. Apply the same shape twice: `classify_ci_state` (from
   `ci_run_coordinator.poll_ci_until_concluded`) and `classify_pr_merge_state` (from
   `ci_driver._wait_for_pr_terminal`'s loop body).

6. **UN-COLLAPSE overloaded sentinels: one `None` for two outcomes becomes two enum members.**
   The legacy `poll_ci_until_concluded` returns `None` for BOTH "no checks configured" AND "timeout" —
   two semantically-different cases collapsed into one sentinel (see `ci_run_coordinator.py`: the
   docstring is literally "Poll CI until all required checks conclude, no checks exist, or timeout hits",
   and the caller does `if poll_result is None: return WorkerResult(success=True)` — treating BOTH as
   success). The new enum SEPARATES them: `NO_CHECKS` (advance/success) vs `PENDING` (timer-park, with
   NO timeout — the coordinator heap owns the deadline, not the classifier). When extracting a
   classifier, un-collapse overloaded sentinels and document each enum member's meaning.

7. **Place the classifier in the module that ALREADY owns the loop (a cycle-free leaf); verify no cycle.**
   Put `classify_ci_state` in `ci_run_coordinator.py` (which imports only cycle-free leaf modules). The
   stage imports FROM the coordinator, never back into `ci_driver.py`. This mirrors the leaf-placement /
   cycle-avoidance discipline: a pure helper belongs in the lowest module that already owns the data, so
   nothing higher needs a back-edge. Verify with a `grep`/import check that the stage is never imported
   into the coordinator or driver.

8. **Treat "the 269 existing `patch.object` seams stay green" as a PROXY for behavior preservation, not a PROOF.**
   Refactoring the legacy `poll_ci_until_concluded` to CALL the new classifier (instead of duplicating
   the logic) risks a behavior change. Existing mock seams staying green is a necessary-but-not-sufficient
   signal; a reviewer MUST diff the refactored loop branch-by-branch against the original. State this
   explicitly in the plan — do not present the green seams as if they proved equivalence.

9. **Flag the WALL-CLOCK → COUNT semantic change as the single riskiest assumption — do NOT silently convert.**
   The legacy `_wait_for_pr_terminal` bounds by WALL-CLOCK seconds (`HEPH_PR_MERGE_MAX_WAIT`, default
   1800s, with `min(2**attempt, 60)` exponential backoff), NOT by a poll COUNT. Describing the new
   `merge` budget as "`--max-merge-attempts` poll windows" is a SEMANTIC CHANGE: N poll windows × backoff
   ≠ 1800s. Surface it as an explicit reviewer risk rather than converting it silently. If the timer-heap
   model genuinely requires a count bound, say so and give the reviewer the math to check the equivalence
   (or the deliberate divergence).

10. **Verify the coverage/omit invariants for any NEW covered module you add.**
    Confirm the loop-owning module is NOT on the coverage omit list (so its new pure function is
    auto-covered), AND confirm that adding a NET-NEW covered module under the new package does not trip a
    frozen-omit-allowlist test. Net-new covered code is usually fine, but the frozen-list guard is
    load-bearing enough to check explicitly, not assume.

11. **Keep the honesty gate: this is a planning artifact, mark it `unverified`.**
    No code ran, no tests ran, no CI validated it. The line anchors you cite ARE verified reads (you
    Read them from disk during planning), but the PLAN was never implemented — say both, plainly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Design `classify_ci_state(pr_number)` to take a PR number and fetch the checks internally with `gh`. | Puts a `gh` call inside the stage step, so the "pure" classifier is no longer pure — its unit tests would need `gh` mocking and the stage module would import subprocess/gh. | Make the classifier `list-in / enum-out`: pass `checks: list[dict]` (already fetched by the caller). The `gh` fetch stays in the caller; the classifier is trivially testable over fixtures and the stage imports no gh/sleep. |
| 2 | Reuse the legacy `None` sentinel as-is for the extracted classifier (return `None` for both "no checks" and "timeout"). | It collapses two semantically-different outcomes (NO_CHECKS vs TIMEOUT/PENDING) into one value. The timer-heap model must treat NO_CHECKS as advance/success and PENDING as a timer-park with NO timeout (the coordinator heap owns the deadline) — those cannot share a sentinel. | Un-collapse the overloaded sentinel into a proper enum (`GREEN/FAILING/PENDING/NO_CHECKS`) and document each member's meaning. A single `None` that means two things is a latent bug when the two meanings later diverge. |
| 3 | Keep the merge-wait's 1800s WALL-CLOCK bound (`HEPH_PR_MERGE_MAX_WAIT`) while describing the new `merge` budget as "`--max-merge-attempts` poll windows." | A count of poll windows × exponential backoff does NOT equal a fixed 1800-second budget. Silently converting a time-bounded loop into a count-bounded timer-park changes the semantics of when a merge-wait gives up — arguably the single riskiest assumption in the whole plan. | Do not silently convert a time-bounded loop into a count-bounded one. Flag it as an explicit reviewer risk, and either preserve the wall-clock bound in the timer-heap model or give the reviewer the equivalence math for the deliberate divergence. |
| 4 | Move the whole sleep/backoff poll loop into the stage step so the stage "owns" the wait. | An in-stage `time.sleep` freezes the single-threaded coordinator — the entire pipeline stalls while one stage sleeps. | Extract ONLY the pure conclusion-classifier into the stage; leave the impure sleep/backoff tail in the legacy method, and let the coordinator's timer heap own the deadline (PENDING → park, re-poll later). |
| 5 | Place the new classifier in the stage module (or in `ci_driver.py`) and have the coordinator import it. | Risks an import cycle (stage ↔ driver) and puts a pure helper above the module that already owns the loop and the data. | Place the pure classifier in the module that ALREADY owns the loop (`ci_run_coordinator.py`, a cycle-free leaf); the stage imports FROM it, never back. Verify no cycle with an import grep. |
| 6 | Present "the 269 existing `patch.object` seams in `test_ci_driver.py` stay green" as proof that the legacy-loop refactor preserves behavior. | Green mock seams are a PROXY, not a proof — they assert the mocked call boundaries are unchanged, not that the loop's branch logic is byte-for-byte equivalent after being rerouted through the classifier. | Diff the refactored loop branch-by-branch against the original and say in the plan that the green seams are necessary-but-not-sufficient. Never let a proxy masquerade as equivalence. |
| 7 | Drop the `policy_only_failure` logging-only branch (`ci_driver.py:1575-1582`) when mirroring `_wait_for_pr_terminal` into `classify_pr_merge_state` without confirming it was a no-op. | If that branch had altered the returned merge state, dropping it would silently change behavior. (On disk it only calls `logger.info` and falls through — verified read — so dropping it is safe HERE, but the plan must state that verification, not assume it.) | When mirroring a legacy loop into a pure classifier, every branch you DROP must be confirmed to not affect the returned value. A logging-only branch is safe to drop; verify it, cite the line, and record the verification. |

> These are planning-phase design-decision reversals — no code ran, but each is a rejected design that
> a future planner should not re-derive.

## Results & Parameters

- **Status:** Planning-discipline methodology distilled from authoring ProjectHephaestus issue #1816
  (`feat(pipeline): ci drive-green and merge-wait stages`, epic #1809, depends on unmerged #1815). The
  plan was authored but NEVER implemented — no code, no tests, no CI. The gh/git/AST inspection commands
  and line-anchored Reads below WERE run during planning and are real.

- **Verified reads (measured from disk during planning, ProjectHephaestus tree):**
  - `hephaestus/automation/pipeline/` — does NOT exist (`ls` → not-found); no `pipeline` branch
    (`git branch -a | grep -i pipeline` → empty); #1815/#1816 not listed by `gh pr list`. This is the
    genuine "dependency package not on disk" case.
  - `ci_run_coordinator.py` — `poll_ci_until_concluded` (docstring line ~207: "Poll CI until all
    required checks conclude, no checks exist, or timeout hits"); the caller (~lines 167-178) does
    `if poll_result is None: return WorkerResult(success=True)` and tests `conclusion in
    ("success", "skipped", "neutral")`. This is the collapsed `None`-for-two-outcomes sentinel and the
    `("success","skipped","neutral")` conclusion set that `classify_ci_state` would copy.
  - `github_api/checks.py` — `_PR_CHECK_BUCKET_MAP` (lines ~10-16) only ever emits conclusion in
    `{success, failure, skipped, None}`; "neutral" is carried for parity but never appears via the
    pr-checks path. `_map_pr_check` hardcodes `"required": False` (line ~28), so a
    `[c for c in checks if c.get("required")] or checks` filter ALWAYS falls back to "all checks" on the
    pr-checks path — the "required" filter is effectively inert for pr-checks-sourced data.
  - `ci_driver.py` — `_wait_for_pr_terminal` (def ~1479) bounds by `HEPH_PR_MERGE_MAX_WAIT` seconds
    (default 1800, `read_timeout_env` ~1510) with `min(2**attempt, 60)` backoff — WALL-CLOCK, not poll
    count. The `policy_only_failure` branch (~1575-1582) is logging-only (`logger.info` then falls
    through) — safe to drop from a pure `classify_pr_merge_state`.

- **The two reusable patterns:**
  1. **Plan-against-unmerged-dependency:** when issue N depends on unmerged issue N-1 whose package is
     not on disk, treat the EPIC's frozen contract as the interface spec and make implementation step 1
     a compatibility probe that pins the real merged API. List every assumed-from-prose symbol for the
     reviewer.
  2. **Extract-a-pure-classifier-to-de-block-a-poll-loop:** extract ONLY the `list-in / enum-out`
     conclusion classifier (data already fetched by the caller), leave the sleep/backoff in the legacy
     method, un-collapse overloaded sentinels into a proper enum, place the classifier in the cycle-free
     leaf that owns the loop, and treat the timer-heap as the deadline owner (PENDING → park).

- **Uncertain assumptions the reviewer must focus on (be explicit and honest):**
  1. The entire `pipeline/` stage-protocol API (`StageOutcome`, `Disposition`, `ctx.retry/advance/
     fail_back/finish_fail/continue_`, `Route(next=…, fail_routes=…, budgets=…)`, `item.attempts`,
     `item.state`, `StageName`) is ASSUMED from epic prose, unverified against merged code (#1815 unmerged).
  2. `classify_ci_state`'s conclusion set `("success","skipped","neutral")` copied from
     `ci_run_coordinator.py`; the pr-checks mapping (`checks.py`) never emits "neutral" and hardcodes
     `required=False`, so the `required`-filter is inert on that path (fallback to "all checks"). Confirm
     this matches intent.
  3. `classify_pr_merge_state` mirrors `_wait_for_pr_terminal` but DROPS the `policy_only_failure`
     logging-only branch (`ci_driver.py:1575-1582`) — verified logging-only on disk; the reviewer should
     re-confirm dropping it is safe.
  4. **Riskiest:** the `merge` budget is described as "`--max-merge-attempts` poll windows," but the legacy
     bound is WALL-CLOCK seconds (`HEPH_PR_MERGE_MAX_WAIT` 1800s, exponential backoff). N poll windows ×
     backoff ≠ 1800s — scrutinize this semantic change.
  5. `ci_run_coordinator.py` is NOT on the coverage omit list (verified via grep), so its new pure
     function is auto-covered — but the plan did not verify that adding a NEW module under
     `pipeline/stages/` is unaffected by the frozen omit-allowlist test. Net-new covered code should be
     fine, but confirm.
  6. `test_pipeline_architecture.py` is ASSUMED to be created by #1813 and merely EXTENDED here — if
     #1813 named it differently or #1815 owns it, the "extend" step breaks.

- **Companion / counter skills:** `planning-unmerged-parent-contract-compile-smoke-gate` (Mojo-flavored
  frozen-contract-plus-compile-smoke variant), `planning-dependent-issue-unverified-upstream`
  (dependency-already-merged variant), and `automation-pola-poll-helper-none-sentinel` (the counter-lesson:
  that skill KEEPS a single `None` sentinel; THIS skill un-collapses it for a timer-heap model).

### Verified On

| Repository | Session | Notes |
|------------|---------|-------|
| ProjectHephaestus | GitHub issue #1816 plan (epic #1809, dependency #1815 unmerged) | Session 2026-07-04 — plan authored, NEVER implemented. No code, no tests, no CI. The `pipeline/`-absence checks and the `ci_run_coordinator.py` / `ci_driver.py` / `github_api/checks.py` line-anchored Reads were run during planning and are real; the `pipeline/` stage-protocol API remains assumed from epic prose. |
