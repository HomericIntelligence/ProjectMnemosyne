---
name: planning-verify-integration-point-exists-before-guarding
description: "Guard-an-unguarded-convention planning meta-pattern: when an audit issue or prior-learnings/KB advice says 'the convention is correct but un-guarded — add a downstream check to the EXISTING X step/job/hook,' VERIFY that the integration point actually exists (grep the workflows/hooks/config) BEFORE building the plan on it; audit findings and KB advice routinely assume infrastructure that is only documented, not implemented. If the assumed step is absent, ship the guard as a tested library function + CLI --verify entrypoint (non-zero exit = invariant violated) that ANY consumer can call, rather than a bare shell assertion in a possibly-nonexistent CI job. CRITICAL re-plan rule: every assumption you flagged 'unverified' last round MUST be verified against source (or resolved) before resubmitting — a NOGO reviewer treats an acknowledged-but-unfixed defect as equivalent to an unacknowledged one. Use when: (1) planning an issue that asks you to enforce/guard an existing convention, (2) an audit or KB note tells you to 'add the check to the existing CI/artifact step,' (3) deciding enforcement-vs-discovery exit-code semantics for a verifier, (4) a read-only verifier might reuse a resolver with a filesystem side effect, (5) re-planning after a NOGO with an 'uncertain assumptions' block to clear."
category: architecture
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-verify-integration-point-exists-before-guarding.history
tags: [planning, guard, convention, invariant, ci-gate, verify, audit-finding, integration-point, library-first, exit-code-semantics, re-plan, nogo, unverified-assumptions, json-envelope, exit-code-collision]
---

# Planning: Verify the Integration Point Exists Before Guarding an Unguarded Convention

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Capture the planning meta-pattern surfaced while planning ProjectHephaestus issue #1207 ("Coredump handler reliability relies on an unverified convention"): how to plan a guard for an un-guarded convention without anchoring the plan on a CI step that does not actually exist — and, after a NOGO, how to clear an "uncertain assumptions" block instead of merely re-acknowledging it |
| **Outcome** | Plan produced and then re-planned after a NOGO. Round 1 pivoted from "add a line to the existing CI artifact step" (a grep proved it absent) to a tested library function + CLI `--verify` entrypoint. Round 2 (after NOGO) verified four previously-unverified assumptions against source and fixed each one |
| **Verification** | unverified — this is a PLANNING learning; the plan was NOT executed, no tests ran, no CI confirmed it. Round-2 facts below were verified by READING source, not by executing |
| **Category** | architecture / planning |
| **Related Issues** | ProjectHephaestus #1207 (rounds R0 and R1) |
| **History** | [changelog](./planning-verify-integration-point-exists-before-guarding.history) |

## When to Use This Skill

Use this skill when planning (not yet implementing) and any of the following hold:

- An audit issue says a convention is "correct but un-guarded" and recommends adding a downstream check.
- Prior-learnings, a KB skill, or the issue body tells you to "add the assertion/check to the **existing** X step / Y job / Z hook."
- You are deciding the exit-code semantics of a verifier (block the build vs. report-and-continue).
- You are about to reuse an existing resolver/helper inside a new read-only verify path.
- **You are re-planning after a NOGO and your previous plan carried an "uncertain assumptions / risks" block.** That block is a TODO list for this round, not a disclaimer to repeat.

**Triggers:**

- Issue title/body contains "convention," "un-guarded," "unverified convention," "relies on a convention," or "add a CI check."
- Advice presumes an integration point: "the existing CI artifact step," "the existing pre-commit hook," "the workflow that already does X."
- You catch yourself writing a plan step like "append one line to the `upload-artifact` job" without having opened that job.
- A reviewer NOGO'd citing "decide-X-later," "acknowledge-without-changing-the-plan," or a defect you had already flagged as a risk in the prior round.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — planning learning only; the plan it came from was never executed. The round-2 defect confirmations below were established by READING source (grep + open the file), not by running tests.

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
- Non-zero exit when the invariant is violated makes it a real gate any caller can block on. **Pick that exit code collision-free** (Step 6).

### Step 3 — State enforcement-vs-discovery semantics explicitly, and why

This is a deliberate design decision, not an accident of implementation:

- A **lost failure-signal** (the artifact whose absence means a crash went unreported) is a real defect → **BLOCKING** (non-zero exit).
- A **hygiene/discovery** scan → exit `0` and report findings.

