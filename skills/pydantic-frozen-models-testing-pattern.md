---
name: pydantic-frozen-models-testing-pattern
description: "Testing patterns for frozen Pydantic models. Use when: (1) converting mutable config to frozen=True, (2) rewriting mode='after' validators as mode='before', (3) fixing test override patterns with LRU-cached singletons."
category: testing
date: 2026-06-04
version: 1.0.0
verification: verified-local
tags: [pydantic, testing, frozen-models, validators, config, lru-cache]
---

## Overview

| Aspect | Details |
|--------|---------|
| **Objective** | Document testing patterns when converting Pydantic models to `frozen=True` and refactoring tests that mutate config or cached singletons. |
| **Outcome** | All 544 tests pass (97.60% coverage) with no cache-pollution bugs. Frozen models prevent accidental field mutations that lead to test-order failures. |
| **Verification Level** | verified-local: validated in ProjectHermes issue #454 with full test suite run. |
| **Project** | ProjectHermes (issue #454: make Settings immutable) |

## When to Use

This skill applies when:

1. **Converting models to frozen** — You're adding `frozen=True` to a Pydantic model's `model_config` and validators/tests break.
2. **Mode='after' validators fail** — You get `ValidationError` when trying to mutate the model after construction with a `@model_validator(mode="after")`.
3. **Test overrides don't work** — Direct mutations like `get_settings().field = value` no longer work after freezing, and existing tests fail mysteriously.
4. **LRU-cached singletons** — You have functions decorated with `@lru_cache` (e.g., `get_settings()`) and need to override them in tests without test pollution.

## Verified Workflow

### Quick Reference

#### Pattern 1: Mode-Before Validator for Field Defaults

**Problem:** `@model_validator(mode="after")` that mutates fields fails on frozen models.

**Solution:** Use `mode="before"` to compute defaults before the instance is frozen. Operate on the raw input dict:

```python
from pydantic import model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True)

    hermes_port: int = 8080
    hermes_public_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_public_url_default(cls, data: object) -> object:
        """Default ``hermes_public_url`` from ``hermes_port`` when unset.

        Operates on raw input dict before instance construction (freezing).
        """
        if not isinstance(data, dict):
            return data
        if data.get("hermes_public_url") is None:
            port = data.get("hermes_port", 8080)
            data["hermes_public_url"] = f"http://localhost:{port}"
        return data
```

#### Pattern 2: Monkeypatch + cache_clear() for LRU-Cached Config Overrides

**Problem:** `dependency_overrides` don't work for direct `get_settings()` calls (cache returns old value).

**Solution:** Use `monkeypatch.setenv()` + `get_settings.cache_clear()` in test setup:

```python
def test_webhook_with_custom_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from hermes.config import get_settings

    monkeypatch.setenv("WEBHOOK_SECRET", "my-custom-secret-xxxxx")
    get_settings.cache_clear()  # Force re-instantiation from env vars

    settings = get_settings()
    assert settings.webhook_secret == "my-custom-secret-xxxxx"
    # ... rest of test
```

#### Pattern 3: Test Helper with Monkeypatch Parameter

**Problem:** Test helper functions that override config can't clear the cache themselves.

**Solution:** Accept `monkeypatch` as a parameter and let the test method handle cache clearing:

```python
class TestDeadLettersGetAuth:
    def _build_client(self, *, key: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        """Helper to construct a test client with custom DEAD_LETTER_API_KEY."""
        from hermes.config import get_settings
        from hermes.server import app

        monkeypatch.setenv("DEAD_LETTER_API_KEY", key)
        get_settings.cache_clear()

        # ... set up mock publisher, etc.
        return TestClient(app)

    def test_correct_key_returns_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._build_client(key="correct-key", monkeypatch=monkeypatch)
        resp = client.get("/dead-letters", headers={"X-Dead-Letter-Key": "correct-key"})
        assert resp.status_code == 200
```

### Detailed Steps

**Step 1: Add frozen=True to model_config**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,  # <-- Add this
    )
```

**Step 2: Convert mode="after" validators to mode="before"**

For each `@model_validator(mode="after")` that mutates self:
- Change to `@model_validator(mode="before")` with `@classmethod`
- Accept `data: object` parameter (the raw input dict or object)
- Check `isinstance(data, dict)` before accessing dict methods
- Modify the dict and return it; never mutate `self`

Example (Pydantic v2):
```python
# BEFORE (fails on frozen):
@model_validator(mode="after")
def _set_default(self) -> "Settings":
    if self.hermes_public_url is None:
        self.hermes_public_url = f"http://localhost:{self.hermes_port}"
    return self

# AFTER (works on frozen):
@model_validator(mode="before")
@classmethod
def _set_default(cls, data: object) -> object:
    if not isinstance(data, dict):
        return data
    if data.get("hermes_public_url") is None:
        port = data.get("hermes_port", 8080)
        data["hermes_public_url"] = f"http://localhost:{port}"
    return data
```

**Step 3: Update the reset_settings fixture**

Document the frozen guarantee so future developers know not to try direct mutations:

```python
@pytest.fixture(autouse=True)
def reset_settings() -> Generator[None, None, None]:
    """Clear the get_settings LRU cache and dependency overrides before/after each test.

    Settings is ``frozen=True``, so direct field mutation raises ``ValidationError``.
    Tests must override config via env vars + cache_clear() or by constructing
    a fresh ``Settings()`` with explicit kwargs.
    """
    from hermes.server import app

    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()
