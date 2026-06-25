---
name: fastapi-testing-get-settings-direct-call-patch
description: "Fix test failures when app.dependency_overrides has no effect on a FastAPI route. Use when: (1) dependency_overrides for get_settings does not change route behavior in tests, (2) a route calls get_settings() directly instead of via Depends(), (3) settings changes in tests are silently ignored."
category: testing
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# FastAPI Testing: Patch Direct `get_settings()` Calls

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Override settings in tests for FastAPI routes that call `get_settings()` directly (not via `Depends`) |
| **Outcome** | Successful — `patch("module.get_settings", return_value=...)` correctly overrides settings |
| **Verification** | verified-local (507 tests passed) |

## When to Use

- `app.dependency_overrides[get_settings]` is set but the route still uses real settings
- A FastAPI route body calls `cfg = get_settings()` directly instead of declaring `cfg: Settings = Depends(get_settings)`
- Tests asserting on route behavior that depends on settings are silently failing
- Adding a new settings-dependent field to a route response and the test always sees the default value

## Verified Workflow

### Quick Reference

```python
# WRONG — only works for routes using Depends(get_settings)
app.dependency_overrides[get_settings] = lambda: test_settings

# RIGHT — patch the direct call in the module namespace
from unittest.mock import patch
with patch("myapp.server.get_settings", return_value=test_settings):
    body = client.get("/health").json()
```

### Detailed Steps

1. **Identify how the route gets settings** — read the route handler:
   ```python
   # Pattern A — uses DI (dependency_overrides works):
   async def health(cfg: Settings = Depends(get_settings)) -> HealthResponse:
       ...

   # Pattern B — direct call (dependency_overrides does NOT work):
   async def health(response: Response) -> HealthResponse:
       cfg = get_settings()  # <-- bypasses DI
       ...
   ```

2. **For Pattern B routes**, use `unittest.mock.patch` targeting the module where `get_settings` is imported:
   ```python
   from unittest.mock import patch
   from hermes.config import Settings

   test_settings = Settings(some_key="test_value")
   with patch("hermes.server.get_settings", return_value=test_settings):
       body = client.get("/health").json()
   assert body["some_field"] == "expected"
   ```

3. **Target the correct module path** — patch where the name is *used*, not where it is *defined*:
   - Route is in `hermes/server.py` and imports `from hermes.config import get_settings`
   - Patch target: `"hermes.server.get_settings"` ✓
   - NOT `"hermes.config.get_settings"` ✗ (that patches the definition, not the binding)

4. **Scope the patch to the request only** — use the context manager form so the patch is removed after the `with` block, preventing test pollution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `app.dependency_overrides[get_settings]` before `_build_client()` | Set override, then built client | `_build_client()` overwrites the override with its own `Settings` | Set overrides AFTER `_build_client()` returns |
| `app.dependency_overrides[get_settings]` after `_build_client()` | Set override after client built, before request | Route calls `get_settings()` directly — DI override is never consulted | Use `patch()` instead of `dependency_overrides` for direct-call routes |
| `monkeypatch.setenv` + `get_settings.cache_clear()` | Set env var, cleared lru_cache | Works but is fragile — env var isolation requires cleanup and can leak | `patch(return_value=...)` is cleaner and more explicit |

## Results & Parameters

**Pattern to distinguish DI vs direct call:**

```bash
# Check if the route uses Depends:
grep -n "Depends(get_settings)\|get_settings()" src/hermes/server.py
```

If the route has `Depends(get_settings)` → `dependency_overrides` works.
If the route has `cfg = get_settings()` inline → must use `patch()`.

**Full working test example (ProjectHermes style):**

```python
def test_health_reports_dead_letter_api_key_configured_when_set(self) -> None:
    from unittest.mock import patch
    from hermes.config import Settings

    client = _build_client()  # build first — sets its own dependency_overrides
    test_settings = Settings(
        webhook_secret=TEST_SECRET,
        dead_letter_api_key="k" * 32,
    )
    with patch("hermes.server.get_settings", return_value=test_settings):
        body = client.get("/health").json()
    assert body["dead_letter_api_key_configured"] is True
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHermes | PR #690 (issue #520) — testing new `dead_letter_api_key_configured` field in `/health` | Two tests fixed by switching from `dependency_overrides` to `patch()` |
