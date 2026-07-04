---
name: pipeline-budget-tracking-fail-back-exits
description: "Use when: (1) building routing tables with retry budgets for an automation pipeline (e.g., review loops, implementation loops); (2) distinguishing between retry failures that consume budget (re-enter the same stage) and terminal/fail-back exits that don't (leave the stage or terminate); (3) writing property tests to assert that unbudgeted exits guarantee termination to FINISHED; (4) debugging property test assertions that incorrectly assume all state transitions preserve budget semantics."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - routing-table
  - retry-budget
  - state-machine
  - fail-back-exit
  - property-test
  - automation-pipeline
  - work-items
---

# Pipeline Budget Tracking: Distinguishing Retries from Fail-Back Exits

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Distinguish between **retry failures** (re-enter the same stage, consume budget) and **terminal/fail-back exits** (leave the stage or reach FINISHED, do NOT consume budget) when building routing tables and property tests for automation pipelines. |
| **Origin** | ProjectHephaestus issue #1811 (pipeline foundation layer, PR #1833). Reviewer identified three budget tracking errors in property tests where terminal exits were incorrectly mapped to budget-consuming reasons. |
| **Outcome** | Documented the pattern, verified locally (all pipeline tests pass, pre-commit hooks pass). |
| **Verification** | verified-local — tests pass locally; CI pending. |

## When to Use

- You are building a **routing table** (stage → next_stage mapping) for an automation pipeline with retry budgets per stage.
- A stage has **multiple failure/exit reasons** — some loop back to the same stage (retry), others move to the next stage or FINISHED (fail-back/terminal).
- You are writing **property tests** that assert: "if a reason is unbudgeted, the work item will terminate to FINISHED instead of continuing to loop."
- You found that a property test's trivial assertions (e.g., `assert item.stage in set(StageName)`) are always true and fail to capture the real property being tested.
- You suspect budget tracking is wrong because a terminal exit (e.g., `human_blocked`, `agent_error` leaving a stage) is mapped to a budget name instead of `None`.

## Verified Workflow

### Key Concept: Retry Budget vs. Fail-Back Exit

**Retry budget rule:**
- A reason **consumes budget** (`map to "stage_name"`) if the work item **re-enters the SAME stage** on that reason.
- A reason **does NOT consume budget** (`map to None`) if the work item **leaves the stage** (cross-stage transition or terminal exit to FINISHED).

**In code terms:**
```python
# Example: routing table for PR_REVIEW stage
# Outcome → Next Stage (when successful)
PR_REVIEW_ROUTES = {
    "review_complete": IMPLEMENTATION,   # Success: move to next stage
}

# Reason → Budget Name (when failed; None = unbudgeted, don't retry)
PR_REVIEW_BUDGET_MAP = {
    "review_iteration": "pr_review_iter",      # Retry failure: stays in PR_REVIEW → consumes budget
    "human_blocked": None,                      # Terminal exit: → leaves PR_REVIEW → NO budget
    "exhaustion": None,                         # Terminal exit: → leaves PR_REVIEW → NO budget
    "agent_error": None,                        # Fail-back exit (not terminal): → leaves PR_REVIEW → NO budget
}
```

### Pattern 1: Identify All Stage-Exit Reasons

List every reason that can emerge from a stage and classify each:

| Reason | Type | Next Stage | Budget? | Comment |
|--------|------|------------|---------|---------|
| `plan_not_go` | Fail-back | IMPLEMENTATION | No | Leaves PLANNING, advances outside the loop |
| `plan_iteration` | Retry | PLANNING | Yes | Stays in PLANNING, consumed budget |
| `not_implementation_go` | Fail-back | PLANNING | No | Leaves IMPLEMENTATION, retreats but doesn't retry the same stage |
| `impl_iteration` | Retry | IMPLEMENTATION | Yes | Stays in IMPLEMENTATION, consumed budget |
| `no_pr` | Fail-back | FINISHED | No | Terminal exit, no more stages |
| `pr_review_iter` | Retry | PR_REVIEW | Yes | Stays in PR_REVIEW, consumed budget |
| `human_blocked` | Terminal | FINISHED | No | Work item blocked by human, no retry possible |
| `exhaustion` | Terminal | FINISHED | No | Budget exhausted, no retry possible |
| `agent_error` | Fail-back | IMPLEMENTATION | No | Leaves PR_REVIEW, falls back to IMPLEMENTATION (or earlier), does NOT retry the same stage |

**Key insight:** `agent_error` in PR_REVIEW is **not** a terminal exit (work continues in IMPLEMENTATION), but it is a **fail-back exit** from PR_REVIEW — it does NOT cause a retry within PR_REVIEW.

### Pattern 2: Write Routing Table + Budget Map

Separate the concerns:

