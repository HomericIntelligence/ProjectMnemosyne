---
name: nats-subscriber-ack-atmost-once-design
description: "Document and pin the at-most-once delivery contract for NATSSubscriberThread._subscribe_loop in ProjectHephaestus. Use when: (1) the unconditional msg.ack() placement after a handler raise looks like a bug — it is intentional poison-message defense; (2) adding a class docstring Delivery semantics section to explain why ack is outside the except block; (3) writing a pinning test to make the three-way contract (acked even on raise, last_error set, success counter untouched) executable so prose comments cannot drift; (4) reviewing whether to move ack into the else: branch — NOGO, it switches to at-least-once and re-enables redelivery loops."
category: architecture
date: 2026-06-23
version: "1.0.0"
verification: verified-local
user-invocable: false
tags:
  - nats
  - jetstream
  - subscriber
  - ack
  - at-most-once
  - at-least-once
  - poison-message
  - delivery-semantics
  - pinning-test
  - hephaestus
  - executable-invariant
---

# NATS Subscriber Ack At-Most-Once Design (Documenting & Pinning)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-23 |
| **Objective** | Document the by-design at-most-once delivery behavior of `NATSSubscriberThread._subscribe_loop` (ProjectHephaestus `hephaestus/nats/subscriber.py`) and pin the invariant with an executable unit test so the design cannot silently regress. |
| **Outcome** | Successful — added a "Delivery semantics" RST section to `NATSSubscriberThread` class docstring, an 8-line by-design comment above `await msg.ack()` in `_subscribe_loop`, and a new pinning test `test_ack_is_awaited_even_when_handler_raises` in `tests/unit/nats/test_subscriber_polling.py`. No runtime behavior was changed. |
| **Verification** | `verified-local` — all 74 nats unit tests pass; `pixi run ruff check`, `pixi run ruff format`, and `pixi run mypy` all clean. CI not run. |

## When to Use

- `NATSSubscriberThread._subscribe_loop` has a broad `except Exception` handler that logs the error but the code still calls `await msg.ack()` — you need to decide if this is a bug or intentional.
- You are reviewing whether to move `await msg.ack()` into the `else:` branch (i.e., only ack on success). **Stop.** That switches from at-most-once to at-least-once and re-enables the poison-message redelivery loop the current design prevents.
- A class docstring on `NATSSubscriberThread` is missing a "Delivery semantics" section and callers cannot tell whether ack-on-raise is intentional.
- A doc-only invariant (ack-outside-else) needs to be pinned with a unit test so prose comments cannot silently drift.
- You are writing a new test against the NATS subscriber harness and need to know how `_make_msg`, `_install_fake_nats`, and `_run_loop` work together.

## Verified Workflow

### Quick Reference

```python
# hephaestus/nats/subscriber.py — the by-design ack placement
try:
    await handler(msg)
    # ... update success counters
except Exception:
    self.last_error = sys.exc_info()
    logger.exception("Handler raised; message will NOT be redelivered")
# ----- BY DESIGN: ack is OUTSIDE the try/except, not in the else: branch -----
# Rationale: at-most-once delivery. Acking unconditionally means a poison message
# (one that always raises in the handler) is consumed exactly once and never
# requeued. Moving this line into the `else:` branch switches to at-least-once
# semantics and reintroduces the redelivery loop this design was built to prevent.
# Observability: failures are surfaced via self.last_error + logger.exception above.
# Do NOT move this into else: without a deliberate policy change + test update.
await msg.ack()
```

```python
# tests/unit/nats/test_subscriber_polling.py — pinning test
def test_ack_is_awaited_even_when_handler_raises(tmp_path):
    """ack fires unconditionally — at-most-once delivery contract."""
    thread, fake = _make_thread_with_fake_nats()
    msg = _make_msg(subject="hi.test")

    async def raising_handler(m):
        thread._stop_event.set()   # one-message-then-stop
        raise RuntimeError("boom")

    thread.handler = raising_handler
    _install_fake_nats(thread, fake, messages=[msg])
    _run_loop(thread)

    msg.ack.assert_awaited_once()           # acked despite raise
    assert thread.last_error is not None    # failure surfaced
    assert thread.last_message_at is None   # success counter untouched
```

### Detailed Steps

1. **Identify the ack placement.** In `hephaestus/nats/subscriber.py`, `_subscribe_loop` has a broad `try/except Exception` block wrapping `await handler(msg)`. The `await msg.ack()` call sits **outside** (after) the `try/except`, not inside an `else:` branch. This is intentional.

