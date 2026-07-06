---
name: planning-pr-review-go-gate-severity-round-trip
description: "Planning discipline for making a blocking gate severity-aware when the severity attribute must survive a multi-stage pipeline round-trip (reviewer JSON -> coordinator seed -> item.payload -> GitHub post -> GraphQL read-back). Before designing around a per-item field, GREP THE FIELD NAME producer-to-consumer across the whole package: a field emitted in a prompt is NOT the same as a field present in the parsed/consumed data structure. Choose the fail-safe default so the field-absent case reproduces CURRENT (safe) behavior exactly, making the change a no-op until the enabling data is wired. Anchor severity readers on a marker-LINE prefix, not a free substring scan. Cite the DEFINITION site of any helper a plan says to reuse, not the call/import site. Use when: (1) planning a fix that filters a blocking gate (a GO/merge gate) by a per-item severity/attribute that must survive a GitHub review post->read-back round-trip, (2) planning a fix whose core mechanism depends on a data field flowing through several pipeline stages, (3) re-introducing a previously-fixed deadlock in a rewritten subsystem (the #1554 minor-thread deadlock re-appearing in the queue-based pipeline pr_review stage, ProjectHephaestus #1856 / epic #1809), (4) a plan reads `t.get(\"severity\")` off a thread dict — confirm severity is actually seeded there and not just present in the reviewer prompt, (5) a plan says 'reuse the local classifier/helper' — confirm the helper is defined locally versus imported from a sibling module, (6) weighing a single-int blocking-count gate against a by-severity tuple that also RESOLVES the waved threads (required_review_thread_resolution branch-protection can re-deadlock at merge if minor threads stay unresolved — CONFIRMED real via merge_wait.py:427-434 BLOCKED_ADDRESS_WAIT; resolve waved automation threads UPSTREAM via gh_pr_resolve_thread before arming), (7) a fix DEFERS a state to a later pipeline stage — read that downstream stage's handler to confirm the deferral drains or re-deadlocks; prefer resolving upstream, (8) a planning turn that ALSO ran /learn — the emitted FINAL message must BE the full implementation plan, not a /learn recap, or the plan reviewer grades an empty plan and NOGOs."
category: architecture
date: 2026-07-05
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-pr-review-go-gate-severity-round-trip.history
tags:
  - planning-methodology
  - severity-aware-gate
  - go-gate
  - minor-thread-deadlock
  - "1554"
  - "1856"
  - automation-pipeline
  - pr-review-stage
  - field-round-trip
  - grep-producer-to-consumer
  - fail-safe-default
  - marker-line-anchoring
  - cite-definition-site
  - required-review-thread-resolution
  - defer-to-downstream-stage
  - resolve-waved-threads-upstream
  - by-severity-tuple
  - plan-artifact-not-learn-recap
  - "1809"
---

# Planning a Severity-Aware GO Gate That Survives a Pipeline Round-Trip

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-05 |
| **Objective** | Plan a severity-aware GO gate for the pipeline `pr_review` stage to fix the re-introduced #1554 minor-thread deadlock (ProjectHephaestus #1856, epic #1809): only critical/major automation threads should block a GO; minor/nitpick automation threads should be tolerated. |
| **Outcome** | Plan only — unverified. No code written, no tests run, no CI. Verification during planning found the plan's core assumption (a `severity` field present on `review_threads`) is currently FALSE/unwired. The plan de-risks this with a fail-safe default. v1.1.0: the v1.0.0 open design question (merge-stage re-deadlock) is RESOLVED by reading `merge_wait.py:427-434` and resolving waved automation threads upstream via `gh_pr_resolve_thread`. |
| **Verification** | unverified |
| **History** | [changelog](./planning-pr-review-go-gate-severity-round-trip.history) |

## When to Use

