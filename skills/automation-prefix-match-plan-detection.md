---
name: automation-prefix-match-plan-detection
description: "Fix substring-match anti-pattern in plan detection by delegating to canonical helpers or inlining proven prefix-match logic with shared constants. Use when: (1) fixing a substring-match bug in comment detection (like _has_plan), (2) after fixing a prefix-match bug in one automation module, grep sibling modules for the same anti-pattern, (3) implementing plan detection across multiple modules, (4) test regressions show Plan Review comments quoting the plan are miscounted as 'having a plan'."
category: debugging
date: 2026-06-05
version: "1.0.0"
verification: verified-ci
tags: [automation, prefix-match, substring-match, anti-pattern, plan-detection, comment-parsing, comment-filters, canonical-helpers, sibling-modules, test-regression]
---

# Automation: Prefix-Match Plan Detection

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Fix substring-match anti-pattern in implementer_phase_runner._has_plan that was reintroducing bug class fixed in #455/#468/#484 |
| **Outcome** | Success — _has_plan delegated to canonical helper; _fetch_plan_and_review uses inlined prefix-match logic; regression test added; 1085 tests pass (verified-ci) |
| **Verification** | verified-ci |
| **Context** | Issue #715 — ProjectHephaestus automation module |

## When to Use

**Trigger conditions:**

- A bug fix in one automation module involves comment detection (prefix-match vs substring-match)
- You've just fixed a substring-match bug in one module and need to audit sibling modules
- Test regressions show Plan Review comments (which quote the plan) are miscounted as 'having a plan'
- Comment-filtering logic is duplicated across _planner_state, _plan_reviewer, and _implementer modules
- You're implementing a new plan-detection variant across multiple modules and need a proven pattern

## Verified Workflow

### Quick Reference

```python
# Pattern 1: Delegate to canonical helper (preferred when available)
from hephaestus.automation.planner_state import _comments_contain_plan

def _has_plan(comments: list[dict]) -> bool:
    """Check if any comment contains a plan (POLA: single responsibility)."""
    return _comments_contain_plan(comments)

# Pattern 2: Inline prefix-match logic using shared constant (when return type differs)
from hephaestus.automation.planner_state import PLAN_COMMENT_MARKER

def _fetch_plan_and_review(comments: list[dict]) -> tuple[str | None, str | None]:
    """Fetch plan and review comment from comments.

    Return: (plan_text, review_comment) or (None, None) if no plan found.
    """
    for comment in comments:
        body = comment.get("body", "")
        # PREFIX-MATCH: only comments starting with marker count
        if body.startswith(PLAN_COMMENT_MARKER):
            return (body[len(PLAN_COMMENT_MARKER):].strip(), None)
    return (None, None)
```

### Detailed Steps

**Step 1: Identify the bug pattern**

Substring-match anti-pattern (BROKEN):
```python
def _has_plan(comments):
    for comment in comments:
        if "plan:" in comment.get("body", ""):  # BROKEN: matches "review: plan:" too
            return True
    return False
```

Why it's broken:
- Plan Review comments have format: `## Review:\n\nThe plan:\n...` (the word "plan" appears after review text)
- Substring match catches "The plan:" from review comments, not just actual plan comments
- Original plan comments start with `## Plan\n` (the marker is at the start)

Prefix-match fix (CORRECT):
```python
# Correct: check if comment STARTS with the marker
if comment.get("body", "").startswith(PLAN_COMMENT_MARKER):
    return True
```

**Step 2: Search for canonical helper (delegation pattern)**

```bash
# In the module with the bug:
grep -rn "def _has_plan\|def _comments_contain_plan" hephaestus/automation/

# Check if planner_state has the proven implementation:
grep -A 10 "_comments_contain_plan" hephaestus/automation/planner_state.py
grep "PLAN_COMMENT_MARKER" hephaestus/automation/planner_state.py
```

Expected output from planner_state:
```python
PLAN_COMMENT_MARKER = "## Plan\n"  # shared constant

def _comments_contain_plan(comments: list[dict]) -> bool:
    """Canonical implementation: prefix-match only."""
    for comment in comments:
        if comment.get("body", "").startswith(PLAN_COMMENT_MARKER):
            return True
    return False
```

**Step 3: Apply the fix**

**If return type matches** (both return bool) → **delegate**:

```python
# Before (implementer_phase_runner.py, BROKEN)
def _has_plan(comments: list[dict]) -> bool:
    for comment in comments:
        if "## Plan" in comment.get("body", ""):
            return True
    return False

# After (implementer_phase_runner.py, FIXED)
from hephaestus.automation.planner_state import _comments_contain_plan

def _has_plan(comments: list[dict]) -> bool:
    return _comments_contain_plan(comments)  # delegate to canonical
```

**If return type differs** (e.g., need to extract the plan text) → **inline prefix-match**:

```python
# Before (implementer_phase_runner.py, BROKEN)
def _fetch_plan_and_review(comments: list[dict]) -> tuple[str | None, str | None]:
    for comment in comments:
        if "## Plan" in comment.get("body", ""):  # substring match — BROKEN
            return (comment["body"], None)
    return (None, None)

# After (implementer_phase_runner.py, FIXED)
from hephaestus.automation.planner_state import PLAN_COMMENT_MARKER

def _fetch_plan_and_review(comments: list[dict]) -> tuple[str | None, str | None]:
    for comment in comments:
        body = comment.get("body", "")
        # Prefix-match: only comments STARTING with marker count as plans
        if body.startswith(PLAN_COMMENT_MARKER):
            return (body[len(PLAN_COMMENT_MARKER):].strip(), None)
    return (None, None)
```