2. **Add a "Delivery semantics" RST section to the class docstring.** Place it after the existing attribute documentation:

   ```python
   Delivery Semantics
   ------------------
   ``_subscribe_loop`` uses **at-most-once** delivery. ``msg.ack()`` is called
   unconditionally after the handler runs, even when the handler raises. This
   means a poison message — one whose handler always raises — is consumed exactly
   once and never requeued. Failures are surfaced via ``self.last_error`` (the
   most recent ``sys.exc_info()`` triple) and ``logger.exception`` in the handler
   wrapper. Callers that need at-least-once guarantees must implement their own
   retry logic above this layer.
   ```

3. **Add a by-design comment above `await msg.ack()`.** Eight lines is enough to explain the intent and name the anti-pattern it prevents:

   ```python
   # ----- BY DESIGN: ack is OUTSIDE the try/except block ---------------------
   # At-most-once delivery: acking unconditionally ensures that a poison message
   # (a message whose handler always raises) is consumed exactly once and is never
   # requeued for redelivery. Moving this call into the `else:` branch would
   # switch semantics to at-least-once and re-enable poison-message loops.
   # Observability: failures are surfaced via self.last_error (set above in the
   # except block) and via logger.exception — callers can inspect last_error or
   # subscribe to the logger to detect handler failures.
   # Do NOT move this into else: without an explicit policy change + test update.
   await msg.ack()
   ```

4. **Write a pinning test using the existing harness.** The file `tests/unit/nats/test_subscriber_polling.py` provides three helpers:
   - `_make_msg(subject=...)` — builds a fake NATS `Msg` with an `AsyncMock` for `.ack()`.
   - `_install_fake_nats(thread, fake, messages=[...])` — wires the fake broker so `next_msg` returns each message in order and raises `asyncio.TimeoutError` after the last one.
   - `_run_loop(thread)` — runs `thread._subscribe_loop()` in a fresh event loop until the stop event fires.

   One-message-then-stop: call `thread._stop_event.set()` inside the raising handler **before** it raises. This ensures the loop exits cleanly after the single message rather than running forever.

5. **Assert the three-way contract.**
   - `msg.ack.assert_awaited_once()` — ack fired despite the handler raising.
   - `thread.last_error is not None` — failure surfaced via the error channel.
   - `thread.last_message_at is None` — success counter was not incremented (the handler never succeeded).

6. **Run the full test suite for the nats subpackage** to confirm no regressions: `pixi run pytest tests/unit/nats/ -v`. All tests must pass before committing.

7. **Run ruff check, format, and mypy** to confirm no linting issues are introduced.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| n/a | Pure doc + test-pinning task; no runtime changes were attempted | n/a | At-most-once vs at-least-once is a policy choice that lives in the ack placement, not in the exception handler logic |

## Results & Parameters

```yaml
# Key invariant
delivery_semantics:
  model: at-most-once
  mechanism: "msg.ack() called unconditionally outside try/except"
  poison_message_defense: true
  at_least_once_antipattern: "moving ack into else: branch"

# Three-way test contract
pinning_test_assertions:
  - "msg.ack.assert_awaited_once()  # acked even when handler raises"
  - "thread.last_error is not None  # failure surfaced"
  - "thread.last_message_at is None # success counter untouched"

# Stop-after-one-message pattern (test harness)
one_message_then_stop: "call thread._stop_event.set() inside the handler BEFORE it raises"

# Test file
test_file: "tests/unit/nats/test_subscriber_polling.py"
test_helpers:
  - "_make_msg(subject=...)"
  - "_install_fake_nats(thread, fake, messages=[...])"
  - "_run_loop(thread)"

# Source file
subscriber_file: "hephaestus/nats/subscriber.py"
ack_location: "_subscribe_loop — after the try/except Exception block"
```

### Expected Output

All 74 nats unit tests pass:

```text
tests/unit/nats/test_subscriber_polling.py::test_ack_is_awaited_even_when_handler_raises PASSED
...
74 passed in 0.87s
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/ProjectHephaestus | Issue #1551, branch `1551-auto-impl`, 2026-06-23 | Pure doc + test-pinning task. `hephaestus/nats/subscriber.py` class docstring + by-design comment; `tests/unit/nats/test_subscriber_polling.py` pinning test. All 74 nats unit tests pass locally; ruff + mypy clean. |

## References

- [ProjectHephaestus Issue #1551](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1551)
- [NATS JetStream Delivery Policies](https://docs.nats.io/nats-concepts/jetstream/consumers#deliverpolicy)
- [nats-leaf-multi-account-remote-bridging](./nats-leaf-multi-account-remote-bridging.md)
- [testing-jetstream-flaky-stream-state-leak](./testing-jetstream-flaky-stream-state-leak.md)
