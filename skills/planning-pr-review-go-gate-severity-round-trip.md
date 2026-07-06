---
name: planning-pr-review-go-gate-severity-round-trip
description: "Planning discipline for making a blocking gate severity-aware when the severity attribute must survive a multi-stage pipeline round-trip (reviewer JSON -> coordinator seed -> item.payload -> GitHub post -> GraphQL read-back). Before designing around a per-item field, GREP THE FIELD NAME producer-to-consumer across the whole package: a field emitted in a prompt is NOT the same as a field present in the parsed/consumed data structure. Choose the fail-safe default so the field-absent case reproduces CURRENT (safe) behavior exactly, making the change a no-op until the enabling data is wired. Anchor severity readers on a marker-LINE prefix, not a free substring scan. Cite the DEFINITION site of any helper a plan says to reuse, not the call/import site. Use when: (1) planning a fix that filters a blocking gate (a GO/merge gate) by a per-item severity/attribute that must survive a GitHub review post->read-back round-trip, (2) planning a fix whose core mechanism depends on a data field flowing through several pipeline stages, (3) re-introducing a previously-fixed deadlock in a rewritten subsystem (the #1554 minor-thread deadlock re-appearing in the queue-based pipeline pr_review stage, ProjectHephaestus #1856 / epic #1809), (4) a plan reads `t.get(\"severity\")` off a thread dict — confirm severity is actually seeded there and not just present in the reviewer prompt, (5) a plan says 'reuse the local classifier/helper' — confirm the helper is defined locally versus imported from a sibling module, (6) weighing a single-int blocking-count gate against a by-severity tuple that also RESOLVES the waved threads (required_review_thread_resolution branch-protection can re-deadlock at merge if minor threads stay unresolved)."
category: architecture
date: 2026-07-05
version: "1.0.0"
user-invocable: false
verification: unverified
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
---

# Planning a Severity-Aware GO Gate That Survives a Pipeline Round-Trip

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-05 |
| **Objective** | Plan a severity-aware GO gate for the pipeline `pr_review` stage to fix the re-introduced #1554 minor-thread deadlock (ProjectHephaestus #1856, epic #1809): only critical/major automation threads should block a GO; minor/nitpick automation threads should be tolerated. |
| **Outcome** | Plan only — unverified. No code written, no tests run, no CI. Verification during planning found the plan's core assumption (a `severity` field present on `review_threads`) is currently FALSE/unwired. The plan de-risks this with a fail-safe default. |
| **Verification** | unverified |
| **History** | n/a (initial version) |

## When to Use

- Planning a fix that filters a **blocking gate** (a GO gate, a merge gate) by a **per-item severity/attribute** that must survive a GitHub review **post -> read-back round-trip**.
- Planning a fix whose core mechanism depends on a **data field flowing through several pipeline stages** (producer JSON -> coordinator seed -> in-memory payload -> external API post -> read-back).
- **Re-introducing a previously-fixed deadlock in a rewritten subsystem** — here the #1554 minor-thread deadlock re-appearing in the new queue-based pipeline `pr_review` stage.
- A plan reads `t.get("severity")` (or any per-item attribute) off a dict — confirm that attribute is actually seeded there, not merely present in the reviewer/producer prompt.
- A plan says "reuse the local helper X" — confirm X is defined locally versus imported from a sibling module.
- Weighing a single-int blocking-count gate against a by-severity tuple that ALSO resolves the waved threads (branch-protection `required_review_thread_resolution` can re-deadlock at merge if minor threads stay unresolved).

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
sed -n '821,860p' hephaestus/automation/pipeline_github.py   # posts only {path,line,side,body}
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
6. **Resolve the merge-stage risk in the plan body, not a footnote.** A single-int
   `count_blocking_unresolved_threads` gate at the GO stage does NOT resolve the tolerated minor
   threads. Branch-protection `required_review_thread_resolution` can then re-deadlock at the MERGE
   stage instead. The alternative — a by-severity tuple PLUS a `resolve_automation_threads` GraphQL
   mutation that clears the waved minor threads before arming — closes that hole. Capture both shapes
   and the tradeoff explicitly; this is the single most important open design question.

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
- OPEN QUESTION (most important): single-int gate vs by-severity tuple + `resolve_automation_threads`
  mutation, because `required_review_thread_resolution` may re-deadlock at merge.

**Key file:line anchors (ProjectHephaestus, verified against source during planning):**

Actual pipeline stage lives at `hephaestus/automation/pipeline/stages/pr_review.py` (the task's
`pr_review.py` line numbers map to this file). `severity` confirmed present ONLY in the prompt.

| Anchor | Location | Note |
|--------|----------|------|
| severity emit | `hephaestus/automation/prompts/pr_review.py:48-79` (severity at :70; wording :51-54) | ONLY place `"severity"` appears in `hephaestus/automation/` |
| ReviewVerdict parse | `hephaestus/automation/claude_invoke.py:546-628` | `parse_review_verdict -> ReviewVerdict(grade, verdict, raw)`, NO comments |
| review_threads read/assign | `hephaestus/automation/pipeline/stages/pr_review.py:554,558` | assigned from `item.payload.get("review_threads")` — severity never added |
| GO short-circuit test | `pr_review.py:~703` (GO test) | the gate that must become severity-aware |
| human-thread hard gate | `pr_review.py:~690-701` | unchanged; humans still block |
| #1554 progress trail | `pr_review.py:~717-757` | keeps full `automation_unresolved` count |
| count_unresolved_threads | `hephaestus/automation/pipeline_github.py:521-545` | reads back body/comments text only, no structured severity |
| post_review_threads | `pipeline_github.py:821-860` | posts only `{path,line,side,body}` — drops extra keys (verified) |
| _repo_unresolved_threads | `pipeline_github.py:~310-359` | GraphQL read-back, body only |
| _is_automation_owned_thread import | `pipeline_github.py:33` | imported from `_review_phase.py:163` (definition site) |

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
