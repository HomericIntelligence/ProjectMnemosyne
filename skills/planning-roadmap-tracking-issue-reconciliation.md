---
name: planning-roadmap-tracking-issue-reconciliation
description: "When a GitHub issue carries `epic`+`roadmap` labels it is a TRACKING issue, not a code task — the correct 'implementation' is to reconcile its checklist against the ACTUAL shipped state of the codebase and edit the issue body, NOT to write source code. Audit each roadmap item against three independent sources of truth before flipping a checkbox: (1) the implementing source file AND its wiring (grep for the endpoint/decorator/symbol, not just `test -f`), (2) the linked tracking issue's state via `gh issue view <n> --json state`, and (3) dependency pinning in the manifest. Distinguish FULLY shipped from PARTIAL: a wire field that is only EMITTED (e.g. `schema_version` present) without consumer-side NEGOTIATION (`grep -rn 'schema_version >'`) stays unchecked with an inline annotation. Confirm genuinely unstarted phases with a NEGATIVE grep. Use when: (1) an issue is labelled epic/roadmap and its body is a checkbox checklist, (2) you are tempted to write code for a tracking issue, (3) a checklist item links to another issue (`— #NNN`), (4) a checklist item names a registry/version/negotiation feature, (5) producing a verbatim replacement issue body to apply via `gh issue edit`."
category: documentation
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [roadmap, tracking-issue, epic, checkbox, reconcile, audit-vs-issue, issue-body-edit, gh-cli, grep-wiring, schema-version, emit-vs-negotiate, partial-shipped, negative-grep, planning, unverified]
---

# Planning: Reconcile a Roadmap Tracking Issue Against Shipped Code

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Correctly "implement" a GitHub issue that is actually an `epic`+`roadmap` TRACKING checklist — by reconciling each checkbox against the real shipped state of the codebase and editing the issue body, NOT by writing source code |
| **Outcome** | Plan produced (ProjectHermes): classified the issue as a tracker, audited each roadmap item against source-file wiring + linked-issue state + manifest pins, distinguished FULLY-shipped from PARTIAL (emit-only) items, and emitted a verbatim replacement issue body. The body edit was NEVER applied and no CI ran |
| **Verification** | unverified — PLANNING learning only. The plan was produced but NOT executed end-to-end: the `gh issue edit` body edit was never applied and no CI ran. The audit/evidence commands below were read at plan time and may drift before apply |
| **Source** | ProjectHermes — `epic`+`roadmap` tracking issue planning session |

A `roadmap` issue is a **snapshot** of intent that drifts as PRs merge underneath it. Its body is the
deliverable, not source code: "Files to Create/Modify: none — this is a tracking issue; the change is
the issue body itself." The hard part is deciding *truthfully* which boxes to tick, which is why each
item must be checked against **three independent sources of truth** and a FULLY-vs-PARTIAL distinction
applied.

## When to Use

- An issue carries `epic` and/or `roadmap` labels and its body is a markdown checkbox checklist.
- You are about to write source code for a tracking issue — stop; the deliverable is a body edit.
- A checklist item links to another issue (`— #NNN`) whose completion gates the checkbox.
- A checklist item names a "schema registry / version negotiation / version" style feature where a
  field may be *emitted* without the *negotiation* half existing.
- You need to emit a verbatim replacement issue body to apply via `gh issue edit <n> --body-file -`.
- Re-planning a roadmap tracker after work has merged and the body has gone stale.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. Treat it as a
> hypothesis until CI confirms. Verification level: `unverified` — planning learning only; the plan it
> came from was never executed, the `gh issue edit` body edit was never applied, and no CI ran. The
> audit/evidence commands below were established by READING the repo and querying `gh` at plan time and
> may drift before apply.

### Quick Reference

