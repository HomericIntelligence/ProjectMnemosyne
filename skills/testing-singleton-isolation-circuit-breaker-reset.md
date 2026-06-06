---
name: testing-singleton-isolation-circuit-breaker-reset
description: "Test isolation for module-level singleton instances (e.g., circuit breaker, cache, registry) requires calling .reset() on the held reference directly — in a pytest autouse fixture in conftest.py at the broadest scope, OR at the top of any new test that trips the singleton — not via a registry-clearing reset helper that orphans the import-time-bound instance. Use when: (1) adding tests that intentionally trigger failures/exceptions to a class whose code path goes through a module-level circuit breaker / rate limiter / retry primitive, (2) new tests pass in isolation but make UNRELATED sibling tests fail with a 'circuit breaker is open'/unavailable error when the whole class runs, (3) a reset helper clears a registry (`_registry.clear()`) rather than resetting the import-time-bound instance, (4) testing code with module-level singleton instances (breakers, caches, registries, contextvar defaults) that maintain internal state across test runs, (5) a test passes locally in isolation but fails in CI with cross-test contamination, (6) the same test fails identically on multiple Python versions in CI (3.10/3.11/3.12/3.13) — a fingerprint of order-dependent shared state, (7) deciding where to put a pytest autouse fixture: single test file vs package conftest.py, (8) extending a non-transient/fail-fast error classifier and verifying it, (9) deciding whether HTTP 422 or GraphQL schema errors should be retried (they should NOT — they are deterministic)."
category: testing
date: 2026-06-06
version: "1.2.0"
user-invocable: false
history: testing-singleton-isolation-circuit-breaker-reset.history
verification: verified-ci
tags:
  - test-isolation
  - singleton
  - circuit-breaker
  - module-singleton
  - test-pollution
  - shared-state
  - pytest-fixture
  - autouse-fixture
  - conftest-scope
  - cross-test-contamination
  - ci-only-failure
  - stateful-objects
  - fail-fast
  - non-transient-retry
  - registry-reset
  - github-api
  - 422
  - graphql-schema-error
---

