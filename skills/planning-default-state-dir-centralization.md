---
name: planning-default-state-dir-centralization
description: "Planning checklist for centralizing a repeated default automation state directory behind one helper or constant. Use when: (1) a repo repeats a literal default path such as build/.issue_implementer, (2) a refactor moves mkdir side effects into a helper, (3) tests risk hiding literal-path regressions by importing the production constant."
category: architecture
date: 2026-06-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, default-path, state-directory, constants, helper-extraction, mkdir-side-effects, grep-audit, test-regression-risk, hephaestus]
---

# Planning Default State-Dir Centralization

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-26 |
| **Objective** | Preserve the planning-review lessons from ProjectHephaestus issue #1394: centralize the default automation state directory `build/.issue_implementer` behind one helper or constant before implementation. |
| **Outcome** | Planning artifact only. The implementation was not executed or verified end-to-end in this capture. |
| **Verification** | unverified |
| **Related Context** | ProjectHephaestus automation state path construction across `_reviewer_base.py`, `implementer.py`, `ci_driver.py`, `audit_reviewer.py`, `planner_review_loop.py`, `_review_utils.py`, and unit tests under `tests/unit/automation`. |

## When to Use

- Reviewing or implementing a DRY refactor that replaces repeated default directory literals with a shared helper or constant.
- The default path has side effects, especially `mkdir`, and those side effects may move earlier or later in object construction.
- The proposed helper home is convenient but semantically debatable, for example placing general state-dir helpers in a reviewer utility module.
- A plan relies on grep results to claim every default-path construction site was found.
- Tests currently assert a literal path and the refactor would replace that assertion with the same production constant being tested.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. Find literal path uses and likely dynamic constructions.
rg -n 'build/\\.issue_implementer|\\.issue_implementer|issue_implementer|Path\\(\"build\"\\)|/ \"build\"' \
  hephaestus/ tests/

# 2. Find directory creation side effects before moving them.
rg -n 'mkdir\\(|state_dir|learn_state|audit.*state|planner.*state' \
  hephaestus/automation tests/unit/automation

# 3. After implementation, scope the literal audit.
rg -n 'build/\\.issue_implementer' hephaestus/
rg -n 'build/\\.issue_implementer' tests/ docs/

