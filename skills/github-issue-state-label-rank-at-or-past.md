---
name: github-issue-state-label-rank-at-or-past
description: >-
  Use when: (1) classifying issues by mutually-exclusive state labels into a pipeline
  queue (e.g. state:needs-plan, state:plan-go, state:implementation-go), (2) routing
  work based on label progression through a fixed rank sequence where some transitions
  are allowed but others must skip stages, (3) preventing re-queueing of issues that
  have already reached or passed a given state rank (e.g. prevent re-planning an issue
  already at state:plan-go), (4) building a dispatcher that uses RANK COMPARISON (>=)
  not label equality (==) to route issues, (5) debugging "issue keeps re-entering phase X
  despite already being past it" failures in an automated pipeline.
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-labels
  - state-machine
  - rank-comparison
  - pipeline-queue
  - admission-control
  - classifier
  - at-or-past
  - re-queueing
  - state-label-vocabulary
  - automation
---

# GitHub Issue State Label: Rank Comparison (At-Or-Past, Not Equality)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Use RANK COMPARISON (>= rank) when routing issues by state labels, NOT equality (== label). Prevents re-queueing issues that have already reached or passed a given rank (e.g., prevent re-planning an issue at state:plan-go). Codifies the classifier logic for GitHub-journal queue reconstruction in an admission-control gate. |
| **Outcome** | Classifier bugfix in ProjectHephaestus #1813: seeding.py `classify_issue()` changed from == rank checks to >= rank checks; routing logic now prevents re-queueing issues past their current stage. Test `test_issue_already_past_plan_go_not_requeued_to_planning` validates the acceptance criterion. 41-test automation-loop suite green (verified-local). |
| **Trigger** | An automated pipeline uses mutually-exclusive state labels to rank issues through a fixed sequence of stages (e.g., needs-plan → plan-go → implementation-go), and the classifier uses equality (==) to route issues → an issue at rank 4 (implementation-go) gets incorrectly routed by the rank 2 (plan-go) path → re-queueing to planning despite already being in implementation |
| **Verification** | verified-local (ProjectHephaestus #1813: seeding.py classifier and loop_runner test suite, 41 tests green after patch seam retargeting) |

## When to Use

Apply this skill when:

- A pipeline classifies issues into stages via **mutually-exclusive state labels** ordered
  by rank (e.g., `state:needs-plan` rank 1, `state:plan-go` rank 2, `state:implementation-go` rank 4)
- The classifier routes issues to queue stages based on **label matching**: "if has this label, enqueue to this phase"
- You observe **re-queueing bugs**: an issue is enqueued to phase X despite already having a label
  indicating it has reached or passed phase X
- The admission-control gate must prevent **backward transitions** (e.g., prevent re-planning
  an issue already at rank 4)
- You are building a **stateless queue dispatcher** that needs a single canonical check:
  "has issue reached at least rank R?" instead of "is issue exactly at rank R?"

**Don't use when:**

- The pipeline uses a different state storage (e.g., internal database, file-based state)
- Labels are not strictly ordered by rank (e.g., independent orthogonal flags, not a sequence)
- Backward transitions are desired (e.g., a re-plan gate that flips issues back to needs-plan)
- The pipeline has conditional stages (some issues skip certain phases)

## Verified Workflow

### Quick Reference

```python
# ❌ WRONG: equality checks allow re-queueing
def classify_issue(issue, label_ranks):
    """Buggy router that re-queues issues already past a rank."""
    for label in issue.labels:
        if label == "state:plan-go":  # equality check
            return "plan-review"  # ❌ routes rank-2 issue to rank-2 handler
        if label == "state:implementation-go":  # never reached; issue already returned above
            return "implementation"

# ✅ CORRECT: rank comparison prevents re-queueing
def classify_issue(issue, label_ranks):
    """Correct router using at-or-past rank comparison."""
    current_rank = 0
    for label in issue.labels:
        rank = label_ranks.get(label, 0)
        current_rank = max(current_rank, rank)  # track highest rank reached

    # Route based on rank, not label equality
    if current_rank >= 4:  # at-or-past implementation-go rank
        return "implementation"
    if current_rank >= 2:  # at-or-past plan-go rank
        return "plan-review"
    return "planning"  # default: needs-plan or no label

# ✅ ALTERNATIVE: check membership in rank set
def classify_issue(issue, label_ranks):
    """Using set membership: if ANY label has rank >= R, don't route to lower stages."""
    # Load rank map: {"state:needs-plan": 1, "state:plan-go": 2, ...}
    issue_ranks = [label_ranks.get(lbl, 0) for lbl in issue.labels if lbl.startswith("state:")]
    max_rank = max(issue_ranks) if issue_ranks else 0

    # At-or-past routing: skip lower stages
    if max_rank >= 4:
        return "implementation"
    if max_rank >= 2:
        return "plan-review"
    return "planning"
```

### Detailed Steps

1. **Define the state label rank ordering**:
   - Create a map of labels to numeric ranks in a fixed sequence.
   - Ranks should be MONOTONIC (1, 2, 3, 4, ...) with no gaps or ties.
   - Label each rank with its semantic meaning (e.g., rank 1 = "needs-plan", rank 4 = "implementation-go").

```python
LABEL_RANKS = {
    "state:needs-plan": 1,
    "state:plan-go": 2,
    "state:implementation-go": 4,  # gap OK; rank 3 unused
}
```

2. **Change router logic from equality (==) to rank comparison (>=)**:
   - Old (buggy): `if label == "state:plan-go": return "plan-review"`
   - New (correct): `if max_rank >= 2: return "plan-review"`
   - The >= comparison prevents an issue at rank 4 from being routed to rank 2 handler.

3. **Compute the maximum rank reached by any label**:
   - Iterate over issue labels; extract rank from map.
   - Take the maximum rank (handles edge case of multiple labels, though mutually-exclusive
     labels should prevent this).

```python
def get_issue_rank(issue, label_ranks):
    """Return the highest rank of any state label on the issue."""
    return max(
        (label_ranks.get(lbl, 0) for lbl in issue.labels if lbl.startswith("state:")),
        default=0  # no label = rank 0 = needs-plan
    )
```

4. **Route using rank boundaries, not exact labels**:
   - Define routing as nested if/elif with rank thresholds.
   - Process from HIGHEST rank down to catch the rightmost stage.

```python
def classify_issue(issue, label_ranks):
    """Route issue to the next queue stage based on current rank."""
    rank = get_issue_rank(issue, label_ranks)

    # Process highest rank first; each stage covers a rank boundary
    if rank >= 4:
        return "implementation-queue"
    if rank >= 2:
        return "plan-review-queue"
    return "planning-queue"  # rank 0 or 1
```

5. **Add a unit test validating at-or-past logic**:
   - Test that an issue at rank N is NOT routed to any handler for rank M < N.

```python
def test_issue_already_past_plan_go_not_requeued_to_planning():
    """Acceptance criterion: issue at implementation-go (rank 4) never routes to planning (rank 1)."""
    issue = {"labels": ["state:implementation-go"]}
    label_ranks = {
        "state:needs-plan": 1,
        "state:plan-go": 2,
        "state:implementation-go": 4,
    }
    rank = max(
        (label_ranks.get(lbl, 0) for lbl in issue.get("labels", []) if lbl.startswith("state:")),
        default=0
    )
    result = classify_issue_from_rank(rank)
    assert result == "implementation", f"Issue at rank 4 must route to implementation, not {result}"
```

6. **Validation: Check for any equality (==) comparisons in the classifier**:
   - Search for patterns like `if label ==` or `if current_state ==` in the routing logic.
   - Replace with `if rank >= ` or `if current_rank in {allowed_ranks}`.

```bash
# Find potential bugs (equality checks on state labels)
grep -n 'if.*label.*==' hephaestus/automation/seeding.py
grep -n 'if.*state.*==' hephaestus/automation/seeding.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Using `==` (equality) to check if issue has reached a rank | `if label == "state:plan-go": route to planning-review` | An issue at rank 4 (state:implementation-go) matches state:plan-go before it gets to the rank 4 check; re-queued to planning despite already in implementation — infinite-loop potential | Use `>=` (at-or-past) rank comparison, not `==` label equality. Process highest rank first. |
| 2 | Checking membership in a set of "allowed" ranks without maximum | `if label in {"state:plan-go", "state:implementation-go"}: enqueue to review` | Multiple labels (if not strictly mutually-exclusive) or migration edge cases where BOTH labels present leads to ambiguous routing | Always compute the **maximum** rank, not just membership. Only the highest rank matters for routing. |
| 3 | Assuming labels are always exactly one per issue | Built logic assuming `single_label = issue.labels[0]` | Labels may not be set (migration phase), or transient duplicate labels during label transitions → IndexError or wrong rank | Use `max(..., default=0)` to handle label absence gracefully and support edge cases. |
| 4 | Skipping the test for the at-or-past AC | Assumed the broader loop tests would catch re-queueing bugs | Re-queueing bugs are subtle; a loop that de-duplicates issues (by GitHub issue number) masks the bug until a state-based dispatch audit | Add a focused unit test asserting that `rank >= threshold_rank` routing prevents re-queueing. Test name should make the AC explicit: `test_issue_already_past_X_not_requeued_to_Y`. |

## Results & Parameters

### Rank Ordering (Authoritative Specification)

| Label | Rank | Stage | Meaning | Route Decision |
|-------|------|-------|---------|---|
| (absent) | 0 | N/A | No state label; treat as needs-plan | Route to planning |
| `state:needs-plan` | 1 | Planning | Issue needs a plan | Route to planning |
| `state:plan-go` | 2 | Plan-Review | Plan accepted; safe to implement | Route to implementation (or re-review if gated) |
| `state:implementation-go` | 4 | Implementation | Implementation approved; proceed | Route to implementation executor |

**Invariant:** Only ONE `state:*` label per issue (mutually-exclusive). Absence of any label is
treated as rank 0 (needs-plan equivalent for easing migration).

### Router Decision Table

| Current Rank | If rank >= 4 | If rank >= 2 | If rank >= 1 | Else | Route To |
|---|---|---|---|---|---|
| 0 (absent) | No | No | No | Yes | planning |
| 1 (needs-plan) | No | No | No | Yes | planning |
| 2 (plan-go) | No | Yes | Yes | — | implementation |
| 4 (impl-go) | Yes | — | — | — | implementation |

### Classifier Logic (Copy-Pasteable)

```python
def get_issue_rank(issue, label_ranks):
    """Compute the highest state-label rank for an issue.

    Args:
        issue: dict with 'labels' key (list of label strings)
        label_ranks: dict mapping label name to numeric rank

    Returns:
        Numeric rank (0 if no state label found)
    """
    return max(
        (label_ranks.get(lbl, 0) for lbl in issue.get("labels", []) if lbl.startswith("state:")),
        default=0
    )


def classify_issue(issue, label_ranks):
    """Route issue to the appropriate queue stage.

    Args:
        issue: dict with 'labels' key
        label_ranks: dict mapping label → rank

    Returns:
        str: stage name ("planning", "implementation", etc.)

    Routing rule: At-or-past rank comparison. Process highest ranks first
    to prevent re-queueing issues that have already reached later stages.
    """
    rank = get_issue_rank(issue, label_ranks)

    # Route from HIGHEST rank downward (prevent lower-stage routing)
    if rank >= 4:
        return "implementation"
    if rank >= 2:
        return "implementation"  # plan-go is "ready to implement"
    return "planning"  # rank 0 or 1
```

### Acceptance Criterion Test

```python
import pytest

LABEL_RANKS = {
    "state:needs-plan": 1,
    "state:plan-go": 2,
    "state:implementation-go": 4,
}

@pytest.mark.parametrize(
    "labels,expected_stage",
    [
        ([], "planning"),  # no label → rank 0 → planning
        (["state:needs-plan"], "planning"),  # rank 1 → planning
        (["state:plan-go"], "implementation"),  # rank 2 → implementation
        (["state:implementation-go"], "implementation"),  # rank 4 → implementation
    ],
)
def test_classify_issue_at_or_past_routing(labels, expected_stage):
    """Verify at-or-past rank routing prevents re-queueing to earlier stages."""
    issue = {"labels": labels}
    stage = classify_issue(issue, LABEL_RANKS)
    assert stage == expected_stage, f"Labels {labels} routed to {stage}, expected {expected_stage}"


def test_issue_already_past_plan_go_not_requeued_to_planning():
    """Acceptance criterion: issue at implementation-go never routes to planning."""
    issue = {"labels": ["state:implementation-go"]}
    rank = max(
        (LABEL_RANKS.get(lbl, 0) for lbl in issue["labels"]),
        default=0
    )
    # At rank 4, MUST route to implementation (rank >= 4), NOT planning (rank >= 1)
    assert rank >= 4, "Test setup: implementation-go must have rank >= 4"
    # This is what the classifier must enforce:
    stage = classify_issue(issue, LABEL_RANKS)
    assert stage == "implementation", f"Issue at rank 4 re-queued to {stage}; should be implementation"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | issue #1813 "GitHub-journal seeding and admission control" | **verified-local** — seeding.py `classify_issue()` changed from `==` rank checks to `>= rank checks`; test `test_issue_already_past_plan_go_not_requeued_to_planning` validates AC; 41-test automation-loop suite passed after patch-seam retargeting (see also v2.2.0 of automation-god-package-shim-first-decomposition skill) |

## References

- [ProjectHephaestus issue #1813](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1813) — GitHub-journal seeding and admission control for queue-based pipeline
- [ProjectHephaestus epic #1809](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1809) — Queue-based automation pipeline
- [architecture-github-labels-as-state-vocabulary.md](architecture-github-labels-as-state-vocabulary.md) — Foundational skill: labels as state vocabulary (this skill is a corollary specific to rank ordering)