- Planning a fix that filters a **blocking gate** (a GO gate, a merge gate) by a **per-item severity/attribute** that must survive a GitHub review **post -> read-back round-trip**.
- Planning a fix whose core mechanism depends on a **data field flowing through several pipeline stages** (producer JSON -> coordinator seed -> in-memory payload -> external API post -> read-back).
- **Re-introducing a previously-fixed deadlock in a rewritten subsystem** — here the #1554 minor-thread deadlock re-appearing in the new queue-based pipeline `pr_review` stage.
- A plan reads `t.get("severity")` (or any per-item attribute) off a dict — confirm that attribute is actually seeded there, not merely present in the reviewer/producer prompt.
- A plan says "reuse the local helper X" — confirm X is defined locally versus imported from a sibling module.
- Weighing a single-int blocking-count gate against a by-severity tuple that ALSO resolves the waved threads (branch-protection `required_review_thread_resolution` can re-deadlock at merge if minor threads stay unresolved — CONFIRMED real via `merge_wait.py:427-434`).
- A fix **DEFERS a state to a later pipeline stage** ("it'll be handled at merge") — read the downstream stage's handler to confirm the deferral drains the state or re-deadlocks; prefer resolving UPSTREAM before arming.
- A planning turn that **also ran `/learn`** or produced a meta-narrative — the turn's FINAL emitted message must BE the full implementation plan, because the pipeline posts whatever the planning turn outputs as the plan body; a `/learn` recap is graded as an empty plan and NOGO'd.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the
> literal section string `## Verified Workflow`, so the canonical steps are ALSO emitted under
> that heading below to keep validation green. This skill is a PLANNING methodology captured at
> `unverified` level. Read the steps as **proposed**, per the warning.

### Quick Reference

```bash
# 1. GREP THE FIELD PRODUCER-TO-CONSUMER before designing around it.
#    A field in a prompt is NOT a field in the parsed data structure.
grep -rn '"severity"' hephaestus/automation/ --include=*.py
#   -> ONLY the prompt line (prompts/pr_review.py:70). severity is UNWIRED into review_threads.

# 2. Trace where the consumed dict is actually assigned (not just read).
grep -rn 'review_threads' hephaestus/automation/pipeline/stages/pr_review.py
#   -> assigned only at :558 from item.payload.get("review_threads") read at :554.

# 3. Cite the DEFINITION site of any helper the plan says to "reuse", not the call/import site.
grep -rn 'def _is_automation_owned_thread' hephaestus/automation/ --include=*.py
#   -> defined in _review_phase.py:163; IMPORTED into pipeline_github.py:33 (NOT local).

# 4. Confirm the external-API round-trip DROPS extra keys (so the body is the only channel).
sed -n '831,839p' hephaestus/automation/pipeline_github.py   # posts only {path,line,side,body}

# 5. Before DEFERRING a waved state to merge, READ the merge stage's handler.
grep -rn 'required_review_thread_resolution\|BLOCKED_ADDRESS_WAIT' hephaestus/automation/pipeline/stages/merge_wait.py
#   -> merge_wait.py:427-434 BLOCKED_ADDRESS_WAIT: an armed PR BLOCKED on thread-resolution
#      RE-DISPATCHES an address job -> unresolved waved minor thread re-deadlocks. Resolve upstream.

# 6. Resolve waved automation threads UPSTREAM (before arming) with the EXISTING helper.
grep -rn 'def gh_pr_resolve_thread' hephaestus/automation/github_api/threads.py
#   -> threads.py:113 gh_pr_resolve_thread(thread_id, reply_body=None, dry_run=False)
#      wraps resolveReviewThread. Automation resolves threads it OWNS; never human threads.
```

### Detailed Steps (Proposed)

1. **Grep the field end-to-end, producer to consumer.** Before designing a gate that reads a
   per-item attribute, grep the field NAME across the whole package. Trace it from the producer
   (reviewer JSON / prompt) to the consumed dict (the thing the gate iterates). If the field
   appears only at the producer/prompt and never in an ASSIGNMENT to the consumed dict, it is
   **unwired** — the gate would read a field that is always absent. A field emitted in a prompt
   is not the same as a field present in the parsed data structure.
2. **Choose the fail-safe default = current behavior.** When the fix depends on an upstream field
   that may not be wired yet, pick the default for the "field absent/unknown" case so it reproduces
   the CURRENT (safe) behavior EXACTLY — never the new permissive behavior. Here: an absent/unknown
   severity defaults to `major` (BLOCKING). Consequence: while severity is unseeded, every marker is
   `major`, the blocking count equals the full automation-unresolved count, and behavior is identical
   to today (`automation_unresolved == 0`) — NO REGRESSION. The permissive path activates only once
   the coordinator seeds real severities. The change is a safe no-op until the enabling data arrives.
3. **Carry the attribute through the only durable channel and anchor on a marker LINE.** If the
   external API round-trip drops extra keys (GitHub `post_review_threads` posts only
   `{path,line,side,body}`), the comment BODY is the only channel that survives to the live thread
   and back. Encode it as a marker line, e.g. `<!-- hephaestus-severity: minor -->`, and have the
   reader anchor on the marker-line PREFIX (`startswith(SEVERITY_MARKER_PREFIX) and endswith("-->")`),
   NOT a free `"minor" in body` substring scan — a reviewer body legitimately contains the word
   "minor". (This is the `log-line-anchoring` rule applied to a review-comment body.)
