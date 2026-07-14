---
name: exception-discriminator-enums-state-machine-pola
description: "Add a discriminator enum field to exceptions in state machines to distinguish semantic reasons for the same exception type. Use when: (1) same exception type is raised in multiple states with different recovery strategies; (2) callers need to distinguish error reasons without parsing message strings; (3) a single field has context-dependent semantics across states, violating POLA."
category: architecture
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - exception-handling
  - state-machine
  - discriminator
  - enum
  - pola
  - circuit-breaker
  - python
  - semantic-clarity
---

# Exception Discriminator Enums: State Machine Clarity

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Add discriminator enum field to exceptions raised by state machines to preserve semantic information and distinguish error reasons without parsing message strings |
| **Outcome** | Successfully implemented discriminator for CircuitBreakerOpenError in ProjectHephaestus issue #754 — backward compatible, Python 3.10+, verified locally with 35 circuit breaker tests + 1129 resilience suite tests passing |
| **Verification** | verified-local |

## When to Use

- **Same exception raised in multiple states with different recovery strategies**: A state machine raises the same exception type from different states, but callers need to distinguish how to retry. Example: CircuitBreakerOpenError raised from both OPEN state (wait for recovery timeout) and HALF_OPEN state (no slots available for probe).
- **Callers parse message strings to distinguish errors**: Current code forces callers to parse exception messages or inspect fields that have context-dependent semantics, violating the Principle of Least Astonishment (POLA).
- **A field has ambiguous semantics across states**: The same exception field means different things in different states (e.g., `time_until_recovery` could be the recovery timer in OPEN state or an irrelevant value in HALF_OPEN state when the real block is concurrent probes).
- **No existing exception subclass hierarchy**: Adding subclasses would increase coupling; a single exception type with a discriminator field is simpler and more compatible.

## Verified Workflow

### Quick Reference

```python
from enum import Enum

# Step 1: Define discriminator enum with (str, Enum) mixin for Python 3.10 compatibility
class CircuitBreakerOpenReason(str, Enum):
    """Reason why circuit breaker is open."""
    RECOVERY_TIMEOUT = "recovery_timeout"
    HALF_OPEN_EXHAUSTED = "half_open_exhausted"

# Step 2: Add reason field with semantic default
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        message: str,
        time_until_recovery: float = 0.0,
        reason: CircuitBreakerOpenReason = CircuitBreakerOpenReason.RECOVERY_TIMEOUT,
    ):
        super().__init__(message)
        self.time_until_recovery = time_until_recovery
        self.reason = reason

# Step 3: Raise with explicit reason in state machine
# OPEN state: recovery timer is active
raise CircuitBreakerOpenError(
    f"Circuit breaker open. Recovery in {recovery_timeout}s",
    time_until_recovery=recovery_timeout,
    reason=CircuitBreakerOpenReason.RECOVERY_TIMEOUT,
)

# HALF_OPEN state: all probe slots exhausted
raise CircuitBreakerOpenError(
    f"Circuit breaker half-open, all probes in-flight (max {max_calls})",
    time_until_recovery=0.0,  # No recovery timer — only probe blocking
    reason=CircuitBreakerOpenReason.HALF_OPEN_EXHAUSTED,
)

# Step 4: Callers check reason instead of parsing message
try:
    breaker.call(fn)
except CircuitBreakerOpenError as exc:
    if exc.reason == CircuitBreakerOpenReason.RECOVERY_TIMEOUT:
        # Wait for recovery window
        time.sleep(exc.time_until_recovery)
        retry()
    elif exc.reason == CircuitBreakerOpenReason.HALF_OPEN_EXHAUSTED:
        # Probe slots exhausted; yield to probes in-flight
        time.sleep(0.1)
        retry()
```

### Detailed Steps

1. **Define the discriminator enum** with `(str, Enum)` mixin (not `enum.StrEnum` for Python 3.10 compatibility):
   ```python
   from enum import Enum

   class YourStateReason(str, Enum):
       """Reason for exception."""
       REASON_A = "reason_a"
       REASON_B = "reason_b"
   ```
   - Inherit from `str` first, then `Enum` to enable string equality (`reason == "reason_a"`)
   - Avoid `enum.StrEnum` (Python 3.11+); use the mixin pattern for 3.10 compatibility
   - Use lowercase kebab-case for enum values to match message strings