```python
from enum import Enum
from typing import Optional

class StageName(Enum):
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    PR_REVIEW = "pr_review"
    FINISHED = "finished"

# Routing: stage + success reason → next stage
STAGE_ROUTES: dict[StageName, dict[str, StageName]] = {
    StageName.PLANNING: {
        "plan_go": StageName.IMPLEMENTATION,
    },
    StageName.IMPLEMENTATION: {
        "implementation_go": StageName.PR_REVIEW,
    },
    StageName.PR_REVIEW: {
        "review_complete": StageName.FINISHED,
    },
}

# Budget tracking: stage + failure reason → budget name (or None if unbudgeted)
STAGE_BUDGET_MAPS: dict[StageName, dict[str, Optional[str]]] = {
    StageName.PLANNING: {
        "plan_iteration": "planning_iter",       # Retry within same stage
        "plan_not_go": None,                     # Fail-back: leaves PLANNING
    },
    StageName.IMPLEMENTATION: {
        "impl_iteration": "implementation_iter", # Retry within same stage
        "not_implementation_go": None,           # Fail-back: leaves IMPLEMENTATION
    },
    StageName.PR_REVIEW: {
        "pr_review_iter": "pr_review_iter",      # Retry within same stage
        "human_blocked": None,                   # Terminal: → FINISHED
        "exhaustion": None,                      # Terminal: → FINISHED
        "agent_error": None,                     # Fail-back: → IMPLEMENTATION
    },
}
```

**Why separate?** Routing tells you where work goes next (success case). Budget tracking tells you whether the failure consumed a retry slot (retry case). Terminal and fail-back exits do NOT consume budget — the work item escapes the retry loop for that stage.

### Pattern 3: Property Test for Unbudgeted Exits Guarantee Termination

The property being tested: **If a work item exhausts its budget for a stage, it must eventually reach FINISHED. Conversely, if all remaining failure reasons are unbudgeted, the work item cannot loop infinitely — it must exit.**

```python
from hypothesis import given, strategies as st

@given(
    reasons=st.lists(
        st.sampled_from(list(PR_REVIEW_BUDGET_MAP.keys())),
        min_size=1,
        max_size=100,
    )
)
def test_pr_review_unbudgeted_exits_guarantee_termination(reasons):
    """
    If all encountered reasons in PR_REVIEW are unbudgeted (map to None),
    the work item must exit PR_REVIEW (not loop infinitely).
    Equivalently: if we exhaust the budget for a stage, we must reach FINISHED.
    """
    item = WorkItem(stage=StageName.PR_REVIEW, budgets={"pr_review_iter": 3})
    exhausted_a_budget = False

    for reason in reasons:
        # Simulate encountering this reason
        budget_name = PR_REVIEW_BUDGET_MAP.get(reason)
        if budget_name is not None:
            exhausted_a_budget = True
            # Decrement budget and stay in PR_REVIEW (retry)
            item.budgets[budget_name] -= 1
            if item.budgets[budget_name] <= 0:
                # Budget exhausted: must exit
                item.stage = StageName.FINISHED
                break
            # Retry: stay in PR_REVIEW, loop again
        else:
            # Unbudgeted: fail-back or terminal exit
            item.stage = StageName.FINISHED  # or appropriate next stage
            break

    # CORRECTED ASSERTION:
    # Only assert termination to FINISHED if we actually exhausted a budget.
    # If all reasons were unbudgeted, we also reach FINISHED, but the property
    # being tested is "exhaustion → FINISHED", not "validity of stages".
    if exhausted_a_budget:
        assert item.stage == StageName.FINISHED, \
            f"After exhausting budget, stage should be FINISHED, got {item.stage}"
```

**Before (incorrect):**
```python
# Always true, doesn't test the real property
assert item.stage in set(StageName)
```

**After (correct):**
```python
# Only assert the property if a budget was actually exhausted
if exhausted_a_budget:
    assert item.stage == StageName.FINISHED
# If no budget was exhausted (all reasons unbudgeted), we still reach FINISHED
# via fail-back exit, but that's a different invariant — not the budget-exhaustion property.
```

### Pattern 4: Check Documentation for Budget Rules

When a code region has a comment block explaining budget tracking (e.g., lines 38-42), proactively check **all similar cases** in that region, not just the one you're fixing.

**Example from PR #1833 feedback:**

```python
# Lines 38-42 (existing comment)
# Budget tracking rule: terminal exits and fail-back routes
# (those that leave a stage) should NOT consume budget.
# Retry failures (stay in stage) DO consume budget.

# Case 1: PLANNING stage, plan_not_go (fail-back exit)
"plan_not_go": None,  # ✓ Correct — leaves PLANNING

# Case 2: PR_REVIEW stage, human_blocked (terminal exit)
"human_blocked": None,  # ✓ Correct — terminal

# Case 3: PR_REVIEW stage, agent_error (fail-back exit)
"agent_error": "pr_review_iter",  # ✗ WRONG — was mapped to budget
# Fix: change to None (leaves PR_REVIEW, does not retry within stage)
"agent_error": None,  # ✓ Correct after fix
```

