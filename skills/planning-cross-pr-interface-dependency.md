---
name: planning-cross-pr-interface-dependency
description: "Planning discipline for a CAPSTONE / INTEGRATION issue — the terminal issue of a serialized epic that fans IN and wires together modules produced by MANY sibling dependency issues that are ALL STILL OPEN/UNMERGED. The capstone's new code calls ~10 symbols (coordinators, queues, worker pools, stage protocols, route tables, config objects, test conftest fakes) that DO NOT EXIST in the working tree — they are only DESCRIBED in sibling issue bodies and the epic body. You cannot verify them by reading code, so you must plan against the DECLARED (issue-body) contract, and the plan MUST convert that un-verifiable assumption into a checklist gate: (a) add an explicit 'Dependency note' that the PR is cut from a base where the LAST sibling is merged, and (b) make Step 1 of the implementation order a 'pin/confirm upstream interface names on the merged base via grep BEFORE writing any code' gate that rebases onto merged reality if any symbol name drifted. Split the plan's facts into VERIFIED (things you Read from the current repo — main()/dispatch structure, a sleeper that blocks the coordinator thread, the shared arg parser, a symbol's REAL module home, the coverage omit-list membership) vs ASSUMED (every sibling symbol signature, every conftest fake shape, the tick-order contract) in a dedicated section. Ground every DESIGN decision in a VERIFIED repo fact (a blocking sleeper => the new gate must be a non-blocking predicate; dispatch belongs at the top of main() so legacy paths stay byte-for-byte; store_true default-False gives CLI-wins-over-env for free; new modules stay OUT of the omit list so they get covered by doing nothing). Use when: (1) planning the capstone/integration/terminal issue of a serialized epic whose earlier issues are unmerged, (2) your new code references symbols that only exist in sibling issue bodies or the epic body, not on disk, (3) you are about to grep for a symbol's home and might infer its module from a CALLER instead of its real location (e.g. a status-emitter that lives in cli/utils, not automation), (4) you plan to extract a shared helper out of a coverage-omitted module and might trip an omit-list JUSTIFICATION test, (5) you are changing the semantic of an existing CLI flag or making a blocking operation non-blocking and must document the behavior change."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
tags:
  - planning
  - capstone-issue
  - integration-pr
  - serialized-epic
  - unmerged-siblings
  - declared-interface
  - issue-body-contract
  - fan-in-integration
  - pin-upstream-names-first
  - rebase-onto-merged-base
  - verified-vs-assumed
  - non-blocking-predicate
  - dispatch-at-top-of-main
  - store-true-cli-wins
  - coverage-omit-justification
  - symbol-home-grep-not-caller
  - behavior-change-documentation
---

