# module-level-schema-cache — Raw Notes

## Session Context

- **Date**: 2026-03-07
- **Project**: ProjectScylla
- **Issue**: HomericIntelligence/ProjectScylla#1437 (follow-up to #1380)
- **PR**: HomericIntelligence/ProjectScylla#1461
- **Branch**: `1437-auto-impl`

## File Changed

`scylla/config/loader.py` — two additions:
1. `_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}` after `_SCHEMAS_DIR`
2. Cache-miss/hit guard inside `_validate_schema()`

## Test File Changed

`tests/unit/config/test_config_loader.py` — added `TestValidateSchema` class (6 tests).

## Pre-commit Failures Encountered

1. **ruff-check-python** (first run): Auto-removed unused `MagicMock` import from `unittest.mock`
   — import was added speculatively but never used. Re-run passed.
2. **mypy-check-python** (first run): `dict` without type params on `invalid_data: dict = ...`
   — fixed to `dict[str, str]`.

## Tier Schema Fields (additionalProperties: false)

Allowed top-level keys in `schemas/tier.schema.json`:
- `tier` (required, pattern `^t[0-6]$`)
- `name` (required)
- `description`
- `system_prompt`
- `skills`
- `tools`
- `uses_tools`
- `uses_delegation`
- `uses_hierarchy`

Fields NOT in schema (common mistake): `subtests`, `agent_configs`, `subtest_count`

## Minimal Valid Test Fixtures

```python
# tier
{"tier": "t0", "name": "Prompts"}

# model
{"model_id": "claude-3-5-haiku-20241022"}

# defaults — requires evaluation block
{"evaluation": {"runs_per_eval": 3, "timeout": 60}}
```