```bash
# 0. CLASSIFY: is this a tracker (epic/roadmap) or a code task?
gh issue view <n> --json labels --jq '.labels[].name' | grep -qE 'epic|roadmap' \
  && echo "TRACKER → deliverable is a body edit, NOT source code"

# 1. WIRING, not existence — file present AND wired:
test -f src/hermes/rate_limit.py && grep -q "@limiter.limit" src/hermes/server.py   # rate-limit wired
grep -q 'app.get("/metrics")' src/hermes/server.py && test -f src/hermes/metrics.py # metrics wired

# 2. LINKED ISSUE state — '— #NNN' item is checkable only if that issue is CLOSED:
test "$(gh issue view 351 --json state -q .state)" = "CLOSED"                        # linked closed

# 3. EMIT vs NEGOTIATE — a field can be emitted without consumer-side negotiation:
grep -rqn "schema_version >" src/ tests/ || echo "no negotiation → PARTIAL → stays unchecked"

# 4. UNSTARTED phase — confirm with a NEGATIVE grep:
! grep -rqiE "replay|schema.registry|version.negotiat|multi.tenant|plugin" src/      # absent → unchecked

# 5. APPLY (operator/pipeline, NOT the planner): emit the verbatim body, then:
gh issue edit <n> --body-file -   # piped the replacement body
```

### Detailed Steps

1. **Classify the issue before doing anything.** Read its labels. `epic`/`roadmap` ⇒ this is a TRACKING
   issue and the deliverable is an edited issue body — there is no source change. Writing code here
   duplicates already-merged work and fails review. State explicitly: "Files to Create/Modify: none."

2. **For each checklist item, find the implementing symbol AND grep its wiring.** File existence is
   necessary but NOT sufficient — a module can exist unwired. Grep for the actual endpoint/decorator/
   symbol that proves it is hooked up (`grep -q 'app.get("/metrics")'`, `grep -q "@limiter.limit"`).
   Only an item with both the file AND its wiring is FULLY shipped and checkable.

3. **Resolve linked-issue items against live `gh` state.** An item annotated `— #NNN` is gated on that
   issue: `gh issue view NNN --json state -q .state`. CLOSED ⇒ checkable; OPEN ⇒ stays unchecked. Do
   not trust the roadmap body's own status column — it drifts.

4. **Split registry/negotiation/version items into EMIT vs NEGOTIATE halves.** The presence of a wire
   field (e.g. `schema_version`) proves only the EMIT half. The NEGOTIATION half is consumer-side logic
   that compares it (`grep -rn "schema_version >"`). If the negotiation grep is empty, the item is
   **PARTIAL** — leave it unchecked and add an inline annotation (e.g. "(emit-only; no consumer
   negotiation yet)"). Do NOT tick a box on emit-only evidence.

5. **Confirm genuinely unstarted phases with a NEGATIVE grep.** For items you believe are not begun, run
   `! grep -rqiE "replay|plugin|multi.tenant" src/` and cite the empty result. A negative grep is the
   evidence that justifies leaving a box unchecked; "I didn't see it" is not.

6. **Emit the verbatim replacement issue body and hand off the apply.** Output the full new body so a
   reviewer can diff it. Application (`gh issue edit <n> --body-file -`) is run by the operator or
   pipeline, NOT by the planner. Add a re-confirm step to the plan: linked-issue states and the issue
   body may drift between plan time and apply time, so re-run steps 2–4 immediately before the edit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat the roadmap issue as a code task | Started planning source-code edits for an `epic`+`roadmap` issue | Would duplicate already-merged work and fail review; a tracking issue has no source deliverable | Classify by labels FIRST — `epic`/`roadmap` ⇒ the deliverable is a body edit, not src changes |
