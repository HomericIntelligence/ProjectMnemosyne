---
name: testing-non-vacuous-regression-guards-behavior-unchanged
description: "Discipline for proving that 'regression guard' tests added alongside a BEHAVIOR-UNCHANGED fix (documents an existing fallback, adds a docstring `Raises:`, clarifies a contract) are NON-VACUOUS — i.e. that each test would actually FAIL if the guarded branch were removed or altered. Such tests are NOT RED-GREEN TDD: they encode the CURRENT behavior and can pass vacuously, so a reviewer will correctly NOGO a plan that claims 'no behavior change, tests encode the contract' without naming the mutation each test catches. Teaches: (1) a per-test mutation table (Test | Asserts | Mutation it catches); (2) pairing each positive substring assertion with a DISCRIMINATING negative assertion (e.g. `assert '{' not in result`) that excludes the sibling code paths; (3) exploiting a real sibling asymmetry (one function case-SENSITIVE, the other case-INSENSITIVE) as a deliberate discriminator probe; (4) a cheap manual non-vacuity spot-check (temporarily apply the mutation, confirm the test fails, revert). Use when: (1) the fix changes NO logic but adds/clarifies docs and you add tests to 'guard' the now-documented behavior; (2) you wrote a docstring-only / doc-only fix whose regression tests could pass vacuously; (3) a reviewer NOGOs a plan for an un-proven 'tests encode the contract' claim; (4) you assert only a positive substring (`'name: hephaestus' in result`) and need to make it non-vacuous; (5) you are tempted to propose a 'wording alignment' doc edit to text that already states the contract."
category: testing
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - vacuous-test
  - regression-guard
  - negative-assertion
  - docstring-only
  - mutation-testing
  - sibling-asymmetry
  - planning
  - hephaestus
---

# Non-Vacuous Regression Guards for Behavior-Unchanged (Docstring/Doc-Only) Fixes

> **Warning:** This workflow has not been validated end-to-end. Treat as a
> hypothesis until CI confirms. It is a PLANNING-discipline learning derived
> from a plan that was revised after a reviewer NOGO but never executed — no
> tests were run, no mutations applied, no CI observed.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-27 |
| **Objective** | Turn a reviewer NOGO into a GO for a plan whose fix changes NO logic (documents an existing `format_type` fallback in `format_output`/`format_system_info`) but adds regression tests that could pass VACUOUSLY. |
| **Outcome** | Plan revised NOGO → (revised); the discipline below is what the reviewer demanded. NOT executed — the non-vacuity is argued, not demonstrated. |
| **Verification** | unverified (planning learning; no tests run, no mutations applied, no CI) |
| **History** | n/a (initial version) |

