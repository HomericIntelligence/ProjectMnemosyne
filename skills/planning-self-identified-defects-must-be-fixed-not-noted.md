---
name: planning-self-identified-defects-must-be-fixed-not-noted
description: "When a planning agent writes a plan that includes both (a) load-bearing content (fabricated file paths, illustrative numeric values, tensor arithmetic, benchmark tables, verification transcripts) AND (b) a self-authored 'Learnings captured during planning' / 'Known Issues' / 'Caveats' addendum that flags the SAME content as defective (wrong arithmetic, guessed paths, unverified assumptions), the plan is a NOGO regardless of how carefully the addendum is worded. The addendum is a CONFESSION, not a FIX. Reviewers observe the confession and reject; executors may skip the addendum and ship the defective content. The self-identification proves the planner could have fixed the defect — declining to do so and shifting the burden to the reader is what causes the NOGO. RULE: if you (the planner) identify a defect in your own plan, you have exactly two acceptable paths — (1) FIX the defect in the plan body before submitting (replace fabricated content with a placeholder token + structural gate that blocks execution until resolved, or delete the section and mark scope as reduced), OR (2) DOWNGRADE the plan verdict to `BLOCKED` and mark the affected section `## TODO: BLOCKED ON <specific missing input>` with no defective content in that section. NEVER emit BOTH a defect note AND the defective content in the plan body; NEVER present a defect note as 'transparency' — transparency is not a substitute for correctness. Use when: (1) you are writing a 'Learnings' / 'Caveats' / 'Known Gaps' section in your own plan, (2) a reviewer asks you to revise a plan they NOGO'd where your prior revision self-flagged defects but did not fix them, (3) you are tempted to add a hedging note ('the executor must overwrite these values before creating the PR') alongside illustrative content in a plan template, (4) you are drafting any plan where you notice you cannot verify something a section claims — decide FIX or BLOCK before writing that section, not after."
category: architecture
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - plan-verdict
  - self-identified-defect
  - addendum-not-fix
  - transparency-not-correctness
  - blocked-vs-fabricated
  - reviewer-nogo
  - fix-or-block
  - meta-rule
---

# Planning: Self-Identified Defects Must Be Fixed Or Blocked — Never Noted

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Prevent the anti-pattern where a planning agent flags its own plan's defects (fabricated content, unverified assumptions, wrong arithmetic) in a "Learnings" or "Known Issues" addendum while leaving the defective content in the plan body, producing a plan that is guaranteed to be NOGO'd by any competent reviewer. |
| **Outcome** | PLAN ONLY — captured on the R1 revision cycle of ProjectOdyssey issue #5527, where the R0 plan included a "Learnings captured during planning" section that identified F1/F2/F3/F4 defects (wrong tensor arithmetic, guessed file paths, illustrative loss values, unverified compat wrapper) but LEFT the defective content in the plan body. The reviewer NOGO'd R0 specifically because the self-identified defects were left in place. R1 replaced the fabricated content with placeholder tokens plus render-script structural gates. This skill documents the meta-rule. |
| **Verification** | unverified |

## When to Use