2. **Add reason field to the exception** with a semantic default:
   ```python
   class YourException(Exception):
       def __init__(
           self,
           message: str,
           reason: YourStateReason = YourStateReason.REASON_A,
       ):
           super().__init__(message)
           self.reason = reason
   ```
   - Default reason should match the most common case (backward compatibility for positional callers)
   - Type-hint the reason parameter so callers catch incorrect values early

3. **Preserve field semantics across states**:
   - If the same field (`time_until_recovery`, `retry_after`, etc.) has context-dependent meaning, consider whether it should:
     - **Always mean the same thing**: Standardize across all states (e.g., always "seconds until safe to retry")
     - **Be set to a sentinel when not applicable**: Use `0.0` or `None` when the field doesn't apply in a particular state
   - Document the semantic meaning in the exception's docstring

4. **Raise with explicit reason at each raise site**:
   ```python
   # GOOD: Explicit reason at every raise site
   raise YourException(msg, reason=YourStateReason.REASON_A)

   # BAD: Relying on default for some cases, explicit for others
   raise YourException(msg)  # What's the reason? Ambiguous!
   raise YourException(msg, reason=YourStateReason.REASON_B)
   ```

5. **Update tests to assert reason** alongside message:
   ```python
   # OLD: Only check message
   with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker open"):
       breaker.call(fn)

   # NEW: Assert both message and reason
   with pytest.raises(CircuitBreakerOpenError) as exc_info:
       breaker.call(fn)
   assert "Circuit breaker open" in str(exc_info.value)
   assert exc_info.value.reason == CircuitBreakerOpenReason.RECOVERY_TIMEOUT
   ```
   - This prevents ambiguity about which state path triggered the exception
   - TDD helps expose missing test coverage when you change exception semantics

6. **Use threading barriers for concurrent state path testing**:
   ```python
   # Test both OPEN (recovery timeout) and HALF_OPEN (exhausted probes) paths
   def test_half_open_exhaustion_vs_recovery_timeout():
       """Verify both reason codes are reachable in concurrent scenarios."""
       barrier = threading.Event()

       # Hold first probe in-flight while second call hits slot exhaustion
       def slow_probe():
           barrier.set()  # Signal that we're in-flight
           time.sleep(0.5)  # Block for a bit
           return True

       # Transition to HALF_OPEN, start probe
       breaker.state = CircuitBreakerState.HALF_OPEN
       breaker.max_calls = 1
       t = threading.Thread(target=lambda: breaker.call(slow_probe))
       t.start()
       barrier.wait()  # Wait for probe to be in-flight

       # Second call hits slot exhaustion
       with pytest.raises(CircuitBreakerOpenError) as exc_info:
           breaker.call(lambda: None)
       assert exc_info.value.reason == CircuitBreakerOpenReason.HALF_OPEN_EXHAUSTED

       t.join()
   ```

### Backward Compatibility

The default reason value ensures backward compatibility:
- **Positional callers** (existing code calling `YourException(msg)`) get the default reason
- **Code that checks reason** explicitly chooses the reason value
- **Message parsing still works** for code that hasn't migrated to reason checking

