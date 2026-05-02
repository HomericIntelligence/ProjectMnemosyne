---
name: fastapi-pydantic-settings-test-isolation
description: "Fix FastAPI test isolation failures caused by Depends() capturing function references at import time and pydantic-settings reading .env at instantiation. Use when: (1) patching get_settings returns mock but tests still use real settings, (2) tests pass in CI but fail locally due to .env, (3) rate limiting returns 202 instead of 429, (4) AsyncMock triggers unawaited coroutine warnings."
category: testing
date: '2026-04-24'
version: 1.0.0
---
# Skill: FastAPI Pydantic-Settings Test Isolation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-24 |
| **Category** | testing |
| **Objective** | Reliably isolate FastAPI tests that depend on pydantic-settings and Depends() injection |
| **Outcome** | Success — fixes confirmed in CI on HomericIntelligence/ProjectHermes |
| **Verification** | verified-ci |

## When to Use

Apply this skill when:
- `patch("hermes.server.get_settings", return_value=mock)` has no effect on request handling
- Tests pass in CI (no `.env`) but fail locally (`.env` present with secrets)
- `@limiter.limit("N/minute")` decorator is present but rate limiting is not enforced (HTTP 202 instead of 429)
- `AsyncMock` combined with `asyncio.wait_for` patching produces `RuntimeWarning: coroutine ... was never awaited`
- Any FastAPI app using `Depends(get_settings)` with `lru_cache`-decorated settings functions

## Verified Workflow

### Quick Reference

```python
import os
from contextlib import contextmanager
from fastapi.testclient import TestClient

@contextmanager
def _settings_client(overrides: dict):
    from hermes.server import app
    from hermes.config import get_settings

    old_env = {k: os.environ.get(k) for k in overrides}
    os.environ.update(overrides)
    get_settings.cache_clear()
    try:
        yield TestClient(app)
    finally:
        get_settings.cache_clear()
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
```

### Detailed Steps

#### 1. Stop patching the module-level name — set env vars instead

`Depends(get_settings)` captures the **function object** at import time. Patching
`"hermes.server.get_settings"` replaces the name in the module namespace but `Depends` still holds
a reference to the original callable. The patch is silently ignored by FastAPI's DI system.

```python
# WRONG — Depends already captured the original get_settings at import time
with patch("hermes.server.get_settings", return_value=mock_settings):
    response = client.post("/webhook", ...)

# CORRECT — set env vars so the real get_settings returns the desired values
os.environ["WEBHOOK_SECRET"] = "test-secret-value-32-chars-minimum"
get_settings.cache_clear()   # if decorated with @lru_cache
```

#### 2. Always save and restore env vars around settings-dependent tests

pydantic-settings reads `.env` at `Settings()` instantiation. A `.env` file at the project root
(e.g. containing `WEBHOOK_SECRET=...`) will be picked up locally but not in CI, causing asymmetric
failures. Never assume env state is blank.

```python
# Save original values
old_secret = os.environ.get("WEBHOOK_SECRET")

os.environ["WEBHOOK_SECRET"] = "test-secret-value-32-chars-minimum"
get_settings.cache_clear()

try:
    # ... run test ...
finally:
    get_settings.cache_clear()
    if old_secret is None:
        os.environ.pop("WEBHOOK_SECRET", None)
    else:
        os.environ["WEBHOOK_SECRET"] = old_secret
```

Use the context manager pattern from Quick Reference to handle multiple keys cleanly.

#### 3. Add SlowAPIMiddleware explicitly for rate-limit tests

`@limiter.limit("N/minute")` decorates the route but does **not** enforce limits on its own. The
`SlowAPIMiddleware` must be registered on the app for limits to be checked. Without it, every
request returns 202 (or the normal success code) regardless of how many requests are sent.

```python
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)   # required — @limiter.limit() alone is not enough
```

In tests that verify 429 responses, make sure `SlowAPIMiddleware` is added before creating
`TestClient(app)`.

#### 4. Use AsyncMock(side_effect=...) directly — do not patch asyncio.wait_for

When a timed-out async publish needs to be simulated:

```python
# WRONG — patching asyncio.wait_for with a real async def causes unawaited coroutine warnings
async def _timeout():
    raise asyncio.TimeoutError()

with patch("asyncio.wait_for", side_effect=_timeout):
    ...

# CORRECT — set side_effect directly on the AsyncMock
mock_js = AsyncMock()
mock_js.publish = AsyncMock(side_effect=asyncio.TimeoutError())
```

#### 5. Full context manager for rate-limit + settings isolation

```python
@contextmanager
def _rate_limit_client(rate_limit: str = "5/minute"):
    from hermes.server import app
    from hermes.config import get_settings
    from hermes.rate_limit import limiter

    env_overrides = {"WEBHOOK_SECRET": _TEST_SECRET, "WEBHOOK_RATE_LIMIT": rate_limit}
    old_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    get_settings.cache_clear()
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        get_settings.cache_clear()
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | `patch("hermes.server.get_settings", return_value=mock)` | `Depends()` captured the original function at import time; patching the module name has no effect on what DI calls | Never patch the name bound by `Depends` — manipulate env vars + clear the cache instead |
| Attempt 2 | Assumed blank env state for tests that require HMAC disabled | `.env` at project root supplies `WEBHOOK_SECRET`; tests passed in CI (no file) but failed locally | Always explicitly set or unset every env var a test depends on; never assume a blank state |
| Attempt 3 | Added `@limiter.limit()` decorator only, no middleware | Requests returned 202; rate limit was never enforced | `SlowAPIMiddleware` is mandatory — the decorator alone registers the limit but doesn't evaluate it |
| Attempt 4 | Defined `async def _timeout(): raise asyncio.TimeoutError()` and patched `asyncio.wait_for` | Produced `RuntimeWarning: coroutine '_timeout' was never awaited` | Use `AsyncMock(side_effect=asyncio.TimeoutError())` directly on the mock method |

## Results & Parameters

### Configuration

Minimum env var setup for a webhook test that requires HMAC validation:

```python
_TEST_SECRET = "test-secret-value-that-is-at-least-32-chars"

env_overrides = {
    "WEBHOOK_SECRET": _TEST_SECRET,
    # add other Settings fields as needed
}
```

For `lru_cache`-decorated settings:

```python
from hermes.config import get_settings

get_settings.cache_clear()   # before test — ensure fresh settings from env
# ... test ...
get_settings.cache_clear()   # after test — don't leak cached values to next test
```

### Expected Output

- Settings-dependent tests pass both locally (with `.env`) and in CI (without `.env`)
- Rate-limit tests receive HTTP 429 after the configured threshold
- No `RuntimeWarning: coroutine ... was never awaited` in test output
- `mock_patch` of `get_settings` is replaced entirely by env var manipulation

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/ProjectHermes | CI — webhook rate-limit and timeout tests | verified-ci — all five test patterns confirmed passing |

## References

- [FastAPI Dependency Injection docs](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [pydantic-settings env var precedence](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [slowapi middleware setup](https://slowapi.readthedocs.io/en/latest/)
- [flaky-test-patch-isolation.md](flaky-test-patch-isolation.md)
