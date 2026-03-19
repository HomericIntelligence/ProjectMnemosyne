---
name: precommit-schema-validation
description: 'TRIGGER CONDITIONS: Adding a pre-commit hook that validates YAML config
  files against JSON schemas at commit time. Use when you have schemas/ JSON schemas
  and config/ YAML files and want to catch schema violations before CI. Also use when
  extending an existing _SCHEMA_MAP to cover an additional config directory (e.g.
  adding config/tiers/ alongside config/models/).'
category: ci-cd
date: 2026-03-07
version: 1.1.0
user-invocable: false
tags:
- pre-commit
- jsonschema
- yaml
- validation
- config
- hooks
- schema-map
---
# precommit-schema-validation

How to add or extend a pre-commit hook that validates YAML config files against JSON schemas,
surfacing violations at commit time rather than in CI or at runtime.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 (updated 2026-03-07) |
| Objective | Add/extend `scripts/validate_config_schemas.py` + `validate-config-schemas` pre-commit hook |
| Outcome | Success — PR HomericIntelligence/ProjectScylla#1439 (initial), #1464 (extend to config/tiers/) |
| Issues | HomericIntelligence/ProjectScylla#1382, #1441 |

## When to Use

- Adding schema validation to a pre-commit pipeline where schemas already exist in `schemas/`
- When you want commit-time (not just runtime) validation for YAML configs
- When multiple config directories each have a different schema (dispatch by path pattern)
- **Extending an existing `_SCHEMA_MAP`** to cover a new config directory (e.g. production configs
  alongside test fixtures that share the same schema)
- Follow-up to wiring schemas into a config loader (see `wire-schema-validation` skill)

## Verified Workflow

### 1. Create (or extend) the validation script

The core pattern is an ordered `_SCHEMA_MAP` list of `(regex_pattern, schema_path)` pairs:

```python
_SCHEMA_MAP: list[tuple[re.Pattern[str], Path]] = [
    (re.compile(r"^config/defaults\.yaml$"), Path("schemas/defaults.schema.json")),
    (re.compile(r"^config/models/.+\.yaml$"), Path("schemas/model.schema.json")),
    # Production tier configs — same schema as test fixtures
    (re.compile(r"^config/tiers/.+\.yaml$"), Path("schemas/tier.schema.json")),
    (re.compile(r"^tests/fixtures/config/tiers/.+\.yaml$"), Path("schemas/tier.schema.json")),
]
```

**Key**: Order matters only if two patterns can match the same path (they don't here). Multiple
paths can map to the same schema file.

### 2. Register (or extend) the hook in `.pre-commit-config.yaml`

Use `pass_filenames: true` so pre-commit passes only the changed files:

```yaml
- id: validate-config-schemas
  name: Validate Config Files Against JSON Schemas
  description: >-
    Validates config/defaults.yaml, config/models/*.yaml,
    config/tiers/*.yaml, and tests/fixtures/config/tiers/*.yaml
    against their JSON schemas in schemas/
  entry: pixi run python scripts/validate_config_schemas.py
  language: system
  files: >-
    ^(config/defaults\.yaml|config/models/.+\.yaml|config/tiers/.+\.yaml|
    tests/fixtures/config/tiers/.+\.yaml)$
  pass_filenames: true
```

**Key**: `pass_filenames: true` means pre-commit passes only staged matched files as positional
args. The script receives them via `argparse` `nargs="*"` positional parameter.

### 3. Use `Draft7Validator.iter_errors()` not `jsonschema.validate()`

`iter_errors()` collects **all** violations in one pass, so every error is reported at once
rather than stopping at the first. This is critical for useful pre-commit feedback.

### 4. Cache loaded schemas

If multiple files share the same schema (e.g., all `config/tiers/*.yaml` use `tier.schema.json`),
load the schema once and reuse via a `dict[Path, dict]` cache:

```python
schema_cache: dict[Path, dict[str, object]] = {}
if schema_path not in schema_cache:
    schema_cache[schema_path] = json.loads(schema_path.read_text())
```

### 5. Warn (not fail) for unknown paths

Files that don't match any schema pattern should produce a WARNING to stderr but return exit code 0.
This makes the hook future-safe when new file types are staged alongside existing ones.

### 6. Write tests that skip gracefully when directories are absent

For production config directories that may not exist yet, use `pytest.skip`:

```python
def test_production_tier_configs_validate(self) -> None:
    tiers_dir = _REPO_ROOT / "config" / "tiers"
    if not tiers_dir.exists():
        pytest.skip("config/tiers/ directory not present")
    ...
```

This pattern works for `resolve_schema` unit tests too — the function accepts hypothetical paths,
so `_REPO_ROOT / "config" / "tiers" / "t0.yaml"` resolves correctly even without the directory.

### 7. Write comprehensive unit tests

Test all three public functions (`resolve_schema`, `validate_file`, `check_files`) plus
integration tests against real config files. When adding a new pattern, add:

- A dedicated `test_<new_pattern>_matches` unit test in `TestResolveSchema`
- A new parametrize entry in `test_all_supported_patterns_match`
- An integration test `test_<new_dir>_configs_validate` in `TestMainIntegration`

```python
class TestResolveSchema:
    def test_production_tier_yaml_matches(self) -> None:
        path = _REPO_ROOT / "config" / "tiers" / "t0.yaml"
        result = resolve_schema(path, _REPO_ROOT)
        assert result is not None
        assert result.name == "tier.schema.json"

    @pytest.mark.parametrize("rel_path", [
        "config/defaults.yaml",
        "config/models/claude-sonnet.yaml",
        "config/tiers/t0.yaml",
        "tests/fixtures/config/tiers/t1.yaml",
    ])
    def test_all_supported_patterns_match(self, rel_path: str) -> None:
        path = _REPO_ROOT / rel_path
        assert resolve_schema(path, _REPO_ROOT) is not None
```

## Failed Attempts

| Attempt | What Happened | Fix |
|---------|---------------|-----|
| Used `files:` as a single-line regex in `.pre-commit-config.yaml` | YAML multi-line regex with a newline in the middle caused yamllint `wrong indentation` error | Use `files: >-` (block scalar) and keep the continuation on the next line; yamllint accepts folded scalars |
| Used `jsonschema.validate()` (raises on first error) | Only the first schema violation was shown; users had to fix-commit-fix-commit multiple times | Switch to `Draft7Validator.iter_errors()` which collects all errors |

## Results & Parameters

- `jsonschema` version: `>=4.0,<5` (already in `pixi.toml` for ProjectScylla)
- Validator: `jsonschema.Draft7Validator` (matches `"$schema": "http://json-schema.org/draft-07/schema#"` in existing schema files)
- Unknown-path behavior: `WARNING:` to stderr, exit 0 (not a failure)
- Test count: 29 unit tests across 4 test classes (28 pass, 1 skips when `config/tiers/` absent)
- Hook trigger: `pass_filenames: true` with regex covering all four config directories

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1439, issue #1382 | Initial creation of hook (3 schema map entries) |
| ProjectScylla | PR #1464, issue #1441 | Extended to `config/tiers/*.yaml` (4th `_SCHEMA_MAP` entry) |
