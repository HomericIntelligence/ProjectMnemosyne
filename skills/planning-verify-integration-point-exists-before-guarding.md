---
name: planning-verify-integration-point-exists-before-guarding
description: "Guard-an-unguarded-convention planning meta-pattern: when an audit issue or prior-learnings/KB advice says 'the convention is correct but un-guarded — add a downstream check to the EXISTING X step/job/hook,' VERIFY that the integration point actually exists (grep the workflows/hooks/config) BEFORE building the plan on it; audit findings and KB advice routinely assume infrastructure that is only documented, not implemented. If the assumed step is absent, ship the guard as a tested library function + CLI --verify entrypoint (non-zero exit = invariant violated) that ANY consumer can call, rather than a bare shell assertion in a possibly-nonexistent CI job. Use when: (1) planning an issue that asks you to enforce/guard an existing convention, (2) an audit or KB note tells you to 'add the check to the existing CI/artifact step,' (3) deciding enforcement-vs-discovery exit-code semantics for a verifier, (4) a read-only verifier might reuse a resolver with a filesystem side effect."
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, guard, convention, invariant, ci-gate, verify, audit-finding, integration-point, library-first, exit-code-semantics]
---

# Planning: Verify the Integration Point Exists Before Guarding an Unguarded Convention

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Capture the planning meta-pattern surfaced while planning ProjectHephaestus issue #1207 ("Coredump handler reliability relies on an unverified convention"): how to plan a guard for an un-guarded convention without anchoring the plan on a CI step that does not actually exist |
| **Outcome** | Plan produced — pivoted from "add a line to the existing CI artifact step" (which a grep proved does not exist) to a tested library function + CLI `--verify` entrypoint any consumer can call |
| **Verification** | unverified — this is a PLANNING learning; the plan was NOT executed, no tests ran, no CI confirmed it |
| **Category** | architecture / planning |
| **Related Issues** | ProjectHephaestus #1207 |

## When to Use This Skill

Use this skill when planning (not yet implementing) and any of the following hold:

- An audit issue says a convention is "correct but un-guarded" and recommends adding a downstream check.
- Prior-learnings, a KB skill, or the issue body tells you to "add the assertion/check to the **existing** X step / Y job / Z hook."
- You are deciding the exit-code semantics of a verifier (block the build vs. report-and-continue).
- You are about to reuse an existing resolver/helper inside a new read-only verify path.

**Triggers:**

- Issue title/body contains "convention," "un-guarded," "unverified convention," "relies on a convention," or "add a CI check."
- Advice presumes an integration point: "the existing CI artifact step," "the existing pre-commit hook," "the workflow that already does X."
- You catch yourself writing a plan step like "append one line to the `upload-artifact` job" without having opened that job.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — planning learning only; the plan it came from was never executed.

### Step 1 — Distrust the assumed integration point; grep for it FIRST

Before any plan step depends on "the existing X step," prove X exists. Audit findings and KB advice frequently describe infrastructure that lives only in docstrings/docs, not in committed YAML/hooks.

```bash
# Example from #1207: the convention (crash bundle / coredump / handler.log
# artifact upload) was assumed to live in a CI job. It did not.
grep -rn "crash-bundle\|coredump\|handler.log" .github/workflows/
# → no matches: the "existing CI artifact step" does NOT exist.
# The convention lived only in docstrings.
```

If the grep returns nothing, the recommended "add a line to the existing job" approach would guard **nothing**. Pivot now, before writing the rest of the plan.

### Step 2 — Ship the guard as a tested library function + CLI verify entrypoint

For "make an un-guarded convention enforced," prefer a reusable, unit-testable library function exposed via a CLI `--verify` mode over a bare shell assertion embedded in a (possibly nonexistent) CI job:

- A library function is unit-testable, portable across consumers, and matches a library-first boundary.
- A CLI `--verify` entrypoint can be called by CI YAML, pre-commit, or downstream tooling — wire CI to call it rather than re-implementing the check inline.
- Non-zero exit (e.g., `2`) when the invariant is violated makes it a real gate any caller can block on.

### Step 3 — State enforcement-vs-discovery semantics explicitly, and why

This is a deliberate design decision, not an accident of implementation:

- A **lost failure-signal** (the artifact whose absence means a crash went unreported) is a real defect → **BLOCKING** (non-zero exit).
- A **hygiene/discovery** scan → exit `0` and report findings.

Write down which one you chose and why. (Reinforced by the known failure mode where an advisory-only check let `main` go red — see Failed Attempts.)

### Step 4 — Distinguish "ran-and-failed" from "never-ran" with separate verdicts

Collapsing these two states defeats the very contract being guarded: "the handler ran and produced a bad artifact" and "the handler never ran at all" are different failures and must surface as different verdicts. A single boolean pass/fail hides the never-ran case, which is usually the one the convention exists to catch.

### Step 5 — A read-only verifier must not reuse a side-effecting resolver

Correctness trap caught during planning: the verify path was about to reuse `resolve_target_dir`, which performs a `mkdir`. A verifier that checks for the **absence** of an artifact must not call code that **creates** that artifact — it would fabricate the very thing whose absence is the signal. Inline a side-effect-free resolution for verify paths.

### Quick Reference

