---
name: testing-semantic-enum-order-guard
description: "Use when an enum's declaration order is semantic runtime behavior, such as a pipeline order tuple derived from tuple(EnumClass) or contiguity checks based on list/index position; document the invariant at the enum site and pin tuple(EnumClass) in tests."
category: testing
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - testing
  - enum
  - declaration-order
  - pipeline
  - routing
  - regression-guard
  - projecthephaestus
---

# Guard Semantic Enum Declaration Order

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Make maintainers see when enum declaration order is semantic runtime behavior, then add an order-sensitive test so accidental alphabetization or regrouping fails visibly. |
| **Outcome** | Proposed ProjectHephaestus routing change: document `StageName` order at the enum declaration site and pin both `tuple(StageName)` and `PIPELINE_ORDER` to the intended pipeline sequence. |
| **Verification** | unverified |

When code derives a sequence from an enum declaration, the enum body is no longer just a
bag of named constants. In ProjectHephaestus pipeline routing, `PIPELINE_ORDER =
tuple(StageName)` means enum member order is the pipeline order, and `PipelineScope`
contiguity checks use `PIPELINE_ORDER.index(...)`. A test that asserts only the set of
values will miss a reorder.

The maintainability fix has two parts: put the "do not reorder" warning at the enum
declaration site, and add a narrow test that asserts `tuple(StageName)` and the exported
order constant both equal the explicit intended sequence.

## When to Use

- An enum declaration feeds `tuple(EnumClass)`, `list(EnumClass)`, `enumerate(EnumClass)`, or another order-preserving construct.
- Runtime behavior depends on enum position, such as pipeline stage order, state-machine rank, priority ordering, or contiguous scope checks.
- Existing tests assert enum values with a `set`, so they catch missing or extra members but not accidental reordering.
- A reviewer asks for a warning at the declaration site because the order is not obvious from the enum values alone.
- A future refactor might alphabetize, regroup, or insert enum members without noticing the behavioral consequence.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat it as a proposed workflow until the targeted tests and lint run on the implementation branch.

### Quick Reference

```python
from enum import Enum


class StageName(str, Enum):
    """Pipeline stage identifiers."""

    # Members are declared in pipeline order. PIPELINE_ORDER derives from this
    # declaration order, so members MUST NOT be reordered unless the pipeline
    # sequence is intentionally changing.
    REPO = "repo"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    IMPLEMENTATION = "implementation"
    PR_REVIEW = "pr_review"
    CI = "ci"
    MERGE_WAIT = "merge_wait"
    FINISHED = "finished"


PIPELINE_ORDER = tuple(StageName)
```

```python
def test_stage_name_declaration_order_is_pipeline_order() -> None:
    expected = (
        StageName.REPO,
        StageName.PLANNING,
        StageName.PLAN_REVIEW,
        StageName.IMPLEMENTATION,
        StageName.PR_REVIEW,
        StageName.CI,
        StageName.MERGE_WAIT,
        StageName.FINISHED,
    )

    assert tuple(StageName) == expected
    assert PIPELINE_ORDER == expected
```

### Detailed Steps

1. **Find the semantic order dependency.** Search for `tuple(EnumClass)`, `list(EnumClass)`, `.index(...)`, rank maps built from `enumerate(...)`, or comparisons that imply enum position matters.
2. **Document the invariant at the declaration site.** Put the warning directly inside the enum class above the members, where future maintainers are most likely to see it before reordering.
3. **Keep the warning behavior-specific.** State what derives from declaration order and when reordering is allowed. Avoid a generic "do not edit" comment.
4. **Add an order-sensitive regression test.** Assert `tuple(EnumClass)` equals an explicit tuple of members in intended order. This catches both reordering and accidental insertion at the wrong position.
5. **Also assert exported aliases derived from the enum.** If production code exposes `PIPELINE_ORDER = tuple(StageName)`, assert that constant equals the same expected tuple so a future change to the alias is covered too.
6. **Keep existing value tests.** A set-based value test still usefully catches missing, extra, or misspelled enum values; it just cannot be the only guard.
7. **Run the narrow test and lint.** For the ProjectHephaestus case, run the specific order test, then the full routing test file, then lint the touched source and test files.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assert enum values as a `set` only | Existing coverage checked that `StageName` contained the expected string values | Sets intentionally discard order, so alphabetizing or regrouping the enum would still pass | Keep set/value coverage, but add a separate `tuple(EnumClass)` order test when order is semantic |
| Put the warning near the derived constant only | Documented `PIPELINE_ORDER = tuple(StageName)` but left the enum declaration looking reorderable | A maintainer changing the enum members may never inspect the derived constant before editing | Put the warning directly inside the enum class above the members |
| Test only the exported order constant | Asserted `PIPELINE_ORDER == expected` but did not assert `tuple(StageName) == expected` | If `PIPELINE_ORDER` later stops deriving from the enum, the enum declaration could drift silently | Pin both the source declaration order and the derived alias |
| Treat the comment as sufficient | Added a `MUST NOT be reordered` comment with no test | Comments do not fail CI when ignored | Pair maintainability comments with executable regression coverage |
| Update architecture docs for a no-op guard | Considered changing architecture docs while runtime semantics stayed the same | No behavior or routing table semantics changed; doc churn would distract from the guard | Keep the change local to the enum and its owning tests unless the pipeline sequence itself changes |

## Results & Parameters

ProjectHephaestus-specific planned implementation:

```bash
rg -n "PIPELINE_ORDER|class StageName|PipelineScope" hephaestus/automation/pipeline/routing.py
```

Expected production edit:

- File: `hephaestus/automation/pipeline/routing.py`
- Add a `MUST NOT be reordered` comment inside `class StageName` above the enum members.
- Leave runtime behavior unchanged: `PIPELINE_ORDER = tuple(StageName)` remains the derived order source.

Expected test edit:

- File: `tests/unit/automation/pipeline/test_routing.py`
- Import `PIPELINE_ORDER`.
- Add `test_stage_name_declaration_order_is_pipeline_order`.
- Assert both `tuple(StageName)` and `PIPELINE_ORDER` equal the explicit stage tuple:
  `REPO`, `PLANNING`, `PLAN_REVIEW`, `IMPLEMENTATION`, `PR_REVIEW`, `CI`,
  `MERGE_WAIT`, `FINISHED`.

Verification commands for the implementation branch:

```bash
rg -n "MUST NOT be reordered" hephaestus/automation/pipeline/routing.py
pixi run pytest tests/unit/automation/pipeline/test_routing.py -k stage_name_declaration_order_is_pipeline_order -v
pixi run pytest tests/unit/automation/pipeline/test_routing.py -v
pixi run ruff check hephaestus/automation/pipeline/routing.py tests/unit/automation/pipeline/test_routing.py
```

## Verified On

| Project | Scenario | Status |
|---------|----------|--------|
| ProjectHephaestus | Implementation plan for guarding `StageName` declaration order behind `PIPELINE_ORDER = tuple(StageName)` and `PipelineScope` contiguity checks | unverified - plan captured before implementation, tests, lint, or CI were run |
