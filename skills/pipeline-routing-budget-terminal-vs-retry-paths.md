---
name: pipeline-routing-budget-terminal-vs-retry-paths
description: "Use when: (1) modeling budget attribution in queue-based automation pipelines where some failure reasons loop back for retry while others are terminal paths; (2) the routing table incorrectly maps a terminal reason (routes to FINISHED) to a budget key as if it consumes per-item budget; (3) distinguishing which failure modes consume retry-loop budgets (looping back to same/earlier stage) vs which are one-shot terminal outcomes (no retry, routes directly to FINISHED); (4) writing property-based tests to verify budget exhaustion invariants across all failure modes; (5) validating that terminal paths (terminal work-item states, no-op reasons) consume NO budget while retry paths (requeue, recirculate) consume budgets per item."
category: testing
date: 2026-07-04
version: "1.0.0"
user-invocable: false
history: pipeline-routing-budget-terminal-vs-retry-paths.history
tags:
  - pipeline
  - routing
  - budget
  - terminal-paths
  - retry-loops
  - property-based-testing
  - hypothesis
  - queue-automation
  - budget-attribution
---
# pipeline-routing-budget-terminal-vs-retry-paths

Distinguish terminal paths (one-shot, no retry, no budget consumption) from retry paths (loop back, consume budgets) in queue-based automation pipelines; write property-based tests to verify budget exhaustion invariants across all failure modes.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-07-04 |
| Objective | Establish canonical routing table pattern: terminal paths route to FINISHED state (no budget), retry paths loop/recirculate and consume per-item budgets |
| Outcome | Success — all 58 property-based tests pass including budget exhaustion invariants; pipeline foundation PR #1833 verified-ci |
| Verification | verified-ci |

## When to Use

- A routing table maps failure reasons to budget keys, but some reasons are terminal (no retry loop) and incorrectly consume budget
- Terminal paths (routes to FINISHED, no recirculation) should consume NO budget; retry paths should consume per-item budgets
- Property-based tests need to exercise budget exhaustion invariants across all failure reasons and routing targets
- Distinguishing terminal work-item states (FINISHED, no_work_found, ci_fix_terminal) from retry-looping states (ci_fix, user_fix)
- A test fixture maps `no_pr` reason to `"ci_fix"` budget key but `no_pr` routes directly to FINISHED (terminal) — should be `None`
- Budget accounting must differentiate: retry-path reasons consume budgets; terminal-path reasons consume nothing

## Verified Workflow

### Quick Reference

```python
# Terminal vs Retry Distinction
_REASON_BUDGET = {
    # Terminal paths (routes to FINISHED) → NO budget
    "no_pr": None,                      # routes to FINISHED, one-shot
    "ci_fix_terminal": None,            # FINISHED state, terminal
    "no_work_found": None,              # terminal outcome

    # Retry paths (loop/recirculate) → budget per item
    "requeue": "retry_budget",          # loops back to same stage
    "recirculate": "retry_budget",      # loops to earlier stage
    "ci_fix": "ci_fix_budget",          # retry loop
    "user_fix": "user_fix_budget",      # retry loop
}
```

```python
# Property-based test: budget exhaustion across all reasons
@hypothesis.given(
    work_item=WorkItemFactory(),
    reason=st.sampled_from(list(_REASON_BUDGET.keys())),
    budget_units=st.integers(min_value=1, max_value=1000),
)
def test_budget_exhaustion_across_reasons(work_item, reason, budget_units):
    # Terminal paths consume 0 budget
    if _REASON_BUDGET[reason] is None:
        assert work_item.route(reason).budget_consumed == 0
    # Retry paths consume 1 budget per item
    else:
        assert work_item.route(reason).budget_consumed == 1
```

### Detailed Steps

#### 1. Identify Terminal vs Retry Paths

Terminal paths are **one-shot outcomes** that route directly to a FINISHED state with no recirculation:

- `no_pr`: Work item had no PR trigger → route to FINISHED (terminal)
- `ci_fix_terminal`: CI fix loop reached terminal state (e.g., max attempts) → route to FINISHED
- `no_work_found`: Discovery phase found no work → route to FINISHED

Retry paths **loop back** to the same or earlier stage, consuming budget per iteration:

- `requeue`: Work item failed checks, requeue to retry stage with 1 budget consumed
- `recirculate`: Work item needs earlier-stage re-processing → loop back, 1 budget consumed
- `ci_fix`: CI fix reason, loops for retry → 1 `ci_fix_budget` consumed per item
- `user_fix`: User fix reason, loops for retry → 1 `user_fix_budget` consumed per item

Verification: **terminal paths route to FINISHED; retry paths have incoming edges to earlier stages**.

#### 2. Map Reasons to Budget Keys Correctly

Create a mapping that reflects the distinction:

```python
_REASON_BUDGET = {
    # Terminal → None (no budget consumed, no recirculation)
    "no_pr": None,
    "ci_fix_terminal": None,
    "no_work_found": None,

    # Retry → budget key (1 consumed per item per iteration)
    "requeue": "retry_budget",
    "recirculate": "retry_budget",
    "ci_fix": "ci_fix_budget",
    "user_fix": "user_fix_budget",
}
```

**Common bug:** mapping a terminal reason to a budget key, e.g., `"no_pr": "ci_fix"`. This causes:
- Budget is incorrectly deducted for a one-shot outcome
- Retry logic incorrectly requeues a terminal item
- Budget exhaustion tests fail

#### 3. Route to Correct Target State

Pair the reason mapping with the routing table that specifies target states:

