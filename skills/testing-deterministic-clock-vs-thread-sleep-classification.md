---
name: testing-deterministic-clock-vs-thread-sleep-classification
description: "Eliminate real time.sleep() from a test suite by classifying EVERY sleep by WHAT IT WAITS ON before choosing a fix, because the fix differs per class. A timer-boundary sleep (waits only for a monotonic/wall clock to cross a timeout like recovery_timeout) is fixed by patching the EXACT clock name the production code reads (@patch('<module>.time.monotonic')) and advancing the return value past the threshold — NOT by constructor-injecting a clock (YAGNI when the code already calls time.monotonic() at module scope). A thread-coordination sleep (orders real OS threads against a threading.Condition/Event/Barrier) has NO clock to mock; the CORRECT fix is deterministic Event-based coordination (instrument condition.wait to set a threading.Event from inside the lock right before parking), NOT @pytest.mark.slow — quarantining behind slow removes the wait/notify code from the fast CI suite AND leaves the flakiness intact, and a reviewer will reject it. Use when: (1) a refactor wants to remove real sleeps from unit tests for speed/determinism; (2) you see time.sleep near recovery_timeout/circuit-breaker/backoff logic; (3) you see time.sleep near threading.Barrier/Condition/Event 'give threads time to start' comments; (4) you are tempted to inject a clock into a constructor that already calls time.monotonic() directly; (5) you are tempted to mark a thread-coordination test @pytest.mark.slow instead of making it deterministic."
category: testing
date: 2026-06-30
version: "2.0.0"
history: testing-deterministic-clock-vs-thread-sleep-classification.history
user-invocable: false
verification: verified-local
tags:
  - time-sleep
  - monotonic
  - mock-clock
  - threading-event
  - condition-wait-instrumentation
  - deterministic-test
  - circuit-breaker
  - recovery-timeout
  - thread-coordination
  - happens-before
  - flaky
  - yagni
  - dry
  - kiss
  - ruff-unused-import
---

# Deterministic Clock vs Thread-Sleep: Classify Before You Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Objective** | Remove real `time.sleep()` calls from a unit-test suite (issue #1469) to make tests fast and deterministic, WITHOUT introducing thread races, breaking timeout-ETA assertions, or quarantining the code under test out of the fast CI suite. |
| **Outcome** | Successful and verified locally. 13 timer-boundary sleeps in `tests/unit/resilience/test_circuit_breaker.py` replaced with a mocked `time.monotonic`; 6 thread-coordination sleeps in `tests/unit/automation/test_status_tracker.py` replaced with deterministic `threading.Event` coordination. Full targeted suite green across 3 runs; ruff clean. PR #1725. |
| **Verification** | verified-local — 23 status_tracker tests + 35 circuit_breaker tests passed locally across 3 runs, ruff clean; CI on PR #1725 still pending at capture time. |

## When to Use

- A refactor/issue asks to remove real `time.sleep()` from unit tests for speed or determinism.
- You see `time.sleep(...)` immediately before an assertion about a timeout having elapsed (circuit-breaker `recovery_timeout`, backoff windows, TTL expiry).
- You see `time.sleep(...)` near `threading.Barrier`/`Condition`/`Event` with comments like "give threads time to start waiting" or "release after delay".
- You are tempted to add a `clock`/`time_source` constructor parameter to production code that already calls `time.monotonic()` directly at module scope.
- You are tempted to mark a thread-coordination test `@pytest.mark.slow` instead of making it deterministic.

## Verified Workflow

### Quick Reference

