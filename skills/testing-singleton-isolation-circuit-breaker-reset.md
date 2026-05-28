---
name: testing-singleton-isolation-circuit-breaker-reset
description: "Test isolation for module-level singleton instances (e.g., circuit breaker) requires calling .reset() on the held reference directly in pytest fixture. Simply clearing a registry does not reset the held instance. Use when: testing code with module-level singleton instances (breakers, caches, registries) that maintain internal state across test runs."
category: testing
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - test-isolation
  - singleton
  - circuit-breaker
  - pytest-fixture
  - stateful-objects
---

# Testing: Singleton Isolation — Circuit Breaker Reset Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Ensure test isolation for module-level singleton instances by resetting held instance state, not just clearing registries |
| **Outcome** | 5 circuit breaker tests passing with proper isolation; no test state leakage |
| **Verification** | verified-ci |

## When to Use

- Testing code with module-level singleton instances (circuit breaker, cache, connection pool, registry)
- Singleton maintains internal state (failure counter, open/closed state, reset timer) across test runs
- Simply clearing a registry does not reset the held instance
- Tests must be independent and repeatably pass in any order
- Fixture must reset state both before AND after each test (setup + teardown)

## Verified Workflow

### Quick Reference

```python
# Module under test: hephaestus/automation/github_api.py
_GH_BREAKER = CircuitBreaker(fail_max=5, reset_timeout=60)

def _gh_call(cmd):
    try:
        return _GH_BREAKER.call(_gh_subprocess_call, cmd=cmd)
    except CircuitBreakerOpenError as exc:
        raise GitHubUnavailableError(...) from exc

# Test file: tests/unit/automation/test_gh_call_circuit_breaker.py
import pytest
from hephaestus.automation import github_api
from hephaestus.resilience.circuit_breaker import reset_all_circuit_breakers

@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset circuit breaker before and after each test."""
    # IMPORTANT: Reset the held instance directly, not just registry
    github_api._GH_BREAKER.reset()
    yield
    github_api._GH_BREAKER.reset()

def test_breaker_opens_after_5_failures(monkeypatch):
    """Breaker opens after fail_max consecutive failures."""
    # Test runs with clean breaker state
    # No carry-over from previous tests
    ...

def test_breaker_closes_after_reset_timeout(monkeypatch):
    """Breaker transitions to half-open after reset_timeout."""
    # Again, clean breaker state from fixture
    ...
```

### Detailed Steps

1. **Identify the module-level singleton instance**:
   ```python
   # In hephaestus/automation/github_api.py (module level)
   _GH_BREAKER = CircuitBreaker(fail_max=5, reset_timeout=60)
   ```

2. **Understand what state the singleton holds**:
   - Circuit breaker: fail_counter, state (CLOSED/OPEN/HALF_OPEN), last_failure_time
   - Cache: entries, hit/miss counts
   - Connection pool: active connections, pending queue
   - Any instance variable that persists across calls

3. **Create a pytest fixture with autouse=True**:
   ```python
   @pytest.fixture(autouse=True)
   def _reset_breaker():
       """Reset circuit breaker state for test isolation."""
       # Setup: reset before test
       github_api._GH_BREAKER.reset()
       yield
       # Teardown: reset after test
       github_api._GH_BREAKER.reset()
   ```

4. **Import the module containing the singleton**:
   ```python
   import hephaestus.automation.github_api as github_api
   
   # Directly access the module-level instance
   github_api._GH_BREAKER.reset()
   ```

5. **DO NOT rely on clearing a registry alone**:
   ```python
   # ❌ WRONG: This does not reset the held instance
   reset_all_circuit_breakers()  # clears registry only
   # _GH_BREAKER is still in memory with old state
   
   # ✅ CORRECT: Reset the held instance directly
   github_api._GH_BREAKER.reset()
   ```

6. **Reset both before and after (setup + teardown)**:
   - Before: ensure test starts clean even if previous test crashed
   - After: ensure next test doesn't inherit this test's state

7. **Verify isolation with parametrized tests**:
   ```python
   @pytest.mark.parametrize("test_order", [0, 1, 2])
   def test_order_independent(test_order):
       """Tests should pass in any order."""
       # If isolation works, passing test_order=2 first gives same result as 0,1,2 sequence
       ...
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Clearing the circuit breaker registry in conftest.py: `reset_all_circuit_breakers()` | Registry was cleared, but the module-level _GH_BREAKER instance still held old state (fail_counter=5, OPEN). Subsequent tests saw breaker still open. | Clearing a registry is not the same as resetting an instance. The held reference _GH_BREAKER is a separate object that must be reset directly. |
| 2 | Assuming pytest automatically resets module-level instances between tests | No such mechanism exists. Module-level instances persist in memory for the lifetime of the Python process. Tests inherit the previous test's state. | Fixture must explicitly reset state. No automatic cleanup without code. |
| 3 | Using `pytest.monkeypatch` to replace the breaker with a fresh one: `monkeypatch.setattr(github_api, "_GH_BREAKER", CircuitBreaker(...))` | Works, but requires instantiating a new CircuitBreaker per test (expensive). Also fragile: if later code imports _GH_BREAKER directly, monkeypatch won't affect it. | Just call reset() on the existing instance — simpler, faster, less fragile. |
| 4 | Resetting the breaker only in fixture setup, not teardown | If a test crashed or was interrupted, subsequent tests started with dirty state. Isolation was conditional on test success. | Always reset in both setup and teardown (yield pattern). Ensures clean state even if previous test failed. |
| 5 | Using module-scope fixture instead of function-scope | Multiple tests in one module share the same fixture run. Cross-test pollution still happened. | Use `@pytest.fixture(autouse=True)` with default function scope (resets for each test). |
| 6 | Trying to patch CircuitBreaker.reset() method | Would break actual reset calls in production code; confusing test vs. production behavior. | Don't patch the reset method; just call it normally. |

## Results & Parameters

### Circuit Breaker Reset Fixture (Copy-Paste Ready)

```python
# tests/unit/automation/test_gh_call_circuit_breaker.py

