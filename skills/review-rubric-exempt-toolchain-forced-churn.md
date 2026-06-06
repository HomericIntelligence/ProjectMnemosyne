---
name: review-rubric-exempt-toolchain-forced-churn
description: "Use when: (1) an automated PR-review agent flags lint/formatter/pre-commit-driven incidental changes as scope creep or YAGNI, (2) designing or fixing a code-review rubric's scope/YAGNI dimension, (3) a reviewer demands removal of whitespace/import-sort/mypy-annotation churn that the toolchain forced, (4) distinguishing toolchain-forced churn from author-chosen opportunistic work in review prompts"
category: tooling
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [pr-review, rubric, yagni, scope-creep, pre-commit, lint, automation, review-agent]
---

# Exempting Toolchain-Forced Churn from PR-Review Scope/YAGNI Rubrics

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Stop automated PR-review rubrics from flagging linter/formatter/pre-commit-forced incidental churn as scope creep, while still catching author-chosen opportunistic work |
| **Outcome** | Added an intent-based carve-out to all three composable scope/YAGNI rubric blocks; TDD tests assert both the carve-out and retained scope-creep detection |
| **Verification** | verified-ci (shipped in HomericIntelligence/ProjectHephaestus#1019, closes #1017; CI green) |

## When to Use

- An automated PR-review agent flags lint/formatter/pre-commit-driven incidental changes as scope creep or YAGNI
- You are designing or fixing a code-review rubric's scope or YAGNI dimension
- A reviewer (human or agent) demands removal of whitespace, import-sort, trailing-newline, or mypy-annotation churn that the toolchain *forced* in order to land a change
- You need to distinguish toolchain-forced churn from author-chosen opportunistic work in review prompts
- A scope rule is duplicated across multiple per-stage rubrics and they disagree after a partial fix

## Verified Workflow

### Quick Reference

```bash
# 1. Find every place the scope/YAGNI rule lives (it is usually duplicated)
grep -nE 'scope creep|opportunistic|changed-lines|formatting churn|YAGNI' \
    hephaestus/automation/prompts/_strict_rubric.py

# 2. The three composable blocks that must ALL agree:
#    _SEVEN_PRINCIPLES_DIMENSIONS   -> P2/YAGNI block (shared: plan, plan-loop, impl-loop, PR)
#    _PR_STRICT_RUBRIC_DIMENSIONS   -> D2 "changed-lines-only"
#    _IMPL_LOOP_STRICT_RUBRIC       -> dimension 6 "Diff scope"

# 3. RED first: add tests asserting carve-out present AND scope-creep detection retained
grep -nE 'pre-commit|toolchain|opportunistic|dependency bumps' tests/unit/automation/test_prompts.py

# 4. Add the SAME intent-based carve-out to all three blocks (anchor phrases below)

# 5. GREEN: rubric tests pass
pixi run pytest tests/unit/automation/test_prompts.py -v
```

### Detailed Steps

1. **Locate every copy of the scope rule.** A scope/YAGNI rule that feeds multiple
   per-stage rubrics is almost always duplicated. In ProjectHephaestus it lived in
   THREE blocks inside `hephaestus/automation/prompts/_strict_rubric.py`:
   - `_SEVEN_PRINCIPLES_DIMENSIONS` — the P2/YAGNI block, shared by the plan,
     plan-loop, impl-loop, and PR rubrics.
   - `_PR_STRICT_RUBRIC_DIMENSIONS` — D2 "changed-lines-only".
   - `_IMPL_LOOP_STRICT_RUBRIC` — dimension 6 "Diff scope" (the most explicit; it
     literally said to flag "formatting churn in untouched files").

   The original P2/YAGNI text was: *"Every diff hunk must map to a stated requirement
   in THIS issue. Flag scope creep, opportunistic refactors..."* — with NO carve-out.

2. **Write the carve-out as an intent test, not a size test.** The dividing line is
   *who chose the change*, not how big it is:
   - **ACCEPTABLE (do NOT flag, stay silent):** toolchain-FORCED incidental churn —
     formatter/whitespace normalization, import sorting, trailing-newline fixes, type
     annotations required to pass mypy, and other lint/pre-commit auto-fixes — on
     files the change already touches.
   - **STILL FLAG:** author-CHOSEN work — opportunistic refactors, unrelated rewrites,
     "while we're here" features, dependency bumps that weren't asked for, new config
     knobs without a consumer.
   - **Key principle:** *"The test is intent, not size: churn the toolchain requires
     is fine; churn the author chose is a finding."*

3. **Apply the carve-out to all three blocks so they agree.** Fixing only the shared
   `_SEVEN_PRINCIPLES` P2 block is insufficient: the per-stage `_IMPL_LOOP_STRICT_RUBRIC`
   and `_PR_STRICT_RUBRIC_DIMENSIONS` copies still said "flag formatting churn", and a
   per-stage copy overrides the shared carve-out for that stage. Every block that
   restates the scope rule must restate the carve-out.

4. **Use stable anchor phrases.** Write the carve-out around robust substrings —
   `pre-commit`, `toolchain`, `opportunistic`, `dependency bumps that weren't asked for`
   — so tests assert on durable anchors rather than brittle full sentences that break
   on minor rewording.

5. **TDD both directions.** Add tests in `tests/unit/automation/test_prompts.py` that
   assert BOTH:
   - the carve-out language is present (toolchain/pre-commit churn is exempt), AND
   - genuine scope-creep detection is retained (e.g. "opportunistic",
     "dependency bumps that weren't asked for").

   Asserting both prevents over-correcting into a rubric so permissive it flags nothing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Flag every diff hunk not in the issue | P2/YAGNI rule said "Every diff hunk must map to a stated requirement in THIS issue. Flag scope creep, opportunistic refactors..." with no exception | Punished lint-forced churn; the agent generated false-positive review comments demanding removal of CI-required edits (e.g. PR #1015 inline comment r3366637812 flagged a whitespace-normalization edit as P2/YAGNI scope creep) | Carve out toolchain-forced incidental churn explicitly; an unbounded "flag everything" rule fights the linter |
| Fix only the shared `_SEVEN_PRINCIPLES` P2 block | Added the carve-out to the shared constant only | The impl-loop dimension 6 and PR D2 per-stage copies still said "flag formatting churn", so the carve-out didn't fully take for those stages | A per-stage copy overrides the shared rule; update all three blocks so they agree |
| Test on full-sentence rubric text | Assert exact carve-out sentence in tests | Minor rewording of the prompt broke the test even when behavior was correct | Assert on stable anchor substrings (pre-commit, toolchain, opportunistic), not whole sentences |
| Soften the rule wholesale | Loosen scope language to stop the false positive | Risked a rubric that flags nothing — opportunistic refactors and unasked dependency bumps would slip through | Distinguish intent (toolchain-forced vs author-chosen); keep scope-creep detection and test for it |

## Results & Parameters

### Applied to issue #1017 (PR #1019)

**Files changed**:
- `hephaestus/automation/prompts/_strict_rubric.py` — carve-out added to all three
  scope/YAGNI blocks:
  - `_SEVEN_PRINCIPLES_DIMENSIONS` (P2/YAGNI block)
  - `_PR_STRICT_RUBRIC_DIMENSIONS` (D2 "changed-lines-only")
  - `_IMPL_LOOP_STRICT_RUBRIC` (dimension 6 "Diff scope")
- `tests/unit/automation/test_prompts.py` — tests asserting the carve-out is present
  AND scope-creep detection is retained.

**The carve-out wording**:
- ACCEPTABLE (do NOT flag, stay silent): toolchain-FORCED incidental churn —
  formatter/whitespace normalization, import sorting, trailing-newline fixes, type
  annotations required to pass mypy, lint/pre-commit auto-fixes — on files the change
  already touches.
- STILL FLAG: author-CHOSEN work — opportunistic refactors, unrelated rewrites,
  "while we're here" features, dependency bumps that weren't asked for, new config
  knobs without a consumer.
- Key principle: *"The test is intent, not size: churn the toolchain requires is fine;
  churn the author chose is a finding."*

### Key Insights

1. When a shared rubric constant feeds multiple per-stage rubrics, fix the shared block
   AND each stage's own scope dimension so they agree — otherwise the per-stage copy
   overrides the shared carve-out.
2. Use STABLE ANCHOR phrases (`pre-commit`, `toolchain`, `opportunistic`) in rubric text
   so tests assert on robust substrings, not brittle full sentences.
3. TDD both directions: assert the carve-out language is present AND genuine
   scope-creep detection (e.g. "dependency bumps that weren't asked for",
   "opportunistic") is retained — this prevents over-correcting into a rubric that
   flags nothing.

### Verification Commands

```bash
# Carve-out anchors present in all three blocks
grep -cE 'pre-commit|toolchain' hephaestus/automation/prompts/_strict_rubric.py
# >= 3 (one per block)

# Scope-creep detection retained
grep -nE "opportunistic|dependency bumps that weren't asked for" \
    hephaestus/automation/prompts/_strict_rubric.py

# Rubric tests pass (RED -> GREEN)
pixi run pytest tests/unit/automation/test_prompts.py -v
```

### References

- ProjectHephaestus issue #1017 (problem report)
- ProjectHephaestus PR #1019 (fix; closes #1017; CI green)
- ProjectHephaestus PR #1015 inline comment r3366637812 (original false-positive example)
