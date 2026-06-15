---
name: planning-frozen-registry-guard-co-update
description: "When a planned change removes or edits an entry in a list/registry/manifest that is ENFORCED by a frozen 'exact-set' guard test, the edit silently breaks the guard unless the guard's hard-coded copy is co-updated — or you prove the edit is unnecessary via sibling precedent and drop it. Use when: (1) planning to remove/add/edit an entry in a coverage omit-allowlist, `__all__`, a plugin/skill registry, or any hard-coded enumerated set, (2) an issue suggests a side cleanup like 'also de-list X', (3) you are about to edit pyproject.toml/setup.cfg/a config list and are unsure whether a test pins its contents, (4) adding tests to a coverage-omitted module, (5) a reviewer or CI surfaces a `*_frozen`/exact-set assertion failure after a list edit."
category: testing
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - testing
  - frozen-test
  - allowlist
  - registry
  - manifest
  - coverage-omit
  - pyproject
  - guard-test
  - sibling-precedent
  - dry
  - orthogonality
---

# Planning Changes Behind a Frozen Registry Guard: Co-Update or Drop the Edit

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Plan a change that removes/edits an entry in a list/registry/manifest WITHOUT silently breaking a separate frozen "exact-set" guard test that pins that list's contents |
| **Outcome** | Re-plan converged after a NOGO by DROPPING the de-listing step entirely and proving it was unnecessary via sibling precedent; plan not executed |
| **Verification** | unverified |

A first implementation plan for ProjectHephaestus issue #1362 (add unit tests for two
untested methods of `PostMergeProcessor`) proposed conditionally REMOVING
`hephaestus/automation/post_merge_processor.py` from the coverage omit-allowlist in
`pyproject.toml`. A reviewer flagged a MAJOR gap: a separate frozen guard test
`tests/unit/validation/test_omit_allowlist.py::test_omit_allowlist_frozen` asserts
`actual_set == expected_set` over the EXACT omit list, where `expected_set` is a
hard-coded set (`expected_modules`) IN the test. Removing the module from `pyproject.toml`
without mirroring the deletion in the guard's `expected_modules` makes the guard FAIL — a
hidden two-file change the plan never called out, which earned a NOGO.

The resolution that converged the re-plan: the omit-allowlist entry is ORTHOGONAL to
whether a module has tests. All THREE already-tested sibling collaborators
(`pr_discovery`, `ci_check_inspector`, `ci_fix_orchestrator`) each have a
`test_*_helpers.py` AND remain in the omit list. So adding tests does NOT require
de-listing. The fix: DROP the de-listing step entirely, keep the module in the allowlist,
make ZERO `pyproject.toml` edits, and add a verification step that runs the guard test to
prove it stays green. This eliminated the entire failure path rather than adding a fragile
two-file co-edit.

## When to Use

The generalizable rule: when a planned change edits a list/registry/manifest enforced by a
"frozen"/"exact-set" guard test, EITHER (a) co-update BOTH the source list AND the guard's
hard-coded copy in the same change and add a verification step running the guard, OR (b)
prove the edit is unnecessary by checking whether siblings already in the same state
satisfy the goal without the edit — and drop the edit. Before proposing to remove an entry
from any allowlist, grep the test tree for a test that pins that allowlist's contents.

Use this skill when:

