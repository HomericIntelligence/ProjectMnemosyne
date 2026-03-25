---
name: architecture-rest-api-httpx-integration
description: "Pattern for adding REST API client integration to a Python project using httpx. Use when: (1) adding HTTP client to codebase with no existing HTTP dependency, (2) integrating external REST API with Pydantic config system, (3) wiring optional feature into existing config hierarchy."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags:
  - httpx
  - rest-api
  - pydantic
  - config-integration
  - http-client
---

# REST API Client Integration with httpx

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add AI Maestro REST API integration to ProjectScylla - HTTP client, Pydantic models, error hierarchy, config wiring, and tests |
| **Outcome** | Successful - 31 tests pass, 96.6% coverage on new module, all pre-commit hooks pass |

## When to Use

- Adding a new HTTP client to a Python project that has no existing HTTP dependency
- Integrating an external REST API into a Pydantic-based configuration system
- Creating an optional feature that must be backwards-compatible with existing configs
- Building a self-contained module with client, models, and error hierarchy
- Wiring a new config section through a multi-level config loader (defaults > model > test)

## Verified Workflow

### Quick Reference

```bash
# 1. Add httpx dependency
# pixi.toml [pypi-dependencies]:
httpx = ">=0.27,<1"
# pyproject.toml [project] dependencies:
"httpx>=0.27,<1"

# 2. Create module structure
mkdir -p scylla/<module>/
# errors.py -> models.py -> client.py -> __init__.py

# 3. Wire config (optional field, None = disabled)
# In config/models.py:
maestro: MaestroConfig | None = Field(default=None)

# 4. Install and test
pixi install
pixi run python -m pytest tests/unit/<module>/ -v
```

### Detailed Steps

1. **Add dependency to both `pixi.toml` and `pyproject.toml`** - pixi.toml controls the dev environment, pyproject.toml controls the package. Both need httpx.

2. **Create error hierarchy first** (`errors.py`):
   - Base exception (e.g., `MaestroError`)
   - Connection error subclass for network/timeout failures
   - API error subclass with `status_code` and `response_body` attributes

3. **Create Pydantic models** (`models.py`):
   - Config model with `enabled: bool = False` (opt-in pattern)
   - Request/response models for API payloads
   - Use `Field(default_factory=dict)` for dict fields (Pydantic None coercion safety)

4. **Create HTTP client** (`client.py`):
   - Context manager support (`__enter__`/`__exit__`)
   - Central `_request()` helper that maps httpx exceptions to custom errors
   - Health check returns `None` on failure (never raises)
   - Other methods raise on failure
   - Use `response.json() or {}` to guard against null JSON responses

5. **Create `__init__.py`** with explicit re-exports using `import X as X` pattern (required when `implicit_reexport=false` in mypy)

6. **Wire into config system**:
   - Import in `config/models.py` using `from module import Class as Class` for re-export
   - Add optional field to both `DefaultsConfig` and `ScyllaConfig`
   - Pass through in `config/loader.py` merge logic
   - Export from `config/__init__.py` and add to `__all__`

7. **Update JSON schema** (`defaults.schema.json`) with new property

8. **Write comprehensive tests** using `unittest.mock.patch` on `httpx.Client`

### Key Pattern: Mocking httpx in Tests

```python
@patch("scylla.maestro.client.httpx.Client")
def test_success(self, mock_client_cls, config):
    mock_http = mock_client_cls.return_value
    mock_http.request.return_value = _mock_response(json_data={"status": "ok"})

    client = MaestroClient(config)
    client._client = mock_http  # Replace the real client
    result = client.health_check()
    assert result is not None
```

### Key Pattern: Explicit Re-export for Strict Mypy

```python
# In config/models.py - with implicit_reexport=false
from scylla.maestro.models import MaestroConfig as MaestroConfig  # as X pattern

# In __init__.py
from scylla.maestro.client import MaestroClient as MaestroClient
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `type: ignore[arg-type]` on Pydantic int fields | Added `# type: ignore[arg-type]` to test calls like `MaestroConfig(timeout_seconds=0)` | Mypy flagged them as `unused-ignore` because `0` and `301` are valid `int` types - Pydantic validates at runtime, not type level | Don't add `type: ignore` for Pydantic runtime validators on correctly-typed fields; the validation is runtime, not type-level |
| Plain import for re-export | `from scylla.maestro.models import MaestroConfig` in `config/models.py` | Mypy `implicit_reexport=false` setting means plain imports are not re-exported from the module | Always use `import X as X` pattern when a symbol needs to be importable from the importing module |
| `# noqa: SLF001` on private attribute access in tests | Added noqa comments on `client._client = mock_http` lines | A linter automatically removed these comments | The linter configuration allows private access in test files via per-file-ignores |

## Results & Parameters

### Module Structure Created

```
scylla/maestro/
  __init__.py    # Public API re-exports
  errors.py      # MaestroError, MaestroConnectionError, MaestroAPIError
  models.py      # MaestroConfig, FailureSpec, HealthResponse, InjectionResult
  client.py      # MaestroClient (httpx-based)

tests/unit/maestro/
  __init__.py
  conftest.py    # Shared fixtures
  test_client.py # 17 tests
  test_models.py # 14 tests
```

### Config Integration Points

```python
# DefaultsConfig and ScyllaConfig both get:
maestro: MaestroConfig | None = Field(
    default=None,
    description="AI Maestro REST API configuration (None = disabled)",
)

# ConfigLoader.load() passes through:
config_data["maestro"] = defaults.maestro
```

### Coverage Results

| Module | Coverage |
|--------|----------|
| `scylla/maestro/errors.py` | 100% |
| `scylla/maestro/models.py` | 100% |
| `scylla/maestro/client.py` | 96.6% |
| **Total** | **31 tests, 0 failures** |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1504 - Add AI Maestro REST API integration | PR #1548, all CI hooks pass |