The triggering case (ProjectHephaestus issue #1509): document — not raise —
the silent `format_type` fallback in `format_output` (`hephaestus/cli/utils.py`)
and `format_system_info` (`hephaestus/system/info.py`). Because the fix only
adds a docstring `Raises:`/contract note and changes no branch, any "regression
guard" test simply re-encodes the behavior that already ships. The reviewer's
MAJOR finding was a **vacuous-test risk**: a test that asserts current behavior
without proving it would fail under a plausible mutation gates nothing.

## When to Use

- A fix changes NO logic — it documents an existing fallback, adds a docstring
  `Raises:` section, or clarifies a contract — and you add tests to "guard" the
  now-documented behavior.
- You wrote a docstring-only / doc-only fix whose regression tests could pass
  **vacuously** (they encode current behavior, so they are green from the start).
- A reviewer NOGOs a plan for claiming "no behavior change, so the tests encode
  the contract" **without** naming the mutation each test would catch.
- Your test asserts only a positive substring (e.g. `"name: hephaestus" in result`)
  and you need to make it discriminate the intended code path from siblings.
- You are tempted to propose a "wording alignment" doc edit to text that ALREADY
  states the contract (pure churn — a reviewer will flag it).

## Verified Workflow

> **Warning:** Proposed, not verified. Derived from a revised plan that was
> never run; the non-vacuity claims below are argued, not demonstrated.

### Quick Reference

```text
For a behavior-UNCHANGED (docstring/doc-only) fix whose tests "guard" the contract:

1. MUTATION TABLE — for EACH new test, name the exact code mutation it would FAIL
   against. Put it in the plan: | Test | Asserts | Mutation it catches |.
   e.g. "if the else text-fallback became `raise ValueError`, bogus input → raises → test fails"
        "if the `== "json"` guard became `.lower() == "json"`, input `"JSON"` → emits JSON → test fails"

2. POSITIVE + NEGATIVE PAIR — never assert only a positive substring. Pair it with
   a DISCRIMINATING negative assertion that EXCLUDES the sibling paths:
        assert "name: hephaestus" in result   # weak alone (text AND table contain it)
        assert "{" not in result              # pins the TEXT branch, excludes json AND table

3. SIBLING-ASYMMETRY PROBE — find a real asymmetry between sibling functions and
   use it as a discriminator. Here format_output is case-SENSITIVE
   (`format_type == "json"`) while format_system_info is case-INSENSITIVE
   (`.lower() == "json"`). Feed `"JSON"` (wrong case) and assert it STILL falls
   back to text — fails if anyone "helpfully" switches format_output to `.lower()`.

4. CHEAP NON-VACUITY SPOT-CHECK (optional, NOT committed) — temporarily apply the
   mutation (change `== "json"` to `.lower() == "json"`), run the test, confirm it
   FAILS, revert. Lightweight alternative to a full mutmut run; gives the reviewer
   concrete evidence.

5. DOC-EDIT DELTA CHECK — before proposing any doc/wording edit, READ the current
   text. If it ALREADY states the contract, DROP the edit (no-op churn → NOGO).
```

### Detailed Steps

1. **Recognise the trap.** A behavior-unchanged fix produces tests that are GREEN
   from the first run. That is the opposite of RED-GREEN TDD, where a new test
   first fails. Green-from-the-start tests can be vacuous: they may assert
   something that is true regardless of the branch you intend to guard.

2. **Build the mutation table.** For every new test, write down the smallest
   realistic code change that would break it. If you cannot name such a mutation,
   the test guards nothing — delete it or strengthen its assertions. Ship the
   table IN THE PLAN so the reviewer can check each row.

3. **Add a discriminating negative assertion.** A positive substring is satisfied
   by multiple renderings (text, a mis-rendered table, etc.). Add a negative
   assertion that is true ONLY for the path you mean to pin. For the text
   fallback, `assert "{" not in result` excludes the JSON rendering AND a
   `{...}`-style table dump. The positive+negative PAIR is what makes the test
   non-vacuous.

4. **Exploit a sibling asymmetry as a probe.** When two sibling functions handle
   the same selector differently, that difference is a free discriminator. Feed
   the input that only one of them treats specially (here `"JSON"` — accepted by
   the case-insensitive sibling, rejected by the case-sensitive one) and assert
   the case-sensitive function STILL falls back. The test now fails the moment
   someone homogenises the two. Hunt for these asymmetries — they are gold for
   non-vacuous assertions.

5. **Offer the manual spot-check.** Apply one mutation by hand, run the single
   test, confirm RED, revert. Do NOT commit the mutation. This is the cheap
   stand-in for a mutation-testing tool and the most persuasive evidence you can
   hand a reviewer.

6. **Verify there is a real doc delta.** Read the existing docstring(s). Only the
   docstring with a genuine gap needs editing. Do not propose "consistency"/
   "wording alignment" edits to text that already documents the contract — that
   is materially identical churn and a reviewer will (correctly) flag it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Positive-only assertion | Guarded the text fallback with only `assert "name: hephaestus" in result` | Vacuous: the substring also appears in a (mis-rendered) table and is not unique to the text branch, so the test passes regardless of which path ran | Pair every positive substring with a DISCRIMINATING negative assertion (`assert "{" not in result`) that excludes the sibling paths |
| No-op "wording alignment" doc edit | Proposed editing `info.py:237-239` for "cross-function consistency" with `format_output` | The `format_system_info` docstring ALREADY documented the fallback — the edit was materially identical churn; reviewer flagged it as a redundant no-op | READ the current text first; if it already states the contract, DROP the edit. The real gap was ONLY `format_output`'s docstring |
| "No behavior change so tests encode the contract" | Asserted the regression tests guard the documented behavior without naming what each would catch | Behavior-unchanged tests are green from the start and can pass vacuously; an un-proven "they encode the contract" claim gates nothing → reviewer NOGO | For EACH test, name the exact mutation it would FAIL against, in a Test \| Asserts \| Mutation table, so the reviewer can verify discrimination |

## Results & Parameters

### Per-test mutation table (the artifact that turns NOGO → GO)

Ship this table IN THE PLAN. Each row proves the test discriminates a real
mutation rather than restating current behavior.

| Test | Asserts | Mutation it catches |
|------|---------|---------------------|
| Unknown `format_type` falls back to text | `"name: hephaestus" in result` AND `"{" not in result` | If the `else` text-fallback branch were replaced with `raise ValueError`, the bogus-input case raises → test fails |
| Case-sensitive `format_output` rejects `"JSON"` | Output is the TEXT rendering, NOT json (`"{" not in result`) | If the `== "json"` guard became `.lower() == "json"`, input `"JSON"` would emit JSON → `"{" not in result` fails |
| `format_output` emits JSON only for exact `"json"` | `"{" in result` for `format_type="json"` | If the guard were removed/inverted, JSON path would not fire → assertion fails |

### Positive + negative assertion pattern

```python
# WEAK — vacuous: "name: hephaestus" appears in text AND in a mis-rendered table.
result = format_output(data, format_type="bogus")
assert "name: hephaestus" in result

# STRONG — positive pins the value, negative EXCLUDES the json (and {...} table) path.
result = format_output(data, format_type="bogus")
assert "name: hephaestus" in result   # positive: value is present
assert "{" not in result              # negative: NOT the json/{...} rendering
```

### Sibling-asymmetry discriminator probe

```python
# format_output is case-SENSITIVE: hephaestus/cli/utils.py  (`format_type == "json"`)
# format_system_info is case-INSENSITIVE: hephaestus/system/info.py (`.lower() == "json"`)
# Feeding the WRONG case to the case-sensitive one is a deliberate probe:
result = format_output(data, format_type="JSON")  # wrong case
assert "{" not in result   # MUST still fall back to text;
                           # fails if format_output is "helpfully" switched to .lower()
```

### Cheap manual non-vacuity spot-check (NOT committed)

```bash
# 1. Temporarily mutate the guard:
#    in hephaestus/cli/utils.py change  `== "json"`  ->  `.lower() == "json"`
# 2. Run only the probe test; confirm it now FAILS (RED):
pixi run pytest tests/unit/cli/test_utils.py -k "json_case" -q
# 3. Revert the mutation. Do NOT commit it.
```

### Residual risks the reviewer should still watch

- The mutation table is a **reasoning aid, not executed proof.** The plan has not
  RUN the tests or applied the mutations; the non-vacuity claims are argued, not
  demonstrated, until implementation runs them (ideally with the optional
  spot-check).
- `assert "{" not in result` assumes the TEXT rendering of the chosen dict never
  contains a literal `{`. It is safe for `{"name": "hephaestus", "version":
  "0.3.0"}` (plain-string values), but the assertion is **data-dependent** — a
  dict whose VALUE contained `{` would break the discriminator. Choose test data
  so the negative assertion is sound.
- The case-sensitivity asymmetry (`format_output` `== "json"` vs
  `format_system_info` `.lower() == "json"`) was reviewer-verified in this
  session, but **line numbers drift.** Implementation MUST re-confirm the guard
  is still `== "json"` (case-sensitive) before relying on the `"JSON"` probe.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1509 re-plan (NOGO → revised) — document the silent `format_type` fallback in `format_output`/`format_system_info` | Planning-only; not executed. Distinct from PR #2853 (which captured the separate "Arm B: document the fallback" learning in `error-message-consistency-optional-dependency-pola` v2.1.0). |
