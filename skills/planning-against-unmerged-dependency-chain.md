---
name: planning-against-unmerged-dependency-chain
description: "Write a correct, reviewable implementation plan for an issue whose ENTIRE dependency chain is still OPEN — you are planning against a code surface that does not exist yet because it will be created by unmerged predecessor issues, so you CANNOT read the real code (contrast planning-dependent-issue-unverified-upstream, where the dependency is almost always already merged and readable). Verify the dependency state first (`gh issue view` each predecessor is OPEN; `ls <package-dir>` exits non-zero — the surface is absent), then anchor every claim about the not-yet-written surface on an EXISTING sibling convention in-tree (the module's real env-bool idiom, its CLI-over-env precedence pattern), never a guess. Separate the tiny CODE deliverable (default-flag flip + a re-guard escape-hatch flag + docs) from the MERGE-GATE EVIDENCE (operator/CI runs attached as issue comments), and make a default-flip ADD a re-guard (`--legacy-*` store_false sharing dest + mirrored env var) rather than silently no-op the old mode. Use when: (1) planning an issue whose `Depends on #N` predecessor is still OPEN and its package/module is absent from the tree, (2) writing a feature-flag default-flip / cutover / flag-flip plan, (3) anchoring assumptions about not-yet-written code on an existing sibling convention instead of inventing signatures, (4) separating a code deliverable from merge-gate evidence (dry-run, shadow-diff, scoped live drive, interrupt drill) for a cutover issue, (5) about to cite a predecessor's attribute name / dispatch shape / log-marker string / doc banner wording that you have not read from merged code."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - unmerged-dependency-chain
  - open-predecessor
  - surface-does-not-exist-yet
  - conditional-plan
  - feature-flag-default-flip
  - cutover
  - flag-flip
  - anchor-on-sibling-convention
  - verified-in-tree-anchors
  - assumed-from-predecessor-surface
  - code-deliverable-vs-merge-gate-evidence
  - re-guard-relaxed-argparse-path
  - unverified-api-assumptions
  - verify-before-planning
  - hephaestus
  - loop-runner
  - pipeline-epic-1809
---

# Planning Against an Unmerged Dependency Chain: The Surface Does Not Exist Yet

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Plan ProjectHephaestus issue #1818 — the epic-#1809 pipeline **cutover** (flip the automation loop from the legacy phase/issue-major path to the new queue-based pipeline as the default) — when its ENTIRE dependency chain (#1810–#1817) is still OPEN, so the `hephaestus/automation/pipeline/` package the plan must reference does not exist in the tree yet. |
| **Outcome** | PLAN ONLY — never executed; no code written, no CI run. The durable learning: how to keep such a plan correct and reviewable by verifying the dependency state, anchoring every not-yet-written-surface claim on an existing in-tree sibling convention, and separating the tiny code deliverable from the merge-gate evidence. |
| **Verification** | **unverified** (plan only). The `gh issue view` / `ls` / `grep` inspection commands below WERE run against the live ProjectHephaestus tree and are real; the predecessor package and its APIs were NOT read because they are not merged. |

> **This is the mirror-image of `planning-dependent-issue-unverified-upstream`.** That
> skill's thesis is "the dependency is almost always ALREADY MERGED and readable — read
> it and DELETE the conditional forks." This skill covers the genuinely different case
> where the dependency chain is *confirmed OPEN and unreadable*, so a conditional,
> anchored-on-convention plan is the correct output, not a trap. Verify which world you
> are in FIRST (see step 1) before choosing.

## When to Use

- Planning an issue whose `Depends on #N` predecessor(s) are still **OPEN**, and the
  package/module the plan must touch is **absent** from the current tree.
- Writing a **feature-flag default-flip / cutover / flag-flip** plan where the flag and
  its dispatch fork are created by an unmerged predecessor.
- You are about to write a file path, attribute name, function signature, dispatch shape,
  log-marker string, or doc-banner wording that belongs to **not-yet-written** predecessor
  code — anchor it on an existing sibling instead of guessing.
- The issue's entry criteria are **operator/CI evidence** (dry-run, shadow diff, scoped
  live drive, interrupt drill) rather than code — you must separate them from the code
  deliverable.
- Skip when the dependency is already merged: use
  `planning-dependent-issue-unverified-upstream` (read it, delete the forks) instead.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis
> until CI confirms. This is a PLAN that was NEVER executed — no code was written, no CI
> ran. The `gh` / `ls` / `grep` inspection commands below WERE genuinely run against the
> live ProjectHephaestus tree; the predecessor's package and APIs were NOT read because
> they are not merged. The step-by-step is titled **Proposed Workflow** for that reason —
> the `## Verified Workflow` heading is retained only to satisfy the flat skill schema
> (`scripts/validate_plugins.py` hard-requires the literal `## Verified Workflow`).

### Quick Reference

