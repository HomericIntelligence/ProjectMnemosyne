# automation-prefix-match-plan-detection — Session Notes

## Issue #715 Context

**ProjectHephaestus**: Fix substring-match anti-pattern in implementer_phase_runner._has_plan

### The Bug

In `hephaestus/automation/implementer_phase_runner.py`, the `_has_plan()` function was checking:
```python
if "## Plan" in comment.get("body", ""):
```

This is a substring match — it catches any comment containing the text "## Plan" anywhere in the comment body.

**Problem**: Plan Review comments have format like:
```
## Review:

The plan is well-designed and follows best practices...
```

The substring "Plan" appears in "The plan", triggering a false positive. The function incorrectly reports that a Review comment counts as "having a plan".

### The Fix

**Pattern 1: Delegation**

When `_comments_contain_plan` already exists in planner_state with the proven implementation:
```python
# Before
def _has_plan(comments: list[dict]) -> bool:
    for comment in comments:
        if "## Plan" in comment.get("body", ""):  # BROKEN
            return True
    return False

# After
from hephaestus.automation.planner_state import _comments_contain_plan

def _has_plan(comments: list[dict]) -> bool:
    return _comments_contain_plan(comments)
```

**Pattern 2: Inline prefix-match**

When the function has a different return type (e.g., needs to extract plan text):
```python
# Before
def _fetch_plan_and_review(comments: list[dict]) -> tuple[str | None, str | None]:
    for comment in comments:
        if "## Plan" in comment.get("body", ""):  # BROKEN
            return (comment["body"], None)
    return (None, None)

# After
from hephaestus.automation.planner_state import PLAN_COMMENT_MARKER

def _fetch_plan_and_review(comments: list[dict]) -> tuple[str | None, str | None]:
    for comment in comments:
        body = comment.get("body", "")
        if body.startswith(PLAN_COMMENT_MARKER):  # FIXED
            return (body[len(PLAN_COMMENT_MARKER):].strip(), None)
    return (None, None)
```

### Test Regression

Added test to prevent reintroduction of the false-positive bug:

```python
# tests/unit/automation/test_implementer.py :: TestHasPlanPrefixMatch

def test_has_plan_prefix_match():
    """Regression: Plan Review comments quoting the plan should NOT count as having a plan."""
    plan_comment = {"body": "## Plan\n\n1. Implement foo\n2. Test bar"}
    assert _has_plan([plan_comment]) is True

    review_comment = {"body": "## Review:\n\nThe plan is good, implementation is correct."}
    assert _has_plan([review_comment]) is False  # Critical: Review ≠ Plan
```

### Testing Pitfall

**Initial attempt failed**: Tried to patch `IssueImplementer._impl_module` in the test.
- `IssueImplementer` class has a `phase_runner` attribute (not `_impl_module`)
- The `phase_runner` object has the `_impl_module` attribute
- Patch point must be at `implementer_phase_runner.run`, not on the IssueImplementer instance

**Lesson**: Always inspect class structure before patching. Use:
```bash
grep -n "class IssueImplementer\|self._impl_module\|self.phase_runner" \
  hephaestus/automation/implementer.py | head -20
```

### Verification

- **1085 tests pass** in CI (verified-ci)
- Regression test explicitly covers Plan Review comment false positive
- Grep of sibling automation modules shows no similar substring-match anti-patterns in:
  - `planner_state.py` (has canonical prefix-match implementation)
  - `plan_reviewer.py` (uses canonical helper)
  - `implementer.py` (uses phase_runner methods)

### Related Issues

This fixes a **recurrence pattern** from:
- #455: Substring-match bug in planner (fixed with prefix-match)
- #468: Similar pattern in plan_reviewer (fixed)
- #484: Another instance elsewhere (fixed)

The learning: **After fixing a substring-match bug in one module, grep all sibling modules in the same package** — copy-paste implementations often replicate the anti-pattern across multiple files.

### Architectural Pattern

**Comment marker anchoring**:
```python
# hephaestus/automation/planner_state.py
PLAN_COMMENT_MARKER = "## Plan\n"

def _comments_contain_plan(comments: list[dict]) -> bool:
    """Canonical implementation."""
    for comment in comments:
        if comment.get("body", "").startswith(PLAN_COMMENT_MARKER):
            return True
    return False
```

All modules import this constant and either:
1. Delegate to `_comments_contain_plan()` (preferred)
2. Inline the prefix-match using the constant (when return type differs)

Never use substring search for comment markers — always prefix-match.

### Why This Matters

The `_has_plan()` function is called in the implementer phase to determine if a plan has been reviewed before proceeding. False positives cause the automation to skip plan review and proceed directly to implementation without stakeholder approval — a critical safety gate bypass.

The fix ensures:
- Only actual plan comments (starting with `## Plan\n`) count as plans
- Review comments that happen to mention "the plan" don't trigger false acceptance
- Regression test prevents accidental reintroduction of the substring-match pattern