**Lesson:** When fixing one case, search the same code region for all similar patterns. The documented rule applies uniformly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Budget map included only "happy path" successes | Assumed budget tracking was only for successful stage transitions, not failures | Ignored failure reasons in the budget map, causing completeness gaps | Budget map must cover ALL possible failure/exit reasons from a stage, not just successes |
| Mixed routing and budget into one table | Tried `reason → (next_stage, budget_name)` tuple to save space | Conflated two distinct concerns (where work goes vs. whether it consumes a retry slot) | Separate routing (success/cross-stage) from budget tracking (failure/same-stage). Mixing obscures both. |
| Property test only asserted `item.stage in set(StageName)` | Test passed trivially because every state assignment in the loop produces a valid StageName | Failed to capture the real property: unbudgeted reasons guarantee termination to FINISHED | Assert the specific property being tested (`item.stage == FINISHED` when budget exhausted), not a weaker invariant |
| No budget tracking flag in property test | Forgot to track whether any budget was actually consumed | Could not distinguish between "we exhausted budget and reached FINISHED" vs. "we encountered an unbudgeted exit and reached FINISHED" — different properties | Track `exhausted_a_budget` flag and only assert FINISHED termination when a budget was actually spent |
| Applied budget rule to only one failure reason | Saw `human_blocked` was unbudgeted, fixed it, missed `exhaustion` and `agent_error` in the same stage | Left two similar budget-tracking errors in place | Proactively audit all exit reasons in a stage when fixing one |
| Assumed all "error" reasons are terminal | Named `agent_error` as a terminal exit (like `human_blocked`) | Missed that `agent_error` in PR_REVIEW is a fail-back (not terminal) — exits PR_REVIEW but continues in IMPLEMENTATION | Terminal exits reach FINISHED; fail-back exits leave a stage but continue elsewhere. Read routing table to distinguish. |

## Results & Parameters

### Budget Map Correctness Checklist

For each stage, verify the budget map:

```python
# 1. List all failure reasons that can emerge from this stage
# 2. For each reason, check: does it retry within the stage, or exit the stage?
# 3. If retry → map to budget name; if exit → map to None
# 4. Cross-reference the routing table to confirm next stage(s)

# Template:
for reason in all_reasons_for_stage(stage):
    next_stage = routing.get((stage, reason))
    if next_stage == stage:
        # Retry within stage → must consume budget
        budget_map[reason] = f"{stage.value}_iter"
    else:
        # Exit stage (fail-back or terminal) → no budget
        budget_map[reason] = None
```

### Property Test Structure

```python
# 1. Generate random sequences of failure reasons
# 2. Simulate work item advancement through reasons
# 3. Track whether any budget was consumed
# 4. Assert: if budget exhausted, final stage is FINISHED
# 5. Note: if all reasons were unbudgeted, we also reach FINISHED, but that's orthogonal

@given(reasons=st.lists(...))
def test_stage_budget_exhaustion_terminates(reasons):
    item = WorkItem(stage=STAGE, budgets={"stage_iter": N})
    exhausted_a_budget = False
    for reason in reasons:
        budget = BUDGET_MAP[reason]
        if budget is not None:
            exhausted_a_budget = True
            item.budgets[budget] -= 1
            if item.budgets[budget] <= 0:
                item.stage = StageName.FINISHED
                break
        else:
            item.stage = StageName.FINISHED  # or exit_stage
            break

    if exhausted_a_budget:
        assert item.stage == StageName.FINISHED
```

### Common Budget Names

| Stage | Budget Name | Example Consumption |
|-------|-------------|---------------------|
| PLANNING | `planning_iter` | `plan_iteration` reason detected, budget -= 1 |
| IMPLEMENTATION | `implementation_iter` | `impl_iteration` reason detected, budget -= 1 |
| PR_REVIEW | `pr_review_iter` | `pr_review_iter` reason detected, budget -= 1 |

### Terminal vs. Fail-Back: Quick Reference

| Type | Example Reason | Next Stage | Budget? | Comment |
|------|----------------|-----------|---------|---------|
| Retry | `plan_iteration` | PLANNING | Yes | Re-enters same stage |
| Fail-Back | `agent_error` in PR_REVIEW | IMPLEMENTATION | No | Exits stage, continues elsewhere |
| Fail-Back | `not_implementation_go` | PLANNING | No | Exits stage, retreats |
| Terminal | `human_blocked` | FINISHED | No | Work blocked, no more stages |
| Terminal | `no_pr` | FINISHED | No | Mandatory exit condition |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1811, PR #1833 | Pipeline foundation layer: routing table + work items, three budget-tracking errors in property tests identified by reviewer |
| ProjectHephaestus | PR #1833 (after fix) | All pipeline tests pass, pre-commit hooks pass locally; CI pending |