import pytest
from unittest.mock import patch, MagicMock

from hephaestus.automation.github_api import _gh_call, GitHubUnavailableError
from hephaestus.automation import github_api

@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset circuit breaker before and after each test for isolation.
    
    CRITICAL: This fixture resets the module-level _GH_BREAKER instance
    directly. Do not rely on registry cleanup alone.
    """
    # Setup: clean state before test
    github_api._GH_BREAKER.reset()
    yield
    # Teardown: clean state after test
    github_api._GH_BREAKER.reset()
```

### Full Test Suite Example

```python
# tests/unit/automation/test_gh_call_circuit_breaker.py

import pytest
from unittest.mock import patch
from subprocess import CalledProcessError

from hephaestus.automation.github_api import _gh_call, GitHubUnavailableError
from hephaestus.automation import github_api

@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset circuit breaker for test isolation."""
    github_api._GH_BREAKER.reset()
    yield
    github_api._GH_BREAKER.reset()

class TestCircuitBreakerIntegration:
    """Test circuit breaker integration in _gh_call()."""
    
    def test_breaker_opens_after_5_failures(self, monkeypatch):
        """Breaker opens (raises GitHubUnavailableError) after 5 failures."""
        call_count = 0
        
        def mock_subprocess_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise CalledProcessError(1, "gh")
        
        monkeypatch.setattr(
            "hephaestus.automation.github_api._gh_subprocess_call",
            mock_subprocess_call,
        )
        
        # Fail 5 times (triggers breaker)
        for i in range(5):
            with pytest.raises(CalledProcessError):
                _gh_call(["pr", "view", "123"])
        
        # 6th call should raise GitHubUnavailableError (breaker open)
        with pytest.raises(GitHubUnavailableError, match="circuit open"):
            _gh_call(["pr", "view", "123"])
        
        # Verify subprocess was called exactly 5 times (not 6)
        assert call_count == 5
    
    def test_breaker_allows_calls_when_closed(self, monkeypatch):
        """Breaker allows calls when closed (success case)."""
        monkeypatch.setattr(
            "hephaestus.automation.github_api._gh_subprocess_call",
            lambda **kwargs: '{"state": "OPEN"}',
        )
        
        # Should succeed without raising
        result = _gh_call(["pr", "view", "123", "--json=state"])
        assert result == '{"state": "OPEN"}'
    
    def test_breaker_half_open_succeeds_closes_breaker(self, monkeypatch):
        """Breaker transitions to closed after successful call in half-open state."""
        call_sequence = [
            ("fail1", True),
            ("fail2", True),
            ("fail3", True),
            ("fail4", True),
            ("fail5", True),
            ("success", False),  # This succeeds, breaker closes
        ]
        
        call_index = [0]  # mutable counter
        
        def mock_subprocess_call(**kwargs):
            idx = call_index[0]
            call_index[0] += 1
            label, should_fail = call_sequence[idx]
            
            if should_fail:
                raise CalledProcessError(1, "gh")
            return f'{{"status": "{label}"}}'
        
        monkeypatch.setattr(
            "hephaestus.automation.github_api._gh_subprocess_call",
            mock_subprocess_call,
        )
        
        # Fail 5 times (breaker opens)
        for _ in range(5):
            with pytest.raises(CalledProcessError):
                _gh_call(["pr", "view", "123"])
        
        # Fast-forward reset_timeout
        github_api._GH_BREAKER.opened_at = 0
        
        # Next call succeeds, breaker closes
        result = _gh_call(["pr", "view", "123"])
        assert "success" in result
    
    def test_isolation_order_independent(self):
        """Tests can run in any order with proper fixture isolation."""
        # If this test runs after test_breaker_opens_after_5_failures,
        # _GH_BREAKER was reset by fixture, so it's still CLOSED
        assert github_api._GH_BREAKER.state == "closed"
```

### CircuitBreaker.reset() Method Location

The reset() method typically appears in the breaker implementation:

```python
# hephaestus/resilience/circuit_breaker.py

class CircuitBreaker:
    def reset(self):
        """Reset breaker state to CLOSED and clear failure counter.
        
        Used for test isolation and manual recovery.
        """
        self.fail_counter = 0
        self.opened_at = None
        self.state = "closed"  # or "CLOSED" depending on implementation
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — CircuitBreaker testing | tests/unit/automation/test_gh_call_circuit_breaker.py; 5 tests all passing; no cross-test state leakage |