```python
# CLASS 1 — Timer-boundary sleep: patch the EXACT clock the production code reads.
# First confirm the source: grep for the clock call in the module under test.
#   grep -n "time.monotonic\|time.time" hephaestus/resilience/circuit_breaker.py
# Then patch that exact attribute path (the name in the MODULE UNDER TEST, not `time`).
# CRITICAL ORDERING: production _record_failure stamps _last_failure_time = time.monotonic()
# AT FAILURE TIME, so advance the clock AFTER the failing call returns, NOT at construction.
import unittest.mock as mock

@mock.patch("hephaestus.resilience.circuit_breaker.time.monotonic")
def test_recovers_after_timeout(self, mono):
    mono.return_value = 1000.0          # baseline read while tripping the breaker
    cb = CircuitBreaker(recovery_timeout=30.0)   # use a NON-tiny timeout
    # ... trip the breaker: _record_failure() now stamps _last_failure_time = 1000.0 ...
    mono.return_value = 1030.0          # advance PAST the boundary AFTER the failing call
    assert cb.allow()                    # half-open transition, no real sleep

# CLASS 2 — Thread-coordination sleep: NO clock to mock. Make it DETERMINISTIC, not slow.
# Instrument condition.wait to fire an Event from inside the lock right before parking,
# so the releaser provably cannot run until the main thread is parked in wait().
import threading

def test_release_unblocks_waiter(self):
    waiting = threading.Event()
    real_wait = tracker.condition.wait

    def wait_announcing(timeout=None):
        waiting.set()                    # fires while still holding the condition lock
        return real_wait(timeout=timeout)

    tracker.condition.wait = wait_announcing  # type: ignore[method-assign]

    def release_when_waiting():
        assert waiting.wait(timeout=5.0)  # safety net only, never the happy path
        tracker.release_slot(slot_id)     # contends for the SAME lock -> happens-after

    # ... start release_when_waiting in a thread, then acquire the (full) slot ...
```

```bash
# Housekeeping after edits:
#  - removing the last time.sleep -> `import time` is now unused -> ruff F401, delete it
#  - making thread tests deterministic -> remove @pytest.mark.slow AND the now-unused
#    `import pytest` if it was only used for the marker
ruff check tests/unit/resilience/test_circuit_breaker.py tests/unit/automation/test_status_tracker.py
# Re-grep rather than trusting cited line numbers — they drift between reads:
grep -rn "time.sleep" tests/unit/
```

### Detailed Steps

1. **Inventory every `time.sleep` by re-grepping** (`grep -rn "time.sleep" tests/`). Do
   NOT trust line numbers from a prior read — they drift.
2. **Classify each sleep** as either **timer-boundary** (waits only for a clock to cross a
   threshold) or **thread-coordination** (orders real OS threads against a sync primitive).
   This classification, not the call site, drives the fix.
3. **For timer-boundary sleeps**: confirm the production clock source first
   (`grep -n "time.monotonic\|time.time" <module>.py`). Patch THAT exact name with
   `@patch("<module_under_test>.time.monotonic")`. `@patch` targets the name in the module
   under test, not the global `time` module. Seed the baseline value, then advance
   `return_value` past the threshold.