4. **Cite definition sites, not call sites.** When the plan says "reuse helper X", cite where X is
   `def`-ined (grep `def <name>`). `_is_automation_owned_thread` is defined in `_review_phase.py:163`
   and imported into `pipeline_github.py:33`; a plan that calls it "the local classifier" is imprecise.
5. **Tighten the gate; don't rewrite it.** Only the GO short-circuit uses the new blocking count; the
   #1554 progress-aware extension trail keeps keying off the full `automation_unresolved` count so
   progress accounting is untouched. Human threads keep their existing hard block — severity filtering
   applies to AUTOMATION threads only (automation owns them and may resolve them; it cannot resolve
   human threads, which is why those still block).
6. **Read the downstream stage before deferring a state to it (v1.1.0 — RESOLVED).** A single-int
   `count_blocking_unresolved_threads` gate at the GO stage does NOT resolve the tolerated minor
   threads. Do not leave "may re-deadlock at merge" as an open question — GREP the downstream stage
   for the branch-protection condition. Here `hephaestus/automation/pipeline/stages/merge_wait.py:427-434`
   has a `BLOCKED_ADDRESS_WAIT` handler: an armed PR sitting BLOCKED behind
   `required_review_thread_resolution` re-dispatches an ADDRESS job — so an unresolved waved minor
   thread re-invokes the address leg (churn / potential re-deadlock). The risk is REAL. Chosen fix:
   on an otherwise-clean GO, RESOLVE the waved automation minor/nitpick threads UPSTREAM (before
   arming) using the EXISTING helper `gh_pr_resolve_thread(thread_id, reply_body=None, dry_run=False)`
   at `hephaestus/automation/github_api/threads.py:113` (wraps the `resolveReviewThread` GraphQL
   mutation). Automation may resolve threads it OWNS (`_is_automation_owned_thread`); it CANNOT
   resolve human threads — which is exactly why human threads still hard-block. Prefer resolving
   upstream over relying on the downstream stage to clean up.
7. **Return a by-severity tuple, not a single int.** The gate helper is
   `count_unresolved_threads_by_severity(pr) -> (blocking_auto, minor_auto, human)`, mirroring
   `count_unresolved_threads` (`pipeline_github.py:521-545`). Three values because three downstream
   decisions each need an input: `minor_auto` decides whether to call `resolve_automation_threads`
   at all (skip the mutation when zero minors — no wasted GraphQL call); `human` feeds the existing
   human hard gate; and the full `automation_unresolved = blocking_auto + minor_auto` feeds the
   unchanged #1554 progress-aware extension trail (`pr_review.py:717-757`). A single-int loses the
   minor count and cannot drive the resolve-or-not decision. Keep DRY: `count_unresolved_threads`,
   `count_unresolved_threads_by_severity`, and `resolve_automation_threads` all share one extracted
   private `_unresolved_threads(pr)` fetch helper (repo-scoped-vs-legacy branch + fail-open-to-`[]`),
   so all three have identical fetch semantics. The `<!-- hephaestus-severity: X -->` marker is
   idempotent on re-post — skip if the body already starts with the prefix.
8. **The planning turn's FINAL message must BE the plan (meta-lesson).** The pipeline posts whatever
   the planning turn OUTPUTS as the plan body — it does not extract "the plan" from a longer message.
   If a turn does BOTH real planning AND a `/learn`, the emitted final artifact must be the full
   implementation plan (every required section, concrete `file:line`, fenced code, per-criterion
   verification), NOT the `/learn` completion notice, reviewer bullets, a meta-narrative, or
   "see above". A recap-as-plan is graded as an empty plan and NOGO'd. (A prior #1856 iteration got
   an F/NOGO for exactly this — the reviewer received the previous turn's `/learn` recap, not the plan.)

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

