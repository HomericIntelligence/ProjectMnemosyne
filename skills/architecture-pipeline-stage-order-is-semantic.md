---
name: architecture-pipeline-stage-order-is-semantic
description: "Use when: (1) a pipeline derives `PIPELINE_ORDER = tuple(StageName)` or similar from enum declaration order; (2) scope/routing/contiguity checks depend on the enum iteration order; (3) reordering the enum would silently change routing semantics and needs an explicit regression guard."
category: architecture
date: 2026-07-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pipeline
  - stage-order
  - enum
  - routing
  - invariant
  - regression-guard
---

# Pipeline Stage Order Is Semantic

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-07 |
| **Objective** | Preserve pipeline semantics when stage order is derived from `tuple(StageName)` and consumed by routing/contiguity logic. |
| **Outcome** | Success — stage order is now documented as a contract and pinned by a regression test. |
| **Verification** | verified-local |

## When to Use

- A pipeline stage enum is iterated directly to build the canonical stage order.
- Scope trimming or contiguity checks depend on that order.
- Reordering enum members would not break type checks, but would silently change routing behavior.
- You need a small regression test that fails when someone moves, inserts, or swaps a stage.

## Verified Workflow

### Quick Reference

```python
class StageName(str, Enum):
    """Pipeline stage identifiers.

    Members are declared in pipeline order and MUST NOT be reordered.
    """

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
def test_stage_order_is_pinned() -> None:
    assert tuple(StageName) == PIPELINE_ORDER
```

### Detailed Steps

1. Document the enum itself as an ordered contract, not just a label list.
2. Keep the canonical order derived from `tuple(StageName)` so one source of truth feeds routing and scope checks.
3. Pin the exact iteration order in a test, ideally alongside a contiguity or scope test.
4. Re-run the routing tests whenever a stage is added, removed, or renamed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rely on `tuple(StageName)` without documentation | Kept the enum order implicit and assumed readers would notice | A later reorder still changes routing semantics, but nothing tells the maintainer the order is load-bearing | Make the order explicit in the enum docstring and nearby comments |
| Test route targets only | Asserted individual `ROUTES[...]` values but not the enum iteration order | Routing targets can stay correct while scope/contiguity behavior silently shifts | Pin the order itself, not just downstream mappings |
| Compare against a sorted list | Used alphabetical order in the test | Alphabetical order is not the runtime contract; it hides the semantic dependency on declaration order | Compare against the exact intended pipeline sequence |

## Results & Parameters

### Invariant

- `PIPELINE_ORDER = tuple(StageName)` means declaration order is semantic.
- `StageName` members must stay in the canonical pipeline sequence.
- Any reorder must be treated as a behavior change and reviewed alongside routing/scope tests.

### Expected Output

- `tuple(StageName)` matches the documented pipeline order.
- Scope-contiguity checks continue to accept contiguous subsets and reject gaps.
- A future reorder fails fast in tests instead of silently changing routing behavior.

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1903 / PR #1987 | Stage order is semantic because `PIPELINE_ORDER = tuple(StageName)` and `PipelineScope` depends on declaration order. |

