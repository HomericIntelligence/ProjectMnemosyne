---
name: nats-publish-retry-backoff
description: "Exponential backoff with jitter for NATS JetStream publish retries in Python. Use when: (1) building a NATS publisher that must survive transient broker outages, (2) implementing retry logic that distinguishes retryable from non-retryable NATS errors, (3) configuring publish retry parameters via Pydantic Settings, (4) designing envelope schema versioning for NATS messages."
category: architecture
date: 2026-04-24
version: "1.0.0"
user-invocable: false
tags:
  - nats
  - nats-py
  - jetstream
  - retry
  - backoff
  - jitter
  - asyncio
  - python
  - publisher
  - resilience
  - schema-versioning
---

# NATS Publish Retry Backoff with Jitter

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-24 |
| **Objective** | Implement exponential backoff with jitter for NATS JetStream publish retries, distinguishing retryable from non-retryable errors, with schema-versioned envelopes and Pydantic Settings integration |
| **Outcome** | Verified in CI — full retry loop with jitter, configurable via env vars, 5 retryable error types captured |
| **Verification** | verified-ci (HomericIntelligence/ProjectHermes) |
| **Project** | ProjectHermes (NATS JetStream webhook bridge) |

## When to Use

- Building an async Python NATS JetStream publisher that must survive transient broker outages
- Distinguishing retryable NATS errors (timeout, no responders, drain timeout, reconnecting, stale) from non-retryable errors (auth errors, bad subjects, general exceptions)
- Configuring publish retry parameters (`publish_retries`, `publish_retry_base_delay`) via Pydantic Settings / env vars
- Versioning NATS message envelopes with `schema_version` for forward-compatible consumers
- Implementing degraded-mode behavior where the `/webhook` endpoint returns 503 when the NATS publisher is unavailable (e.g., post-disconnect)

## Verified Workflow

### Quick Reference

```python
import asyncio
import json
import random
import time

import nats

# ---- 1. Retryable error types ----
_RETRYABLE_PUBLISH_ERRORS = (
    nats.errors.TimeoutError,
    nats.errors.NoRespondersError,
    nats.errors.DrainTimeoutError,
    nats.errors.ConnectionReconnectingError,
    nats.errors.StaleConnectionError,
)

# ---- 2. Retry loop with exponential backoff + jitter ----
async def publish_with_retry(js, subject, message, retries=3, base_delay=0.1, timeout=5.0):
    last_exc = None
    for attempt in range(retries):
        try:
            t0 = time.perf_counter()
            await js.publish(subject, message, timeout=timeout)
            latency = time.perf_counter() - t0
            return latency
        except _RETRYABLE_PUBLISH_ERRORS as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = min(base_delay * (2 ** attempt), 2.0) * random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
    raise last_exc  # propagate after exhausting retries
    # Non-retryable errors (e.g. nats.errors.AuthorizationError, Exception) are
    # NOT caught here — they propagate immediately out of js.publish()

# ---- 3. Versioned envelope ----
payload = json.dumps({
    "schema_version": 1,
    "event": event_type,
    "data": data,
    "timestamp": timestamp.isoformat(),
    "request_id": request_id,
}).encode()
await js.publish(subject, payload, timeout=publish_timeout)
```

### Detailed Steps

#### Step 1: Define Retryable Error Types

Five NATS error types are safe to retry; everything else propagates immediately:

```python
_RETRYABLE_PUBLISH_ERRORS = (
    nats.errors.TimeoutError,           # broker did not ACK within timeout
    nats.errors.NoRespondersError,      # no JetStream consumers/server listening
    nats.errors.DrainTimeoutError,      # drain in progress, retry after backoff
    nats.errors.ConnectionReconnectingError,  # TOCTOU race: connection lost between
    nats.errors.StaleConnectionError,         # is_connected check and publish call
)
```

`ConnectionReconnectingError` and `StaleConnectionError` handle the TOCTOU race: a caller checked `publisher.is_connected == True` but the connection dropped before the actual `publish()` call. These are always transient.

Non-retryable errors (`nats.errors.AuthorizationError`, `nats.errors.BadSubjectError`, generic `Exception`) are not in the tuple so they propagate immediately without burning retry budget.

#### Step 2: Exponential Backoff with Jitter Formula

```python
delay = min(base_delay * (2 ** attempt), 2.0) * random.uniform(0.5, 1.5)
await asyncio.sleep(delay)
```

- `base_delay * 2^attempt`: doubles each attempt (0.1s, 0.2s, 0.4s with default base)
- `min(..., 2.0)`: hard cap at 2 seconds prevents runaway waits
- `* random.uniform(0.5, 1.5)`: ±50% jitter prevents thundering herd when many publishers retry simultaneously

Only sleep between attempts, not after the last attempt. Pattern:

```python
for attempt in range(retries):
    try:
        await js.publish(subject, message, timeout=timeout)
        return  # success
    except _RETRYABLE_PUBLISH_ERRORS as exc:
        last_exc = exc
        if attempt < retries - 1:   # don't sleep after final attempt
            delay = min(base_delay * (2 ** attempt), 2.0) * random.uniform(0.5, 1.5)
            logger.warning("Retrying in %.3fs (attempt %d/%d): %s", delay, attempt+1, retries, exc)
            await asyncio.sleep(delay)
raise last_exc
```

#### Step 3: Publisher Configuration via Pydantic Settings

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    publish_retries: int = Field(default=3, ge=1)
    publish_retry_base_delay: float = Field(default=0.1, gt=0)
    nats_publish_timeout: float = Field(default=5.0, gt=0)
    # ge=1 ensures at least 1 attempt; gt=0 ensures positive delay
