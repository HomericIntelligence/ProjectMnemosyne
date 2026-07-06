---
name: planning-absorb-existing-module-into-unmerged-stage
description: "Planning discipline for a MID-CHAIN sub-issue of a strictly-serialized epic whose job is to ABSORB / MIGRATE an EXISTING covered module into a pipeline stage FILE that does not exist yet because it is PRODUCED by an EARLIER, UNMERGED sibling issue. The acceptance criteria name symbols (`PipelineConfig`, `PipelineScope`, `run_pipeline`) and destination paths (`.../pipeline/stages/plan_review.py`, `tests/unit/.../pipeline/test_stage_plan_review.py`) that are ABSENT on the current tree — the tell is the issue's OWN wording 'absorbed into stages/plan_review.py IN THE EPIC', which reveals the target is created by a prior sub-issue, not by this one. The load-bearing move is a SPLIT-ANCHOR plan: SOURCE-side facts (the existing module's patch-seam sweep surface, `main()` line, `class X` line, the shared arg-parser home, and every `patch.object`/`mock` seam a test suite pins) are VERIFIED against the current tree and DO NOT drift while the dep is unmerged, so they anchor the plan usefully NOW; DESTINATION-side pipeline symbol names DO drift and must be marked 'match whatever the merged API exports — verify before writing'. State BLOCKED up front with the evidence greps, still deliver the full executable spec, make implementation Step 1 an explicit 'GATE — confirm dependency merged; if not, STOP', and warn that all destination `file:line` anchors re-grep after the dep lands. A structural assertion in an existing test (e.g. an agent-wiring assertion) that guards behavior the migration preserves must be RE-HOMED to the new test module, NOT deleted. Use when: (1) planning a sub-issue of a serialized epic whose `Depends on #N` chain is not yet merged and whose ACCEPTANCE CRITERIA reference symbols/files/modules that do not exist on the current tree; (2) the issue asks you to MOVE/ABSORB an existing (often coverage-COVERED) module into a not-yet-existing stage file; (3) you must decide implement-now vs. write a forward-referencing 'execute after #N merges' plan; (4) you must avoid hallucinating an entire dependency's API surface while STILL anchoring the plan to real current-tree facts on the source side; (5) an existing structural/wiring test assertion would be orphaned by the migration and must be re-homed rather than dropped."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - serialized-epic
  - dependency-gated
  - blocked-issue
  - unmerged-dependency
  - absorb-existing-module
  - module-migration
  - split-anchor
  - source-vs-destination-anchors
  - forward-referencing-plan
  - gate-confirm-dep-merged
  - re-home-structural-assertion
  - patch-seam-sweep
  - covered-module
  - coverage-omit-list
  - verify-before-planning
  - grep-ls-every-named-symbol
  - anchor-drift
  - honest-blocked-plan
---

# Planning a Sub-Issue That Absorbs an Existing Module Into a Stage File an Unmerged Sibling Produces

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Capture the planning discipline for a MID-CHAIN sub-issue of a strictly-serialized epic whose task is to ABSORB an existing (covered) module into a pipeline stage FILE that another, EARLIER, UNMERGED sibling issue is supposed to create — so the plan is honest about being BLOCKED, does NOT hallucinate the missing destination API, and still ships a full executable spec anchored to the real source-side facts that do not drift while the dependency is unmerged. |
| **Outcome** | Planning artifact only. Distilled from a ProjectHephaestus plan for issue #1820 (item 11 of 14 in the strictly-serialized queue-pipeline epic #1809), whose entire `Depends on` chain #1810–#1819 was OPEN/unmerged at plan time, and whose acceptance criteria referenced a `hephaestus/automation/pipeline/` package and a `stages/plan_review.py` file that DO NOT EXIST on the current tree — they are produced by earlier sub-issue #1814. NO code was written, NO build ran, NO CI ran. |
| **Verification** | **unverified** — this is a planning-discipline learning, not an executed workflow. The `gh`/`find`/`grep`/`ls` verification commands below WERE run this session and returned the cited results; the SOURCE-side `file:line` anchors were `Read` from disk and are real. But the plan was never implemented and the destination (pipeline) surface is un-verifiable by construction (its producing PR is unmerged). Treat every checklist item as a hypothesis until CI confirms it post-merge. |
| **History** | v1.0.0 (2026-07-04): initial capture from the ProjectHephaestus #1820 absorb-into-stage plan. |

