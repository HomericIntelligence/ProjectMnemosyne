# Notes: Pydantic Frozen Models Testing Pattern

## Session Context

**Issue:** ProjectHermes #454 — Make Settings immutable with `frozen=True`

**Problem:** After adding `frozen=True` to the Settings Pydantic model, direct field mutations in tests raised `ValidationError`, breaking:
1. Test helper methods that override config via direct assignment
2. Validators that tried to mutate `self` after construction
3. Test teardown cleanup that mutated cached singleton instances

**Solution:** Refactor to use mode='before' validators and monkeypatch + cache_clear() pattern.

## Code Evidence

### 1. Validator Rewrite: mode="after" → mode="before"

**File:** `src/hermes/config.py` (lines 103-107 in fixed version)

**Problem Validator (mode="after"):**
```python
@model_validator(mode="after")
def _set_public_url_default(self) -> "Settings":
    if self.hermes_public_url is None:
        self.hermes_public_url = f"http://localhost:{self.hermes_port}"
    return self
```

When frozen=True, attempting `self.hermes_public_url = ...` raises:
```
pydantic.ValidationError: Field is immutable (frozen model)
```

**Fixed Validator (mode="before"):**
```python
@model_validator(mode="before")
@classmethod
def _set_public_url_default(cls, data: object) -> object:
    """Default ``hermes_public_url`` from ``hermes_port`` when unset.

    Runs before instance construction so it works on a frozen model. Operates
    on the raw input dict (env-var dict from pydantic-settings or a kwargs
    dict from explicit ``Settings(...)`` calls). Other input shapes
    (e.g. ``BaseModel`` instances) are passed through unchanged.
    """
    if not isinstance(data, dict):
        return data
    if data.get("hermes_public_url") is None:
        port = data.get("hermes_port", 8080)
        data["hermes_public_url"] = f"http://localhost:{port}"
    return data
```

**Key Points:**
- mode="before" runs before instance construction, so the model isn't frozen yet
- Data is a raw dict (not the frozen instance)
- Must check `isinstance(data, dict)` because other input types (BaseModel instances) are passed through as-is
- Modify the dict in-place and return it

**Commit:** b7191ad (ProjectHermes)

### 2. Test Pattern: monkeypatch + cache_clear()

**File:** `tests/test_webhook.py` (lines 877-889, fixed version)

**Before (fails on frozen model):**
```python
class TestDeadLettersGetAuth:
    def _build_client(self, *, key: str) -> TestClient:
        from hermes.config import get_settings
        from hermes.publisher import Publisher
        from hermes.server import app

        mock_publisher = MagicMock(spec=Publisher)
        mock_publisher.is_connected = True
        mock_publisher.active_subjects = []
        mock_publisher.publish = AsyncMock()
        mock_publisher.dead_letters = []
        app.state.publisher = mock_publisher
        get_settings().dead_letter_api_key = key  # <-- Raises ValidationError
        return TestClient(app, raise_server_exceptions=True)

    def teardown_method(self) -> None:
        from hermes.config import get_settings
        get_settings().dead_letter_api_key = ""  # <-- Also raises
```

**After (works on frozen model):**
```python
class TestDeadLettersGetAuth:
    def _build_client(self, *, key: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        from hermes.config import get_settings
        from hermes.publisher import Publisher
        from hermes.server import app

        monkeypatch.setenv("DEAD_LETTER_API_KEY", key)
        get_settings.cache_clear()

        mock_publisher = MagicMock(spec=Publisher)
        mock_publisher.is_connected = True
        mock_publisher.active_subjects = []
        mock_publisher.publish = AsyncMock()
        mock_publisher.dead_letters = []
        app.state.publisher = mock_publisher
        return TestClient(app, raise_server_exceptions=True)

    def test_correct_key_returns_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._build_client(key=_DEAD_LETTER_KEY, monkeypatch=monkeypatch)
        resp = client.get("/dead-letters", headers={"X-Dead-Letter-Key": _DEAD_LETTER_KEY})
        assert resp.status_code == 200

    # No teardown_method — reset_settings fixture handles cleanup
```

