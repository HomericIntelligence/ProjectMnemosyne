---
name: nats-py-connection-resilience-patterns
description: "Patterns for making nats-py Python clients show clean connection state instead of stack traces. Use when: (1) building a NATS event viewer or console that must handle NATS being unreachable, (2) nats-py is printing full tracebacks on connection failures, (3) implementing retry-with-clean-status for asyncio NATS clients, (4) needing interruptible reconnection loops with graceful shutdown."
category: debugging
date: 2026-04-05
version: "1.0.0"
user-invocable: false
tags:
  - nats
  - nats-py
  - asyncio
  - connection-handling
  - resilience
  - python
  - odysseus-console
  - error-handling
  - reconnection
---

# nats-py Connection Resilience Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Make odysseus-console.py show clean [CONNECTED]/[DISCONNECTED]/[RECONNECTING] status instead of full stack traces when NATS is unreachable |
| **Outcome** | Successful -- full lifecycle verified: NATS down -> clean retry -> NATS up -> events flowing -> NATS down -> clean disconnect -> retry |
| **Verification** | verified-local |

## When to Use

- Building a Python NATS client (using nats-py) that must gracefully handle NATS being unreachable at startup or during operation
- nats-py's default error callback is printing full tracebacks (`logging.error("nats: encountered error", exc_info=True)`) and you want clean status output
- Implementing a retry loop for initial NATS connection that shows user-friendly status messages
- Needing interruptible sleep in reconnection loops (graceful shutdown on Ctrl+C)
- Debugging why `connect()` hangs forever when NATS is down with `allow_reconnect=True`

## Verified Workflow

### Quick Reference

```python
import asyncio
import logging
import nats as nats_mod

# Step 1: Suppress nats-py internal traceback logging
logging.getLogger("nats").setLevel(logging.CRITICAL)

RETRY_INTERVAL = 5  # seconds between reconnection attempts

async def run(nats_url: str):
    stop = asyncio.Event()

    # Step 2: Define async callbacks (MUST be coroutines)
    async def disconnected_cb():
        print("[DISCONNECTED]")

    async def reconnected_cb():
        print("[RECONNECTED]")

    async def closed_cb():
        print("[CLOSED]")

    # Step 3: Outer retry loop with fast-fail connect
    while not stop.is_set():
        try:
            nc = await asyncio.wait_for(
                nats_mod.connect(
                    nats_url,
                    allow_reconnect=False,       # fail fast, don't retry internally
                    connect_timeout=3,            # TCP socket timeout
                    disconnected_cb=disconnected_cb,
                    reconnected_cb=reconnected_cb,
                    closed_cb=closed_cb,
                ),
                timeout=5,  # hard timeout wrapper
            )
            print(f"[CONNECTED] {nats_url}")

            # Step 4: Main event loop -- poll nc.is_closed
            while not nc.is_closed:
                # ... subscribe and process messages ...
                await asyncio.sleep(0.1)

            print("[DISCONNECTED] Connection lost")

        except (OSError, asyncio.TimeoutError, Exception) as e:
            print(f"[DISCONNECTED] {type(e).__name__}: {e}")

        # Step 5: Interruptible sleep before retry
        if not stop.is_set():
            print(f"[RECONNECTING] Retrying in {RETRY_INTERVAL}s...")
            try:
                await asyncio.wait_for(stop.wait(), timeout=RETRY_INTERVAL)
            except asyncio.TimeoutError:
                pass  # normal -- timeout means retry interval elapsed
```

### Detailed Steps

1. **Suppress nats-py internal logging**: `logging.getLogger("nats").setLevel(logging.CRITICAL)` prevents nats-py's `_default_error_callback` from printing full tracebacks via `logging.error("nats: encountered error", exc_info=True)`.

2. **Use `allow_reconnect=False`**: This makes `connect()` fail fast on the first attempt instead of entering an internal retry loop. With `allow_reconnect=True` and `max_reconnect_attempts=-1`, `connect()` never returns when NATS is down -- it hangs indefinitely in the internal reconnection loop.

3. **Wrap `connect()` with `asyncio.wait_for()`**: The `connect_timeout` parameter only controls the TCP socket timeout, not the overall `connect()` call duration. Adding `asyncio.wait_for(..., timeout=5)` provides a hard ceiling on how long connect can take.