```

**Step 4: Refactor test methods that mutate config**

For each test class with setup/teardown that mutates `get_settings()`:
- Remove direct field assignments
- Add `monkeypatch: pytest.MonkeyPatch` parameter to setup helper
- Use `monkeypatch.setenv()` to override env vars
- Call `get_settings.cache_clear()` to force re-instantiation
- Remove `teardown_method` (the `reset_settings` fixture cleans up)

Example:
```python
# BEFORE (fails on frozen):
class TestDeadLettersGetAuth:
    def _build_client(self, *, key: str) -> TestClient:
        get_settings().dead_letter_api_key = key  # <-- Raises ValidationError
        return TestClient(app)

    def teardown_method(self) -> None:
        get_settings().dead_letter_api_key = ""  # <-- Also raises

# AFTER (works on frozen):
class TestDeadLettersGetAuth:
    def _build_client(self, *, key: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        monkeypatch.setenv("DEAD_LETTER_API_KEY", key)
        get_settings.cache_clear()
        return TestClient(app)

    def test_correct_key_returns_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._build_client(key="valid-key", monkeypatch=monkeypatch)
        assert client.get("/dead-letters", headers={"X-Dead-Letter-Key": "valid-key"}).status_code == 200

    # No teardown_method needed — reset_settings fixture handles cleanup
```

**Step 5: Add immutability tests**

Verify that the frozen model actually prevents mutations (regression guard):

```python
class TestSettingsImmutable:
    def test_settings_is_frozen_direct_mutation_raises(self) -> None:
        from hermes.config import Settings

        s = Settings(_env_file=None)
        with pytest.raises(ValidationError):
            s.nats_url = "nats://mutated:4222"  # type: ignore[misc]

    def test_settings_is_frozen_via_get_settings(self) -> None:
        from hermes.config import get_settings

        get_settings.cache_clear()
        s = get_settings()
        with pytest.raises(ValidationError):
            s.hermes_port = 9999  # type: ignore[misc]

    def test_public_url_default_still_applies_under_frozen(self) -> None:
        from hermes.config import Settings

        s = Settings(hermes_port=8123, _env_file=None)
        assert s.hermes_public_url == "http://localhost:8123"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| **Keep mode='after' validators on frozen models** | Left `@model_validator(mode="after")` that mutated `self.field = value` | Pydantic freezes the instance after construction; mode="after" validators run on the frozen instance, so any field assignment raises `ValidationError` | mode="after" validators cannot mutate. Use mode="before" to modify input dict before instance construction and freezing. |
| **Use dependency_overrides for direct get_settings() calls** | Set `app.dependency_overrides[get_settings] = lambda: custom_settings` and called `get_settings()` directly in tests | Direct calls to `get_settings()` hit the `@lru_cache` decorator, returning the cached instance instead of the overridden value. dependency_overrides only applies to FastAPI's dependency injection. | For direct calls to `@lru_cache` functions, clear the cache after env var overrides: `monkeypatch.setenv()` + `get_settings.cache_clear()`. |
| **Use teardown_method for cleanup** | Added `teardown_method(self)` to reset mutated fields after each test | The `reset_settings` autouse fixture runs at test start and clears `dependency_overrides`, undoing cleanup from the previous test. Also clashes with frozen models (teardown can't mutate). | Don't use teardown_method for config cleanup. Let the autouse `reset_settings` fixture handle cache + overrides clearing before/after each test. |

## Results & Parameters

### Config Changes (src/hermes/config.py)

**Add frozen=True:**
```python
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    frozen=True,  # NEW
)
```

**Rewrite _set_public_url_default validator:**
- Change from `@model_validator(mode="after")` (instance method) to `@model_validator(mode="before")` (@classmethod)
- Accept `data: object` instead of `self`
- Operate on dict keys: `data.get("hermes_port", 8080)`
- Return the modified dict

### Test Pattern Changes

| Pattern | Files Affected | Change |
|---------|----------------|--------|
| **LRU-cache override (monkeypatch + cache_clear)** | test_webhook.py:877-889, test_dead_letter_limits.py (14 methods) | Replace `get_settings().field = value` with `monkeypatch.setenv()` + `get_settings.cache_clear()` |
| **Helper function refactoring** | test_webhook.py:877, test_dead_letter_limits.py helpers | Add `monkeypatch: pytest.MonkeyPatch` parameter to test helper methods |
| **Remove teardown_method** | test_webhook.py:891-894, test_webhook.py:940-943 | Delete `teardown_method` entirely; reset_settings fixture handles cleanup |
| **Add immutability tests** | test_config.py:317-345 | New class TestSettingsImmutable with 3 tests verifying frozen behavior |

### Coverage & Test Results

- **Total tests:** 544
- **Pass rate:** 100% (all 544 pass)
- **Coverage:** 97.60%
- **Affected test classes:** 12 (TestDeadLettersGetAuth, TestDeadLettersDeleteAuth, TestSettingsImmutable, etc.)
- **Lines changed:** 162 additions, 99 deletions

## Verified On

| Project | Issue | Status | Evidence |
|---------|-------|--------|----------|
| **ProjectHermes** | #454 (make Settings immutable with frozen=True) | ✅ verified-local | Commit b7191ad: All 544 tests pass, 97.60% coverage. src/hermes/config.py:24-107 (Settings with frozen=True), tests/test_config.py:317-345 (TestSettingsImmutable). |

---

**Last Updated:** 2026-06-04
**Author:** Claude Haiku 4.5
