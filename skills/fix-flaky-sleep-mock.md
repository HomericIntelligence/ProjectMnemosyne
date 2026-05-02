---
name: fix-flaky-sleep-mock
description: Fix timing-sensitive tests by replacing wall-clock assertions with deterministic time.sleep mocks
category: testing
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Fix Flaky Sleep Mock

## Overview

| Item | Details |
| ------ | --------- |
| **Date** | 2026-02-27 |
| **Objective** | Fix `test_exponential_backoff_delay` flaky failure in `test_retry.py` — passes in isolation, fails in full-suite runs |
| **Outcome** | ✅ SUCCESS — All 3257 tests pass, deterministic mock replaces wall-clock timing |
| **Issue** | #1147 (follow-up from #1110) |
| **PR** | #1217 |

## When to Use This Skill

Use this skill when:

1. **A test passes in isolation but fails in the full test suite** — classic flakiness indicator
2. **Test uses `time.time()` start/stop to measure elapsed duration** with an `assert elapsed >= N` pattern
3. **Test has a `@pytest.mark.skipif(COVERAGE_RUN == "1")` workaround** — sign of a timing-sensitive test
4. **A decorator or utility calls `time.sleep()` internally** and the test tries to measure that sleep externally
5. **Retry/backoff utilities** with `initial_delay`, `backoff_factor`, `max_retries` parameters

### Problem Indicators

```python
# RED FLAG: wall-clock timing assertion
start = time.time()
result = decorated()
elapsed = time.time() - start
assert elapsed >= 0.3  # FLAKY under CPU contention

# RED FLAG: skip workaround hiding flakiness
@pytest.mark.skipif(
    os.getenv("COVERAGE_RUN") == "1", reason="Skipped when running under coverage"
)
def test_exponential_backoff_delay(self): ...
```

## Root Cause

When a function under test calls `time.sleep()` internally, measuring wall-clock elapsed time is
unreliable because:

- Full suite runs have high CPU contention from concurrent test processes
- Coverage instrumentation adds overhead, causing sleep-start delays
- OS scheduler jitter can cause actual elapsed time to be less than the sum of `sleep()` calls
- The test was previously patched with `COVERAGE_RUN` skip instead of proper mocking

## Verified Workflow

### 1. Identify the Patch Target

**Find how the module imports `time.sleep`:**

```python
# retry.py — uses module-level import
import time
# ...
time.sleep(delay)  # ← patch target: "scylla.automation.retry.time.sleep"
```

**vs. direct function import:**

```python
from time import sleep
sleep(delay)  # ← patch target: "scylla.automation.retry.sleep"
```

The patch path must match WHERE the name is looked up, not where it is defined.

### 2. Replace Wall-Clock Assertion with sleep Mock

**Before (flaky):**
```python
import os
import time
from unittest.mock import MagicMock

@pytest.mark.skipif(
    os.getenv("COVERAGE_RUN") == "1", reason="Skipped when running under coverage"
)
def test_exponential_backoff_delay(self):
    mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
    decorated = retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2)(mock_func)

    start = time.time()
    result = decorated()
    elapsed = time.time() - start

    assert result == "success"
    assert elapsed >= 0.3  # FLAKY
```

**After (deterministic):**
```python
from unittest.mock import MagicMock, patch

def test_exponential_backoff_delay(self):
    """Test exponential backoff delays are calculated correctly."""
    mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
    decorated = retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2)(mock_func)

    with patch("scylla.automation.retry.time.sleep") as mock_sleep:
        result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3
    # Two failures → two sleep calls: 0.1*2^0=0.1, 0.1*2^1=0.2
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(0.1)
    mock_sleep.assert_any_call(0.2)
```

### 3. Fix Related Tests Using Wrong Patch Path

Check all other tests in the file that patch `time.sleep`:

```python
# WRONG: patches the stdlib module globally (may not intercept module-level usage)
with patch("time.sleep") as mock_sleep:

# CORRECT: patches the name as imported in the module under test
with patch("scylla.automation.retry.time.sleep") as mock_sleep:
```

### 4. Clean Up Unused Imports

After mocking, remove unused imports:

```python
# Remove these (no longer needed):
import os
import time

# Consolidate mock imports:
from unittest.mock import MagicMock, patch
```

### 5. Verify the Fix

```bash
# Run the specific test file
pixi run python -m pytest tests/unit/automation/test_retry.py -v

# Run isolation vs full suite (confirm no flakiness)
pixi run python -m pytest tests/unit/ --no-cov -q
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Files Changed

| File | Change |
| ------ | -------- |
| `tests/unit/automation/test_retry.py` | Replace wall-clock with mock; fix patch path; remove unused imports |

### Retry Module Parameters (for context)

```python
# scylla/automation/retry.py
def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: int = 2,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    logger: Callable[[str], None] | None = None,
) -> Callable[[F], F]:
    # Delay formula: initial_delay * (backoff_factor ** attempt)
    # attempt=0 → delay=0.1; attempt=1 → delay=0.2
    delay = initial_delay * (backoff_factor**attempt)
    time.sleep(delay)
```

### Test Outcome

```
tests/unit/automation/test_retry.py::TestRetryWithBackoff::test_exponential_backoff_delay PASSED
============================= 16 passed in 7.63s ==============================
# Full suite: 3257 passed, coverage 78.38% ✅
```

## Key Insights

### 1. Patch Path Must Match Import Style

```python
# Module uses:  import time; time.sleep(delay)
# Correct patch: "module.path.time.sleep"

# Module uses:  from time import sleep; sleep(delay)
# Correct patch: "module.path.sleep"
```

### 2. Assert Call Values, Not Wall Time

Mock tests are more precise and stable:
- Assert `mock_sleep.call_count == N` (number of retries)
- Assert `mock_sleep.assert_any_call(expected_delay)` (backoff formula)
- Verifies BOTH that sleep happens AND the delay value is correct

### 3. Skip Workarounds Are Tech Debt

`@pytest.mark.skipif(COVERAGE_RUN)` masks flakiness. If a test needs a timing
workaround, refactor to use mocks instead of skipping.

### 4. Full Suite Pressure Exposes Flakiness

Run suspect tests in full suite context:
```bash
pixi run python -m pytest tests/ --no-cov -q 2>&1 | grep -E "(PASSED|FAILED|ERROR)" | grep test_retry
```

## Related Skills

- `resolve-skipped-tests` — Removing skip workarounds from tests
- `fix-ci-test-failures` — Diagnosing and fixing CI-only failures
- `pytest-real-io-testing` — When to use real vs mocked I/O

## Prevention

### For New Retry/Backoff Tests

Always mock `time.sleep` from the start:

```python
def test_backoff_delays(self):
    with patch("your.module.time.sleep") as mock_sleep:
        # ... call decorated function ...
    mock_sleep.assert_called_with(expected_delay)
```

### For Any Test That Measures Duration

- Use mocks for `time.sleep`, `time.time`, `datetime.now`
- Never use `assert elapsed >= N` — too environment-sensitive
- If you must test real timing (performance), use `pytest-benchmark` instead
