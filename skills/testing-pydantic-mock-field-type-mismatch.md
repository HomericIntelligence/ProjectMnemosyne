---
name: testing-pydantic-mock-field-type-mismatch
description: "Fix HTTP 500 errors in tests caused by Pydantic response model rejecting MagicMock attributes during response serialization. Use when: (1) an endpoint test expects 4xx/5xx but gets 500 unexpectedly, (2) a FastAPI/Starlette endpoint uses a Pydantic response model, (3) mock objects populate response model fields, (4) Pydantic ValidationError appears in server logs during testing."
category: testing
date: '2026-04-25'
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pydantic
  - magicmock
  - fastapi
  - validation
  - http-status
  - response-model
  - serialization
---

# Skill: Pydantic Response Model Rejects MagicMock Attributes

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-25 |
| **Objective** | Fix test asserting specific HTTP status code (503) receiving 500 instead |
| **Outcome** | Success — test passes after explicitly typing mock attributes; PR #300 merged to main |
| **Verification** | verified-ci |
| **Project** | HomericIntelligence/ProjectHermes PR #300 |

## When to Use

- A test expects a specific HTTP status code (e.g. 503) but receives 500 instead
- The endpoint constructs a Pydantic response model populated from a mock object's attributes
- Server logs (or `raise_server_exceptions=False` test output) show a `ValidationError` during response serialization
- You have `MagicMock()` attributes flowing into `int`, `str`, `bool`, or other concrete Pydantic field types
- The 500 occurs during response body construction, not during application logic

## Verified Workflow

### Quick Reference

```python
# WRONG — MagicMock attributes are MagicMock objects, not int/str
mock_publisher = MagicMock()
# mock_publisher.reconnect_count  →  MagicMock (not int) → Pydantic ValidationError → 500

# RIGHT — Explicitly set typed values for every Pydantic response field
mock_publisher = MagicMock()
mock_publisher.reconnect_count = 0      # int field
mock_publisher.last_error = ""          # str field
mock_publisher.is_connected = False     # bool field
mock_publisher.dead_letter_count = 0    # int field
```

### Detailed Steps

1. **Identify which Pydantic model is used as the response model** for the endpoint under test.
   Look at the route decorator: `@router.get("/health", response_model=HealthResponse)` or
   the explicit `return HealthResponse(...)` in the handler.

2. **List every field** in that Pydantic model and note its type annotation.

3. **Find which fields are populated from mock object attributes.** Trace the handler code
   to see which `mock.attribute` values end up in the response model.

4. **Explicitly set each field on the mock** to a concrete value of the correct Python type:

   ```python
   mock_publisher.reconnect_count = 0    # must match nats_reconnect_count: int
   mock_publisher.last_error = ""        # must match nats_last_error: str
   mock_publisher.is_connected = False   # must match is_connected: bool
   ```

5. **Use `raise_server_exceptions=False`** in `TestClient` to get the actual HTTP status code
   from error responses rather than having the framework re-raise the exception:

   ```python
   with TestClient(app, raise_server_exceptions=False) as client:
       resp = client.get("/health")
       assert resp.status_code == 503
   ```

6. **Run the test** and verify the expected status code is returned, not 500.

### Full Test Example

```python
def test_lifespan_degraded_health_returns_503(mock_publisher: MagicMock) -> None:
    err = OSError("NATS down")
    mock_publisher.connect.side_effect = err
    mock_publisher.is_connected = False
    mock_publisher.dead_letter_count = 0
    mock_publisher.reconnect_count = 0      # <-- must be int, not MagicMock
    mock_publisher.last_error = ""          # <-- must be str, not MagicMock
    with (
        patch("hermes.server.Publisher", return_value=mock_publisher),
        patch("hermes.server.asyncio.sleep", new_callable=AsyncMock),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            assert resp.status_code == 503
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Assumed 500 was from `connect.side_effect = OSError(...)` in application logic | The OSError was handled — the 500 came from Pydantic `ValidationError` at serialization time, not from the connect call | Always check where in the request lifecycle a 500 originates; application logic errors vs. response serialization errors are distinct failure points |

## Results & Parameters

**Pydantic model that triggered the bug (`HealthResponse`):**

```python
class HealthResponse(BaseModel):
    status: str
    is_connected: bool
    dead_letter_count: int
    nats_reconnect_count: int    # ← MagicMock object fails here
    nats_last_error: str         # ← MagicMock object fails here
```

**Endpoint handler pattern:**

```python
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="degraded" if not publisher.is_connected else "ok",
        is_connected=publisher.is_connected,
        dead_letter_count=publisher.dead_letter_count,
        nats_reconnect_count=publisher.reconnect_count,   # ← reads from mock
        nats_last_error=publisher.last_error,             # ← reads from mock
    )
```

**Root cause:** `MagicMock()` auto-attributes return `MagicMock` instances. Pydantic v2
rejects `MagicMock` for `int` and `str` fields, raising `ValidationError` at serialization
time. The framework catches this and returns 500 — masking the intended 503.

**Key rule:** When testing endpoints that serialize Pydantic response models, every field
populated from a mock object must be explicitly set to a value of the correct Python type.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | PR #300 — NATS publisher health endpoint test | `test_lifespan_degraded_health_returns_503` in `tests/test_server.py` |