```bash
# 1. CONFIRM THE DEPENDENCY IS ACTUALLY OPEN — do not assume. If any predecessor
#    is merged, STOP and use planning-dependent-issue-unverified-upstream instead.
for n in {1810..1817}; do
  gh issue view "$n" --repo HomericIntelligence/ProjectHephaestus --json state -q .state
done                                            # all -> OPEN

# 2. CONFIRM THE SURFACE IS ABSENT — a non-zero exit proves the predecessor's
#    package has not landed, so you CANNOT read the real code.
ls hephaestus/automation/pipeline/              # exit 2: No such file or directory

# 3. ANCHOR ON AN EXISTING SIBLING CONVENTION, not a guess. Grep the module for
#    the idioms the predecessor will most likely reuse, and cite the file:line.
grep -nE 'os\.environ\.get\("[A-Z_]+", "1"\) == "0"' hephaestus/automation/loop_runner.py
#   -> env-bool idiom, e.g. loop_runner.py:1335 (HEPHAESTUS_RATE_GUARD default-on)
grep -nE 'def _build_parser|def run_loop|def main\(' hephaestus/automation/loop_runner.py
#   -> VERIFIED-IN-TREE anchors: _build_parser():451, run_loop():1464, main():1633
sed -n '583,592p' hephaestus/automation/loop_runner.py
#   -> --phase-timeout / HEPH_PHASE_TIMEOUT CLI-over-env precedence pattern to mirror

# 4. LABEL every anchor as one of two kinds in the plan:
#    - "verified-in-current-tree anchor"  (grepped/read NOW: _build_parser()@451, main()@1633)
#    - "assumed-from-predecessor surface" (INFERRED from the epic: args.pipeline, coordinator.py)
```

### Proposed Workflow

1. **Verify the dependency state — do not assume it.** When an issue says
   `Depends on #N`, confirm #N's merge state on `origin/main` FIRST. Run
   `gh issue view <predecessor>` for every one in the chain (#1810–#1817 were all
   **OPEN**) and `ls <the-package-dir>` (`hephaestus/automation/pipeline/` exited 2 —
   the package is absent). Only once you have proven the surface does not exist yet do
   you write a single file path. If any predecessor turns out to be merged, stop and
   switch to `planning-dependent-issue-unverified-upstream` (read the real code, delete
   the forks). The plan that follows must be **explicitly conditional** and target the
   surface the predecessor *will* create, naming the exact chokepoint the current issue
   mutates. For #1818 those are the **verified-in-current-tree anchors** `_build_parser()`
   at `loop_runner.py:451` and the dispatch fork inside `run_loop()` at
   `loop_runner.py:1464`, with `main()` at `loop_runner.py:1633` — cite these as
   grepped-now facts, distinct from the **assumed-from-predecessor surface** (the pipeline
   package the flag will route into).

2. **Ground every claim about the predecessor's surface in an EXISTING convention, not a
   guess.** You cannot read not-yet-written code, but you CAN anchor on a sibling pattern
   that already exists in the same module, so the plan is right even before the dependency
   lands. For the `--pipeline` / `HEPH_PIPELINE` default-flip, reuse the module's real
   env-bool idiom `os.environ.get("<VAR>", "1") == "0"` (present at `loop_runner.py:1335`
   for `HEPHAESTUS_RATE_GUARD`) and the CLI-over-env precedence pattern already used by
   `--phase-timeout` / `HEPH_PHASE_TIMEOUT` (`loop_runner.py:583-590`). Anchoring on
   these makes the flag's shape a near-certainty rather than an invention.

3. **Separate the CODE deliverable from the MERGE-GATE evidence.** A cutover / flag-flip
   issue's entry criteria are usually operator/CI **evidence**, not code. Issue #1818's
   five criteria — a two-layer check, a dry-run, a shadow diff on 3 distinct-state issues,
   a scoped live drive through merge, and an interrupt drill — are runs whose logs are
   attached as **issue comments**. The plan must call these out as a **gate** and list the
   exact commands, but keep the code section tiny: default flip + escape-hatch flag +
   docs. Do not smuggle evidence-gathering into the code diff.

4. **A default-flip must ADD a re-guard, not silently no-op the old mode.** Flipping
   `--pipeline` ON requires adding `--legacy-loop` (`store_false`, sharing the same
   argparse `dest`) so the legacy path stays reachable and is smoke-tested, plus a
   mirrored env escape hatch `HEPH_PIPELINE=0`. This applies the
   `architecture-executable-convention-guard-pattern` lesson "re-guard the relaxed
   argparse path": relaxing a required behaviour for a new default without re-guarding the
   old one lets the removed mode silently disappear. See also
   `automation-loop-phase-major-to-issue-major` for the loop topology this pipeline
   replaces.

5. **List the unverified assumptions in a dedicated risk section.** Every claim about the
   predecessor's surface that you could not read is a load-bearing guess — the reviewer
   must be able to target them. Put them in the Failed Attempts table below framed as
   "what could fail," and add an assumption→file/line re-plan map so that once the
   predecessor merges, verification is mechanical: grep the real `args.<attr>`, read the
   real coordinator log markers, diff the real doc banner wording, and revise every
   assumption that was wrong.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Name the pipeline entry package | Assumed #1817 creates `hephaestus/automation/pipeline/coordinator.py` and exposes the flag as `dest="pipeline"` read via `args.pipeline` in `main()` | INFERRED from the epic #1809 body, NOT verified against merged code — the actual attribute name / module path / dispatch shape could differ, which would invalidate the "no change to the dispatch fork" claim | Any predecessor attribute name / module path / dispatch shape is a guess until read; re-grep `args.<attr>` and the real dispatch site the moment #1817 merges, before touching the flip |