- Planning a change that removes/adds/edits an entry in a coverage omit-allowlist, an `__all__`, a plugin/skill registry, a CODEOWNERS-style manifest, or any hard-coded enumerated set
- An issue suggests a "nice to have" cleanup (e.g. "also de-list X from the omit list") as a side change
- You are about to edit `pyproject.toml`/`setup.cfg`/a config list and are unsure whether a test pins its contents
- Adding tests to a module that is currently coverage-omitted (tests are orthogonal to omit-listing)
- Any time a reviewer or CI surfaces a `*_frozen` / exact-set / `assert ... == {hard-coded set}` test failure after a list edit

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. The plan was never executed; the orthogonality claim rests on reading test/config source, not running the guard test. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# BEFORE removing an entry from any allowlist/registry/manifest, find the pinning guard:
grep -rE "actual_set == expected_set|frozen|expected_modules|EXPECTED_" tests/
# Found a frozen guard? Two safe options:
#   (a) co-update BOTH the source list AND the guard's hard-coded set, then run the guard:
#       pixi run pytest tests/unit/validation/test_omit_allowlist.py -v
#   (b) prove the edit is UNNECESSARY: check whether siblings already in the target state
#       satisfy the goal without the edit; if so, DROP the edit entirely (zero source changes).
```

### Detailed Steps

1. **Identify any list/registry/manifest your plan touches.** Coverage omit-allowlists, `__all__`, plugin registries, CODEOWNERS-style manifests, and config enumerations are all candidates.
2. **Grep the test tree for a pinning guard BEFORE editing the list.** Look for `*_frozen` tests, `actual_set == expected_set` assertions, or hard-coded `expected_*`/`EXPECTED_*` sets that enumerate the list's contents.
3. **If a frozen guard exists, choose one of two safe paths.**
   - Path (a) co-update: edit BOTH the source list AND the guard's hard-coded copy in the same change, then add a verification step that RUNS the guard.
   - Path (b) drop: check whether siblings already in the target state satisfy the goal without the edit. If they do, drop the edit entirely (zero source changes).
4. **Prefer path (b) when the edit is not load-bearing.** The safest change is the one you do not make; dropping an unnecessary edit removes the failure path instead of adding a fragile two-file invariant.
5. **Add an explicit verification step that runs the frozen guard** before calling the plan verified. Reading the test source is not the same as running it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| De-list a coverage-omitted module as a nice-to-have | First plan proposed (conditionally) removing `hephaestus/automation/post_merge_processor.py` from the `pyproject.toml` coverage omit-allowlist while adding tests | A separate frozen guard `test_omit_allowlist.py::test_omit_allowlist_frozen` pins the EXACT set via a hard-coded `expected_modules`; deleting from `pyproject.toml` alone makes `actual_set == expected_set` FAIL — a hidden second-file edit the plan never named (got a NOGO) | Before removing any allowlist entry, grep the test tree for a `*_frozen`/exact-set guard that pins it; either co-update both copies + run the guard, or prove the edit is unnecessary |
| Assume having tests requires de-listing from the omit allowlist | Plan treated "add tests" and "remove from omit list" as coupled steps | Three already-tested siblings (`pr_discovery`, `ci_check_inspector`, `ci_fix_orchestrator`) each have `test_*_helpers.py` AND remain in the omit list — proving the two are orthogonal | Coverage-omit-listing is orthogonal to whether a module has tests; check sibling precedent before coupling them |
| Fix the NOGO by adding a two-file co-edit | One option was to mirror the deletion into the guard's `expected_modules` set (co-update both files) | Technically correct but adds a fragile, easy-to-forget two-file invariant for zero benefit, since de-listing was never required to meet the goal | Prefer eliminating a failure path (drop the unneeded edit) over adding a fragile co-edit to satisfy a guard; the safest change is the one you don't make |
| Declare the (non-)change verified from reading source | Orthogonality + guard behavior were established by reading `test_omit_allowlist.py:49-52` and `pyproject.toml:259-262` via grep, not by running the guard after the (non-)change | Reading is not running; the guard test was never executed post-change | Add an explicit verification step that RUNS the frozen guard (`pytest .../test_omit_allowlist.py`) before calling the plan verified; until then mark unverified |

## Results & Parameters

The concrete grep recipe to find a pinning guard before editing any allowlist:

```bash
grep -rE "actual_set == expected_set|frozen|expected_modules|EXPECTED_" tests/
```

**Orthogonality evidence (sibling precedent).** Three already-tested sibling collaborators
each have a `test_*_helpers.py` AND remain in the coverage omit-allowlist:

- `pr_discovery`
- `ci_check_inspector`
- `ci_fix_orchestrator`

This proves that adding tests to a module does NOT require de-listing it from the omit
allowlist — the two concerns are orthogonal.

**File/line references.**

- Frozen guard: `tests/unit/validation/test_omit_allowlist.py:49-52` (`actual_set == expected_set` over hard-coded `expected_modules`)
- Source list: `pyproject.toml:259-262` (coverage omit-allowlist)

**Context.** ProjectHephaestus issue #1362 asked for unit tests covering two untested
methods of `PostMergeProcessor`. The first plan bundled a de-listing of
`hephaestus/automation/post_merge_processor.py` from the omit-allowlist; the re-plan
dropped it after the NOGO.

**Risks for the reviewer.** The plan was NOT executed (unverified). Orthogonality rests on
grep-reading the test and config source; the frozen guard was NOT run after the
non-change. The orthogonality claim is a hypothesis until CI runs the guard test.

### Related skills

- `doc-comment-count-drift-verify-frozen-test` — verifying frozen counts/sets after a change drifts the pinned value
- `coverage-omit-orchestration-pure-function-testing` — coverage-omit interplay with pure-function test design
- `planning-test-coverage-verify-premise-and-mock-targets` — verifying the "untested" premise and mock targets when planning coverage tasks

## Verified On

| Project | Scenario | Status |
|---------|----------|--------|
| ProjectHephaestus | Issue #1362 re-plan after NOGO | unverified — plan from source reading, guard not run |