# Planning a Capstone / Integration PR Against Sibling Interfaces That Don't Exist On Disk Yet

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Capture the planning meta-discipline for authoring the CAPSTONE (terminal) issue of a serialized epic — the one issue that fans IN and integrates modules produced by many earlier sibling issues that are ALL STILL OPEN/UNMERGED. The capstone's new code calls ~10 symbols that DO NOT EXIST in the working tree; they are only DESCRIBED in sibling issue bodies and the epic body. Plan against the DECLARED (issue-body) contract of the unmerged siblings, not against verified code — and mandate the mitigations that turn an un-verifiable assumption into a checklist gate: an explicit "Dependency note" pinning the merged base, and a Step-1 "pin/confirm upstream interface names on the merged base by grep before writing any code" gate that rebases onto merged reality on any name drift. Separate VERIFIED repo facts from ASSUMED sibling-contract facts in a dedicated section, and ground every DESIGN decision in a VERIFIED fact. |
| **Outcome** | Planning artifact produced (an implementation plan for a capstone integration issue). NO code was written, NO build ran, NO CI ran. The sibling modules the plan integrates have never existed in the working tree — every symbol they expose is transcribed from an issue body, not read from source. |
| **Verification** | **unverified** — this is a PLANNING artifact. No code was executed, no CI ran, and the sibling interfaces the plan integrates are un-verifiable by construction (their producing PRs are unmerged). Treat every checklist item as a hypothesis until CI confirms it post-merge. |
| **History** | v1.0.0 (2026-07-04): initial capture from a ProjectHephaestus capstone-issue plan (#1817), the terminal issue of the 14-issue serialized queue-pipeline epic #1809, whose dependency issues #1810–#1816 were ALL still open/unmerged at plan time. |

> **Scope and companion skills.** This skill is the FAN-IN / MANY-SIBLINGS / CAPSTONE case. It is
> distinct from three neighbors: `planning-follower-issue-unmerged-dependency-assumptions` and
> `planning-unmerged-parent-contract-compile-smoke-gate` both handle a SINGLE unmerged parent (one
> `Depends on #N`), not a terminal issue that integrates the interfaces of MANY unmerged siblings at
> once. `planning-dependent-issue-unverified-upstream` handles the OPPOSITE case where the dependency
> is already MERGED and just needs reading. `planning-epic-verify-live-child-state` covers planning
> the EPIC itself (verifying live child state); this skill covers planning the CAPSTONE issue that
> CONSUMES the siblings' declared interfaces. The gap those leave: a terminal integration PR whose
> new code calls ~10 symbols that live only in sibling issue bodies, where the load-bearing move is a
> Step-1 pin-upstream-names gate on the merged base plus a strict verified-vs-assumed split.

## When to Use

- Planning the CAPSTONE / INTEGRATION / terminal issue of a serialized epic whose EARLIER sibling issues are still open/unmerged. The capstone's job is to wire together modules the siblings produce, so it references their public surface before that surface exists on disk.
- Your new code references symbols — coordinators, queues, worker pools, stage protocols, route tables, config objects, factory functions, or test conftest fakes — that exist ONLY in sibling issue bodies or the epic body, not in the working tree. `grep` finds nothing; that is expected and is NOT license to treat the invented signature as verified.
- You are about to grep for a symbol's home and might infer its module from a CALLER rather than its real location. A status-emitter used by automation code may actually LIVE in a shared cli/utils module, not in automation — inferring "it's in automation because automation calls it" is a naming-location trap.
- You plan to extract a shared helper out of a module that is on the coverage OMIT list, and the extraction could trip an omit-list JUSTIFICATION test (which checks that every omitted module has a backing unit-test suite by import-parsing test files). Extraction can move the justification anchor.
- You are changing the SEMANTIC of an existing CLI flag (e.g. per-phase-subprocess timeout → per-agent-job timeout) or making a previously BLOCKING operation NON-BLOCKING. Both are behavior changes that must be documented explicitly, not slipped in.
- You must decide where new dispatch/entrypoint logic goes relative to legacy code paths, and you want the legacy path to stay byte-for-byte untouched so the diff is auditable and the risk is contained.

## Verified Workflow

<!-- The literal token "## Verified Workflow" is required by scripts/validate_plugins.py
(validate_sections). This skill's verification level is "unverified" — the PROPOSED WORKFLOW
subsection below carries the real semantics. Do NOT read this heading as a warranty. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
> It was distilled from an UNEXECUTED capstone-integration plan whose sibling interfaces are
> un-verifiable by construction (their producing PRs are unmerged). No build, no test, no CI run has
> exercised any assumption below. The Step-1 pin-upstream-names gate and the verified-vs-assumed split
> are the only mechanisms that convert the un-verifiable sibling-contract assumptions into a
> discoverable, mechanical reconciliation after the siblings merge.

### Quick Reference

```bash
# === Capstone / integration-issue planning checklist (siblings UNMERGED) ===
# EPIC = the serialized epic issue; SIBS = the unmerged dependency issues; CAP = the capstone.

EPIC=1809
SIBS="1810 1811 1812 1813 1814 1815 1816"
CAP=1817
REPO=HomericIntelligence/ProjectHephaestus

# 1. Confirm the siblings are genuinely unmerged and read their DECLARED contract.
#    The issue body is the ONLY contract source until the sibling PR merges.
for n in $SIBS; do gh issue view "$n" --repo "$REPO" --json state,title,body; done
gh issue view "$EPIC" --repo "$REPO" --json body    # the epic body enumerates the fan-in order

# 2. VERIFY what you CAN by reading the current repo. Anything you cannot Read is ASSUMED.
#    Grep a symbol's REAL home — do NOT infer its module from a caller.
grep -rn "def emit_json_status" hephaestus/       # confirm the real module, not the caller's
grep -rn "def <sibling_symbol>" hephaestus/       # expect NOTHING for unmerged siblings — that's fine

# 3. In the plan, add an explicit DEPENDENCY NOTE: the PR is cut from a base where the LAST
#    sibling (highest-numbered dependency) has merged, and it rebases onto merged reality if any
#    symbol name drifted. This states the un-verifiable assumption AND its discharge condition.

# 4. Make Step 1 of the IMPLEMENTATION ORDER a pin-upstream-names GATE, before any code:
#    grep each assumed symbol on the merged base; if a name drifted, rebase + rename first.
grep -rn "class PipelineConfig\|def run_pipeline\|class StageQueue" hephaestus/   # on merged base

# 5. Split plan facts into VERIFIED (Read from repo, line-anchored) vs ASSUMED (from issue bodies).
#    Ground every DESIGN decision in a VERIFIED fact (see Detailed Steps 6).

# 6. If extracting a shared helper out of a coverage-OMITTED module, check the omit-JUSTIFICATION
#    test first; hedge with an inline-copy fallback so the extraction cannot strand the omit anchor.
grep -rn "omit" pyproject.toml                    # find the frozen omit list + its membership test
```

### Detailed Steps

1. **Confirm the siblings are unmerged, then read their DECLARED contract from the issue bodies.**
   Run `gh issue view <n>` for each dependency and `gh issue view <epic>` for the fan-in order.
   For an unmerged sibling, the issue body is the ONLY contract source — there is no code to read.
   Transcribe the symbol names, signatures, and tick-order semantics AS DECLARED, but do not
   present them as verified. The epic body is the authority on the integration/tick order.

2. **Add an explicit "Dependency note" that pins the merged base.** State in the plan that the PR
   is cut from a base where the LAST (highest-numbered) sibling dependency has merged, so ALL the
   integrated interfaces exist, and that it rebases onto merged reality if any symbol name drifted.
   This converts "I assumed these symbols exist" into "the PR is only valid on a base where they do,
   and here is the reconciliation step if they differ." Without this note, a reviewer cannot tell
   whether you knew the siblings were unmerged or overlooked it.

3. **Make Step 1 of the implementation order a "pin/confirm upstream interface names" GATE — before
   any code.** The FIRST implementation-order item must be: on the merged base, `grep` each assumed
   sibling symbol (`run_pipeline`, `PipelineConfig`, `StageQueue`, `CompletionQueue`,
   `WorkerPool.submit`, the stage protocol names, the route table, the config objects, the conftest
   fakes) and confirm the name/signature matches the plan. If any drifted, rebase and rename BEFORE
   writing integration code. This is the mechanical gate that discharges the un-verifiable
   assumption; do not defer it to "we'll find out when it fails to import."

4. **Split every plan fact into VERIFIED vs ASSUMED, in a dedicated section.** VERIFIED = things you
   `Read` from the CURRENT repo, line-anchored (e.g. the entrypoint `main()`/dispatch structure, a
   sleeper that blocks the coordinator thread, the shared arg parser's location, a status-emitter's
   REAL module home, the coverage omit-list membership and its frozen-membership test). ASSUMED =
   things you read ONLY from an issue body and never executed (every sibling symbol signature, every
   conftest fake shape, the stage-protocol names, the tick-order contract, any helper extraction
   from an unmerged sibling). A reviewer must be able to tell the two apart at a glance.

5. **Grep a symbol's REAL home; never infer its module from a caller.** When you need a symbol that
   DOES already exist (a shared helper the capstone reuses), grep for its definition
   (`grep -rn "def <symbol>" hephaestus/`) and cite the real file:line. A symbol used heavily by one
   subsystem may LIVE in a shared utility module, not in that subsystem — e.g. a JSON status emitter
   consumed by automation code can live in `cli/utils`, not in `automation`. Inferring "it's in
   automation because automation calls it" writes a false fact into the plan that a reviewer or the
   implementer then trusts.

6. **Ground every DESIGN decision in a VERIFIED repo fact — these are the SAFE parts of the plan.**
   The design choices that rest on things you actually read are the low-risk core; make the grounding
   explicit so the reviewer can see the chain. Canonical examples from the capstone that produced
   this skill:
   - A rate/budget check that must become a NON-BLOCKING predicate *because* the verified existing
     sleeper sleeps the single coordinator thread — a blocking sleep there would freeze every queue.
   - New dispatch logic placed at the TOP of `main()` (after signal-handler install) *because* that
     keeps the legacy loop path byte-for-byte untouched and the diff auditable.
   - A `store_true` flag with default `False` *because* that gives CLI-wins-over-env precedence for
     free (flag absent → env consulted; flag present → CLI wins) with no extra precedence code.
   - The new modules stay OUT of the coverage omit list *because* doing nothing is the correct action
     — new source with tests gets counted automatically; adding an omit entry would need justification.

7. **Guard any helper extraction out of a coverage-OMITTED module with an inline-copy fallback.**
   If the plan extracts a shared helper (e.g. a "format preserved worktrees" helper) out of a module
   that is on the coverage omit list, the extraction can trip the omit-list JUSTIFICATION test — the
   test that import-parses `tests/` to prove every omitted module has a backing test suite. Moving the
   symbol can move the anchor that test keys on. Hedge: state a fallback of copying the helper inline
   in the new module (so the omitted module is unchanged) if the shim-first extraction trips the
   justification guard. This keeps the plan robust to a test you have not run.

8. **Document every behavior change explicitly — CLI-flag semantics and blocking→non-blocking.**
   A flag whose meaning shifts (per-phase-subprocess timeout → per-agent-job timeout) or a previously
   BLOCKING operation made NON-BLOCKING is a behavior change, not a refactor. Call it out in a
   dedicated line so reviewers and downstream consumers are not surprised. Silent semantic shifts on a
   shared flag are a POLA violation and a common review NOGO.

9. **Name the reviewer's highest-risk attack surface in the plan.** The acceptance-critical,
   highest-risk deliverables in a capstone integration are typically (a) any DRIFT between the plan's
   assumed upstream symbol names and what the siblings actually merged; (b) the shim-first extraction
   that could trip the omit-list justification test; (c) the acceptance test suites (e.g. a crash
   matrix + a journal-order suite) whose assertions depend ENTIRELY on an unverified conftest fake's
   API (a fake's mutation-log shape you never ran); (d) the documented behavior change on a shared
   CLI flag. Enumerating these tells the reviewer where to spend their attention and admits, up front,
   where the plan is a hypothesis rather than a fact.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Assumed a JSON status emitter (`emit_json_status`) lived in the automation package because the automation loop is its heaviest caller, and cited `hephaestus/automation/...` in the plan. | The symbol actually lives in `hephaestus/cli/utils.py:352` — a shared utility module. The plan would have pointed the implementer and reviewer at a file that does not define it. | Grep the symbol's REAL home (`grep -rn "def emit_json_status" hephaestus/`); do not infer a module from a caller. A heavily-used-by-X symbol frequently lives in a shared module, not in X. |
| 2 | Planned to write the coordinator/integration code against the assumed sibling signatures (`run_pipeline`, `PipelineConfig`, `StageQueue`, `WorkerPool.submit`, the stage protocol) BEFORE pinning the upstream names on the merged base. | The sibling PRs (#1811–#1816) are unmerged; every one of those ~10 symbol names could drift on merge (a rename, a reordered arg, a moved module). Code written first becomes a rename/rewrite pass, and the drift is discovered at the slowest feedback loop (import error). | Make "pin/confirm upstream interface names on the merged base by grep" the FIRST implementation-order step, gated on a base where the last sibling has merged. No integration code until the names are pinned. |
| 3 | Treated the sibling issue-body signatures (stage protocol `Stage`/`StageContext`/`Continue`/`JobRequest`/`StageOutcome`, the `ROUTES`/`Route`/`Disposition` route table, `PipelineScope`, the tick-order contract) as verified facts and wrote plan assertions against them without qualification. | None of those symbols were ever executed or even read from source — they exist only in issue prose. Design intent in an issue body is not a schema; drift on merge silently invalidates the assertions. | Mark unverified assumptions explicitly with a "Dependency note" and split the plan into VERIFIED (Read from repo) vs ASSUMED (read only from issue bodies). A reviewer must be able to tell the two apart. |
| 4 | Planned to make the rate/budget check a blocking wait, mirroring the existing `_maybe_sleep_for_rate_budget` sleeper, without accounting for the fact that the new code runs on the single coordinator thread. | The verified sleeper (`loop_runner.py:1333`) sleeps the loop thread; in the new queue-coordinator design that single thread drives every queue, so a blocking sleep there would FREEZE all queues, not just pace one job. | Ground the design in the VERIFIED fact: because the sleeper blocks the coordinator thread, the new gate must be a NON-BLOCKING predicate. Read what the existing primitive actually blocks before reusing its shape. |
| 5 | Considered threading the new dispatch logic INTO the legacy `run_loop` body so the pipeline and legacy paths shared a code path. | That would rewrite `run_loop` line-for-line, enlarge the diff, and put the byte-for-byte-stable legacy path at risk for a feature that should be additive. | Place new dispatch at the TOP of `main()` (after signal-handler install) so the legacy `run_loop` stays byte-for-byte untouched. Prefer additive entrypoints over threading new behavior through stable legacy code. |
| 6 | Planned to shim-extract `format_preserved_worktrees` out of `implementer_summary` (a coverage-OMITTED module) to reuse it, without checking the omit-list justification test. | Extracting a symbol out of an omitted module can move the anchor that `test_omit_justification.py` keys on (it import-parses `tests/` to prove each omitted module has a backing suite), potentially tripping a test the plan never ran. | When extracting a helper out of a coverage-omitted module, check the omit-JUSTIFICATION test first and hedge with an inline-copy fallback so the extraction cannot strand the omit anchor. |
| 7 | Wrote the crash-matrix and journal-order acceptance test suites in the plan as if the `FakeGitHub`/`FakeWorkerPool` conftest mutation-log API were known, since it is described in a sibling issue body. | Those fakes do not exist in the working tree; their `mutation_log` shape was never executed. The highest-risk, acceptance-critical suites rest entirely on an unverified fake API — if the fake's real shape differs, every assertion is wrong. | Name the acceptance-critical suites and their unverified-fake dependency as the reviewer's top risk. Do not present tests built on an unrun conftest fake as verified; flag them as the hypothesis they are. |
| 8 | Left the `--phase-timeout` flag's semantic shift (per-phase-subprocess → per-agent-job) implicit, treating the change as an internal refactor. | It is a behavior change on a user-facing flag; a user relying on the old per-phase meaning gets silently different timeout behavior — a POLA violation and a likely review NOGO. | Document every behavior change explicitly (CLI-flag semantic shifts, blocking→non-blocking). Silent semantic changes on shared/user-facing surfaces must be called out in a dedicated line. |

## Results & Parameters

### Verified On

| Repository | Session | Notes |
|------------|---------|-------|
| ProjectHephaestus | Capstone plan for GitHub issue #1817 (terminal issue of serialized epic #1809; dependency siblings #1810–#1816 ALL open/unmerged at plan time) | Session 2026-07-04 — implementation plan authored for the queue-pipeline capstone integration. The plan integrates `pipeline/coordinator.py`, `summary.py`, and terminal stages that call ~10 symbols existing only in sibling issue bodies. NO code written, NO build/CI run. Used as the sole "Verified On" instance; the skill itself is generalizable to any serialized-epic capstone. |

### What was VERIFIED vs ASSUMED (the load-bearing split)

**VERIFIED (Read directly from the ProjectHephaestus tree, line-anchored):**

- `loop_runner.py` `main()` / dispatch structure (≈ lines 1633–1747) — where new dispatch can be added at the top of `main()` without touching legacy `run_loop`.
- `_maybe_sleep_for_rate_budget` (`loop_runner.py:1333`) SLEEPS the loop thread — the fact that grounds "the new gate must be a non-blocking predicate."
- `build_automation_parser` (`_review_utils.py:340`) is the shared arg parser.
- `emit_json_status` lives in `hephaestus/cli/utils.py:352` — NOT in automation (a naming-location trap the plan could have gotten wrong).
- `_print_preserved_worktrees` (`implementer_summary.py:96–111`) — the extraction candidate.
- `[tool.coverage.run].omit` at `pyproject.toml:267` with frozen membership enforced by `test_omit_allowlist.py`.

**ASSUMED (read ONLY from issue bodies #1811–#1816 / epic #1809 — never executed):**

- Every `pipeline/*` symbol signature (`run_pipeline`, `PipelineConfig`, `StageQueue`, `CompletionQueue`, `WorkerPool.submit`).
- The stage-protocol names (`Stage` / `StageContext` / `Continue` / `JobRequest` / `StageOutcome`).
- The route table (`ROUTES`, `Route`, `Disposition`) and `PipelineScope`.
- The `FakeGitHub` / `FakeWorkerPool` conftest fake shape (esp. the `mutation_log` API the acceptance suites assert on).
- The tick-order contract and `classify_ci_state` extraction from the last sibling.

### Design decisions grounded in verified facts (the SAFE parts of the plan)

1. **Rate/budget → non-blocking predicate** — because the verified `_maybe_sleep_for_rate_budget` sleeps the single coordinator thread (a blocking wait would freeze all queues).
2. **Dispatch at the top of `main()`** (after signal-handler install) — so legacy `run_loop` stays byte-for-byte untouched.
3. **`store_true` default-False** — gives CLI-wins-over-env precedence for free (flag absent → env; flag present → CLI wins).
4. **New modules stay OUT of the omit list** — doing nothing is correct; new source with tests is covered automatically.

### Reviewer / Author Pre-Flight Checklist for a Capstone-Integration Plan (copy-paste)

```text
[ ] Confirmed every sibling dependency is genuinely unmerged (gh issue view / gh pr list).
[ ] Read each sibling issue body + the epic body; transcribed the DECLARED contract, not
    presented it as verified.
[ ] "Dependency note" present: PR is cut from a base where the LAST sibling merged; rebases
    onto merged reality on any symbol-name drift.
[ ] Implementation-order Step 1 = "pin/confirm upstream interface names on the merged base by
    grep, before any code." No integration code precedes this gate.
[ ] Plan has a VERIFIED-vs-ASSUMED section; every VERIFIED item is line-anchored; every ASSUMED
    item is from an issue body and flagged.
[ ] Every symbol I claim already exists was grep'd to its REAL home, not inferred from a caller.
[ ] Every DESIGN decision is chained to a VERIFIED repo fact (blocking sleeper → non-blocking
    predicate; top-of-main dispatch → legacy untouched; store_true → CLI-wins-over-env; new
    modules stay out of the omit list).
[ ] Any helper extraction out of a coverage-omitted module is hedged with an inline-copy fallback
    against the omit-JUSTIFICATION test.
[ ] Every behavior change (CLI-flag semantic shift, blocking→non-blocking) is documented in a
    dedicated line.
[ ] Reviewer's top risks named: symbol-name drift, omit-justification trip, acceptance suites on
    an unverified conftest fake, the documented flag behavior change.
[ ] Plan is labeled `unverified`; the sibling contract is a hypothesis until CI confirms post-merge.
```

### Prescriptive Recommendations for Future Planners

1. **The capstone's sibling interfaces are a hypothesis, not a schema.** Issue-body signatures are design intent written before implementation. Plan against the declared contract, but gate on a Step-1 grep-pin on the merged base.
2. **A "Dependency note" + a pin-upstream-names Step 1 are the two load-bearing mitigations.** Together they convert an un-verifiable assumption into a mechanical reconciliation the implementer performs on merged reality.
3. **Split VERIFIED from ASSUMED, and ground every design decision in a VERIFIED fact.** The verified core is the low-risk part of the plan; make the grounding chain explicit so the reviewer can audit it.
4. **Grep a symbol's real home; never infer its module from a caller.** A symbol heavily used by one subsystem often lives in a shared module.
5. **Guard extractions out of coverage-omitted modules with an inline-copy fallback.** An extraction can move the anchor an omit-justification test keys on.
6. **Prefer additive entrypoints over threading new behavior through stable legacy code.** Top-of-`main()` dispatch keeps the legacy path byte-for-byte and the diff auditable.
7. **Document every behavior change on a shared/user-facing surface.** Silent CLI-flag semantic shifts and blocking→non-blocking changes are POLA violations and common review NOGOs.