| Reuse the arch doc's removable banner | Assumed #1810 creates `docs/AUTOMATION_LOOP_ARCHITECTURE.md` with a removable "pre-implementation banner" whose exact wording is `> **Status: pre-implementation**` | The banner wording is guessed, not read from the merged doc; the real marker string may differ, so a mechanical `sed`/grep removal in the cutover could miss it | Never hardcode a predecessor doc's exact marker string; grep the merged doc for the actual banner and match on that, not on invented wording |
| Match the crash-runbook log markers | Assumed the coordinator emits log markers like `[coordinator] stage {stage} raised` for the interrupt-drill / crash-runbook criterion | The marker strings are invented, not read from code — if #1817 emits different markers the interrupt-drill assertions and runbook grep will silently match nothing | Log-marker strings are code, not documentation; read them from the merged coordinator before asserting on them, and anchor on the line PREFIX not a free substring |
| Assume no new `state:*` labels | Assumed the pipeline introduces no new `state:*` labels, per the existing `index.md:33-38` label table | Assumed from the current label vocabulary, not confirmed against the merged pipeline; a new queue/coordinator stage could add a label the plan does not account for | Re-list the `state:*` label vocabulary against the merged pipeline; a cutover that ignores a newly-introduced state label can strand issues |
| Treat entry criteria as code | (Considered) folding the two-layer check / dry-run / shadow-diff / live-drive / interrupt-drill into the code diff | Those are operator/CI EVIDENCE attached as issue comments, not code — folding them in bloats the diff and confuses the reviewer about what actually ships | Keep the code section tiny (flip + re-guard + docs); route the five criteria to a merge-gate evidence checklist, not the diff |

Every row above is a MOST-UNCERTAIN, load-bearing assumption this PLAN rests on. None was
verified against merged code — they are recorded as "what could fail" so a reviewer can
target them and so re-planning after the predecessor merges is mechanical (grep the real
`args.<attr>`, read the real coordinator log markers, diff the real doc banner wording,
re-list the real `state:*` labels, and revise every assumption that was wrong).

## Results & Parameters

**Deliverable class:** PLAN ONLY (code-free). No files written, no tests run, no CI.
**Verification level:** `unverified`.

**Verified-in-current-tree anchors** (grepped/read against the live ProjectHephaestus tree
on 2026-07-04):

| Anchor | Location | How verified |
| ------ | -------- | ------------ |
| `_build_parser()` | `hephaestus/automation/loop_runner.py:451` | `grep -nE 'def _build_parser'` |
| dispatch fork host `run_loop()` | `hephaestus/automation/loop_runner.py:1464` | `grep -nE 'def run_loop'` |
| `main()` | `hephaestus/automation/loop_runner.py:1633` | `grep -nE 'def main\('` |
| env-bool idiom to reuse | `hephaestus/automation/loop_runner.py:1335` (`HEPHAESTUS_RATE_GUARD` default-on) | `sed -n` read |
| CLI-over-env precedence to mirror | `hephaestus/automation/loop_runner.py:583-590` (`--phase-timeout` / `HEPH_PHASE_TIMEOUT`) | `sed -n` read |
| pipeline package ABSENT | `ls hephaestus/automation/pipeline/` → exit 2 | proves predecessor unmerged |

**Assumed-from-predecessor surface** (INFERRED, unread — see Failed Attempts):
`args.pipeline` / `dest="pipeline"`, `hephaestus/automation/pipeline/coordinator.py`,
`docs/AUTOMATION_LOOP_ARCHITECTURE.md` banner wording, coordinator log markers, the
`state:*` label set.

**Code deliverable (tiny):** default-flip `--pipeline` ON + `--legacy-loop`
(`store_false`, shared `dest`) re-guard + mirrored `HEPH_PIPELINE=0` env escape hatch +
doc update removing the pre-implementation banner.

**Merge-gate evidence (not code, attached as issue comments):** two-layer check, dry-run,
shadow diff on 3 distinct-state issues, scoped live drive through merge, interrupt drill.

**Related learnings (cross-references):**
- `planning-dependent-issue-unverified-upstream` — the mirror case (dependency already
  merged → read it, delete forks). Choose that skill when step 1 finds a merged predecessor.
- `planning-unmerged-parent-contract-compile-smoke-gate` — sibling case where an unmerged
  parent has an APPROVED PLAN to consume (contract + compile-smoke gate); this skill covers
  the case where there is no approved plan and you must anchor on in-tree sibling conventions.
- `automation-loop-phase-major-to-issue-major` — the loop topology the pipeline replaces.
- `architecture-executable-convention-guard-pattern` — the "re-guard the relaxed argparse
  path" lesson applied in step 4.