# 4. Keep at least one regression assertion independent of the production constant.
rg -n 'DEFAULT_STATE_DIR|build/\\.issue_implementer' tests/unit/automation
```

### Detailed Steps

1. **Choose the helper home by ownership, not only by import convenience.**
   `_review_utils.py` can be a pragmatic shared home if every caller already depends on automation review utilities, but a default automation state directory is broader than reviewer code. A reviewer should ask whether the helper belongs in a smaller state-path module, an automation constants module, or `_review_utils.py` with a clear rationale.

2. **Define both the constant and the side-effect boundary explicitly.**
   A useful split is `DEFAULT_STATE_DIR = Path("build/.issue_implementer")` plus `ensure_state_dir(state_dir: Path | None = None) -> Path`. The plan must state whether the helper merely returns the path or also creates it. If it creates the directory, every caller that switches to it changes the timing of `mkdir`.

3. **Audit dynamic path construction beyond the literal string.**
   Literal grep for `build/.issue_implementer` is not enough. Also search for `.issue_implementer`, `Path("build") / ...`, variables named `state_dir`, and constructor defaults that pass through `None` before becoming a path. Treat grep results as an inventory to inspect, not proof that no indirect construction remains.

4. **Map side effects per default caller.**
   For each default construction site, record whether directory creation already happens before the refactor, after the refactor, or not at all. Pay special attention to `AuditReviewer` default construction and planner learn-state setup: creating the directory in the default case may be desirable, but it is still a behavior change if it did not happen before.

5. **Respect patch-surface and import conventions without cargo-cult aliases.**
   If `implementer.py` exposes imported helpers so tests can patch them, document that convention and add the import deliberately. Avoid no-op aliases such as `ensure_state_dir as ensure_state_dir` unless a real patch target, `__all__`, or style convention requires it.

6. **Keep tests capable of catching the default literal.**
   Replacing every expected `tmp_path / "build" / ".issue_implementer"` assertion with `tmp_path / DEFAULT_STATE_DIR` can make tests mirror the bug. At least one test should assert the literal expected path independently, while other tests may import the constant to avoid repetition.

7. **Scope the final literal grep carefully.**
   A production invariant such as "only the constant definition contains `build/.issue_implementer`" should be scoped to production code. Test fixtures, regression assertions, docs, and this skill may legitimately mention the literal. Use separate production and non-production grep checks instead of requiring exactly one repo-wide hit.

## Verified Workflow

This skill is `unverified`. The actionable workflow is intentionally under `## Proposed Workflow`; this heading is retained because the current ProjectMnemosyne validator requires it for all flat skills.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat `_review_utils.py` as obviously correct | Plan placed `DEFAULT_STATE_DIR` and `ensure_state_dir` in `_review_utils.py` because many automation review paths already import from it | The helper may become a cross-stage state concern, not a reviewer concern; adding `Path` and helper exports there widens the module surface | Justify helper placement by ownership and import graph, not only shortest diff |
| Trust literal grep as complete inventory | Plan relied on current-state grep results for `build/.issue_implementer` and named call sites | Pathlib joins, variables, constructor defaults, and indirect `None` default handling can build the same path without the full literal | Search both literal and structural patterns, then inspect each hit |
| Move `mkdir` into a shared helper without a side-effect matrix | Default callers were to switch to a helper that may create the directory | The timing of directory creation can change for `AuditReviewer` defaults and planner learn state | List creation timing before and after per caller before approving |
| Preserve a fragile patch surface mechanically | Plan anticipated exposing `ensure_state_dir` through `implementer.py`, possibly with `ensure_state_dir as ensure_state_dir` | A no-op alias can be unnecessary or signal that tests are patching the wrong boundary | Keep patch targets deliberate; remove aliases unless the existing patch convention actually requires them |
| Replace all literal-path test expectations with the production constant | Tests hardcoding `tmp_path/build/.issue_implementer` were to prefer `DEFAULT_STATE_DIR` | Tests that import the same constant cannot catch a changed default literal | Keep at least one literal expected-path assertion independent of the production constant |
| Require exactly one repo-wide grep hit for the literal | Verification plan said production grep should have exactly one hit for `build/.issue_implementer` | Tests and docs may intentionally mention the literal; a repo-wide count can reject legitimate regression coverage | Scope the invariant to production files, then separately review test/doc hits |

## Results & Parameters

### Planning Assumptions to Mark Unverified

- `_review_utils.py` is the correct shared home for `DEFAULT_STATE_DIR` and `ensure_state_dir`.
- All default-path construction sites were found by grep, with no dynamic or indirect construction remaining.
- `implementer.py` has an explicit patch-surface table or import convention that justifies exposing `ensure_state_dir`.
- `AuditReviewer` and `planner_review_loop` should create the directory as a side effect in the default case.
- Tests that currently hardcode `tmp_path / "build" / ".issue_implementer"` can import `DEFAULT_STATE_DIR` without reducing path-regression coverage.

### Sources Relied On Without Direct Verification

- Issue #1394 wording and current-state grep results, not direct CI.
- Referenced files and call sites in `hephaestus/automation/_reviewer_base.py`, `implementer.py`, `ci_driver.py`, `audit_reviewer.py`, `planner_review_loop.py`, `_review_utils.py`, and `tests/unit/automation`, without proving every line number remained stable.
- Repo convention assumptions that `pixi run pytest` and `pixi run ruff` are the correct verification entrypoints.
- A cited `dry-refactoring-workflow` skill whose instructions were not directly shown in the plan text.

### Reviewer Focus Checklist

```markdown
- [ ] Is the helper placed in the module that owns automation state paths, not merely the module with the easiest imports?
- [ ] Does the plan distinguish a pure default-path constant from a helper that performs `mkdir`?
- [ ] Did the audit search for dynamic path construction and default `None` resolution, not only the literal string?
- [ ] Is directory-creation timing unchanged or intentionally changed for AuditReviewer and planner learn-state code?
- [ ] Is any `implementer.py` import or alias needed for a real patch target?
- [ ] Does at least one unit test still assert the literal default path independently of the production constant?
- [ ] Is the final literal grep scoped to production code, with test/doc hits reviewed separately?
```

### Verification Entry Points to Confirm Before Claiming Success

```bash
pixi run pytest tests/unit/automation -v
pixi run ruff check hephaestus/automation tests/unit/automation
pixi run ruff format --check hephaestus/automation tests/unit/automation
```
