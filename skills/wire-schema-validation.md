---
name: wire-schema-validation
description: 'TRIGGER CONDITIONS: Wiring JSON schema validation into a config loader
  that already parses YAML into dataclass/Pydantic models. Use when load_defaults(),
  load_model_config(), or load_tier_config() should validate raw YAML data against
  a corresponding JSON schema and raise a typed ConfigurationError on failure.'
category: testing
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# wire-schema-validation

How to add automatic JSON schema validation to YAML config loaders in ProjectScylla, surfacing invalid configs at load time rather than runtime.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-04 |
| Objective | Wire `schemas/defaults|tier|model.schema.json` into `load_defaults()`,`load_tier()`, and`load_model()` in `scylla/config/loader.py` |
| Outcome | Success — PR HomericIntelligence/ProjectScylla#1424 merged |
| Issue | HomericIntelligence/ProjectScylla#1380 |

## When to Use

- Adding `jsonschema.validate()` calls to existing config loader methods
- Any loader that parses YAML then constructs a Pydantic/dataclass model and needs early validation
- When schema files already exist in `schemas/` but are not yet wired to load-time checks
- When a fixture field name needs to match a Pydantic `Field(alias=...)` value

## Verified Workflow

### 1. Add imports and helper after all imports

```python
import json
import jsonschema

from .models import ConfigurationError  # must be imported BEFORE _validate_schema

_SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"

def _validate_schema(data: dict[str, Any], schema_name: str, path: Path) -> None:
    schema_path = _SCHEMAS_DIR / f"{schema_name}.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise ConfigurationError(
            f"Invalid {schema_name} configuration in {path}: {e.message}"
        ) from e
```

**Critical**: Place `_SCHEMAS_DIR` and `_validate_schema` **after all imports** (including local `.models` imports). If placed between stdlib and local import blocks, ruff-format will reorder imports and leave `ConfigurationError` undefined at `_validate_schema` definition time.

### 2. Wire into each loader — after YAML parse, before dataclass construction

```python
# load_defaults
data = self._load_yaml(defaults_path)
if not defaults_path.stem.startswith("_"):
    _validate_schema(data, "defaults", defaults_path)
return DefaultsConfig(**data)

# load_tier
data = self._load_yaml(tier_path)
if "tier" not in data:
    data["tier"] = tier
if not tier.startswith("_"):
    _validate_schema(data, "tier", tier_path)
config = TierConfig(**data)

# load_model
data = self._load_yaml_optional(model_path)
if "model_id" not in data:
    data["model_id"] = model_id
if not model_id.startswith("_"):
    _validate_schema(data, "model", model_path)
config = ModelConfig(**data)
```

### 3. Skip validation for `_`-prefixed fixture files

Both `load_tier()` and `load_model()` already skip certain logic for `_`-prefixed names (test fixtures). Apply the same guard to schema validation calls to avoid breaking test helpers that deliberately use non-schema-conforming data.

### 4. Fix Pydantic alias mismatches in test fixtures

When adding schema validation, existing YAML fixtures may fail because they use the Python attribute name instead of the Pydantic `Field(alias=...)` name.

**Example**:
```python
# Model definition
class EvaluationConfig(BaseModel):
    runs_per_tier: int = Field(default=10, alias="runs_per_eval")
```
The YAML key must be `runs_per_eval` (the alias), not `runs_per_tier`. Check fixtures against schema field names after wiring validation.

### 5. Write unit tests

```python
class TestSchemaValidation:
    def test_load_defaults_wrong_type_raises(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "defaults.yaml").write_text(
            "evaluation:\n  runs_per_eval: 'not-an-int'\n"
        )
        with pytest.raises(ConfigurationError, match="Invalid defaults configuration"):
            ConfigLoader(base_path=tmp_path).load_defaults()

    def test_load_tier_missing_required_raises(self, tmp_path):
        tiers_dir = tmp_path / "config" / "tiers"
        tiers_dir.mkdir(parents=True)
        (tiers_dir / "t0.yaml").write_text("tier: t0\n")  # missing required 'name'
        with pytest.raises(ConfigurationError, match="Invalid tier configuration"):
            ConfigLoader(base_path=tmp_path).load_tier("t0")
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

- `jsonschema` version: `>=4.0,<5` (already in `pixi.toml`)
- Error message pattern: `"Invalid {schema_name} configuration in {path}: {e.message}"`
- Fixture bypass pattern: `if not name.startswith("_"):` (consistent with existing loader guards)
- Test count added: 15 new tests in `TestSchemaValidation`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1424, issue #1380 | [notes.md](wire-schema-validation.notes.md) |
