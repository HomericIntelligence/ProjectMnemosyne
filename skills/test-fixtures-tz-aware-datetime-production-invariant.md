---
name: test-fixtures-tz-aware-datetime-production-invariant
description: "Use when: (1) production code guarantees all timestamps are tz-aware UTC (coordination layer convention); (2) test fixtures use naive datetime.now() instead of tz-aware datetime.now(timezone.utc); (3) timezone-aware invariants are enforced at runtime (TypeError, ValueError, or silent logical bugs when comparing aware/naive); (4) fixtures should mirror production constraints to catch timezone bugs at authoring time, not at CI time; (5) refactoring fixtures to use tz-aware UTC across history events, event timestamps, or any temporal data that flows through coordination layers; (6) coordinating timestamps across multiple subsystems (agents, events, work items) where some use naive and others use aware, causing comparison failures."
category: testing
date: 2026-07-04
version: "1.0.0"
user-invocable: false
history: test-fixtures-tz-aware-datetime-production-invariant.history
tags:
  - testing
  - datetime
  - timezone
  - fixtures
  - tz-aware
  - UTC
  - python-datetime
  - production-invariants
  - coordination-layer
---
# test-fixtures-tz-aware-datetime-production-invariant

Ensure test fixtures use tz-aware UTC datetimes to match production invariants; catch timezone bugs at fixture authoring time, not CI time; maintain consistency across all temporal data in coordination layers.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-07-04 |
| Objective | Establish test fixture pattern: all timestamps MUST be tz-aware UTC (datetime.now(timezone.utc)) to match production coordination layer contracts |
| Outcome | Success — all 3 HistoryEvent test fixtures refactored to tz-aware UTC; all 58 tests pass; integration verified-ci |
| Verification | verified-ci |

## When to Use

- Production code enforces "all timestamps must be tz-aware UTC" (e.g., WorkItem, HistoryEvent, Event coordination layer)
- Test fixtures use naive `datetime.now()` instead of tz-aware `datetime.now(timezone.utc)`
- Comparing work-item timestamps with fixture timestamps raises `TypeError: can't compare offset-naive and offset-aware datetimes`
- Fixtures should enforce the same invariants as production to catch timezone bugs early
- Refactoring a coordination layer to use UTC and all temporal fixtures need consistent updates
- Subsystems are splitting between naive (old) and aware (new) datetimes, causing subtle logical bugs
- An async event coordinator receives event timestamps from multiple agents with inconsistent timezone info

## Verified Workflow

### Quick Reference

```python
# WRONG: Naive datetime
from datetime import datetime

history_event = HistoryEvent(
    timestamp=datetime.now(),  # naive — violates production contract
    work_item_id="w1",
    reason="ci_fix",
)
```

```python
# RIGHT: Tz-aware UTC datetime
from datetime import datetime, timezone

history_event = HistoryEvent(
    timestamp=datetime.now(timezone.utc),  # tz-aware UTC — matches production
    work_item_id="w1",
    reason="ci_fix",
)
```

### Detailed Steps

#### 1. Identify Production Timestamp Contracts

Scan the production code for datetime invariants:

```bash
grep -rn "datetime.now\|timezone\|UTC\|utc" hephaestus/automation/ --include="*.py" \
  | grep -E "(tz-aware|timezone.utc|assert.*timezone)" \
  | head -10
```

Look for:
- `datetime.now(timezone.utc)` — production uses tz-aware UTC
- Type hints like `datetime: datetime` with docstring `"Must be UTC"` or `"Tz-aware"`
- Runtime checks: `if dt.tzinfo is None: raise ValueError(...)`
- Coordination layer classes (WorkItem, HistoryEvent, Event) that enforce the constraint

Example from ProjectHephaestus pipeline:

```python
class HistoryEvent:
    """Immutable event in work-item history.

    Attributes:
        timestamp: Creation time in UTC (tz-aware). Must not be naive.
        reason: Failure or success reason code.
        work_item_id: Reference to the work item.
    """
    timestamp: datetime  # ← docstring implies tz-aware UTC
    reason: str
    work_item_id: str
```

#### 2. Audit Test Fixtures for Naive Datetimes

Find all fixture creation sites that use naive datetimes:

```bash
grep -rn "datetime.now()" tests/unit/automation/ --include="*.py" \
  | grep -v "timezone.utc"
```

Common patterns to fix:

```python
# ❌ WRONG
HistoryEvent(timestamp=datetime.now(), ...)
Event(created_at=datetime.now(), ...)
WorkItem(discovered_at=datetime.now(), ...)

# ✅ RIGHT
HistoryEvent(timestamp=datetime.now(timezone.utc), ...)
Event(created_at=datetime.now(timezone.utc), ...)
WorkItem(discovered_at=datetime.now(timezone.utc), ...)
```