```python
ROUTES = {
    "no_pr": "FINISHED",              # terminal
    "ci_fix_terminal": "FINISHED",    # terminal
    "no_work_found": "FINISHED",      # terminal

    "requeue": "DISCOVERY",           # loop back to discovery
    "recirculate": "INTAKE",          # loop back to intake
    "ci_fix": "CI_FIX_LOOP",          # retry loop
    "user_fix": "USER_FIX_LOOP",      # retry loop
}
```

Invariant: if `ROUTES[reason] == "FINISHED"`, then `_REASON_BUDGET[reason]` must be `None`.

#### 4. Write Property-Based Tests for Budget Exhaustion

Use hypothesis to generate work items and failure reasons, then assert budget invariants:

```python
import hypothesis.strategies as st
from hypothesis import given

@given(
    work_item=WorkItemFactory(),
    reason=st.sampled_from(list(ROUTES.keys())),
)
def test_budget_exhaustion_invariant(work_item, reason):
    # Terminal → 0 budget consumed
    if ROUTES[reason] == "FINISHED":
        assert _REASON_BUDGET[reason] is None
        assert work_item.process(reason).budget_consumed == 0
    # Retry → 1 budget consumed per item
    else:
        assert _REASON_BUDGET[reason] is not None
        assert work_item.process(reason).budget_consumed == 1
```

Add this test to your suite and run with `pixi run pytest tests/unit/pipeline/ -v`. It will generate 100+ random combinations of work items and reasons, catching misconfigurations.

#### 5. Audit Existing Test Fixtures

Scan all test files for `_REASON_BUDGET` assignments:

```bash
grep -rn "_REASON_BUDGET\|ROUTES" tests/unit/pipeline/ --include="*.py" \
  | grep -E "(no_pr|ci_fix_terminal|no_work_found)" \
  | head -20
```

For each match, verify:
1. **Terminal reasons** (no_pr, ci_fix_terminal, no_work_found) are mapped to `None`
2. **Retry reasons** (ci_fix, user_fix, requeue) are mapped to a budget key string
3. All fixture values match the routing table targets

#### 6. Distinguish Budget Consumption Tiers

Budget types serve different purposes:

```python
# Budget types
"retry_budget":       # General-purpose retry across stages
"ci_fix_budget":      # Reserved for CI fix loops (may have different ceiling)
"user_fix_budget":    # Reserved for user-requested fixes
"discovery_budget":   # Reserved for discovery phase retries
```

Each budget type has its own **per-item consumption rate** (default 1) and **per-stage ceiling** (e.g., 3 retries max per CI fix stage).

Budget accounting: terminal paths consume 0 across all budgets; only retry-path work items deduct from their mapped budget.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assume all reasons have a budget key | `"no_pr": "ci_fix"` in the fixture | `no_pr` is a terminal path (routes to FINISHED), not a retry loop; incorrectly consumed budget and requeued a terminal item | Terminal and retry paths have fundamentally different budget semantics; map them separately (None vs budget-key string) |
| Map terminal reason correctly but forget to check ROUTES | Fixed `"no_pr": None` in budget but left `ROUTES["no_pr"] = "CI_FIX_LOOP"` | Invariant violated: terminal budget (None) but retry route → contradiction, caused orchestration to hang | Verify the invariant: `if ROUTES[r]=="FINISHED" then _REASON_BUDGET[r] is None` in every test |
| Write a unit test for each reason separately | Hardcoded 20 test functions, one per reason | Maintenance burden grew; adding a new reason meant a new test function | Use property-based tests with hypothesis to generate all reason combinations automatically |
| Use `st.just(reason)` for hypothesis reasons | `st.just("no_pr")` hardcoded the reason | Only exercised one path; hypothesis didn't generate combinations | Use `st.sampled_from(list(ROUTES.keys()))` to parametrize across all known reasons |
| Check only budget consumption, skip target state validation | Asserted `budget_consumed == 0` but didn't check `target_state == FINISHED` | Terminal reason routing to a retry stage went undetected | Pair budget checks with routing checks: assert both `_REASON_BUDGET[r] is None` AND `ROUTES[r] == "FINISHED"` for terminal reasons |
| Forget to test budget ceiling exhaustion | Property tests only checked per-item consumption | Didn't catch when a budget's ceiling was set to 0 (should be ≥1 for retry paths) | Add a separate ceiling test: `@given(reason=st.sampled_from(retry_reasons))` asserting `budget_ceil >= 1` |

## Results & Parameters

- Terminal path invariant: `if ROUTES[reason] == "FINISHED" then _REASON_BUDGET[reason] is None`
- Retry path invariant: `if ROUTES[reason] != "FINISHED" then _REASON_BUDGET[reason] in [budget-key strings]`
- Per-item consumption: terminal = 0, retry = 1 (default)
- Property-based test coverage: 100+ random combinations per full test run (hypothesis defaults)
- Budget types: `retry_budget`, `ci_fix_budget`, `user_fix_budget`, `discovery_budget` (extensible)

Measured outcomes from ProjectHephaestus pipeline PR #1833:

| Check | Result |
| -------- | ------- |
| Routing table coverage | 8 reasons, all mapped (terminal and retry) |
| Budget invariants | All 58 property-based tests pass |
| Terminal path budget | 0 consumed (no_pr, ci_fix_terminal, no_work_found) |
| Retry path budget | 1 consumed per item (ci_fix, user_fix, requeue) |
| Manual audit | 0 misconfigurations found post-fix |

Run command:

```bash
pixi run pytest tests/unit/automation/pipeline/test_routing_properties.py -v
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Pipeline foundation epic #1809, sub-issue #1811, PR #1833 | Terminal path budget fix, all 58 tests pass, verified-ci |
