# Session Notes: Fix Flaky Sleep Mock

## Session Context

- **Date**: 2026-02-27
- **Repo**: ProjectScylla / worktree `issue-1147`
- **Branch**: `1147-auto-impl`
- **Issue**: #1147 — [Test] Fix flaky test_exponential_backoff_delay in test_retry.py

## What Was Done

### Problem Statement

`tests/unit/automation/test_retry.py::TestRetryWithBackoff::test_exponential_backoff_delay`
failed in full test suite runs but passed in isolation. Issue #1147 is a follow-up to #1110.

A prior partial fix (commit `2f5219c`) had added `@pytest.mark.skipif(COVERAGE_RUN == "1")`
to work around coverage-run failures, but the root cause (wall-clock timing assertion) remained.

### Root Cause Analysis

```python
# retry.py uses:
import time
time.sleep(delay)
```

The test used:
```python
start = time.time()
result = decorated()
elapsed = time.time() - start
assert elapsed >= 0.3
```

This is flaky because:
1. Full suite runs have high CPU/IO contention
2. OS scheduler can defer `time.sleep` wakeup
3. Coverage instrumentation adds overhead between sleep calls

### Fix Applied

Three changes to `tests/unit/automation/test_retry.py`:

1. **Removed** `import os` and `import time` (unused after fix)
2. **Replaced** `from unittest.mock import MagicMock` with `from unittest.mock import MagicMock, patch`
3. **Rewrote** `test_exponential_backoff_delay`:
   - Removed `@pytest.mark.skipif(COVERAGE_RUN == "1", ...)` decorator
   - Replaced wall-clock `elapsed >= 0.3` assertion with `patch("scylla.automation.retry.time.sleep")`
   - Asserts `mock_sleep.call_count == 2` and `mock_sleep.assert_any_call(0.1)` / `assert_any_call(0.2)`
4. **Fixed** `test_uses_longer_initial_delay` patch path:
   - Was: `patch("time.sleep")` — wrong namespace
   - Fixed: `patch("scylla.automation.retry.time.sleep")` — correct namespace

### Results

- 16 tests in `test_retry.py`: all pass
- 3257 tests in full suite: all pass
- Coverage: 78.38% (above 75% threshold)
- PR #1217 created, auto-merge enabled

## Diff Summary

```diff
-import os
-import time
-from unittest.mock import MagicMock
+from unittest.mock import MagicMock, patch

-    @pytest.mark.skipif(
-        os.getenv("COVERAGE_RUN") == "1", reason="Skipped when running under coverage"
-    )
     def test_exponential_backoff_delay(self):
-        """Test exponential backoff delays."""
+        """Test exponential backoff delays are calculated correctly."""
         mock_func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
         decorated = retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2)(
             mock_func
         )

-        start = time.time()
-        result = decorated()
-        elapsed = time.time() - start
+        with patch("scylla.automation.retry.time.sleep") as mock_sleep:
+            result = decorated()

         assert result == "success"
-        # Should wait 0.1 + 0.2 = 0.3 seconds minimum
-        assert elapsed >= 0.3
+        assert mock_func.call_count == 3
+        # Two failures → two sleep calls: 0.1*2^0=0.1, 0.1*2^1=0.2
+        assert mock_sleep.call_count == 2
+        mock_sleep.assert_any_call(0.1)
+        mock_sleep.assert_any_call(0.2)

     def test_uses_longer_initial_delay(self):
         """Test retry_on_network_error uses 2.0s initial delay."""
-        from unittest.mock import patch
-
         mock_func = MagicMock(side_effect=[ConnectionError("fail"), "success"])
         decorated = retry_on_network_error(max_retries=1)(mock_func)

-        with patch("time.sleep") as mock_sleep:
+        with patch("scylla.automation.retry.time.sleep") as mock_sleep:
```

## Key Command Reference

```bash
# Run just the retry tests
pixi run python -m pytest tests/unit/automation/test_retry.py -v

# Run full unit suite without coverage
pixi run python -m pytest tests/unit/ --no-cov -q

# Check pre-push hook runs full suite with coverage
git push -u origin 1147-auto-impl
```