#### 3. Update Fixture Classes with Tz-Aware Defaults

If fixtures use factory patterns or dataclass defaults, ensure defaults are tz-aware:

```python
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass
class HistoryEventFixture:
    """Fixture for HistoryEvent with tz-aware UTC defaults."""

    @staticmethod
    def default_timestamp() -> datetime:
        return datetime.now(timezone.utc)

    timestamp: datetime = field(default_factory=default_timestamp)
    work_item_id: str = "default-w1"
    reason: str = "ci_fix"
```

Or use a factory function:

```python
def make_history_event(
    timestamp: Optional[datetime] = None,
    work_item_id: str = "w1",
    reason: str = "ci_fix",
) -> HistoryEvent:
    """Create a HistoryEvent fixture with tz-aware UTC timestamp."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    return HistoryEvent(timestamp=timestamp, work_item_id=work_item_id, reason=reason)
```

#### 4. Fix Comparison Failures in Tests

When comparing timestamps, ensure both sides are tz-aware:

```python
# ❌ WRONG — one naive, one aware
event = HistoryEvent(timestamp=datetime.now())  # naive
expected_time = datetime.now(timezone.utc)      # aware
assert event.timestamp == expected_time         # TypeError

# ✅ RIGHT — both aware
event = HistoryEvent(timestamp=datetime.now(timezone.utc))  # aware
expected_time = datetime.now(timezone.utc)                  # aware
assert event.timestamp == expected_time                     # passes
```

If comparing against a hardcoded time, specify the timezone:

```python
# ❌ WRONG
reference = datetime(2026, 7, 4, 12, 30, 0)  # naive
assert event.timestamp > reference

# ✅ RIGHT
reference = datetime(2026, 7, 4, 12, 30, 0, tzinfo=timezone.utc)  # aware
assert event.timestamp > reference
```

#### 5. Test Timezone Handling Explicitly

Add dedicated tests for the timezone invariant:

```python
from datetime import datetime, timezone, timedelta
import pytest

def test_history_event_timestamp_must_be_tz_aware():
    """Verify HistoryEvent enforces tz-aware UTC timestamps."""
    # Naive datetime should raise or be rejected
    with pytest.raises((TypeError, ValueError)):
        HistoryEvent(timestamp=datetime.now(), work_item_id="w1", reason="ci_fix")

def test_history_event_timestamp_accepts_tz_aware_utc():
    """Verify HistoryEvent accepts tz-aware UTC timestamps."""
    ts = datetime.now(timezone.utc)
    event = HistoryEvent(timestamp=ts, work_item_id="w1", reason="ci_fix")
    assert event.timestamp == ts
    assert event.timestamp.tzinfo == timezone.utc

def test_history_event_timestamp_comparison_with_offset():
    """Verify timestamp comparisons work with timezone-aware datetimes."""
    base = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)
    later = datetime(2026, 7, 4, 13, 0, 0, tzinfo=timezone.utc)

    event1 = HistoryEvent(timestamp=base, work_item_id="w1", reason="ci_fix")
    event2 = HistoryEvent(timestamp=later, work_item_id="w1", reason="ci_fix")

    assert event1.timestamp < event2.timestamp
    assert (event2.timestamp - event1.timestamp) == timedelta(hours=1)
```

#### 6. Document the Invariant in Fixture Docstrings

Add explicit documentation so future maintainers understand the constraint:

```python
def make_history_event(
    timestamp: Optional[datetime] = None,
    work_item_id: str = "w1",
    reason: str = "ci_fix",
) -> HistoryEvent:
    """Create a HistoryEvent fixture.

    Args:
        timestamp: Event creation time. MUST be tz-aware UTC.
                   Defaults to datetime.now(timezone.utc).
        work_item_id: Reference to work item.
        reason: Failure or success reason code.

    Returns:
        A HistoryEvent with tz-aware UTC timestamp.

    Note:
        Production invariant: all timestamps are tz-aware UTC.
        Fixtures enforce the same constraint.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        raise ValueError(
            f"Fixture timestamp must be tz-aware UTC; got naive datetime: {timestamp}"
        )

    return HistoryEvent(timestamp=timestamp, work_item_id=work_item_id, reason=reason)
```

#### 7. Bulk Refactor with grep + sed

For large-scale fixture updates, use grep to find all naive datetimes and replace them:

