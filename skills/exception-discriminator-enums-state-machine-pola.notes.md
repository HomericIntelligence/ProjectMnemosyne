# Exception Discriminator Enums — Session Notes

## Issue #754 Context

**Repository**: ProjectHephaestus
**Issue**: #754 — Add CircuitBreakerOpenReason discriminator to distinguish OPEN-state recovery timeout from HALF_OPEN slot exhaustion
**PR**: #959 (verified-local, signed commits)

## Root Cause Analysis

The original `CircuitBreakerOpenError` was raised in two distinct states with different recovery strategies:

1. **OPEN state**: Circuit is waiting for recovery timeout before transitioning to HALF_OPEN
   - `time_until_recovery`: seconds remaining in recovery window
   - Callers should: `time.sleep(exc.time_until_recovery)` then retry

2. **HALF_OPEN state**: Circuit is probing for recovery, but all `max_calls` probe slots are in-flight
   - `time_until_recovery`: was being set to `recovery_timeout` (WRONG — timer already fired)
   - Callers should: yield briefly to probes in-flight, then retry
   - Real block: concurrent in-flight probes, not recovery timer

**Problem**: `time_until_recovery` had context-dependent semantics:
- In OPEN state: meaningful ETA for recovery
- In HALF_OPEN state: misleading ETA from the recovery timer (which is no longer active)

This forced callers to parse the message string or perform defensive checks on fields, violating POLA.

## Implementation Details

### Enum Design

```python
class CircuitBreakerOpenReason(str, Enum):
    RECOVERY_TIMEOUT = "recovery_timeout"
    HALF_OPEN_EXHAUSTED = "half_open_exhausted"
```

**Why `(str, Enum)` instead of `enum.StrEnum`?**
- `StrEnum` available in Python 3.11+
- ProjectHephaestus requires Python 3.10+
- `(str, Enum)` mixin enables:
  - String equality: `reason == "recovery_timeout"` works
  - IDE autocomplete
  - Type checking
  - Backward compatibility with 3.10

### Exception Field Semantics

| State | `time_until_recovery` | `reason` | Retry Strategy |
|-------|----------------------|----------|-----------------|
| OPEN | Recovery timeout (e.g., 45.2s) | `RECOVERY_TIMEOUT` | Wait until `time_until_recovery` elapses |
| HALF_OPEN | `0.0` (timer already fired) | `HALF_OPEN_EXHAUSTED` | Yield briefly (~100ms) to probes in-flight |

**Key insight**: Keep field semantics _consistent_ by using sentinel value (`0.0`) when field is not applicable. The discriminator clarifies which recovery strategy to use.

### Backward Compatibility

```python
# Existing code (no changes needed)
try:
    breaker.call(fn)
except CircuitBreakerOpenError as e:
    logger.error(f"Breaker open: {e}")  # Message still works

# New code (uses reason)
except CircuitBreakerOpenError as e:
    if e.reason == CircuitBreakerOpenReason.RECOVERY_TIMEOUT:
        time.sleep(e.time_until_recovery)
```

Default reason value ensures:
- Positional callers (`CircuitBreakerOpenError(msg)`) get sensible default
- Existing exception handlers continue to work
- Gradual migration path for callers

### Testing Strategy

**TDD Revealed Coverage Gap**:
- OLD test: `with pytest.raises(CircuitBreakerOpenError, match="Circuit breaker open"):`
- NEW test: Also assert `exc_info.value.reason == CircuitBreakerOpenReason.HALF_OPEN_EXHAUSTED`

The reason assertion exposed that `test_half_open_max_calls_exceeded` was ambiguous — it could pass whether the code raised from the OPEN or HALF_OPEN path. Adding the reason assertion forced explicit coverage of both paths.

**Threading Barrier Pattern**:
```python
def test_half_open_exhaustion():
    barrier = threading.Event()

    def slow_probe():
        barrier.set()  # Signal we're in-flight
        time.sleep(0.5)
        return True

    # Hold probe in-flight while second call hits exhaustion
    breaker.state = CircuitBreakerState.HALF_OPEN
    breaker.max_calls = 1
    t = threading.Thread(target=lambda: breaker.call(slow_probe))
    t.start()
    barrier.wait()  # Wait for probe to be in-flight

    # Now second call should hit slot exhaustion
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        breaker.call(lambda: None)
    assert exc_info.value.reason == CircuitBreakerOpenReason.HALF_OPEN_EXHAUSTED
    t.join()
```

This pattern proves the concurrent code path is exercisable and the correct exception path is taken.

## Verified Outcomes

### Local Testing
- **35 circuit breaker tests pass** (3 new + 2 updated for reason assertions)
- **1129 resilience + automation tests pass** (backward compatibility verified)
- **All commits cryptographically signed** (verified with `git log --show-signature`)

### External Consumers
- **1 site identified**: `github_api.py:486` wraps CircuitBreakerOpenError in GitHubUnavailableError
- **Impact**: None — translation layer absorbs the change
- **Verified**: Code inspection + grep search confirms no other consumers

### PR State
- **Branch**: `754-auto-impl`
- **PR**: `#959` created with proper "Closes #754" syntax
- **Status**: Awaits `state:implementation-go` label for auto-merge (per pr-policy)

## Related Skills

- `resilience-circuit-breaker-error-translation.md` — Exception translation at integration boundary
- `state-machine-and-resource-lifecycle-patterns.md` — State machine sentinel exceptions (UntilHaltError)
- `testing-singleton-isolation-circuit-breaker-reset.md` — Test isolation for circuit breaker

## Key Learnings for Future Work

1. **POLA Violations**: When a field has context-dependent semantics across states, add an explicit discriminator enum instead of forcing callers to parse messages or make defensive checks.

2. **Enum Compatibility**: Use `(str, Enum)` mixin for Python 3.10+ support (not `enum.StrEnum` which requires 3.11+).

3. **TDD Catches Ambiguity**: Writing reason assertions in tests exposed missing test coverage that would have let the code pass with semantically wrong behavior.

4. **Threading Barriers for Concurrent Paths**: Use `threading.Event` to hold a concurrent operation in-flight while another thread hits the target code path. This proves race-condition scenarios are actually reachable.

5. **Default Reason Values**: Set a sensible default for backward compatibility with positional callers, but make explicit reason values mandatory at all raise sites (via type hints + code review).