**Step 4: Add regression test**

```python
# tests/unit/automation/test_implementer.py

def test_has_plan_prefix_match():
    """Regression: Plan Review comments quoting the plan should NOT count as having a plan.

    Issue #715: substring-match was broken because Review comments contain 'The plan:' text.
    """
    # Plan comment (starts with marker)
    plan_comment = {
        "body": "## Plan\n\n1. Implement foo\n2. Test bar"
    }
    assert _has_plan([plan_comment]) is True

    # Review comment (contains word 'plan' but doesn't start with marker) — MUST be False
    review_comment = {
        "body": "## Review:\n\nThe plan is good, implementation is correct."
    }
    assert _has_plan([review_comment]) is False

    # Both comments: only plan comment counts
    assert _has_plan([plan_comment, review_comment]) is True
```

**Step 5: Grep sibling modules for the same pattern**

```bash
# After landing the fix in implementer_phase_runner.py, check all sibling modules:
cd hephaestus/automation

# Search for the broken pattern in all files
grep -rn "in .*\.get(\"body\"\|if \".*\" in.*body\|startswith.*Plan" *.py | grep -v planner_state | grep -v test

# Expected: no matches (all modules either delegate or use prefix-match)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Patching `IssueImplementer._impl_module` in test to mock `_has_plan` behavior | `IssueImplementer` doesn't have `_impl_module`; the attribute is on `phase_runner` which is a different class | Always check class structure before patching; patch at the correct module level (`patch('implementer_phase_runner.run')` not `patch('IssueImplementer._impl_module')`) |
| 2 | Using substring match ("## Plan" in body) for plan detection | Plan Review comments contain the string "The plan:" after review text, triggering false positives on substring match | Prefix-match is the only safe pattern for start-of-comment markers; use `startswith(PLAN_COMMENT_MARKER)` not `in` or `find()` |
| 3 | Inline prefix-match in each module without a shared constant | Maintenance burden: if marker format changes, all inline locations must be updated; test fixtures may mask the invariant | Define the constant in the canonical module (planner_state.py) and import everywhere; prefer delegation when return types match |

## Results & Parameters

### Code Locations

| File | Function | Change |
|------|----------|--------|
| `hephaestus/automation/implementer_phase_runner.py` | `_has_plan` | Delegated to `_comments_contain_plan` from planner_state |
| `hephaestus/automation/implementer_phase_runner.py` | `_fetch_plan_and_review` | Inlined prefix-match using `PLAN_COMMENT_MARKER` constant |
| `tests/unit/automation/test_implementer.py` | `TestHasPlanPrefixMatch` | Added regression test for Plan Review comment false positive |

### Shared Constants

```python
# hephaestus/automation/planner_state.py
PLAN_COMMENT_MARKER = "## Plan\n"  # Anchor for prefix-match

# Usage:
def _comments_contain_plan(comments: list[dict]) -> bool:
    for comment in comments:
        if comment.get("body", "").startswith(PLAN_COMMENT_MARKER):
            return True
    return False
```

### Test Regression Pattern

```python
# Regression test: Review comments with quoted plan should NOT count as having plan
review_with_quoted_plan = {
    "body": "## Review:\n\nThe plan is well-designed. Implementation follows the design."
}
assert _has_plan([review_with_quoted_plan]) is False

# Only comments STARTING with marker count
plan_comment = {"body": "## Plan\n\n1. Do X\n2. Do Y"}
assert _has_plan([plan_comment]) is True
```

### Verification Commands

```bash
# Run affected tests
pixi run pytest tests/unit/automation/test_implementer.py::TestHasPlanPrefixMatch -v

# Run full automation test suite
pixi run pytest tests/unit/automation/ -v

# Grep for sibling-module anti-patterns (all should be negative)
grep -rn "in .*body.*Plan\|if \"Plan\" in" hephaestus/automation/*.py | grep -v planner_state
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #715 — implementer_phase_runner prefix-match bug fix | [PR #1085](https://github.com/HomericIntelligence/ProjectHephaestus/pull/1085) — 1085 tests pass |

## Key References

- **Related Issues**: #455, #468, #484 (earlier substring-match bugs in other modules)
- **Similar Pattern**: See `audit-driven-remediation-workflow` skill for post-fix grep workflow
- **Canonical Helper Location**: `hephaestus/automation/planner_state.py:_comments_contain_plan`
- **Shared Constant**: `PLAN_COMMENT_MARKER = "## Plan\n"`

## Architecture Notes

**Why delegation is preferred over duplication:**

- `_comments_contain_plan` in planner_state is the authoritative implementation
- Delegating ensures single source of truth for the prefix-match logic
- If marker format changes (e.g., to `## Implementation Plan`), only one location needs update
- Tests automatically pass the regression (Plan Review comment false positive)

**Why inline prefix-match is acceptable for different return types:**

- `_fetch_plan_and_review` returns `(plan_text, review_comment)` tuple, not bool
- Can't delegate to `_comments_contain_plan` without wrapping
- Inlining with shared `PLAN_COMMENT_MARKER` constant keeps the logic identical
- Import the constant to maintain single source of truth

**Anti-pattern to avoid (substring match):**

- ❌ `if "## Plan" in body:` — catches partial matches
- ❌ `if body.find("Plan") >= 0:` — catches word anywhere in comment
- ✅ `if body.startswith(PLAN_COMMENT_MARKER):` — prefix-anchored, canonical format only