**Why This Works:**
1. `monkeypatch.setenv("DEAD_LETTER_API_KEY", key)` modifies the environment
2. `get_settings.cache_clear()` clears the `@lru_cache`, forcing re-instantiation
3. Next call to `get_settings()` reads the modified env var and constructs a fresh Settings instance
4. The `reset_settings` autouse fixture clears cache+overrides at test start, preventing pollution

**Key Points:**
- Monkeypatch parameter must be passed to helper method that overrides env
- Can't use `dependency_overrides[get_settings] = ...` for direct `get_settings()` calls — they hit the cache
- Must call `get_settings.cache_clear()` after `monkeypatch.setenv()` to force re-instantiation
- No teardown_method needed; the autouse fixture cleans up

**Affected Files & Methods:**
- `test_webhook.py`: TestDeadLettersGetAuth (14 methods fixed), TestDeadLettersDeleteAuth (14 methods fixed)
- `test_dead_letter_limits.py`: Multiple test methods using similar pattern
- Total: ~28 test methods refactored

**Commit:** b7191ad (ProjectHermes)

### 3. Fixture Clarification

**File:** `tests/conftest.py` (reset_settings fixture)

**Before:**
```python
@pytest.fixture(autouse=True)
def reset_settings() -> Generator[None, None, None]:
    """Clear the get_settings LRU cache and dependency overrides before/after each test."""
    from hermes.server import app

    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()
```

**After (with documentation):**
```python
@pytest.fixture(autouse=True)
def reset_settings() -> Generator[None, None, None]:
    """Clear the get_settings LRU cache and dependency overrides before/after each test.

    Settings is ``frozen=True`` (see ``hermes.config.Settings.model_config``), so
    direct field mutation raises ``ValidationError``. Tests must override config via
    ``app.dependency_overrides[get_settings] = ...`` or by setting env vars and
    constructing a fresh ``Settings()``.
    """
    from hermes.server import app

    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()
```

**Note:** No code change needed, just added clarifying docstring to explain the frozen guarantee.

**Commit:** b7191ad (ProjectHermes)

### 4. Immutability Verification Tests

**File:** `tests/test_config.py` (lines 317-345)

```python
class TestSettingsImmutable:
    """Settings is frozen to prevent test pollution (issue #454)."""

    def test_settings_is_frozen_direct_mutation_raises(self) -> None:
        """Direct field mutation must raise ValidationError (see issue #454)."""
        from hermes.config import Settings

        s = Settings(_env_file=None)
        with pytest.raises(ValidationError):
            s.nats_url = "nats://mutated:4222"  # type: ignore[misc]

    def test_settings_is_frozen_via_get_settings(self) -> None:
        """Mutation through the cached get_settings() instance must also raise."""
        from hermes.config import get_settings

        get_settings.cache_clear()
        s = get_settings()
        with pytest.raises(ValidationError):
            s.hermes_port = 9999  # type: ignore[misc]

    def test_public_url_default_still_applies_under_frozen(self) -> None:
        """Regression: the mode='before' default must still populate hermes_public_url."""
        from hermes.config import Settings

        s = Settings(hermes_port=8123, _env_file=None)
        assert s.hermes_public_url == "http://localhost:8123"
```

**Purpose:**
1. Verify frozen=True actually prevents mutations (guard against accidental regression)
2. Ensure mode='before' validator still computes defaults correctly
3. Test the cached singleton path to ensure immutability holds there too

**Commit:** b7191ad (ProjectHermes)

## Why mode="before" Validators Work

Pydantic v2 validator execution order:
1. `mode="before"` validators run on raw input (dict or object) BEFORE instance construction
2. Field deserialization / validation
3. `mode="after"` validators run on constructed instance AFTER all fields are set

When `frozen=True`:
- Instance is immutable after construction
- Any attempt to set `self.field = value` in mode="after" raises ValidationError
- mode="before" operates on the input dict before freezing, so mutations are safe

**Example Flow:**