Write down which one you chose and why. (Reinforced by the known failure mode where an advisory-only check let `main` go red — see Failed Attempts.)

### Step 4 — Distinguish "ran-and-failed" from "never-ran" with separate verdicts

Collapsing these two states defeats the very contract being guarded: "the handler ran and produced a bad artifact" and "the handler never ran at all" are different failures and must surface as different verdicts. A single boolean pass/fail hides the never-ran case, which is usually the one the convention exists to catch.

### Step 5 — A read-only verifier must not reuse a side-effecting resolver

Correctness trap caught during planning: the verify path was about to reuse `resolve_target_dir`, which performs a `mkdir`. A verifier that checks for the **absence** of an artifact must not call code that **creates** that artifact — it would fabricate the very thing whose absence is the signal. Inline a side-effect-free resolution for verify paths.

### Step 6 — Re-plan gate: verify every prior "unverified assumption" against source before resubmitting

**This is the most important durable step.** After a NOGO, open your previous plan's "uncertain assumptions / risks" block and, for EACH item, either verify it against source or resolve it. Never resubmit carrying a known-acknowledged defect — verdict-floor reviewers treat an acknowledged-but-unfixed defect as equivalent to an unacknowledged one. Round-2 of #1207 found all four flagged assumptions were defects:

1. **Exit-code collision — grep the WHOLE CLI's exit-code map before picking a gate code.** argparse exits `2` on usage errors, and a sibling module CLI already returned `2`:

   ```bash
   grep -rn "return [0-9]\|sys.exit([0-9]" hephaestus/forensics/*.py
   # coredump_handler: 0/1 ; gdb_runner: 0/2/127 (gdb_runner.py:380 returns 2)
   ```

   Fix: use a distinct unused code (`3`) behind a NAMED constant (`VERIFY_SIGNAL_LOST_EXIT`), not a bare literal. An enforcement gate's exit code must be collision-free against argparse's `2` AND every code the module's CLIs already return.

2. **JSON-envelope key contract — open the helper AND an existing test, then mirror it.** Never assert a shared helper's output shape from memory. `hephaestus/cli/utils.py` `emit_json_status(exit_code, message, **extra)` sets `envelope["status"]` to the STRING `"ok"`/`"error"` (ok iff `exit_code == 0`), puts the numeric code in `envelope["exit_code"]`, and merges `**extra`. The prior test asserted `payload["status"] == 2` — guaranteed to fail (actual `"error"`). Sibling tests confirm: `test_coredump_handler.py:187,204` assert `payload["status"] == "error"/"ok"`. A verification step containing a guaranteed-to-fail test is itself a planning defect — its RED won't mean what you think.

3. **Log-classifier heuristic fragility — enumerate ALL logger call sites; key off the authoritative POSITIVE signal.** A classifier keyed off a `" WARNING:"` substring mislabels SUCCESS, because a successful capture can log BOTH a WARNING (chmod fail at `coredump_handler.py:198`, or bad `COREDUMP_MAX_BYTES` at `:290`) AND a `wrote ` success line (`:200`). Prefer the success signal (`wrote `) over a substring that co-occurs with success.

4. **Widening an arg contract has a blast radius — pair relax-to-optional with an explicit guard + test.** Changing 4 positionals to `nargs="?"` (so `--verify` can omit them) silently weakens the kernel capture path: a typo'd `core_pattern` line would no longer error, it would no-op. Fix: add an explicit missing-positionals guard in `main` returning exit 1, plus a regression test. Relaxing required→optional to enable a new mode must preserve the original mode's loud-failure behavior.

### Quick Reference

```text
1. grep the workflows/hooks/config to PROVE the "existing X step" exists  ← do this first
2. if absent → ship a tested library fn + CLI --verify (non-zero exit = violated), wire CI to call it
3. choose BLOCKING (lost failure-signal) vs report-only (hygiene) — and say why
4. emit separate verdicts for ran-and-failed vs never-ran
5. verify paths must use a side-effect-free resolver (no mkdir on a read-only check)
6. RE-PLAN GATE: clear every prior "unverified assumption" against source before resubmitting:
   - exit code: grep the whole CLI's exit-code map; avoid argparse's 2; use a NAMED constant
   - JSON shape: open the helper AND an existing test; mirror that test's assertions
   - log classify: enumerate ALL logger call sites; key off the POSITIVE success signal
   - relax-to-optional: add an explicit guard + test that preserves loud-failure
```

