---
name: module-level-schema-cache
description: 'TRIGGER CONDITIONS: A _validate_schema() helper reads a JSON schema
  file from disk on every call, and it is invoked N times for N config files (e.g.
  in load_all_tiers() or load_all_models()). Use when adding a module-level dict cache
  to eliminate redundant file I/O for repeated schema validation calls.'
category: optimization
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# module-level-schema-cache

How to add a module-level schema cache to a `_validate_schema()` helper so JSON schema files are
read from disk exactly once per process lifetime, regardless of how many config files are validated.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Eliminate N redundant file reads in `load_all_tiers()` / `load_all_models()` by caching JSON schemas at module level |
| Outcome | Success — PR HomericIntelligence/ProjectScylla#1461 merged |
| Issue | HomericIntelligence/ProjectScylla#1437 |

## When to Use

- A `_validate_schema()` helper opens and `json.load()`s a schema file on every call
- `load_all_*()` functions call the helper once per config file, causing N reads for N files
- The schema files are static and do not change between calls in the same process
- Follow-up to wiring schema validation (see `wire-schema-validation` skill)

## Verified Workflow

### 1. Add the module-level cache dict after `_SCHEMAS_DIR`

```python
_SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}
```

Place it immediately after the path constant. The type annotation `dict[str, dict[str, Any]]`
satisfies mypy — bare `dict` triggers `[type-arg]` errors.

### 2. Update `_validate_schema()` with cache-miss/hit logic

```python
def _validate_schema(data: dict[str, Any], schema_name: str, path: Path) -> None:
    """Validate data against a JSON schema, with module-level caching.

    Reads the schema file from disk on first call for a given schema_name;
    subsequent calls reuse the cached schema dict.
    """
    schema_file = f"{schema_name}.schema.json"
    if schema_file not in _SCHEMA_CACHE:
        schema_path = _SCHEMAS_DIR / schema_file
        with open(schema_path) as f:
            _SCHEMA_CACHE[schema_file] = json.load(f)
    try:
        jsonschema.validate(data, _SCHEMA_CACHE[schema_file])
    except jsonschema.ValidationError as e:
        raise ConfigurationError(
            f"Invalid {schema_name} configuration in {path}: {e.message}"
        ) from e
```

Key points:
- Cache key is `f"{schema_name}.schema.json"` (the filename), not the bare `schema_name`
- Each unique schema name gets its own entry; multiple schemas coexist independently
- The `open()` call is inside the `if` guard — only executes on cache miss

### 3. Write tests with cache isolation

Clear `_SCHEMA_CACHE` in `setup_method` to prevent test ordering dependencies:

```python
class TestValidateSchema:
    def setup_method(self) -> None:
        from scylla.config import loader as loader_module
        loader_module._SCHEMA_CACHE.clear()

    def test_cache_hit_avoids_second_file_read(self) -> None:
        from scylla.config.loader import _validate_schema
        read_count = 0
        original_open = open

        def counting_open(path: object, *args: object, **kwargs: object) -> object:
            nonlocal read_count
            if "tier.schema.json" in str(path):
                read_count += 1
            return original_open(path, *args, **kwargs)  # type: ignore[call-overload]

        with patch("builtins.open", side_effect=counting_open):
            _validate_schema(valid_tier, "tier", Path("t0.yaml"))
            _validate_schema(valid_tier, "tier", Path("t1.yaml"))

        assert read_count == 1  # only one disk read for two calls

    def test_cache_populated_after_first_call(self) -> None:
        from scylla.config import loader as loader_module
        from scylla.config.loader import _validate_schema
        assert "tier.schema.json" not in loader_module._SCHEMA_CACHE
        _validate_schema(valid_tier, "tier", Path("t0.yaml"))
        assert "tier.schema.json" in loader_module._SCHEMA_CACHE
```

### 4. Use valid test data matching the schema's `additionalProperties: false`

Read the actual schema file before writing test fixtures — schemas with
`additionalProperties: false` reject any field not in `properties`. For the tier schema:

```python
# CORRECT — only fields in tier.schema.json properties
valid_tier = {"tier": "t0", "name": "Prompts"}

# WRONG — "subtests" and "description" are not in the schema
valid_tier = {"tier": "t0", "name": "Prompts", "description": "desc", "subtests": []}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

- Cache dict type: `dict[str, dict[str, Any]]` (keyed by filename, value is the parsed schema)
- Cache key format: `f"{schema_name}.schema.json"` (full filename stem)
- Test class setup: `loader_module._SCHEMA_CACHE.clear()` in `setup_method`
- Tests added: 6 (cache miss, cache hit, populated state, failure raises, success no-raise, independent keys)
- Pre-commit: ruff auto-removes unused imports (e.g. `MagicMock` from `unittest.mock`) on first run — expect one hook failure, re-run passes

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1461, issue #1437 (follow-up to #1380 / PR #1424) | `scylla/config/loader.py` |