# Testing: Singleton Isolation — Circuit Breaker Reset Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Ensure test isolation for module-level singleton instances by (a) resetting the held instance state, not just clearing registries, (b) putting the autouse reset fixture in `conftest.py` at the broadest scope OR calling `module._BREAKER.reset()` at the top of any new failure-triggering test, and (c) ALWAYS running the full test class/module so shared-state pollution surfaces |
| **Outcome** | v1.0.0: 5 circuit breaker tests passing in `test_gh_call_circuit_breaker.py`. v1.1.0: cross-test contamination fixed in `tests/unit/automation/` after moving the fixture into a package-level conftest. v1.2.0: adding 2 new fail-fast tests turned 5 unrelated sibling tests red (shared `_GH_BREAKER` pushed OPEN); fixed by `module._GH_BREAKER.reset()` at each new test's top. Bundled with the 422/GraphQL non-transient retry-classifier fix that motivated the new tests. |
| **Verification** | v1.0.0 verified-ci. v1.1.0 verified-ci (bug) / verified-local (fix). v1.2.0 **verified-ci** — fix merged to ProjectHephaestus main (PR #1042, closes #1040). |

## When to Use

- Testing code with module-level singleton instances (circuit breaker, cache, connection pool, registry, contextvar default, env-var snapshot)
- Singleton maintains internal state (failure counter, open/closed state, reset timer) across test runs
- Simply clearing a registry does not reset the held instance
- Tests must be independent and repeatably pass in any order
- Fixture must reset state both before AND after each test (setup + teardown)
- **A test passes locally in isolation but fails in CI** — classic order-dependent contamination signature
- **The same test fails identically on multiple Python versions in CI (3.10/3.11/3.12/3.13)** — singleton state is a deterministic shared resource; parallel Python versions reproduce the same test order and therefore the same contamination
- **Deciding the scope of an autouse reset fixture**: it MUST live in `conftest.py` at the broadest package scope where any contaminating test lives. Putting it in a single `test_*.py` file only protects that file
- **Adding tests that intentionally trigger failures/exceptions** to a class whose code path goes through a module-level circuit breaker / rate limiter / retry primitive — each raised exception (even a deterministic fail-fast one) counts as a breaker failure and accumulates toward the OPEN threshold
- **New tests pass in isolation but make UNRELATED sibling tests fail** with a "circuit breaker is open" / unavailable error when the WHOLE class runs in file order — the signature of shared-state pollution from a module-level singleton
- **A reset helper clears a registry** (`reset_all_circuit_breakers()` → resets each breaker then `_registry.clear()`) rather than resetting the import-time-bound instance — the helper ORPHANS the import-time `_GH_BREAKER`, so it keeps accumulating state across tests
- **Extending a non-transient / fail-fast error classifier and verifying it** — e.g. adding patterns to `_NON_TRANSIENT_PATTERNS`. The new failing-call tests you write to verify it are exactly the tests that trip the shared breaker
- **Deciding whether HTTP 422 / "unprocessable entity" or GraphQL schema errors should be retried** — they should NOT. They are deterministic; retrying can never succeed and wastes ~31s/failure (5 attempts × `2**attempt` backoff)

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

### Conftest Scope Pattern (v1.1.0)

The fixture above is correct, but its LOCATION matters as much as its content. If it lives only inside `test_gh_call_circuit_breaker.py`, sibling tests in the same package — e.g. `test_pr_reviewer_posting.py` — do NOT get reset. They will inherit the OPEN-breaker state from any earlier test that tripped it.

The fix: lift the autouse fixture into the package-level `conftest.py`.

```text
tests/unit/automation/
├── conftest.py                       # ← autouse fixture LIVES HERE
├── test_github_api.py                # ← no longer needs its own copy
├── test_gh_call_circuit_breaker.py   # ← no longer needs its own copy
├── test_pr_reviewer_posting.py       # ← now protected (was contaminated)
└── ... every other test_*.py in the subtree is automatically protected
```

```python
# tests/unit/automation/conftest.py
"""Package-level fixtures for automation tests.

Lives at the broadest scope covering any test that mutates the
GitHub circuit breaker singleton, so EVERY test in this subtree
runs with a clean breaker. Do not duplicate this fixture inside
individual test_*.py files.
"""

import pytest
from hephaestus.automation import github_api


@pytest.fixture(autouse=True)
def _reset_circuit_breakers():
    """Reset the GitHub circuit breaker before and after each test.

    Why here, not in a single test file?

    The `_GH_BREAKER` singleton lives at module scope in
    `hephaestus.automation.github_api`. Any test in this package
    that exercises a failure path can trip it. Once tripped, the
    OPEN state persists across test files in the same pytest
    session. Tests later in the run order then see a generic
    "circuit breaker is open" message instead of the domain
    error they were asserting on, and they fail in CI even though
    they pass locally in isolation.
    """
    github_api._GH_BREAKER.reset()
    yield
    github_api._GH_BREAKER.reset()
```

#### How to verify the scope is right

Replicate CI's order-dependent contamination in one local pytest invocation by running the contaminating file FIRST, then the previously-failing file:

```bash
pixi run pytest \
    tests/unit/automation/test_github_api.py \
    tests/unit/automation/test_pr_reviewer_posting.py \
    -v
```

If both pass, the conftest scope is broad enough. If the second file still fails with the breaker-open error, the conftest needs to be lifted higher (e.g. `tests/unit/conftest.py` or `tests/conftest.py`).

#### Choosing the right conftest level

| Where the singleton is tripped | Where the autouse reset belongs |
|--------------------------------|---------------------------------|
| One test file only             | That file (rare — usually wrong) |
| Multiple files in one package  | `tests/<package>/conftest.py`   |
| Multiple packages              | `tests/conftest.py` (top-level) |
| Across unit + integration      | `tests/conftest.py` (top-level) |

The cost of running the reset on a test that doesn't need it is negligible (a few attribute writes). The cost of a single order-dependent CI flake is hours of debugging. Default to the broader scope when in doubt.

### Fail-Fast Test Pattern (v1.2.0) — reset the bound instance at the test top

`setup_method` is not always enough. The automation test class calls
`reset_all_circuit_breakers()` in `setup_method`, but that helper resets each
registered breaker and then does `_registry.clear()`. The import-time-bound
`_GH_BREAKER` singleton in `hephaestus/automation/github_api.py` is created at
module import; once the registry is cleared, the helper no longer touches that
orphaned instance. So `setup_method` gives a FALSE sense of isolation.

The consequence: adding new tests that intentionally trigger a *fail-fast*
(non-transient) error still raises an exception, and **every raised exception —
even one that fails fast on the first attempt — counts as one breaker failure**.
With `failure_threshold=5`, adding two new failure-triggering tests near the top
of the class pushed `_GH_BREAKER` to 5 accumulated failures and OPEN. The next
five sibling tests then failed with
`GitHubUnavailableError: circuit breaker is open` — even though each new test
caused only ONE failure on its own.

The fix matches the file's existing `test_circuit_breaker_wraps_gh_call_impl`
pattern: any new test that triggers a breaker failure must reset the bound
instance DIRECTLY at the top, not rely on the registry-clearing helper.

```python
from hephaestus.automation import github_api as module

def test_my_new_fail_fast_error(monkeypatch):
    module._GH_BREAKER.reset()  # ← reset the bound instance, not the registry
    # ... arrange a deterministic 422 / GraphQL-schema failure ...
    with pytest.raises(SomeError):
        module._gh_call([...])
```

#### Why setup_method's helper does not protect it

```python
# hephaestus/resilience/circuit_breaker.py  (sketch)
def reset_all_circuit_breakers():
    for breaker in _registry.values():
        breaker.reset()
    _registry.clear()          # ← orphans any import-time-bound reference
```

`_GH_BREAKER` is bound once at import time. After `_registry.clear()`, future
calls to the helper iterate an empty registry and never touch `_GH_BREAKER`.
The held module attribute keeps its accumulated `fail_counter` / OPEN state.

#### The 422 / GraphQL-schema retry-classifier fix that motivated the new tests

`_NON_TRANSIENT_PATTERNS` in `hephaestus/automation/github_api.py` classifies
which `gh` failures are non-retryable so `_gh_call_impl` fails fast instead of
retrying 5× with `2**attempt` backoff (~31s wasted per deterministic failure).
It listed 403/404/400/401/invalid-argument/unknown-json-field/token-scope but
OMITTED HTTP 422 ("unprocessable entity") AND GraphQL schema errors. Those are
deterministic — retrying can never succeed. The fix adds three patterns:

```python
_NON_TRANSIENT_PATTERNS = [
    # ... existing 403/404/400/401/invalid-argument/... patterns ...
    r"(?:^|\s)422(?:\s|$)|unprocessable entity",
    r"doesn't accept argument",
    r"is declared by .* but not used",
]
```

Verifying that fix required adding tests that assert these errors raise WITHOUT
retrying — and those very tests are what tripped the shared breaker, which is
how the test-pollution bug surfaced.

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
| 7 | Putting the autouse reset fixture in a single test file (`test_github_api.py`) instead of `conftest.py` | Only protected `test_github_api.py`. Sibling files in the same package (e.g. `test_pr_reviewer_posting.py`) still inherited the OPEN-breaker state. CI failed identically on Python 3.10/3.11/3.12/3.13 — the deterministic test order tripped the breaker before the affected test ran. (ProjectHephaestus PR #707, fixed in commit `3e4bc10`.) | The autouse reset fixture belongs in `conftest.py` at the broadest scope covering any contaminating test, not in a single test file. |
| 8 | Widening the failing assertion to tolerate the breaker-open message (e.g. `assert '#0' in err or 'circuit breaker' in err`) | Papered over the contamination. The domain-specific `#0` diagnostic (issue-not-found) was the whole point of the test; allowing the generic breaker message meant any real regression of that diagnostic would silently slip through. | Fix the isolation, do not widen the assertion. If your test "fails" because the wrong error appeared, the wrong error is the bug, not the assertion. |
| 9 | Per-test `monkeypatch` on the singleton — `monkeypatch.setattr(github_api, "_GH_BREAKER", CircuitBreaker(...))` inside each test | Only patches the lookup `github_api._GH_BREAKER`, not the underlying held state in other modules that may have already imported the original. Also: the next test re-instantiates and the original singleton (if accessed via `import hephaestus.automation.github_api`) is still in OPEN state. | Reset the existing instance, do not replace it. `instance.reset()` is simpler, faster, and avoids reference-aliasing bugs. |
| 10 | Per-test reset inside each test function body (no fixture) | DRY violation. Easy to forget on a new test. The forgotten test then becomes the contaminator for every test that runs after it in CI order. | Use `@pytest.fixture(autouse=True)` in `conftest.py`. Autouse means new tests added later are automatically protected. |
| 11 | Module-level `setup_module` / `teardown_module` | Resets at module boundaries only. Tests within a module still share state with tests in OTHER modules that ran in the same pytest session. | Use a function-scoped autouse fixture in `conftest.py`, not a module-level hook. |
| 12 | Relying on `reset_all_circuit_breakers()` in the class's `setup_method` to isolate new fail-fast tests | The helper resets each registered breaker then calls `_registry.clear()`, ORPHANING the import-time-bound `_GH_BREAKER`. After the first clear, the helper iterates an empty registry and never touches the singleton, which keeps accumulating `fail_counter`. Adding 2 fail-fast tests pushed it OPEN; 5 unrelated sibling tests then failed with `GitHubUnavailableError: circuit breaker is open`. | A registry-clearing reset helper does NOT protect import-time references. Reset the actual bound object: `module._GH_BREAKER.reset()` at the top of each failure-triggering test (matches the file's `test_circuit_breaker_wraps_gh_call_impl` pattern). |
| 13 | Running only the new test in isolation to confirm it works | Each new fail-fast test PASSES alone — no prior test ran, so the shared breaker was clean. The pollution only manifests when the WHOLE class runs in file order: the new tests trip the breaker before later siblings execute. On pristine main all tests passed; adding 2 tests turned 5 siblings red. | ALWAYS run the full test class/module (not just your new test) to catch shared-state pollution. "Passes in isolation" is the trap, not the proof. |
| 14 | Letting `_gh_call_impl` retry HTTP 422 / GraphQL-schema errors (no classifier entry) | 422 ("unprocessable entity") and GraphQL schema errors ("doesn't accept argument", "is declared by ... but not used") are deterministic — retrying can never succeed. `_gh_call_impl` retried them 5× with `2**attempt` backoff (~31s wasted per failure) before raising, AND each attempt is a breaker failure that worsens pollution. | Add deterministic failures to `_NON_TRANSIENT_PATTERNS` so they fail fast on attempt 1. Patterns added: `(?:^\|\s)422(?:\s\|$)\|unprocessable entity`, `doesn't accept argument`, `is declared by .* but not used`. |

## Results & Parameters

### v1.2.0 — Fail-Fast Test Reset + Non-Transient Retry Patterns

The one-line fix at the top of every new failure-triggering test:

```python
module._GH_BREAKER.reset()   # reset the BOUND instance, not the registry
```

The exact non-transient regex patterns added to `_NON_TRANSIENT_PATTERNS` in
`hephaestus/automation/github_api.py` so 422 / GraphQL-schema errors fail fast
(no retry, no extra breaker failures):

```python
r"(?:^|\s)422(?:\s|$)|unprocessable entity"
r"doesn't accept argument"
r"is declared by .* but not used"
```

| Parameter | Value | Why it matters |
|-----------|-------|----------------|
| `_GH_BREAKER` failure_threshold | 5 | Each raised exception (incl. fail-fast) = 1 failure; 5 across the class trips OPEN |
| Wasted time per un-classified deterministic failure | ~31s | 5 retries × `2**attempt` backoff before raising |
| Reset call | `module._GH_BREAKER.reset()` | Resets the import-time-bound instance directly |
| Anti-pattern | `reset_all_circuit_breakers()` in `setup_method` | Clears registry → orphans the bound singleton |
| Verification rule | run the WHOLE class/module | Pollution is invisible when the new test runs alone |

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

### General Pattern: Package-Shared Singletons That Need This Treatment

The circuit breaker is one example of a broader class. Any of these singletons benefits from a package-scoped autouse reset in `conftest.py`:

| Singleton family | Concrete example | Reset method |
|------------------|-----------------|--------------|
| Circuit breakers | `_GH_BREAKER`, `_NATS_BREAKER` | `.reset()` |
| In-memory caches | `@lru_cache`, custom dict caches, `functools.cache` | `cache.cache_clear()` or `dict.clear()` |
| Registry singletons | Plugin registries, agent registries, route maps | re-register from scratch, or `.clear()` |
| `contextvars` defaults | Trace-context, request-context | `var.set(default)` |
| Env-var snapshots | A module that captures `os.environ[...]` at import | re-read env, or `monkeypatch.setenv` + reload |
| Connection pools | DB connection pools, HTTP session singletons | `.close()` + new instance |
| Time / clock state | Frozen-time monkeypatches | restore wall-clock in teardown |

Rule of thumb: if reading a module attribute at test start ever shows a value that depends on what other tests did, that attribute needs a conftest-level autouse reset.

#### Why this bites only in CI

| Symptom | Why CI shows it but local does not |
|---------|------------------------------------|
| Test passes locally in isolation | Single-test run never executes the contaminator |
| Test passes in `pytest <one_file>` locally | Other files in the package are not collected; the contaminator never runs |
| Test passes locally on full suite | Local file iteration order may differ from CI (alphabetical, but filesystem-dependent) |
| Test fails identically on Python 3.10/3.11/3.12/3.13 in CI | Each Python version runs the same deterministic test order; the singleton is process-local but test-order-deterministic |
| Test passes under `pytest-xdist` workers | Each worker has its own process; the singleton is per-worker, hiding cross-file contamination unless both files land on the same worker |

The "passes locally" trap is real: running a single failing test in isolation always passes because no prior test has run.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — CircuitBreaker testing (v1.0.0) | tests/unit/automation/test_gh_call_circuit_breaker.py; 5 tests all passing; no cross-test state leakage |
| ProjectHephaestus | PR #707 — conftest scope fix (v1.1.0) | Cross-test contamination: `test_pr_reviewer_posting.py` failed identically on Python 3.10/3.11/3.12/3.13 in CI because the autouse breaker reset lived only in `test_github_api.py`. Fixed by moving the fixture into `tests/unit/automation/conftest.py` (commit `3e4bc10`). 911 tests pass locally under the new conftest scope; CI re-run pending at /learn time, hence v1.1.0 is **verified-local** for the fix, **verified-ci** for the bug. |
| ProjectHephaestus | PR #1042 — fail-fast test pollution + 422/GraphQL classifier (v1.2.0) | Adding 2 new fail-fast tests to a class in `hephaestus/automation/github_api.py`'s test suite turned 5 unrelated sibling tests red (`GitHubUnavailableError: circuit breaker is open`) because `setup_method`'s `reset_all_circuit_breakers()` clears the registry and orphans the import-time `_GH_BREAKER`. Fixed by calling `module._GH_BREAKER.reset()` at each new test's top. Bundled with adding `422`/`unprocessable entity`, `doesn't accept argument`, and `is declared by .* but not used` to `_NON_TRANSIENT_PATTERNS`. **verified-ci** — merged to main (PR #1042, closes #1040). |