> **Scope and companion skills.** This is the ABSORB-AN-EXISTING-MODULE-INTO-AN-UNMERGED-STAGE case,
> distinct from its four neighbors in the same epic-planning family:
> `planning-cross-pr-interface-dependency` is the CAPSTONE / FAN-IN case (a terminal issue writing
> NEW code that integrates MANY unmerged siblings). `planning-unmerged-dep-pure-classifier-extraction`
> builds a NEW stage and EXTRACTS a pure classifier to de-block a poll loop.
> `planning-follower-issue-unmerged-dependency-assumptions` and
> `planning-unmerged-parent-contract-compile-smoke-gate` handle a SINGLE unmerged parent whose surface
> you must INVENT/consume. `planning-dependent-issue-unverified-upstream` handles the OPPOSITE case
> where the dependency is already MERGED and readable. The gap they leave, which THIS skill fills: a
> sub-issue that MOVES an EXISTING covered module into a destination FILE a prior sibling creates — so
> the SOURCE anchors are solid current-tree facts that do NOT drift, only the DESTINATION anchors do.
> The signature move here is the SPLIT-ANCHOR plan and re-homing (not deleting) an orphaned structural
> test assertion.

## When to Use

- Planning a sub-issue of a strictly-serialized epic whose `Depends on #N` dependency chain is NOT yet
  merged (state `plan-go` / `in-progress` / open PR pending / no branch at all), AND whose acceptance
  criteria reference symbols, files, or modules that DO NOT exist on the current tree.
- The issue asks you to MOVE / ABSORB / migrate an EXISTING module (often a coverage-COVERED,
  non-omit-listed one) INTO a stage file that another, earlier sub-issue is supposed to create. The
  destination path (`.../pipeline/stages/<stage>.py`) and its test (`.../pipeline/test_stage_<stage>.py`)
  do not exist yet.
- The issue's own wording betrays the dependency: phrasing like "absorbed into `stages/<stage>.py`
  **in the epic**" or "the pipeline package **from #<earlier>**" means the target is PRODUCED by an
  earlier unmerged sub-issue, not by this one. Read that phrasing as a BLOCKED signal, not an
  instruction to create the destination yourself.
- You must decide: implement now vs. write a forward-referencing "execute after #N merges" plan. (If
  the destination file must exist first and it is produced by an unmerged sibling, the honest answer is
  a forward-referencing plan — implementing now would mean re-implementing 9 other serialized siblings.)
- You want to avoid hallucinating an entire dependency's API surface into the plan while STILL anchoring
  it to real, usable current-tree facts on the SOURCE side (the module being absorbed and its tests).
- An existing structural / wiring test assertion (e.g. an agent-wiring or dispatch-shape assertion)
  would be ORPHANED by the migration — it must be RE-HOMED to the new test module, not silently dropped.

## Verified Workflow

<!-- The literal token "## Verified Workflow" is required by scripts/validate_plugins.py
(validate_sections). This skill's verification level is "unverified" — the PROPOSED WORKFLOW
subsection below carries the real semantics. Do NOT read this heading as a warranty. -->

### Proposed Workflow (UNVERIFIED — planning artifact only)