```

Pass through to the publish method for override capability in tests:

```python
async def publish(self, payload, publish_timeout=5.0, *, publish_retries=None, publish_retry_base_delay=None):
    settings = get_settings()
    retries = publish_retries if publish_retries is not None else settings.publish_retries
    base_delay = publish_retry_base_delay if publish_retry_base_delay is not None else settings.publish_retry_base_delay
```

#### Step 4: NATS Envelope Schema Versioning

Include `schema_version: 1` in every published message to enable consumers to handle format migrations:

```python
message = json.dumps({
    "schema_version": 1,       # increment when envelope structure changes
    "event": payload.event,
    "data": payload.data,
    "timestamp": payload.timestamp.isoformat(),
    "request_id": request_id,  # end-to-end correlation ID from HTTP header
}).encode()
```

Consumers check `schema_version` before parsing. When bumping to version 2, consumers can handle both versions during a rolling deploy.

#### Step 5: Degraded-Mode Behavior at the HTTP Layer

When the publisher loses its NATS connection post-startup (via reconnect callbacks setting `_connected = False`), the `/webhook` endpoint must return 503 rather than raising a 500 error:

```python
@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    publisher: Publisher = app.state.publisher
    if not publisher.is_connected:
        raise HTTPException(
            status_code=503,
            detail="NATS publisher not connected",
        )
    # ... proceed with publish
```

**Note on startup failure**: ProjectHermes aborts startup (raises the connection exception) if all NATS connection retries at startup are exhausted — it does NOT enter a degraded mode that continues serving HTTP. The 503 degraded behavior applies only to mid-operation disconnects.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Sleeping after final attempt | `if attempt < retries` instead of `if attempt < retries - 1` | Adds unnecessary sleep latency after all retries are exhausted before raising | Guard the sleep with `if attempt < retries - 1` to avoid sleeping after the last failure |
| Catching bare `Exception` in retry loop | Wrapping entire `except` in `Exception` catch | Hides non-retryable bugs (auth errors, bad subjects, logic errors) as transient failures — burns retry budget and delays surfacing real errors | Only catch the explicit `_RETRYABLE_PUBLISH_ERRORS` tuple; let non-retryable errors propagate immediately |
| Fixed delay without jitter | `delay = base_delay * 2**attempt` (no jitter) | When many publishers fail simultaneously (e.g., broker restart), they all retry at the same times — thundering herd overwhelms broker | Multiply by `random.uniform(0.5, 1.5)` to spread retries across a window |
| Uncapped exponential delay | No `min(..., 2.0)` cap | With base=0.1 and retries=10, delay grows to 51.2s on the 10th attempt — unacceptable latency for webhook processing | Always cap max delay (2.0s works well for interactive webhook pipelines) |
| Degraded-mode lifespan | Continue serving HTTP when NATS is unavailable at startup | Adds complexity; most callers expect NATS to be up before webhooks are accepted | Abort startup on NATS failure; only return 503 for mid-operation disconnects via `publisher.is_connected` check |

## Results & Parameters

### Configuration

| Parameter | Env Var | Default | Constraint | Notes |
|-----------|---------|---------|------------|-------|
| `publish_retries` | `PUBLISH_RETRIES` | 3 | `ge=1` | Total attempts including first try |
| `publish_retry_base_delay` | `PUBLISH_RETRY_BASE_DELAY` | 0.1s | `gt=0` | Doubles each attempt |
| `nats_publish_timeout` | `NATS_PUBLISH_TIMEOUT` | 5.0s | `gt=0` | Per-attempt JetStream ACK timeout |
| Max delay cap | — | 2.0s | hardcoded | `min(base * 2^attempt, 2.0)` |
| Jitter range | — | 0.5–1.5x | hardcoded | `random.uniform(0.5, 1.5)` |

### Retry Budget

With defaults (`retries=3`, `base_delay=0.1s`, `publish_timeout=5.0s`):

| Attempt | Sleep Before (mean) | Timeout Budget |
|---------|---------------------|----------------|
| 1 | 0s | 5.0s |
| 2 | 0.1s | 5.0s |
| 3 | 0.2s | 5.0s |
| Total worst case | ~15.3s + jitter | — |

### Retryable Error Coverage

| Error Type | Cause | Safe to Retry? |
|-----------|-------|----------------|
| `nats.errors.TimeoutError` | Broker did not ACK within `publish_timeout` | Yes |
| `nats.errors.NoRespondersError` | No active JetStream stream or consumer | Yes |
| `nats.errors.DrainTimeoutError` | Client in drain mode | Yes |
| `nats.errors.ConnectionReconnectingError` | TOCTOU race — connection dropped between check and publish | Yes |
| `nats.errors.StaleConnectionError` | TOCTOU race — stale connection handle | Yes |
| `nats.errors.AuthorizationError` | Invalid credentials | No — propagates immediately |
| `nats.errors.BadSubjectError` | Malformed NATS subject | No — propagates immediately |
| `Exception` (generic) | Logic errors, bugs | No — propagates immediately |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | `src/hermes/publisher.py` `Publisher.publish()` | Full retry loop verified in CI; 5 retryable error types, jitter, schema_version, Settings integration |

## References

- [nats-py GitHub](https://github.com/nats-io/nats.py) — Official Python NATS client
- [nats-py-connection-resilience-patterns](nats-py-connection-resilience-patterns.md) — Connection-level retry patterns (vs. publish-level)
- [retry-transient-errors](retry-transient-errors.md) — General subprocess retry pattern with exponential backoff