See "Proposed Workflow" above — the steps are duplicated under this validator-required heading. This
skill is `unverified`: a planning methodology, not an executed workflow.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Design the gate to read `t.get("severity")` directly off each `review_threads` dict, assuming the reviewer's per-comment `severity` tag flows into `item.payload["review_threads"]`. | `grep -rn '"severity"' hephaestus/automation/ --include=*.py` returns ONLY the prompt line (`prompts/pr_review.py:70`). `severity` is parsed NOWHERE into `review_threads`; that payload is assigned only at `pipeline/stages/pr_review.py:558` from `.get("review_threads")` (read :554), and the reviewer `AgentJob` parses via `parse_review_verdict` -> `ReviewVerdict(grade, verdict, raw)` with NO comments (`claude_invoke.py:546-628`). The coordinator "#1817 slice" seeds the payload and does not carry severity. The field is UNWIRED — always absent. | Grep the field name producer-to-consumer across the whole package before designing around it. A field emitted in a prompt is not a field present in the parsed data structure; if it never appears in an assignment to the consumed dict, it is unwired. |
| 2 | Pick the minimal shape: a single `count_blocking_unresolved_threads -> int` mirroring `count_unresolved_threads`, tolerating minor automation threads at the GO gate. | Tolerating (not resolving) minor automation threads may still fail branch-protection's `required_review_thread_resolution` at MERGE time, re-deadlocking one stage later instead of at the GO gate. The alternative shape — a 3-tuple `count_unresolved_threads_by_severity -> (blocking, minor, human)` PLUS a `resolve_automation_threads` GraphQL mutation that clears the waved threads before arming — closes the hole (automation owns those threads, so it can resolve them; it cannot resolve human threads, which is why those still block). | When a permissive gate change "waves through" items, verify a downstream/merge-stage gate does not re-block on the same items. Capture both the minimal and the resolve-the-waved-threads shapes and flag the merge-stage risk explicitly. |
| 3 | Describe `_is_automation_owned_thread` as "the local classifier" in `pipeline_github.py` and plan to "reuse the local helper". | It is NOT local: it is defined at `_review_phase.py:163` and imported at `pipeline_github.py:33`. A plan that implies it is local is imprecise and can send an implementer editing the wrong file. | Cite the DEFINITION site (grep `def <name>`) not the call/import site when a plan says "reuse helper X". |
| 4 | Read severity back from a thread with a free `"minor" in body` substring scan. | A reviewer comment body legitimately contains the word "minor" in prose, causing false severity matches. | Anchor on a marker LINE: `<!-- hephaestus-severity: minor -->`, matched by `startswith(SEVERITY_MARKER_PREFIX) and endswith("-->")` — the `log-line-anchoring` rule applied to a comment body. |
| 5 | Settle on a single-int `count_blocking_unresolved_threads -> int` as the gate helper's return shape. | Three downstream decisions each need a distinct input: whether to call `resolve_automation_threads` needs the `minor_auto` COUNT (skip the GraphQL mutation entirely when zero minors), the existing human hard-gate needs the `human` count, and the unchanged #1554 progress-aware trail (`pr_review.py:717-757`) needs the full `automation_unresolved = blocking + minor`. A single int can only serve one of the three — it loses the minor count needed to decide resolve-or-not and loses the progress-trail total. | Return the full 3-way split `(blocking_auto, minor_auto, human)` mirroring `count_unresolved_threads` so every downstream decision (resolve? / human-block? / progress?) has its own input; share one `_unresolved_threads(pr)` fetch helper for DRY identical fetch semantics. |
| 6 | Emit the plan by producing a message that combined a `/learn` completion notice + reviewer bullets from the previous turn, assuming the plan reviewer would find "the plan" within it. | The pipeline posts whatever the planning turn OUTPUTS as the plan body; it does not extract a sub-section. The reviewer received the `/learn` recap, not an implementation plan, and graded it an empty plan -> F/NOGO (a prior ProjectHephaestus #1856 iteration). | When a turn does BOTH planning AND `/learn` (or any meta-work), the FINAL emitted message must BE the full implementation plan — every required section, concrete `file:line`, fenced code, per-criterion verification. Never emit a `/learn` summary, meta-narrative, or "see above" as the plan artifact. |

## Results & Parameters

**Marker string (proposed):**

```text
<!-- hephaestus-severity: <severity> -->
```

- Reader anchors on the marker-LINE prefix (`startswith(SEVERITY_MARKER_PREFIX) and endswith("-->")`),
  not a substring scan of the body.

**Blocking-severity set (proposed):** `{critical, major}` block a GO. `minor`, `nitpick` are
non-blocking. Absent/unknown severity defaults to `major` (BLOCKING) — the fail-safe default that
reproduces current behavior until severity is seeded. This matches the reviewer prompt's own wording
(`prompts/pr_review.py:51-54`).

**Design decisions the reviewer should sanity-check:**

- Tighten the GO condition (`nogo-tightening`); do not rewrite it.
- Fail-safe: unclassifiable/absent severity => BLOCKING (`fail-safe`).
- Marker-line anchoring, not substring (`log-line-anchoring`).
- Test at the `_eval` orchestrator altitude, not just the helper (coverage-altitude).
- Human threads keep their existing hard block; severity filtering applies to AUTOMATION threads only.
- The #1554 progress-aware extension trail keeps keying off the full `automation_unresolved` count.
- RESOLVED (was v1.0.0's open question): use the by-severity tuple
  `count_unresolved_threads_by_severity(pr) -> (blocking_auto, minor_auto, human)` AND resolve waved
  automation minor threads UPSTREAM (before arming) via `gh_pr_resolve_thread` — because
  `merge_wait.py:427-434` `BLOCKED_ADDRESS_WAIT` re-dispatches an address job on a PR blocked by
  `required_review_thread_resolution`, confirming the merge-stage re-deadlock is real. Skip the
  resolve mutation when `minor_auto == 0`. Marker re-post is idempotent (skip if body already starts
  with the prefix).
- DRY: `count_unresolved_threads`, `count_unresolved_threads_by_severity`, and
  `resolve_automation_threads` share one `_unresolved_threads(pr)` fetch helper.
- Fail-safe reconfirmed: absent/unknown severity => `major` (blocking) in `_with_severity_marker`, so
  if the coordinator (#1817) never seeds `severity`, the new blocking count == today's
  `automation_unresolved` => no regression.
- PLAN-ARTIFACT rule: the planning turn's FINAL emitted message must BE the plan, never a `/learn`
  recap — the pipeline posts the turn's output verbatim as the plan body.

**Key file:line anchors (ProjectHephaestus, verified against source during planning):**

Actual pipeline stage lives at `hephaestus/automation/pipeline/stages/pr_review.py` (the task's
`pr_review.py` line numbers map to this file). `severity` confirmed present ONLY in the prompt.

| Anchor | Location | Note |
|--------|----------|------|
| severity emit | `hephaestus/automation/prompts/pr_review.py:70` (wording :51-54) | ONLY place `"severity"` appears in `hephaestus/automation/` |
| ReviewVerdict parse | `hephaestus/automation/claude_invoke.py:546-566` | `ReviewVerdict(grade, verdict, raw)`, NO comments field |
| GO gate | `pr_review.py:685-708` | the GO short-circuit that becomes severity-aware |
| human-thread hard gate | `pr_review.py:690-701` | unchanged; humans still block |
| #1554 progress trail | `pr_review.py:717-757` | keeps full `automation_unresolved` count |
| write_skip_label | `pr_review.py:756` | end of the progress trail |
| count_unresolved_threads | `hephaestus/automation/pipeline_github.py:521-545` | body/comments text only; fetch branch :529-545 |
| count fetch branch | `pipeline_github.py:529-545` | repo-scoped-vs-legacy fetch, fail-open to `[]` (shared `_unresolved_threads`) |
| post_review_threads | `pipeline_github.py:831-839` | posts only `{path,line,side,body}` — drops extra keys (verified) |
| _is_automation_owned_thread import | `pipeline_github.py:33` | imported from `_review_phase.py:163` (definition site) |
| _is_automation_owned_thread def | `_review_phase.py:163` | the DEFINITION site (cite this, not the import) |
| gh_pr_resolve_thread | `hephaestus/automation/github_api/threads.py:113` | EXISTING helper wrapping `resolveReviewThread`; resolves waved automation threads upstream |
| BLOCKED_ADDRESS_WAIT | `hephaestus/automation/pipeline/stages/merge_wait.py:427-434` | confirms the merge-stage re-deadlock: re-dispatches an address job on a PR blocked by `required_review_thread_resolution` |

**Applied knowledge-base learnings:**

- Skill `architecture-executable-convention-guard-pattern`: `nogo-tightening`, `fail-safe`,
  `log-line-anchoring`, coverage-altitude.
- Memory `project_review_loop_minor_thread_deadlock_1554`: the SAME deadlock class, re-introduced
  in the pipeline. The legacy `_review_phase.py` fix used a no-commit retry directive, NOT severity
  awareness — so this pipeline fix is a genuinely new mechanism, not a port of the legacy fix.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning fix for #1856 (epic #1809) — severity-aware GO gate for the pipeline `pr_review` stage | Plan only; unverified. Source anchors verified via grep/read during planning. |
| ProjectHephaestus | #1856 re-plan (v1.1.0) after an F/NOGO — resolved the merge-stage re-deadlock question, switched to a by-severity tuple + upstream thread resolution, and captured the plan-artifact meta-lesson | Plan only; unverified. `merge_wait.py`, `threads.py`, and `pr_review.py` anchors re-verified this session. |