```bash
# Dry-run: show all naive datetime.now() in test files
grep -rn "datetime.now()" tests/unit/automation/ --include="*.py" | grep -v timezone

# Identify which files need changes
grep -l "datetime.now()" tests/unit/automation/**/*.py | while read f; do
  if ! grep -q "timezone.utc" "$f"; then
    echo "$f needs update"
  fi
done

# Update: import timezone at the top, replace datetime.now() with datetime.now(timezone.utc)
# (Use manual file edits or a careful sed script to avoid false positives)
```

Safe multi-line replacement:

```bash
# Before running any replacement, review the file manually
# Then use a script to add the import and update calls:
python3 << 'EOF'
import re
from pathlib import Path

test_file = Path("tests/unit/automation/pipeline/test_work_item.py")
content = test_file.read_text()

# Add timezone import if not present
if "from datetime import" in content and "timezone" not in content:
    content = re.sub(
        r"from datetime import ([^\n]+)",
        r"from datetime import \1, timezone",
        content,
    )

# Replace datetime.now() with datetime.now(timezone.utc)
content = content.replace("datetime.now()", "datetime.now(timezone.utc)")

test_file.write_text(content)
print(f"Updated {test_file}")
EOF
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use naive datetime in fixture, rely on implicit conversion | `HistoryEvent(timestamp=datetime.now(), ...)` | Production code enforces tz-aware, raises `TypeError: can't compare offset-naive and offset-aware datetimes` at comparison time in integration tests | Fixtures must enforce the same invariants as production; don't rely on implicit conversion |
| Add tz-aware check in one test, leave others naive | Fixed 1 of 3 fixtures | Inconsistent state: some tests pass, others fail with timezone comparison errors → non-reproducible, flaky CI | Fix ALL fixtures at once; partial fixes create a false sense of completion and new failures on other tests |
| Use `datetime.utcnow()` instead of `datetime.now(timezone.utc)` | `datetime.utcnow()` (deprecated in Python 3.12+) | No timezone info attached; `utcnow()` returns naive datetime that LOOKS like UTC but isn't tz-aware | Always use `datetime.now(timezone.utc)` (Python 3.10+); it's explicit, tz-aware, and future-proof |
| Document the invariant but don't enforce it in fixtures | Added comment "Use tz-aware UTC" in docstring | Developers missed the comment, new fixtures still used naive datetime → same bugs reappeared | Enforce with runtime checks: `if dt.tzinfo is None: raise ValueError(...)` in fixture factory functions |
| Only check the fixture creation; skip comparison sites | Fixed `HistoryEvent(timestamp=datetime.now(timezone.utc))` | Forgot that test assertions compare the fixture timestamp with a naive `expected_time = datetime.now()` → comparison still fails | Audit both creation AND comparison sites; check all `datetime.now()` calls in the test file |
| Use a different timezone (e.g., `timezone(timedelta(hours=-5))`) | Thought any tz-aware would work | Production contract specifies UTC, not arbitrary timezone → data serialization and event coordination broke | Use UTC specifically; the production contract is UTC, and fixtures must match |
| Parametrize fixture timezone in test | `@pytest.mark.parametrize("tz", [timezone.utc, timezone(timedelta(hours=-5))])` | Coordination layer expects UTC; tests passing with a different timezone masked a real bug | Fixtures should use the SAME timezone as production (UTC); tests don't parametrize the contract |

## Results & Parameters

- Fixture pattern: `datetime.now(timezone.utc)` for all temporal data
- Production invariant: all timestamps in coordination layer (WorkItem, HistoryEvent, Event) are tz-aware UTC
- Comparison pattern: both sides must be tz-aware; use `datetime(..., tzinfo=timezone.utc)` for hardcoded times
- Runtime guard: `if dt.tzinfo is None: raise ValueError(...)` in fixture factories
- No deprecation: avoid `datetime.utcnow()` (deprecated Python 3.12+); use `datetime.now(timezone.utc)`

Measured outcomes from ProjectHephaestus pipeline PR #1833:

| Check | Result |
| -------- | ------- |
| Fixtures audited | 3 HistoryEvent fixtures |
| Naive datetime fixes | 3 → 3 all tz-aware UTC |
| Integration test passes | 58 tests pass, verified-ci |
| Comparison failures | 0 (no timezone comparison errors) |
| CI timezone bugs | 0 |

Run command:

```bash
pixi run pytest tests/unit/automation/pipeline/test_work_item.py -v
pixi run pytest tests/unit/automation/pipeline/test_routing_properties.py -v
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Pipeline foundation epic #1809, sub-issue #1811, PR #1833 | Refactored HistoryEvent fixtures to tz-aware UTC, all 58 tests pass, verified-ci |