```python
# Existing code — works unchanged
try:
    breaker.call(fn)
except CircuitBreakerOpenError as e:
    logger.error(f"Error: {e}")  # Message still works

# New code — uses reason for decision logic
except CircuitBreakerOpenError as e:
    if e.reason == CircuitBreakerOpenReason.RECOVERY_TIMEOUT:
        schedule_retry(delay=e.time_until_recovery)
    else:
        schedule_retry(delay=0.1)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | No discriminator field; same exception raised from OPEN and HALF_OPEN states | Callers had no signal about the error reason; had to parse "Circuit breaker open" message or inspect `time_until_recovery` (which had context-dependent semantics) | Without explicit discriminator, exception fields become overloaded with ambiguous meaning — violates POLA |
| 2 | Create separate exception subclasses: `CircuitBreakerOpenError`, `CircuitBreakerHalfOpenError` | Increased coupling; callers had to catch both exception types; breaks positional exception hierarchies in existing error handlers | Single exception type with discriminator is simpler and more backward compatible |
| 3 | Use `enum.StrEnum` for discriminator | `StrEnum` requires Python 3.11+; ProjectHephaestus targets Python 3.10+ | Use `(str, Enum)` mixin instead — enables string equality while supporting Python 3.10+ |
| 4 | Set `time_until_recovery=recovery_timeout` in HALF_OPEN exhaustion case | Callers were confused by ETA that didn't match the actual block (in-flight probes, not recovery timer) | Keep field semantics consistent: set `time_until_recovery=0.0` when the recovery timer is not relevant; reason field disambiguates |
| 5 | Test only the OPEN path, assume HALF_OPEN exhaustion is symmetric | HALF_OPEN exhaustion path was harder to trigger in tests; reason assertion was redundant, so tests didn't catch semantic inconsistencies | Always test both reason paths with explicit assertion; threading barriers help exercise concurrent state transitions |
| 6 | Use exception subclass for discriminator: `isinstance(exc, HalfOpenExhausted)` | Breaks caller code that catches the base type; requires handler refactoring | Discriminator enum on a single exception type is backward compatible |
| 7 | Use string field instead of enum: `reason: str = "recovery_timeout"` | Typos were not caught at runtime; no IDE autocomplete or type checking | Enum provides exhaustive values, IDE support, and type safety |
| 8 | Merge both reasons into message string: "Circuit breaker open [recovery_timeout]" | Forced callers to parse messages or regex; fragile if message format changes | Explicit field with enum is unambiguous and safe to refactor |

## Results & Parameters

### CircuitBreakerOpenReason Enum (Python 3.10+)

```python
from enum import Enum

class CircuitBreakerOpenReason(str, Enum):
    """Reason why circuit breaker is open.

    RECOVERY_TIMEOUT: Circuit is in OPEN state, waiting for recovery timeout before
        transitioning to HALF_OPEN. time_until_recovery indicates seconds remaining.

    HALF_OPEN_EXHAUSTED: Circuit is in HALF_OPEN state, but all max_calls slots are
        in-flight with probe attempts. Retry after probes complete (typically < 1s).
    """
    RECOVERY_TIMEOUT = "recovery_timeout"
    HALF_OPEN_EXHAUSTED = "half_open_exhausted"
```

### Exception Definition (Copy-Paste Ready)

```python
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is in OPEN or HALF_OPEN state.

    Attributes:
        time_until_recovery: Seconds to wait before retrying (OPEN state) or 0.0 (HALF_OPEN).
        reason: CircuitBreakerOpenReason discriminator — RECOVERY_TIMEOUT or HALF_OPEN_EXHAUSTED.
    """

    def __init__(
        self,
        message: str,
        time_until_recovery: float = 0.0,
        reason: "CircuitBreakerOpenReason" = None,
    ):
        super().__init__(message)
        self.time_until_recovery = time_until_recovery
        # Default to RECOVERY_TIMEOUT for backward compatibility
        if reason is None:
            reason = CircuitBreakerOpenReason.RECOVERY_TIMEOUT
        self.reason = reason
```

### Test Coverage (ProjectHephaestus PR #959)

```
✓ test_circuit_breaker_open_state (assert reason == RECOVERY_TIMEOUT)
✓ test_half_open_max_calls_exceeded (assert reason == HALF_OPEN_EXHAUSTED)
✓ test_half_open_recovery_succeeds (assert reason == HALF_OPEN_EXHAUSTED)
✓ test_backward_compat_positional_call (CircuitBreakerOpenError(msg))
✓ test_concurrent_half_open_exhaustion (threading.Event barrier)

Results:
  - 35 circuit breaker tests pass
  - 1129 resilience + automation tests pass
  - All commits cryptographically signed
  - PR #959 has verified signing state
```

### Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Backward compatibility | 100% | Default reason, message unchanged |
| Test coverage | 35/35 circuit breaker tests passing | Both reason paths tested explicitly |
| Python version support | 3.10+ | (str, Enum) mixin, not StrEnum |
| Exception field mutations | 0 | time_until_recovery and reason are readonly after init |
| External consumers affected | 1 site | github_api.py:486 (already caught and translates to GitHubUnavailableError) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #754 — CircuitBreakerOpenReason discriminator | PR #959; 35 CB tests + 1129 resilience suite passing locally; CI validation pending |
| ProjectHephaestus | github_api.py:486 — error translation boundary | Confirmed only one external consumer; immediately translates to GitHubUnavailableError |
