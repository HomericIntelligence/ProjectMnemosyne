---
name: documentation-planning-stage-plan-comment-docstring
description: "Clarify ProjectHephaestus PlanningStage plan-comment docstrings without changing behavior. Use when: (1) touching _normalize_plan_comment, (2) documenting PLAN_COMMENT_MARKER keyed upsert dedupe, (3) separating plan-comment normalization from the VERIFY ADVANCE gate."
category: documentation
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - projecthephaestus
  - planning-stage
  - plan-comment
  - docstring
  - regression-test
  - pipeline
---

# Documentation: PlanningStage Plan-Comment Docstring Contract

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Document the correct ProjectHephaestus planning-stage pattern for clarifying `_normalize_plan_comment` without changing behavior. Marker normalization is for `PLAN_COMMENT_MARKER` keyed plan-comment upsert dedupe; the `PlanningStage` VERIFY-to-ADVANCE decision is made separately by stage state using `posted_plan` or `ctx.github.has_existing_plan(item.issue)`. |
| **Outcome** | Skill captured as a ProjectMnemosyne learning. The ProjectHephaestus code change described here was not executed in this session. |
| **Verification** | unverified - proposed ProjectHephaestus docstring/test workflow only. Mnemosyne validation should still be run before committing this skill. |

## When to Use

- Clarifying `_normalize_plan_comment` in `hephaestus/automation/pipeline/stages/planning.py`.
- Reviewing a patch that conflates plan-comment marker normalization with the `PlanningStage` VERIFY-to-ADVANCE gate.
- Adding a narrow regression test that pins docstring wording for a behavior-preserving documentation-only change.
- Checking whether `PLAN_COMMENT_MARKER` normalization is about comment upsert dedupe, not about deciding whether the issue already has a plan.

## Verified Workflow

> **Warning:** This ProjectHephaestus workflow has not been validated end-to-end in this capture. Treat it as a proposed workflow until the listed tests and lint run in a writable ProjectHephaestus checkout or CI confirms it.

### Quick Reference

```bash
# Intended ProjectHephaestus verification commands for the downstream patch:
pixi run pytest tests/unit/automation/pipeline/stages/test_stage_planning.py -k "normalize_plan_comment_docstring" -v
pixi run pytest tests/unit/automation/pipeline/stages/test_stage_planning.py -v
pixi run ruff check hephaestus/automation/pipeline/stages/planning.py tests/unit/automation/pipeline/stages/test_stage_planning.py
```

### Detailed Steps

1. Make the production change docstring-only in `hephaestus/automation/pipeline/stages/planning.py`.

2. In `_normalize_plan_comment`, describe marker normalization as the `PLAN_COMMENT_MARKER` keyed plan-comment upsert dedupe path. The current behavior strips leading whitespace and prepends `PLAN_COMMENT_MARKER` when needed around `planning.py:135-138`.

3. Keep the VERIFY-to-ADVANCE explanation separate from normalization. In `PlanningStage`, VERIFY upserts the normalized plan around `planning.py:312-323`, then advances based on `posted_plan` or `ctx.github.has_existing_plan(item.issue)` around `planning.py:325-329`.

4. Tie dedupe to the GitHub wrapper, not the stage gate. Marker-keyed dedupe lives in `PipelineGitHub.upsert_plan_comment` around `hephaestus/automation/pipeline_github.py:801-810`.

5. Add a narrow regression test in `tests/unit/automation/pipeline/stages/test_stage_planning.py` next to the existing marker-normalization coverage around lines 473-490. Import `_normalize_plan_comment` into the existing planning-stage test import block.

6. Make the test assert that `_normalize_plan_comment.__doc__` includes all three load-bearing phrases:

```python
def test_normalize_plan_comment_docstring_separates_dedupe_from_verify_gate() -> None:
    """Pin the helper docstring to the marker-dedupe and VERIFY-gate split."""
    doc = _normalize_plan_comment.__doc__ or ""

    assert "upsert dedupe key" in doc
    assert "VERIFY ADVANCE gate" in doc
    assert "ctx.github.has_existing_plan(item.issue)" in doc
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Treat `_normalize_plan_comment` as the VERIFY gate | Explain the helper as deciding whether a plan exists or whether the stage can advance | The helper only normalizes comment text for marker-keyed upsert dedupe; `PlanningStage` decides advancement using `posted_plan` or `ctx.github.has_existing_plan(item.issue)` after VERIFY upsert | Keep helper docstrings scoped to the helper's actual responsibility and cite the stage gate separately |
| Change behavior while clarifying docs | Alter marker handling, upsert routing, or the stage transition to make the explanation feel more direct | The intended ProjectHephaestus change is docstring-only; behavior already strips leading whitespace, prepends the marker, upserts, and advances via stage state | Preserve production behavior and pin the explanation with a narrow docstring regression test |
| Assert vague docstring wording | Test only that the docstring mentions plan comments or marker normalization | A vague assertion would not prevent the old confusion from returning | Assert the exact concepts: `upsert dedupe key`, `VERIFY ADVANCE gate`, and `ctx.github.has_existing_plan(item.issue)` |

## Results & Parameters

### Behavior Anchors

| File | Anchor | Meaning |
|------|--------|---------|
| `hephaestus/automation/pipeline/stages/planning.py` | `_normalize_plan_comment`, around lines 135-138 | Strips leading whitespace and prepends `PLAN_COMMENT_MARKER` when absent |
| `hephaestus/automation/pipeline/stages/planning.py` | VERIFY handling, around lines 312-323 | Upserts the normalized plan comment |
| `hephaestus/automation/pipeline/stages/planning.py` | VERIFY advancement, around lines 325-329 | Advances via `posted_plan` or `ctx.github.has_existing_plan(item.issue)` |
| `hephaestus/automation/pipeline_github.py` | `PipelineGitHub.upsert_plan_comment`, around lines 801-810 | Uses the marker as the plan-comment upsert dedupe key |

### Docstring Contract

The docstring must preserve this separation:

- `_normalize_plan_comment` exists so plan comments have the `PLAN_COMMENT_MARKER` prefix used as the upsert dedupe key.
- The helper does not decide whether VERIFY should advance.
- The VERIFY ADVANCE gate is stage logic based on `posted_plan` or `ctx.github.has_existing_plan(item.issue)`.

### Intended ProjectHephaestus Patch Shape

```text
Production:
  hephaestus/automation/pipeline/stages/planning.py
    - docstring-only update to _normalize_plan_comment

Tests:
  tests/unit/automation/pipeline/stages/test_stage_planning.py
    - import _normalize_plan_comment in the existing import block
    - add one docstring regression test near existing marker-normalization tests
```

### Verification Status

The ProjectHephaestus commands in Quick Reference were part of the learned plan, but they were not run during this Mnemosyne capture. Mark downstream ProjectHephaestus usage as unverified until those commands or CI pass.