4. **All callbacks must be `async def`**: nats-py validates that `disconnected_cb`, `reconnected_cb`, `closed_cb`, and `error_cb` are coroutine functions. Using regular `def` raises `"callbacks must be coroutine functions"`.

5. **Use `nc.is_closed` (not `nc.is_connected`) for connection monitoring**: When `allow_reconnect=False`, the client transitions directly to closed state on disconnect. Polling `nc.is_closed` detects this permanent connection loss.

6. **Interruptible sleep pattern**: Use `asyncio.wait_for(stop_event.wait(), timeout=RETRY_INTERVAL)` instead of `asyncio.sleep()`. This allows graceful shutdown (set `stop` event from signal handler) while still sleeping between retries.

### Root Cause Analysis

nats-py's default error callback uses:
```python
logging.error("nats: encountered error", exc_info=True)
```

This prints full stack traces to stderr on every failed connection attempt. The `exc_info=True` parameter causes Python's logging to include the full traceback. The two-pronged fix is:
1. Suppress the logger (`logging.CRITICAL`)
2. Manage retries externally with clean status messages

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Non-async callbacks | `def disconnected_cb():` (regular function) | nats-py validates callbacks with `asyncio.iscoroutinefunction()` and raises "callbacks must be coroutine functions" | All nats-py callbacks (`disconnected_cb`, `reconnected_cb`, `closed_cb`, `error_cb`) must be `async def` coroutines |
| `allow_reconnect=True` with `max_reconnect_attempts=-1` | Let nats-py handle reconnection internally with infinite retries | `connect()` never returns when NATS is down -- hangs in internal retry loop with no way to show status | Use `allow_reconnect=False` and manage retries externally for full control over status display |
| `allow_reconnect=True` with `max_reconnect_attempts=30` + `reconnect_time_wait=2` | Bounded internal retries (30 attempts x 2s = 60s) | 60 seconds of internal retrying before `connect()` raises, during which no status output is possible | Even bounded internal retries are too slow for responsive UX; external retry loop is the only clean solution |
| `connect_timeout=3` alone | Set TCP connect timeout expecting it to cap the overall `connect()` duration | `connect_timeout` only applies to the TCP socket timeout, not the overall `connect()` call with reconnection logic | Always wrap `connect()` with `asyncio.wait_for()` for a hard timeout guarantee |
| `git checkout --ours` during rebase | Used `--ours` to keep "our" changes during rebase conflict | In rebase context, `--ours` refers to the BASE branch (main), not YOUR commits. Opposite of merge semantics. | During rebase: `--ours` = base branch, `--theirs` = your commits. During merge: `--ours` = your branch, `--theirs` = incoming branch |

## Results & Parameters

### Configuration

```python
# Connection parameters
connect_config = {
    "allow_reconnect": False,     # fail fast, manage retries externally
    "connect_timeout": 3,         # TCP socket timeout (seconds)
}

# External retry parameters
RETRY_INTERVAL = 5                # seconds between reconnection attempts
CONNECT_HARD_TIMEOUT = 5          # asyncio.wait_for timeout (seconds)

# Logging suppression
import logging
logging.getLogger("nats").setLevel(logging.CRITICAL)
```

### Expected Output

When NATS is down at startup:
```
[DISCONNECTED] ConnectionRefusedError: ...
[RECONNECTING] Retrying in 5s...
[DISCONNECTED] ConnectionRefusedError: ...
[RECONNECTING] Retrying in 5s...
```

When NATS comes up:
```
[CONNECTED] nats://<host>:4222
```

When NATS goes down during operation:
```
[DISCONNECTED]
[RECONNECTING] Retrying in 5s...
```

When Ctrl+C is pressed during retry:
```
[RECONNECTING] Retrying in 5s...
^C
(clean shutdown, no traceback)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | odysseus-console.py NATS event viewer | Full lifecycle: NATS down -> clean retry -> NATS up -> events flowing -> NATS down -> clean disconnect -> retry |

## References

- [nats-py GitHub](https://github.com/nats-io/nats.py) -- Official Python client for NATS
- [architecture-crosshost-nats-compose-deployment](architecture-crosshost-nats-compose-deployment.md) -- Cross-host NATS deployment patterns (related skill)
- [natsc-fetchcontent-cpp20-integration](natsc-fetchcontent-cpp20-integration.md) -- NATS C client for C++ services (related skill)
