---
name: json-schema-validation-wiring
description: Wire JSON schema validation into config loader methods (load_test, load_rubric).
  Use when adding schema validation to new config file types in ProjectScylla's ConfigLoader.
category: testing
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# JSON Schema Validation Wiring

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-07 |
| Objective | Add JSON schema validation to `load_test()` and `load_rubric()` in `ConfigLoader`, consistent with existing `_validate_schema()` pattern used for `load_defaults()`, `load_tier()`, and `load_model()`. |
| Outcome | Success — PR #1465, 4481 unit tests pass |

## When to Use

- Adding schema validation to a new `ConfigLoader.load_*()` method
- Adding or updating a JSON schema in `schemas/` and wiring it into loading logic
- Updating an existing schema to match real fixture file formats (fields were missing from schema vs actual YAML)

## Verified Workflow

### Step 1: Audit existing fixtures vs schema

Before updating the schema, enumerate all fixture files and check which fields they actually use:

```bash
# Check all YAML IDs/top-level keys vs existing schema
for f in tests/fixtures/tests/*/test.yaml; do head -5 "$f"; done
grep -l "categories:" tests/fixtures/tests/*/expected/rubric.yaml
grep -l "criteria:" tests/fixtures/tests/*/expected/rubric.yaml
```

Catch mismatches between schema patterns and actual fixture values (e.g., ID pattern `^[0-9]{3}-...` vs real IDs `test-001`).

### Step 2: Update schemas to cover real data

Update the JSON schema to add missing fields and adjust constraints to match real fixture data:

- Add required fields that exist in fixtures but were missing from schema
- Add optional fields that appear in some fixtures (e.g., `criteria`, `skill_validation`)
- Broaden patterns/constraints that reject valid fixture data
- Add alternative top-level structures (e.g., `categories` vs `requirements`)

Keep `additionalProperties: false` throughout — this is what makes schema validation useful.

### Step 3: Wire `_validate_schema()` in loader

Add the call after `_load_yaml()`, before Pydantic model construction:

```python
def load_test(self, test_id: str) -> EvalCase:
    test_path = self.base_path / "tests" / test_id / "test.yaml"
    data = self._load_yaml(test_path)

    if not test_id.startswith("_"):       # skip test fixtures (same pattern as load_tier/load_model)
        _validate_schema(data, "test", test_path)

    try:
        return EvalCase(**data)
    except Exception as e:
        raise ConfigurationError(f"Invalid test configuration in {test_path}: {e}") from e
```

The `_`-prefix skip pattern is used by `load_tier()` and `load_model()` for test fixtures — apply the same pattern here.

### Step 4: Add tests in `test_json_schemas.py`

Follow the existing class pattern:

1. Extend `TestSchemaFiles` parametrize lists to include the new schema names
2. Add a `TestXxxSchema` class with:
   - A `schema` fixture loading the schema
   - `test_real_fixture_is_valid` parametrized over real fixture files
   - `test_rejects_missing_<required_field>` for each required field
   - `test_rejects_additional_property`
   - `test_accepts_minimal_valid_<type>`
   - Format-specific acceptance tests (e.g., both `requirements` and `categories` formats for rubric)

### Step 5: Run tests and pre-commit

```bash
pixi run python -m pytest tests/unit/config/test_json_schemas.py -v --no-cov
pixi run python -m pytest tests/unit/ --no-cov -q
pre-commit run --all-files
```

Pre-commit auto-fixes ruff formatting issues on first run — rerun to confirm all pass.

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| ID pattern `^[0-9]{3}-[a-z0-9]+(-[a-z0-9]+)*$` in test.schema.json | Real fixture IDs are `test-001` format; orchestrator test fixtures use `001-test` format — neither matches the old pattern | Always test schema against ALL real fixture files, not just the example in schema comments |
| Pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (starts with letter) | Orchestrator tests use `001-test` which starts with digit | Use `^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$` to allow digit-first IDs |
| `minLength: 10` on rubric requirement description | Orchestrator test fixture has `description: "Must work"` (9 chars) | Use `minLength: 3` or omit length constraint for descriptions |
| `required: ["requirements", "grading"]` in rubric schema | test-001 uses `categories` format, not `requirements` — would fail validation | Make `requirements` optional; only `grading` is truly required |

## Results & Parameters

**Files changed:**
- `schemas/test.schema.json` — added `language` (required, enum python/mojo), `tiers` (optional array), broadened `id` pattern
- `schemas/rubric.schema.json` — added `categories` alternative format, optional `criteria`/`skill_validation`/`skill_source` in requirement items, made `requirements` optional
- `scylla/config/loader.py` — added `_validate_schema()` calls in `load_test()` and `load_rubric()`
- `tests/unit/config/test_json_schemas.py` — added `TestTestSchema` (9 tests) and `TestRubricSchema` (9 tests), extended `TestSchemaFiles` parametrize

**Test results:** 4481 unit tests pass, all pre-commit hooks pass

## References

- ProjectScylla PR #1465 — implementation
- ProjectScylla issue #1438 — original request (follow-up from #1380)
- `scylla/config/loader.py` — `_validate_schema()` module-level helper
- `tests/unit/config/test_json_schemas.py` — full schema test suite