- You are drafting a "Learnings captured during planning" / "Known Gaps" / "Caveats" / "Assumptions" section in your OWN plan document (not another person's plan; a caveats section calling out load-bearing risks is fine; a caveats section calling out defects YOU introduced and did not fix is not).
- A reviewer has NOGO'd a plan you authored with a list of concrete defects, and your revision plan involves "adding a note explaining the defect" rather than fixing or blocking on it.
- You catch yourself writing prose of the form "these numbers are illustrative; the executor must replace them before creating the PR" — this is exactly the pattern this skill warns against; the illustrative content plus hedge is worse than either alone.
- You are producing a plan where a section makes a claim you cannot verify (an API surface, a file path, a numeric value, a compat script's behavior) — decide `FIX` or `BLOCK` BEFORE writing that section, not after.
- Any planning session where the deliverable is "a plan a reviewer will approve or NOGO" — reviewers evaluate the plan body, not the confession addendum; a self-identified defect is a defect.

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed end-to-end: no reviewer has independently confirmed that plans
> written this way avoid NOGO. The rule was inferred from a single R0→R1 NOGO
> cycle on ProjectOdyssey #5527. Test the rule against your own reviewer's
> feedback loop before treating it as universal.

### Quick Reference

```text
Before submitting a plan, for every section you drafted:
  1. Does the section contain a claim, number, path, or arithmetic result?
     - NO → done.
     - YES → continue.
  2. Can you verify the claim from a source available at plan time?
     - YES → verify it now, edit the section to match ground truth, done.
     - NO  → continue.
  3. Choose FIX or BLOCK:
     - FIX:   replace the unverifiable content with a placeholder token
              (`<<TOKEN>>`) AND add a render-script structural gate that
              fails if the token is unresolved at execute time
              (see planning-pr-body-extract-sibling-artifact-at-runtime).
     - BLOCK: mark the section `## TODO: BLOCKED ON <specific missing input>`
              with NO defective content in it; downgrade plan verdict to
              `BLOCKED | Reason: <what is missing>`.
  4. FORBIDDEN: keep the unverifiable content in the section AND add a
     separate note (in a "Learnings" / "Known Issues" / "Caveats" section
     or as inline prose) saying the content is wrong.

Self-review check before submit:
  grep -inE 'illustrative|example.*overwrite|executor.*replace|these values are|actual values will|placeholder for now' plan.md
  # Any hit → either fix, block, or convert to a `<<TOKEN>>` with a gate.
```

### Detailed Steps

1. **Recognize the trap early.** The temptation to write "here is illustrative content, and here is a note explaining it's illustrative" comes from wanting to LOOK complete without BEING complete. Reviewers see through it; executors miss the note. There is no reader for whom this pattern is a net positive.
2. **Transparency about a defect is not a fix for the defect.** A confession disclosure ("I acknowledge the tensor arithmetic below is wrong") is honesty about a flaw, not a repair of it. Only two things count as repairs: (a) editing the plan body so the flaw is gone, (b) marking the section BLOCKED so the flaw is not shipped downstream.
3. **The addendum-is-not-a-fix rule is content-type-independent.** It applies equally to fabricated file paths (see `planning-pr-open-file-scope-via-git-diff`), illustrative numeric values (see `planning-pr-body-numeric-claims-source-derived`), sibling-artifact placeholders (see `planning-pr-body-extract-sibling-artifact-at-runtime`), and unverified load-bearing assumptions (see `planning-pr-open-load-bearing-assumption-hygiene`). Those skills cover the domain-specific fixes; this skill covers the meta-rule that binds them.
4. **When BLOCK is correct, use it.** A plan whose verdict is `BLOCKED | Reason: cannot verify <X> without <Y>` is a GO signal in disguise: it tells the reviewer exactly what unblocks the plan. A plan that ships defective content with a caveat is a NOGO whose only path forward is another revision cycle.
5. **When FIX is correct, use a structural gate — not a conditional prose instruction.** "If the numbers above differ from reality, the executor must overwrite them" is a conditional prose gate: it fires only if the executor NOTICES the mismatch. Replace with `<<TOKEN>>` + a render-time `grep -q '<<' && exit 1` gate that fires regardless of executor attention (see `planning-pr-body-extract-sibling-artifact-at-runtime` §Structural gates > conditional overrides).
6. **In review**, treat a plan's "Learnings captured during planning" section as a reviewer signal: if it flags defects, the plan should be NOGO'd back for repair even if the reviewer had not independently noticed the defects. The planner's own signal is authoritative.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | ProjectOdyssey #5527 R0 plan: include fabricated tensor arithmetic and guessed file paths in the plan body, add a "Learnings captured during planning" section flagging F1/F2/F3/F4 as self-identified defects, submit the plan for review. | Reviewer NOGO'd on the exact defects the planner self-flagged. The addendum did not shield the plan body; it advertised the plan body's flaws. The revision cycle cost a full R1 round-trip that would have been unnecessary if R0 had either fixed or blocked on the flagged items. | Self-identified defects are grounds for internal revision BEFORE submitting, not for adding a caveat AFTER writing the defective content. Fix or block — never note. |
| Attempt 2 | Same R0 plan: include an "illustrative" loss log block inline with a hedging note ("the executor will overwrite these before creating the PR"). | The hedging note is a conditional gate — it depends on the executor reading and honoring it. Reviewers may skim the hedge and treat the numbers as real; executors may skip the hedge and ship the illustrative values. Silent enforcement is not enforcement. | Replace illustrative content + hedge with a `<<TOKEN>>` placeholder + a render-time structural gate that fails when the token is unresolved. See `planning-pr-body-extract-sibling-artifact-at-runtime` §Structural gates. |
| Attempt 3 | Same R0 plan: assert `just precommit` will pass without `SKIP=mojo-format` based on a claim about a compat wrapper the planner had not read; call out the unread status of the wrapper in the "Learnings" section. | The claim is load-bearing (the plan's PR-open step depends on it); calling out that the claim is unverified while still making the claim is the same anti-pattern in a different domain. Reviewer NOGO'd on the unverified assumption. | Either read the wrapper (verify) or hedge the claim explicitly with a documented fallback (see `planning-pr-open-load-bearing-assumption-hygiene`). Do not both make an unverified claim and disclose it as unverified. |

## Results & Parameters

### Configuration

```yaml
plan-pattern:
  self-identified-defect-policy:
    forbidden:
      - "defective content in plan body + caveat noting defect elsewhere"
      - "illustrative values + hedging note telling executor to replace"
      - "unverified load-bearing claim + disclosure that it is unverified"
    allowed:
      - fix:
          replace: "<<TOKEN>> placeholder"
          gate: "render-time structural gate (grep -q '<<' && exit 1)"
      - block:
          section-marker: "## TODO: BLOCKED ON <specific missing input>"
          plan-verdict: "BLOCKED | Reason: <what is missing>"
    self-review-command: |
      grep -inE 'illustrative|example.*overwrite|executor.*replace|these values are|actual values will|placeholder for now' plan.md
      # Any hit MUST be resolved to FIX or BLOCK before submit.
```

### Expected Output

- Plans submitted to review contain no self-identified defects in the plan body. Any defect the planner identifies is either fixed in place (via placeholder + gate) or the section is marked BLOCKED.
- Reviewers do not need to read a "Learnings captured during planning" section to know whether the plan body is defective — the plan body is either correct or explicitly blocked.
- R0 → R1 revision cycles caused by "planner flagged the defect but did not fix it" drop to zero.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #5527 R0→R1 revision cycle (2026-07-02) — R0 shipped self-flagged defects; R0 was NOGO'd; R1 replaced flagged content with placeholder + gate. Meta-rule extracted from the delta. Not applied end-to-end beyond this cycle. | See ProjectOdyssey issue #5527 planning comments (R0 verdict, R1 verdict). |

## References

- [planning-pr-body-extract-sibling-artifact-at-runtime](planning-pr-body-extract-sibling-artifact-at-runtime.md) — domain-specific fix for sibling-artifact content: use placeholder + structural gate instead of illustrative content + hedge.
- [planning-pr-body-numeric-claims-source-derived](planning-pr-body-numeric-claims-source-derived.md) — domain-specific fix for numeric claims: derive from source at execute time; never fabricate.
- [planning-pr-open-file-scope-via-git-diff](planning-pr-open-file-scope-via-git-diff.md) — domain-specific fix for file-path claims: derive from `git diff --name-only`; never guess.
- [planning-pr-open-load-bearing-assumption-hygiene](planning-pr-open-load-bearing-assumption-hygiene.md) — domain-specific fix for load-bearing assumptions: probe or hedge with fallback; never assert un-probed.