4. **Respect the failure-time stamp ordering (the #1 bug here).** Production
   `_record_failure` writes `_last_failure_time = time.monotonic()` at the moment of
   failure. So set the post-timeout advance AFTER the failing call returns — advancing the
   clock before/at construction corrupts the baseline and the boundary math is wrong.
5. **Pick a non-tiny timeout** (e.g. `30.0`) and large explicit advances so the boundary
   crossing is unambiguous, replacing the original sub-second values.
6. **For thread-coordination sleeps**: do NOT clock-mock — there is no clock. Do NOT mark
   them `@pytest.mark.slow` either (see Failed Attempts — a reviewer rejected this). Make
   the happens-before **deterministic** by instrumenting the synchronization primitive:
   wrap `tracker.condition.wait` so it sets a `threading.Event` from INSIDE the lock,
   immediately before parking. The releaser then `event.wait(timeout=5.0)`s on that Event
   before acting. Because the releaser contends for the SAME condition lock, it cannot
   proceed until the main thread atomically releases the lock by entering `wait()`. The
   5.0s timeout is a safety net only; the happy path has zero wall-clock dependence.
7. **For pure-contention "simulate work" sleeps** (e.g. `time.sleep(0.01)` inside a worker
   that the test only checks "eventually acquired/released"): just DELETE the sleep. The
   assertions (all N threads acquired, all slots released) need no artificial delay;
   removing it keeps the contention test valid and fast.
8. **A clock-mocked test that still spawns real threads** (concurrency assertions with
   `threading.Barrier`) keeps the thread machinery; only the timer-boundary sleep inside
   it is mocked. This is SAFE because a `MagicMock.return_value` is a frozen, lock-free,
   thread-shared read AND those tests assert on state/counters/peak-concurrency, never on
   elapsed/ETA time. Advance the frozen clock BEFORE spawning threads.
9. **Fix imports last**: after removing the last `time.sleep`, `import time` is unused
   (ruff F401) — delete it. After removing `@pytest.mark.slow`, delete a now-unused
   `import pytest`.
10. **Run the full targeted suite multiple times** to confirm determinism (flakiness only
    shows up intermittently). Here: 23 status_tracker + 35 circuit_breaker tests green
    across 3 runs.

### If you DO end up marking tests slow (coverage gate check)

If a thread test genuinely cannot be made deterministic and you fall back to
`@pytest.mark.slow`, verify the module under test still clears the coverage gate on the
fast path: `pytest -m "not slow" --cov=<module>`. In issue #1469 `status_tracker.py` held
91.76% even with the candidate tests deselected — but the deterministic Event fix made the
marker (and this check) unnecessary, which is the preferred outcome.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `@pytest.mark.slow` for thread-coordination sleeps | Quarantined the thread tests behind the `slow` marker so the fast CI path deselects them (the v1.x recommendation) | A reviewer REJECTED it: deselecting removes the wait/notify code under test from the default fast suite (less coverage of exactly that logic) AND leaves the underlying flakiness intact, just hidden | Thread-coordination sleeps must be made DETERMINISTIC (instrument `condition.wait` to fire an Event before parking), not quarantined |
| Constructor-injected clock | Considered adding a `clock`/`time_source` parameter to production code so tests pass a fake clock | YAGNI: the production code already calls `time.monotonic()` at module scope, so a `@patch` of that name is sufficient and changes no production API | When the code already reads a module-level clock, mock the name (KISS) — don't widen the constructor surface just for testing |
| `@patch("time.monotonic")` (global) | Patching the global `time` module instead of the name imported in the module under test | `@patch` resolves the attribute on the target object; the SUT reads `circuit_breaker.time.monotonic`, so the global patch may not intercept the call the SUT actually makes | Patch the EXACT attribute path the module under test reads, confirmed by grepping the source first |
| Remove thread-coordination sleeps via mocked clock | Treating "give threads time to start waiting" sleeps the same as timeout sleeps and trying to mock them away | There is no clock involved — the wait is on the OS scheduler; removing the sleep with no replacement creates a notify-before-wait race | Thread-ordering sleeps are a different class; instrument the sync primitive for a deterministic happens-before |
| Advance the mocked clock at construction time | Set `monotonic.return_value` past the boundary before tripping the breaker | `_record_failure` stamps `_last_failure_time = time.monotonic()` at FAILURE time, so a pre-set advance corrupts the baseline — the boundary delta is then wrong | Advance the clock AFTER the failing call returns; the baseline is the value LIVE when `_record_failure` runs, not at construction |
| Single fixed mock value across the whole `call()` path | Setting one constant `monotonic.return_value` and assuming all reads are equivalent | The mocked value is read multiple times within one `call()` (`_effective_state` AND the `time_until` ETA); a value that makes the boundary cross can make an ETA assertion read `0.0`/negative | When the same mocked clock feeds an ETA assertion (`time_until_recovery > 0`), choose the value so `recovery_timeout - elapsed > 0` still holds |
| Keep "simulate work" `time.sleep(0.01)` in a contention test | Left an artificial work delay inside worker threads of a pure contention test | The test only asserts all threads eventually acquired and all slots released — the delay adds wall-clock time and flakiness for no assertion benefit | Pure-contention tests need no artificial work delay; just delete the sleep |
| Trusting cited line numbers | Planning edits against offsets from a single read | Line numbers drift between reads as files change | Re-grep `time.sleep` and the markers at implementation time; never trust a prior read's offsets |

## Results & Parameters

**Two-class decision rule (the core durable insight):**

| Class | What the sleep waits on | Correct fix | Anti-pattern |
|-------|-------------------------|-------------|--------------|
| Timer-boundary | A monotonic/wall clock crossing a timeout threshold (`recovery_timeout`) | `@patch("<module>.time.monotonic")`, advance `return_value` past the threshold AFTER the failing call | Constructor-injected clock (YAGNI); patching global `time`; advancing at construction |
| Thread-coordination | Real OS threads ordered against `threading.Condition`/`Event`/`Barrier` | Instrument the sync primitive (set an `Event` from inside `condition.wait` before parking) for a deterministic happens-before | `@pytest.mark.slow` (hides flakiness, drops coverage — reviewer-rejected); mocking a clock that does not exist |
| Pure-contention "simulate work" | Nothing semantic — just adds delay so threads overlap | DELETE the sleep; assertions are "eventually acquired/released" | Keeping the delay (slow + flaky for no assertion benefit) |

**The deterministic thread-coordination technique (the key technique that converged the review):**

```python
# Instead of time.sleep(0.1) to "give threads time to start waiting":
waiting = threading.Event()
real_wait = tracker.condition.wait

def wait_announcing(timeout=None):
    waiting.set()                       # set INSIDE the lock, right before parking
    return real_wait(timeout=timeout)

tracker.condition.wait = wait_announcing  # type: ignore[method-assign]

def release_when_waiting():
    assert waiting.wait(timeout=5.0)    # generous safety net, never the happy path
    tracker.release_slot(slot_id)       # contends for the SAME lock -> provably happens-after
```

Why it is race-free: `release_slot` contends for the same `condition` lock the main thread
holds, so it cannot proceed until the main thread atomically releases that lock by entering
`wait()`. The `Event` makes the parked state observable; the lock makes the ordering
enforced. Wall-clock independence with a timeout only as a backstop.

**Mocked-clock-across-threads safety reasoning:** when a circuit-breaker concurrency test
spawns real worker threads that read the patched `time.monotonic`, a `MagicMock.return_value`
is a frozen, lock-free, thread-shared read — SAFE precisely because those tests assert on
state/counters/peak-concurrency, never on elapsed/ETA time. Advance the frozen clock BEFORE
spawning threads.

**Verified numbers (issue #1469, local):**

- `tests/unit/resilience/test_circuit_breaker.py`: 13 timer-boundary sleeps removed; 35 tests green ×3 runs.
- `tests/unit/automation/test_status_tracker.py`: 6 thread-coordination sleeps across 5 methods removed; 23 tests green ×3 runs.
- ruff clean; `import time` / `import pytest` removed where they became unused.

**Source-of-truth anchors (re-verify before editing):**

- Production clock source: `hephaestus/resilience/circuit_breaker.py` calls `time.monotonic()` at module scope — patch `hephaestus.resilience.circuit_breaker.time.monotonic`.
- `_record_failure` stamps `_last_failure_time = time.monotonic()` at failure time — advance the mock AFTER the failing call.
- ETA computation reuses the same clock — keep `recovery_timeout - elapsed > 0` for any `time_until_recovery > 0` assertion.
- Status tracker uses a `threading.Condition`; instrument `tracker.condition.wait` to announce parking via an `Event`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1469 / PR #1725 — replaced real `time.sleep()` in `tests/unit/resilience/test_circuit_breaker.py` (mocked clock) and `tests/unit/automation/test_status_tracker.py` (deterministic Event coordination); 58 tests green ×3 runs locally, CI pending | No notes file |
