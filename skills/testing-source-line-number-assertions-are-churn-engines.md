---
name: testing-source-line-number-assertions-are-churn-engines
description: "A test that asserts an exact SOURCE LINE NUMBER (`inspect.getsourcelines(fn)[1] == <literal>`, `fn.__code__.co_firstlineno == N`, or a doc `path:LINE function` reference pinned against the current source line) is a churn engine — REMOVE it and assert symbol presence/resolution instead. Any edit above the function shifts its line number and fails the test with zero behavior change; under concurrent merging the correct line is only knowable at the merge instant, so no PR author (human or agent) can pin it ahead of time. Use when: (1) a doc/regression test fails only because a line number drifted, (2) a PR keeps re-conflicting on a doc that hardcodes `file.py:NNN`, (3) you see `getsourcelines(...)[1]` or `co_firstlineno` compared to a constant in tests, (4) an automation loop keeps force-pushing a wrong-line-number CI fix."
category: testing
date: 2026-07-12
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - line-number-assertion
  - getsourcelines
  - co-firstlineno
  - churn-engine
  - doc-guard
  - regression-test
  - merge-conflict
  - concurrency
  - symbol-presence
  - lint-guard
  - hephaestus
---

# Testing: Source-Line-Number Assertions Are Churn Engines

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-12 |
| **Objective** | Stop a doc/regression test that pinned each documented `path:LINE function` reference to the function's CURRENT source line (`inspect.getsourcelines(fn)[1]`) from manufacturing merge conflicts and stranding a PR across rebase rounds |
| **Outcome** | Successful — removed the test, stripped the volatile `:LINE` from the doc's function references (kept `path function` for navigation), removed the now-unused imports/list, and filed a systemic lint-guard follow-up. Merged into Hephaestus PR #2056 (commit `79f9ebb3`) which then had 0 real CI failures |
| **Verification** | verified-ci |

## When to Use

- A doc or regression test fails **only** because a line number drifted — the referenced code has zero behavior change.
- A PR keeps re-conflicting on a doc that hardcodes `file.py:NNN`, and every rebase round the "correct" number moves again.
- You see `inspect.getsourcelines(x)[1]` (or `x.__code__.co_firstlineno`) compared to a literal constant anywhere under `tests/`.
- An automation loop / CI-fix mesh keeps force-pushing a branch that "fixes" a line number and then fails the exact test it was fixing.
- You are reviewing a new test that pins a documented `path:LINE symbol` reference against the live source line — flag it before it lands.

## Verified Workflow

### Quick Reference

```bash
# 1. Find the offending assertions (the churn engines) across the test suite.
grep -rnE 'getsourcelines\([^)]*\)\[1\]|co_firstlineno' tests/

# 2. REMOVE the test that compares a line number to a literal / to a doc ref.
#    Then de-line the doc: keep `path function` for navigation, drop `:LINE`.
#    e.g.  `automation_loop.py:344 get_impl_resume_feedback_prompt`
#      →    `automation_loop.py get_impl_resume_feedback_prompt`

# 3. Delete the now-unused imports/data the test depended on, or ruff F401/F811 fails.
#    (inspect, re, the PROMPT_REFS list, the imported functions, etc.)
pixi run ruff check tests/ hephaestus/

# 4. Confirm the suite is green WITHOUT the line-number test.
pixi run pytest tests/unit/docs -q
```

### Detailed Steps

1. **Recognize the anti-pattern.** A test that does `inspect.getsourcelines(fn)[1] == <literal>`, `fn.__code__.co_firstlineno == N`, or parses a doc `` `path:LINE function` `` reference and asserts the `LINE` equals the function's current source line is asserting an **implementation detail (line position)**, not behavior. It is a churn engine.

2. **Understand why it is catastrophic under concurrency.** Any edit ABOVE the function — a new import, a comment, a reformat, a reorder — shifts its line number and fails the test with zero behavior change. The "correct" line is only knowable at the INSTANT OF MERGE (it depends on what else lands). No author, human or agent, can pin it ahead of time. Every sibling PR that merges and touches the referenced file moves the function's line (e.g. `get_impl_resume_feedback_prompt`: :338 → :342 → :344), re-failing the test on EVERY open PR carrying the doc. This manufactures merge conflicts out of nothing.

3. **Remove the test — do not chase the value.** Delete the assertion. If line references aid navigation, strip only the volatile `:LINE` from the doc and keep the STABLE `path function` part.

4. **Clean up the dependencies the test pulled in.** Remove the now-unused imports (`inspect`, `re`), any reference list (`PROMPT_REFS`), and the imported functions — otherwise ruff fails on unused imports (F401) or redefinitions.

5. **Prevent recurrence systemically.** File a lint/AST guard that REJECTS any `getsourcelines(...)[1]` or `co_firstlineno` compared to a literal in `tests/`. If line refs are wanted for navigation, GENERATE them via a self-healing pre-commit hook — never ASSERT them (blocking). Assert **symbol presence / resolution** instead: that the function imports and `hasattr(module, "fn")` resolves.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Bump the stale line number | Changed doc `:342` → `:344` to match the current source | The next merge touching the file shifted it again — endless churn | Fixing the value doesn't fix the design; the line number is a moving target under concurrency |
| Let the automation loop re-rebase it | The mesh's ci_fix_orchestrator rebased + force-pushed to "fix CI" | It computed the line wrong and pushed a branch failing the exact test it was fixing, then looped | Never assert a value only knowable at merge instant; never force-push a CI-fix without re-running the guard test locally |
| Keep the test, relax nothing | Treated the red test as a real regression to satisfy | The test guards documentation formatting against an implementation detail (line position), not behavior | Assert symbol presence / that the function RESOLVES (import + hasattr), never a line number |

## Results & Parameters

**The anti-pattern (observed on Hephaestus):**
`tests/unit/docs/test_automation_loop_architecture.py::test_issue_1929_prompt_line_refs_match_source_definitions` asserted every `` `path:LINE function` `` reference in a markdown doc exactly equals `inspect.getsourcelines(fn)[1]` — the function's CURRENT source line.

**Detection command (copy-paste):**

```bash
grep -rnE 'getsourcelines\([^)]*\)\[1\]|co_firstlineno' tests/
```

**The fix (verified-ci, merged in Hephaestus PR #2056, commit `79f9ebb3`):**

- REMOVE the test.
- Strip the volatile `:LINE` from the doc's function references; keep `path function` for navigation.
- Remove the now-unused imports / reference list the test depended on (or ruff fails on unused imports).
- Systemic prevention (filed as Hephaestus #2122): a lint/AST guard rejecting `getsourcelines(...)[1]` / `co_firstlineno` compared to a literal in `tests/`; GENERATE nav line refs via a pre-commit hook (self-healing), never ASSERT them (blocking).

**The durable rule:** documentation line references are for NAVIGATION (generate them, self-healing), not for ASSERTION (blocking). Assert the STABLE invariant — the symbol exists and resolves — never the volatile one (where it currently sits in the file).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #2056, commit `79f9ebb3` (follow-up guard filed as #2122) | Removed `test_issue_1929_prompt_line_refs_match_source_definitions`, de-lined the doc's `path:LINE function` refs to `path function`, dropped the unused `inspect`/`re`/`PROMPT_REFS` deps. PR then had 0 real CI failures after multiple rebase rounds that the line-number test had been re-failing |