```text
1. grep the workflows/hooks/config to PROVE the "existing X step" exists  ← do this first
2. if absent → ship a tested library fn + CLI --verify (exit 2 = violated), wire CI to call it
3. choose BLOCKING (lost failure-signal) vs report-only (hygiene) — and say why
4. emit separate verdicts for ran-and-failed vs never-ran
5. verify paths must use a side-effect-free resolver (no mkdir on a read-only check)
```

```bash
# The one command that changes the whole plan:
grep -rn "<convention-marker>" .github/workflows/ .pre-commit-config.yaml
# empty result ⇒ the assumed integration point is documentation, not infrastructure
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Anchor plan on the existing CI step | Followed audit/KB advice to "add the assertion to the existing CI artifact step" | A grep (`grep -rn "crash-bundle\|coredump\|handler.log" .github/workflows/`) returned no matches — the step never existed; the convention lived only in docstrings | Verify the assumed integration point exists with a grep BEFORE building the plan on it; audit/KB advice routinely assumes infrastructure that is only documented |
| Bare shell assertion in a CI job | Considered enforcing the convention with an inline shell `[ -f ... ]` in CI | Not reusable, not unit-testable, and pointless if the job it belongs to doesn't exist | Prefer a tested library function + CLI `--verify` entrypoint that any consumer (CI YAML, tooling) can call; wire CI to it |
| Collapse verdicts | Considered a single pass/fail boolean | "ran-and-failed" vs "never-ran" are different defects; collapsing them hides the never-ran case the convention exists to catch | Emit separate verdicts; state BLOCKING vs report-only semantics and why (lost failure-signal = BLOCKING) |
| Reuse `resolve_target_dir` in verify path | Considered reusing the existing resolver inside the read-only verifier | `resolve_target_dir` does a `mkdir` — a read-only check would fabricate the artifact whose ABSENCE is the signal | A read-only verifier must use a side-effect-free resolution; never call creating code from a checking path |
| UNVERIFIED ASSUMPTION — `emit_json_status` kwargs passthrough | Plan/test asserts `payload["verdict"]`, assuming `emit_json_status(..., verdict=...)` surfaces arbitrary extra kwargs as a top-level JSON key | NOT directly verified against the implementation | If `emit_json_status` does not pass through extra kwargs, the test and the JSON envelope break — verify before implementing |
| UNVERIFIED ASSUMPTION — JSON status field key is `"status"` | Test asserts `payload["status"] == 2` | NOT verified against `hephaestus/cli/utils.py` | Confirm the envelope's status key name before asserting on it |
| UNVERIFIED ASSUMPTION — `nargs="?"` on the 4 positionals is safe | Plan makes the four positional capture args optional, reasoning the kernel always passes them so optional is a superset | No existing test exercises the kernel capture path with the new optional positionals | Add/run a capture-path test with the new `nargs="?"` args before trusting the superset claim |
| UNVERIFIED ASSUMPTION — exit code `2` is free | Plan uses exit `2` to mean "invariant violated" | argparse itself exits `2` on usage errors — `2` may be overloaded | A reviewer must confirm `2` is an acceptable "invariant violated" code vs colliding with argparse's usage-error `2` |

The rows above capture both the path NOT taken during planning and the four most uncertain
assumptions the resulting plan rests on. A future planner/implementer MUST verify the
"UNVERIFIED ASSUMPTION" rows against ground truth before relying on them.

## Results & Parameters

### What the plan delivered (design intent)

- A guard for an un-guarded convention implemented as a **reusable, tested library function**.
- A **CLI `--verify` mode** exposing it: exit `0` = OK, exit `2` = invariant violated (BLOCKING), so any consumer (CI YAML, downstream tooling) can call it.
- **Separate verdicts** for "ran-and-failed" vs "never-ran."
- **Side-effect-free resolution** in the verify path (no `mkdir`).

### The grep that changes the plan (copy-paste)

```bash
# Replace <markers> with the convention's distinctive filenames/strings.
grep -rn "<marker-1>\|<marker-2>\|<marker-3>" .github/workflows/
# Empty ⇒ the "existing CI step" the advice assumes does not exist. Pivot to library+CLI.
```

### Unverified assumptions a future planner/implementer MUST check

1. `emit_json_status(..., verdict=...)` surfaces arbitrary extra kwargs as a top-level `verdict` key in the JSON envelope. (Test asserts `payload["verdict"]`.)
2. The JSON envelope's status field key is `"status"`. (Test asserts `payload["status"] == 2`; not verified against `hephaestus/cli/utils.py`.)
3. Making the four positional capture args `nargs="?"` does not break the kernel-invoked capture path. (Believed safe since the kernel always passes them, but no existing test exercises it.)
4. Exit code `2` for "invariant violated" does not collide with argparse's usage-error exit `2`.

### Generalizable lessons (the durable takeaway)

1. When KB/prior-learnings advice presumes an integration point ("the existing X step/job/hook"), VERIFY that point exists with a grep BEFORE building the plan on it.
2. For "make an un-guarded convention enforced," prefer a tested library function + CLI verify entrypoint over a bare shell assertion in a (possibly nonexistent) CI job; wire CI to call it.
3. Enforcement vs discovery semantics is a deliberate decision: lost failure-signal → BLOCKING (non-zero exit); hygiene/discovery → exit 0 and report. State which and why.
4. Distinguish "ran-and-failed" from "never-ran" with separate verdicts.
5. A read-only verifier must not reuse a side-effecting resolver (one that `mkdir`s the artifact whose absence is the signal).