> **Warning:** This workflow has not been validated end-to-end. No code was written or run; no tests
> ran; no CI validated it. It is the plan-authoring discipline distilled from an *unexecuted* plan
> (ProjectHephaestus #1820, item 11 of the 14-issue serialized epic #1809, whose entire dependency
> chain #1810–#1819 was unmerged at plan time). The SOURCE-side line anchors cited were `Read` from
> disk and are real; the DESTINATION (pipeline) surface is un-verifiable by construction because its
> producing PR (#1814) is unmerged. The only mechanism that empirically discharges the destination
> assumptions is the Step-1 "confirm dependency merged, else STOP" gate plus a re-grep of every
> destination anchor after the dep lands. Treat every checklist item as a hypothesis until CI confirms.

### Quick Reference

```bash
# ===== 1. PROVE the sub-issue is BLOCKED: dependency chain unmerged + destination absent =====
REPO=HomericIntelligence/ProjectHephaestus
DEPS="$(seq 1810 1819)"   # the whole Depends-on chain
for n in $DEPS; do gh issue view "$n" --repo "$REPO" --json number,state,title --jq \
  '"\(.number)\t\(.state)\t\(.title)"'; done   # expect ALL open/unmerged

gh issue view 1809 --repo "$REPO" --json body   # epic body: "the loop must never work two concurrently"

# The destination package + files the acceptance criteria NAME must be ABSENT on the current tree:
find hephaestus/automation -type d | grep -i pipeline           # -> (empty): no pipeline/ package
grep -rln "PipelineConfig\|PipelineScope\|run_pipeline" hephaestus/  # -> (ZERO hits)
ls hephaestus/automation/pipeline/stages/plan_review.py         # -> No such file or directory
ls tests/unit/automation/pipeline/test_stage_plan_review.py     # -> No such file or directory
# ALL of the above empty/not-found ⇒ the target is produced by an EARLIER unmerged sibling ⇒ BLOCKED.

# ===== 2. ANCHOR the plan to SOURCE-side facts that DO NOT drift while the dep is unmerged =====
# The module being ABSORBED and its tests are on disk NOW — Read/grep them and cite file:line.
grep -rn "planner_review_loop" hephaestus/ tests/ | wc -l   # the full patch-seam sweep surface
grep -n "^def main\|^class Planner\|import" hephaestus/automation/planner.py
grep -rn "patch.object\|mock" tests/unit/automation/test_planner_loop.py | wc -l  # count the seams
grep -rn "build_automation_parser" hephaestus/automation/_review_utils.py

# ===== 3. Mark DESTINATION (pipeline) symbols as VERIFY-AGAINST-MERGED-API, never invented =====
# In the plan's main() sketch, PipelineConfig(...)/PipelineScope(...)/run_pipeline/seed_* are GUESSES
# modeled on issue prose. Replace with the real merged API at implementation time (Step 1 gate).
```

### Detailed Steps

1. **Grep and `ls` EVERY symbol and path the acceptance criteria name — BEFORE planning.** Absence is
   the whole diagnosis. If `find <root> -type d | grep <pkg>` is empty, `grep -rln "<Symbol>"` returns
   ZERO, and `ls <exact/named/file.py>` is not-found, the destination does not exist on the current
   tree. Combined with an unmerged `Depends on` chain, that means the target is produced by an EARLIER
   sub-issue and this issue is BLOCKED. Do not skip this because the issue "reads implementable."

2. **Read the issue's own wording as the tell.** Phrasing like "absorbed into `stages/<stage>.py`
   **in the epic**", "the pipeline package **from #<earlier>**", or "once the coordinator exists"
   reveals that the destination is another sibling's deliverable. This is the cheapest BLOCKED signal —
   it is right there in the AC. Read it as "not my file to create," not as license to scaffold the
   whole pipeline yourself.

3. **State BLOCKED up front, with the evidence greps.** The plan's first section names the blocking
   dependency (`#N`), pastes the three empty/not-found command outputs (dir absent, symbol grep zero,
   file `ls` not-found), and states that implementing now would require re-implementing the other
   serialized siblings — which the epic body explicitly forbids ("never work two of these
   concurrently"). Honesty about the blocked state is the deliverable's credibility.

4. **Still deliver the FULL executable spec — a forward-referencing plan, not a stub.** Being blocked
   is not an excuse to hand back nothing. Provide the complete migration spec a future implementer
   needs: what moves where, which tests re-home, what the new stage's responsibilities are. The plan is
   "execute after #N merges," fully specified against the SOURCE-side facts that are real today.

5. **SPLIT the anchors: SOURCE-side facts anchor NOW; DESTINATION-side names are verify-against-merged.**
   This is the load-bearing move. The module being absorbed and its tests are on disk today — their
   `main()` line, `class X` line, the shared arg-parser home, and EVERY `patch.object`/`mock` seam a
   test suite pins are VERIFIED and DO NOT drift while the dep is unmerged, so they anchor the plan
   usefully NOW. The DESTINATION pipeline symbol names (`PipelineConfig(...)`, `PipelineScope(...)`,
   `run_pipeline`, `seed_*`) DO drift — mark each "match whatever the merged API exports — verify before
   writing," never invent them as if real. Put the two classes of fact in visibly separate lists.

6. **Make implementation Step 1 an explicit GATE — "confirm dependency merged; if not, STOP."** The
   first item of the implementation order is a hard gate: re-run the Step-1 greps on the merged base and
   confirm the destination package/file now exists and the dependency PR is merged. If not, STOP — do
   not begin the migration on a base where the destination is absent. This converts the blocked state
   into a mechanical precondition the implementer checks, not a surprise import error.

7. **Warn that all DESTINATION `file:line` anchors will DRIFT once the dep lands — re-grep them.** Any
   line number on the pipeline side (the new stage file, the new test module, the coordinator) is a
   placeholder; it will change the moment the dependency merges. State explicitly that these anchors
   must be RE-GREPPED at implementation time. The SOURCE-side anchors (the module being absorbed) are
   stable and do not carry this warning — that asymmetry is the point of the split.

8. **RE-HOME an orphaned structural / wiring assertion — do NOT delete it.** If the sweep removes a
   module whose test suite contains a STRUCTURAL assertion (e.g. an agent-wiring or dispatch-shape
   assertion that guards behavior the migration preserves), that assertion must move to the NEW stage's
   test module, not vanish. Deleting it silently drops a real invariant. Flag it in the plan as
   "re-home to `test_stage_<stage>.py`, do not delete."

9. **Add a "Risks / What to verify" section for the assumptions you could NOT verify.** Every claim the
   plan makes that rests on issue prose rather than a `Read` of merged code is a risk. Enumerate them so
   the reviewer and future implementer have a targeted attack surface (see Results & Parameters for the
   concrete four from #1820: CLI-flag→behavior mappings from the issue body, the guessed pipeline symbol
   names, a conditional deletability check, and the coverage-COVERED claim asserted from issue text
   rather than read from `[tool.coverage.run].omit`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Took the issue's acceptance criteria at face value — treated `PipelineConfig` / `PipelineScope` / `stages/plan_review.py` as if they were present on the tree and plannable against directly. | Those symbols and files DO NOT exist on the current tree — `find … | grep pipeline` empty, `grep -rln "PipelineConfig…"` ZERO hits, `ls …/stages/plan_review.py` not-found. They are produced by earlier UNMERGED sub-issues (#1814). | Grep AND `ls` every symbol and path an issue NAMES before planning. An absent target on an issue with an unmerged `Depends on` chain ⇒ the issue is dependency-gated / BLOCKED. |
| 2 | Planned as if the sub-issue were implementable NOW — which would require standing up the whole pipeline package to satisfy the acceptance criteria. | Building the pipeline is the scope of 9 OTHER serialized sub-issues; the epic body explicitly forbids concurrent work ("the loop must never work two of these concurrently"). Implementing now duplicates and conflicts with siblings. | Recognize the blocked state and write a forward-referencing "execute after #N merges" plan, not a fabrication of the missing infrastructure. Honesty-first, still fully specified. |
| 3 | Anchored the WHOLE plan to current `file:line` coordinates, including the destination pipeline side (new stage file, new test module, coordinator). | The DESTINATION-side anchors will DRIFT the instant the dependency merges — every pipeline line number is a placeholder. Only the SOURCE-side (the module being absorbed) anchors are stable while blocked. | Split the anchors: SOURCE-side current-tree facts (the sweep seams, `main()`, `class X`, arg-parser home) are usable NOW and don't drift; DESTINATION-side names are "verify against the merged API — re-grep after the dep lands." |
| 4 | Considered simply DELETING the tests of the absorbed module (including a structural agent-wiring assertion) since the module goes away. | A structural/wiring assertion guards an invariant the migration PRESERVES; deleting it silently drops real test coverage of behavior that still exists in the new stage. | RE-HOME the structural assertion to the new stage's test module (`test_stage_<stage>.py`); never delete an invariant-guarding assertion just because its host module moved. |
| 5 | Asserted "it is a COVERED (non-omit-listed) module" and reasoned about the coverage denominator from the issue text and the epic's omit-trajectory prose, without opening `[tool.coverage.run].omit`. | The coverage-COVERED claim was taken from issue/epic prose, not read from `pyproject.toml`'s frozen omit list — the reasoning could rest on a stale or wrong premise. | Read `[tool.coverage.run].omit` directly before relying on coverage-denominator reasoning; flag any "it is covered/omitted" claim sourced from prose as a risk to verify, not a fact. |

## Results & Parameters

### Verified On

| Repository | Session | Notes |
|------------|---------|-------|
| ProjectHephaestus | Plan for GitHub issue #1820 (item 11 of 14 in the strictly-serialized queue-pipeline epic #1809; dependency chain #1810–#1819 ALL open/unmerged at plan time) | Session 2026-07-04 — forward-referencing "execute after #1814 merges" migration plan authored for absorbing `planner_review_loop` into `pipeline/stages/plan_review.py`. NO code written, NO build/CI run. Sole "Verified On" instance; the skill is generalizable to any serialized-epic absorb-into-unmerged-stage sub-issue. |

### The BLOCKED-state evidence (what proved the issue is dependency-gated)

```bash
# All executed 2026-07-04 against ProjectHephaestus main @ 8143380:
gh issue view <dep> --repo HomericIntelligence/ProjectHephaestus --json state  # #1810–#1819 ⇒ ALL open
find hephaestus/automation -type d | grep -i pipeline        # ⇒ (empty): no pipeline/ package
grep -rln "PipelineConfig\|PipelineScope\|run_pipeline" hephaestus/   # ⇒ ZERO hits
ls hephaestus/automation/pipeline/stages/plan_review.py      # ⇒ No such file or directory
ls tests/unit/automation/pipeline/test_stage_plan_review.py  # ⇒ No such file or directory
```

The issue's own AC wording — "absorbed into `stages/plan_review.py` **in the epic**" — is the tell that
the destination file is produced by an EARLIER unmerged sub-issue (#1814), not by this issue.

### SOURCE-side facts — VERIFIED and STABLE (anchor the plan NOW; do NOT drift while blocked)

- `planner_review_loop` patch-seam sweep surface: **38 hits** across the tree — the full refactor
  surface, usable now.
  - `planner.py:59` — the import site.
  - `tests/unit/automation/test_planner_loop.py` — **34** `patch.object`/mock seams.
  - `tests/unit/automation/test_planner.py:488, 515` — additional seams.
  - `tests/unit/automation/test_phase_agent_wiring.py:86, 91, 209, 212, 288` — includes a STRUCTURAL
    agent-wiring assertion that must be **RE-HOMED** to the new stage's test module, not deleted.
- `main()` at `planner.py:846`.
- `build_automation_parser` at `_review_utils.py:340` (the shared arg parser).
- `class Planner` at `planner.py:271`.
- `PlannerClaudeRunner` at `planner.py:82` — deletability is CONDITIONAL on a post-sweep reference
  check (flagged, not asserted).

### DESTINATION-side names — ASSUMED / GUESSED (verify against the merged API; re-grep after dep lands)

- Every `pipeline/*` symbol in the `main()` sketch is modeled on issue prose, not read from merged code:
  `PipelineConfig(worker_pool_size=…)`, `PipelineScope(stages=(Stage.PLANNING, Stage.PLAN_REVIEW))`,
  `run_pipeline`, `seed_planning_queue`. **Replace with the real merged API before writing.**
- The destination paths `hephaestus/automation/pipeline/stages/plan_review.py` and
  `tests/unit/automation/pipeline/test_stage_plan_review.py` do not exist yet; their eventual line
  anchors will drift on merge and must be re-grepped.

### Risks / What to verify (the most-uncertain assumptions — reviewer's attack surface)

1. **CLI-flag → behavior mappings come from the ISSUE BODY, not a merged seeding API.** `--parallel →
   worker-pool size` and `--force → seeding override that re-plans past `state:plan-go`` are INTENT
   transcribed from the issue, not verified against merged code (the seeding API does not exist yet).
   Re-verify against #1813 / #1814 / #1817 exports at implementation time.
2. **The exact pipeline symbol names in the `main()` sketch are GUESSES** modeled on issue prose
   (`PipelineConfig(worker_pool_size=…)`, `PipelineScope(stages=(…))`, `run_pipeline`,
   `seed_planning_queue`). They MUST be replaced with the real merged API.
3. **Whether `PlannerClaudeRunner` (`planner.py:82`) is deletable depends on a post-sweep reference
   check** — flagged as CONDITIONAL in the plan, not asserted.
4. **"`planner_review_loop.py` is a COVERED (non-omit-listed) module" was asserted from issue text and
   the epic's omit-trajectory prose, NOT by reading `[tool.coverage.run].omit` directly.** A future
   implementer should confirm against `pyproject.toml` before relying on the coverage-denominator
   reasoning.

### Reviewer / Author Pre-Flight Checklist for an Absorb-Into-Unmerged-Stage Plan (copy-paste)

```text
[ ] Grep + ls every symbol and path the AC names; confirmed the destination package/file is ABSENT.
[ ] Confirmed the whole Depends-on chain is genuinely unmerged (gh issue view per dep).
[ ] Read the issue's own wording for the "produced by an earlier sibling / in the epic" tell.
[ ] Plan states BLOCKED up front, with the three empty/not-found command outputs as evidence.
[ ] Plan still ships the FULL executable spec ("execute after #N merges"), not a stub.
[ ] Anchors are SPLIT: SOURCE-side facts line-anchored + marked stable; DESTINATION-side names
    marked "verify against merged API — re-grep after dep lands."
[ ] Implementation Step 1 is a hard GATE: "confirm dependency merged; if not, STOP."
[ ] Every orphaned structural/wiring assertion is flagged to RE-HOME, not delete.
[ ] A "Risks / What to verify" section enumerates every prose-sourced (not Read) assumption.
[ ] Plan is labeled `unverified`; the destination contract is a hypothesis until CI confirms post-merge.
```

### Prescriptive Recommendations for Future Planners

1. **An absent named target on an unmerged-dependency issue means BLOCKED — say so, don't scaffold it.**
   Recognizing the blocked state is the whole skill; the failure mode is hallucinating the missing
   infrastructure to make the AC look satisfiable now.
2. **Split SOURCE anchors from DESTINATION anchors.** The module you are absorbing is real today — anchor
   the plan to its sweep seams, `main()`, class, and arg-parser home. Only the destination side drifts;
   mark it "verify against the merged API."
3. **A forward-referencing plan is still a full plan.** BLOCKED ≠ empty. Ship the complete migration spec
   plus a Step-1 "confirm dep merged, else STOP" gate so it executes mechanically once the dep lands.
4. **Re-home orphaned invariant assertions; never delete them.** A structural/wiring assertion guards
   behavior the migration preserves — it moves to the new stage's test module.
5. **Every prose-sourced claim is a risk, not a fact.** CLI-flag→behavior mappings, guessed symbol names,
   conditional deletability, and coverage-COVERED status all came from issue/epic prose — enumerate them
   in a Risks section and read the real source before relying on any of them.