| Check a box because the file exists | Ticked an item because `metrics.py` was present on disk | A module can exist while being unwired (no route/decorator), so the feature is not actually live | File existence is necessary but not sufficient — also `grep` for the endpoint/decorator/symbol wiring (`grep -q 'app.get("/metrics")'`) before checking the box |
| Check "schema registry / version negotiation" because the `schema_version` field exists | Treated the presence of the `schema_version` wire field as completing the version-negotiation item | Conflates the EMIT half (field present) with the NEGOTIATE half (consumer-side comparison) — emit-only is not the shipped feature | Grep for consumer-side `schema_version >` comparison; absent ⇒ keep the item PARTIAL/unchecked with an inline annotation |
| Trust the roadmap body's own status column / linked-issue marks | Read the checklist's stated status to decide which boxes were done | The body is a snapshot and drifts as linked issues close and PRs merge | Resolve each `— #NNN` item against live `gh issue view NNN --json state`; CLOSED ⇒ checkable |
| Leave an "unstarted" box unchecked on intuition | Assumed a phase was not begun without evidence | "I didn't see it" is not proof; the feature could be present under a different name | Confirm absence with an explicit NEGATIVE grep (`! grep -rqiE 'replay\|plugin\|multi.tenant' src/`) and cite the empty result |

## Results & Parameters

### Copy-paste audit command set (ProjectHermes roadmap tracker)

```bash
# Rate-limit item: file present AND decorator wired in server.py
test -f src/hermes/rate_limit.py && grep -q "@limiter.limit" src/hermes/server.py   # rate-limit wired

# Metrics item: route registered AND module present
grep -q 'app.get("/metrics")' src/hermes/server.py && test -f src/hermes/metrics.py  # metrics wired

# Linked-issue item: checkable only if the referenced issue is CLOSED
test "$(gh issue view 351 --json state -q .state)" = "CLOSED"                         # linked issue closed

# Version negotiation: distinguish EMIT (field present) from NEGOTIATE (consumer compares it)
grep -rqn "schema_version >" src/ tests/ || echo "no negotiation → stays unchecked"  # emit vs negotiate

# Unstarted phase: confirm with a negative grep (empty = genuinely not begun)
! grep -rqiE "replay|schema.registry|version.negotiat|multi.tenant|plugin" src/      # phase unstarted

# Apply (operator/pipeline, NOT the planner): emit the verbatim body, then:
gh issue edit <n> --body-file -
```

### Decision table — when to tick a box

| Item kind | Evidence required | FULLY (tick) | PARTIAL / unstarted (leave unchecked) |
|-----------|-------------------|--------------|----------------------------------------|
| Source feature | implementing file **+** its wiring grep | both present | file present but no wiring grep |
| Linked issue (`— #NNN`) | `gh issue view NNN --json state` | `CLOSED` | `OPEN` |
| Registry/version/negotiation | emit field **+** consumer `schema_version >` grep | both present | emit field only ⇒ annotate PARTIAL |
| New phase | negative grep | n/a | empty grep result ⇒ unstarted |

### Risks / uncertain assumptions the reviewer should know

- **Plan was NOT executed:** the issue-body edit was never applied and no CI ran ⇒ `unverified`.
- **Live `gh` reads may drift:** the plan relied on `gh issue view 351` returning `CLOSED` and on
  another issue's body matching the pasted TASK — both read at plan time. The plan adds a re-confirm
  step (re-run steps 2–4 immediately before `gh issue edit`) to mitigate, but drift remains possible.
- **Grep-based "wiring" is necessary but not sufficient:** it proves the symbol exists, not that it
  behaves correctly. (E.g. per-IP `get_remote_address` was equated to "per-source"; a reviewer may want
  "per-source" defined more strictly than per-IP.)
- **"No src/ change" assumes every roadmap item shipped under its own prior PR** — this was inferred
  from the audit, not independently verified via `git log`/`git blame` history.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | `epic`+`roadmap` tracking-issue planning, 2026-06-19 | Audited each roadmap checkbox against source-file wiring grep + linked-issue `gh` state + manifest pins; distinguished FULLY-shipped from PARTIAL (emit-only `schema_version` with no consumer `schema_version >` negotiation); emitted a verbatim replacement issue body. Unverified: the `gh issue edit` was never applied and no CI ran; the audit commands were read/queried at plan time and may drift before apply |