```python
# Input: env vars + settings overrides
data = {
    "hermes_port": 8123,
    "hermes_public_url": None,
    ...other fields...
}

# Step 1: mode="before" validator (can mutate data dict)
@model_validator(mode="before")
@classmethod
def _set_public_url_default(cls, data: object) -> object:
    if isinstance(data, dict) and data.get("hermes_public_url") is None:
        port = data.get("hermes_port", 8080)
        data["hermes_public_url"] = f"http://localhost:{port}"  # Mutate dict OK
    return data

# After step 1:
data = {
    "hermes_port": 8123,
    "hermes_public_url": "http://localhost:8123",  # <-- Defaulted
    ...other fields...
}

# Step 2: Construct instance from modified dict
instance = Settings(**data)  # Frozen at this point

# Step 3: mode="after" validators (cannot mutate instance)
@model_validator(mode="after")
def _validate_something(self) -> "Settings":
    # self.field = new_value  # <-- Would raise ValidationError
    return self  # Just validate, don't mutate
```

## Common Pitfalls

### Pitfall 1: Forgetting to check isinstance(data, dict)

```python
# WRONG: Assumes data is always a dict
@model_validator(mode="before")
@classmethod
def _set_default(cls, data: object) -> object:
    data["field"] = "value"  # Crashes if data is a BaseModel instance
    return data

# RIGHT: Check type first
@model_validator(mode="before")
@classmethod
def _set_default(cls, data: object) -> object:
    if not isinstance(data, dict):
        return data
    data["field"] = "value"  # Safe; only runs on dict
    return data
```

### Pitfall 2: Forgetting to call cache_clear()

```python
# WRONG: monkeypatch.setenv() alone doesn't affect cached instance
monkeypatch.setenv("MY_VAR", "new_value")
settings = get_settings()  # <-- Cache returns old Settings instance!

# RIGHT: Clear cache after setenv()
monkeypatch.setenv("MY_VAR", "new_value")
get_settings.cache_clear()
settings = get_settings()  # <-- Fresh instance with new value
```

### Pitfall 3: Still trying to mutate in tests

```python
# WRONG: Frozen model raises ValidationError
s = get_settings()
s.webhook_secret = "new-secret"  # ValidationError: frozen model

# RIGHT: Override via env + cache_clear
monkeypatch.setenv("WEBHOOK_SECRET", "new-secret")
get_settings.cache_clear()
s = get_settings()  # Fresh instance with new value
```

## Test Results

**Commit:** b7191ad
**Total Tests:** 544
**Pass Rate:** 100% (544/544 pass)
**Coverage:** 97.60%
**Duration:** ~30 seconds (full suite)

### Test Breakdown

- TestSettingsImmutable (new): 3 tests — all pass
- TestDeadLettersGetAuth (refactored): 5 tests — all pass
- TestDeadLettersDeleteAuth (refactored): 5 tests — all pass
- test_dead_letter_limits.py (refactored): ~14 test methods — all pass
- All other tests (unchanged): pass unchanged

### No Regressions

All tests pass with no regressions. The monkeypatch+cache_clear pattern correctly isolates config overrides per-test.

## Timeline

- **Issue #454 Created:** Request to make Settings immutable
- **Commit b7191ad:** Implementation + test fixes + immutability verification
- **All 544 tests passing:** Same commit
- **Verified in CI:** Pre-commit hooks pass (GPG-signed commits required on push)

## References

- **Pydantic v2 Validators:** https://docs.pydantic.dev/latest/concepts/validators/
- **@model_validator docs:** mode="before" vs mode="after" semantics
- **pytest-benchmark:** https://docs.pytest.org/en/7.1.x/fixture.html#parametrizing-fixtures
- **LRU cache + tests:** https://docs.python.org/3/library/functools.html#functools.lru_cache

---

**Skill File:** pydantic-frozen-models-testing-pattern.md
**Notes File:** pydantic-frozen-models-testing-pattern.notes.md
**Version:** 1.0.0
**Last Updated:** 2026-06-04