```bash
# The one command that changes the whole plan:
grep -rn "<convention-marker>" .github/workflows/ .pre-commit-config.yaml
# empty result ⇒ the assumed integration point is documentation, not infrastructure

# The re-plan exit-code-collision check:
grep -rn "return [0-9]\|sys.exit([0-9]" <module-dir>/*.py   # avoid argparse's 2 + any code already used
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Anchor plan on the existing CI step | Followed audit/KB advice to "add the assertion to the existing CI artifact step" | A grep (`grep -rn "crash-bundle\|coredump\|handler.log" .github/workflows/`) returned no matches — the step never existed; the convention lived only in docstrings | Verify the assumed integration point exists with a grep BEFORE building the plan on it; audit/KB advice routinely assumes infrastructure that is only documented |
| Bare shell assertion in a CI job | Considered enforcing the convention with an inline shell `[ -f ... ]` in CI | Not reusable, not unit-testable, and pointless if the job it belongs to doesn't exist | Prefer a tested library function + CLI `--verify` entrypoint that any consumer (CI YAML, tooling) can call; wire CI to it |
| Collapse verdicts | Considered a single pass/fail boolean | "ran-and-failed" vs "never-ran" are different defects; collapsing them hides the never-ran case the convention exists to catch | Emit separate verdicts; state BLOCKING vs report-only semantics and why (lost failure-signal = BLOCKING) |
| Reuse `resolve_target_dir` in verify path | Considered reusing the existing resolver inside the read-only verifier | `resolve_target_dir` does a `mkdir` — a read-only check would fabricate the artifact whose ABSENCE is the signal | A read-only verifier must use a side-effect-free resolution; never call creating code from a checking path |
| Exit code `2` for "invariant violated" (R0 flagged unverified → R1 CONFIRMED defect) | Plan used exit `2` to mean "invariant violated" | argparse exits `2` on usage errors AND `gdb_runner.py:380` already returns `2` (`grep -rn "return [0-9]\|sys.exit([0-9]" hephaestus/forensics/*.py`: coredump_handler 0/1, gdb_runner 0/2/127) — code `2` was overloaded three ways | Grep the WHOLE CLI's exit-code map before picking a gate code; choose a distinct unused code (`3`) behind a NAMED constant (`VERIFY_SIGNAL_LOST_EXIT`), never a bare literal |
| Assert `payload["status"] == 2` (R0 flagged unverified → R1 CONFIRMED always-fails) | Plan's verify test asserted the numeric exit code lived under the `status` key | `emit_json_status(exit_code, message, **extra)` in `hephaestus/cli/utils.py` sets `status` to the STRING `"ok"`/`"error"` and puts the number under `exit_code`; sibling `test_coredump_handler.py:187,204` assert `status == "error"/"ok"`. The assertion was guaranteed to fail | Never assert a shared helper's output shape from memory — open the helper AND an existing test that uses it and mirror its assertions; a guaranteed-to-fail RED is itself a planning defect |
| Classify success off a `" WARNING:"` substring (R0 flagged unverified → R1 CONFIRMED fragile) | Heuristic: "if log contains WARNING → not success" | A successful capture logs BOTH a WARNING (chmod fail `coredump_handler.py:198`; bad `COREDUMP_MAX_BYTES` `:290`) AND a `wrote ` success line (`:200`) — the substring co-occurs with success | Enumerate ALL call sites of the logger; key the classifier off the authoritative POSITIVE signal (`wrote `), not a substring that co-occurs with success |
| Relax 4 positionals to `nargs="?"` unguarded (R0 flagged unverified → R1 CONFIRMED blast radius) | Made the four capture positionals optional so `--verify` could omit them, assuming "kernel always passes them, so optional is a superset" | Optional silently weakens the kernel path: a typo'd `core_pattern` line would no-op instead of erroring loudly | Pair relax-required→optional with an explicit missing-positionals guard in `main` (exit 1) + a regression test that locks in the original loud-failure behavior |
| Resubmit acknowledging the four risks without fixing them | The R0 plan listed the four items above in an "uncertain assumptions" block and shipped anyway | A NOGO reviewer proved each was a real defect; an acknowledged-but-unfixed defect is treated the same as an unacknowledged one ("decide-X-later" / "acknowledge-without-changing-the-plan") | A plan's "uncertain assumptions / risks" block is a TODO list for the NEXT iteration, not a disclaimer — resolve each against source before resubmitting |

The rows above capture both the path NOT taken during planning and the previously-uncertain
assumptions that round 2 verified and fixed. The remaining open assumptions for THIS round's
plan are listed under Results & Parameters — a future planner/implementer MUST verify them
before relying on them.

## Results & Parameters

### What the plan delivered (design intent, after round-2 fixes)

- A guard for an un-guarded convention implemented as a **reusable, tested library function**.
- A **CLI `--verify` mode** exposing it: exit `0` = OK, exit `3` (named `VERIFY_SIGNAL_LOST_EXIT`, collision-free vs argparse's `2` and gdb_runner's `2`) = invariant violated (BLOCKING).
- **Separate verdicts** for "ran-and-failed" vs "never-ran."
- **Side-effect-free resolution** in the verify path (no `mkdir`).
- **JSON envelope** emitted via `emit_json_status(exit_code, message=detail, verdict=verdict)`; `status` is the string `"ok"`/`"error"`, numeric code under `exit_code`, `verdict` merged via `**extra`. Tests mirror `test_coredump_handler.py` (`status == "ok"/"error"`).
- **Success classifier** keyed off the `wrote ` positive signal, not a `WARNING` substring.
- **Missing-positionals guard** in `main` (exit 1) preserving the kernel path's loud-failure behavior after relaxing the 4 positionals to `nargs="?"`.

### The grep that changes the plan (copy-paste)

```bash
# Replace <markers> with the convention's distinctive filenames/strings.
grep -rn "<marker-1>\|<marker-2>\|<marker-3>" .github/workflows/
# Empty ⇒ the "existing CI step" the advice assumes does not exist. Pivot to library+CLI.

# Before choosing a gate exit code, map every code the module's CLIs already return:
grep -rn "return [0-9]\|sys.exit([0-9]" <module-dir>/*.py
```

### Unverified assumptions THIS round's plan still rests on (for the next reviewer/implementer)

1. `emit_json_status` is invoked exactly as `emit_json_status(exit_code, message=detail, verdict=verdict)` and `verdict` survives as a top-level key via `**extra` — read from source but not executed.
2. Exit code `3` is not assigned special meaning by the repo's CI gate conventions elsewhere — only verified unused WITHIN `hephaestus/forensics/*.py`, not repo-wide.
3. The print-to-stderr-on-failure / stdout-on-success split matches repo CLI convention — assumed, not grep-verified across other CLIs.
4. `nargs="?"` + the new missing-positionals guard fully reproduces the prior argparse error behavior for PARTIAL arg sets (e.g. 2 of 4 positionals present) — the guard checks each for `None`, believed correct but only the all-missing case has an explicit test in the plan.

### Generalizable lessons (the durable takeaway)

1. When KB/prior-learnings advice presumes an integration point ("the existing X step/job/hook"), VERIFY that point exists with a grep BEFORE building the plan on it.
2. For "make an un-guarded convention enforced," prefer a tested library function + CLI verify entrypoint over a bare shell assertion in a (possibly nonexistent) CI job; wire CI to call it.
3. Enforcement vs discovery semantics is a deliberate decision: lost failure-signal → BLOCKING (non-zero exit); hygiene/discovery → exit 0 and report. State which and why.
4. Distinguish "ran-and-failed" from "never-ran" with separate verdicts.
5. A read-only verifier must not reuse a side-effecting resolver (one that `mkdir`s the artifact whose absence is the signal).
6. **A plan's own "uncertain assumptions / risks" block is a TODO list for the NEXT iteration, not a disclaimer.** Resolve each against source before resubmitting; verdict-floor reviewers treat an acknowledged-but-unfixed defect as equivalent to an unacknowledged one.
7. An enforcement gate's exit code must be collision-free against argparse's `2` and every code the module's CLIs already return — grep the whole exit-code map and hide the chosen code behind a named constant.
8. Never assert a shared helper's output shape from memory — open the helper AND an existing test that uses it, and mirror that test's assertions; a guaranteed-to-fail RED is itself a planning defect.
9. When classifying from log text, enumerate ALL call sites of the logger and key off the authoritative POSITIVE signal rather than a substring that co-occurs with success.
10. Relaxing a required arg to optional to enable a new mode must be paired with an explicit guard (and test) that preserves the original mode's loud-failure behavior.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1207 planning, rounds R0 + R1 (post-NOGO re-plan) | Planning-only; unverified — plan never executed. Round-2 defect confirmations from reading source |
