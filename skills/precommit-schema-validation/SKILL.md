---
name: precommit-schema-validation
description: "TRIGGER CONDITIONS: Adding a pre-commit hook that validates YAML config files against JSON schemas at commit time. Use when you have schemas/ JSON schemas and config/ YAML files and want to catch schema violations before they reach CI."
user-invocable: false
category: ci-cd
date: 2026-03-05
---

# precommit-schema-validation

How to add a pre-commit hook that validates YAML config files against JSON schemas, surfacing
violations at commit time rather than in CI or at runtime.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Add `scripts/validate_config_schemas.py` + `validate-config-schemas` pre-commit hook |
| Outcome | Success — PR HomericIntelligence/ProjectScylla#1439 |
| Issue | HomericIntelligence/ProjectScylla#1382 |

## When to Use

- Adding schema validation to a pre-commit pipeline where schemas already exist in `schemas/`
- When you want commit-time (not just runtime) validation for YAML configs
- When multiple config directories each have a different schema (dispatch by path pattern)
- Follow-up to wiring schemas into a config loader (see `wire-schema-validation` skill)

## Verified Workflow

### 1. Create the validation script

```python
#!/usr/bin/env python3
"""Validate config files against their JSON schemas as a pre-commit gate."""

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml

_REPO_ROOT = Path(__file__).parent.parent

# Map path patterns → schema files (relative to repo root)
_SCHEMA_MAP: list[tuple[re.Pattern[str], Path]] = [
    (re.compile(r"^config/defaults\.yaml$"), Path("schemas/defaults.schema.json")),
    (re.compile(r"^config/models/.+\.yaml$"), Path("schemas/model.schema.json")),
    (re.compile(r"^tests/fixtures/config/tiers/.+\.yaml$"), Path("schemas/tier.schema.json")),
]


def resolve_schema(file_path: Path, repo_root: Path) -> Path | None:
    """Return schema path for file_path, or None if no match."""
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = Path(str(file_path))
    rel_str = rel.as_posix()
    for pattern, schema_rel in _SCHEMA_MAP:
        if pattern.match(rel_str):
            return repo_root / schema_rel
    return None


def validate_file(file_path: Path, schema: dict[str, object]) -> list[str]:
    """Validate a YAML file against schema; returns list of error strings."""
    try:
        with open(file_path) as fh:
            content = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        return [f"Could not read/parse YAML: {exc}"]
    errors: list[str] = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(content), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        errors.append(f"  [{path}] {error.message}")
    return errors


def check_files(files: list[Path], repo_root: Path, verbose: bool = False) -> int:
    """Validate each file; return 0 (all valid) or 1 (any failure)."""
    if not files:
        return 0
    schema_cache: dict[Path, dict[str, object]] = {}
    any_failure = False
    for file_path in files:
        schema_path = resolve_schema(file_path, repo_root)
        if schema_path is None:
            print(f"WARNING: No schema mapping for {file_path} — skipping", file=sys.stderr)
            continue
        if schema_path not in schema_cache:
            try:
                schema_cache[schema_path] = json.loads(schema_path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                print(f"ERROR: Could not load schema {schema_path}: {exc}", file=sys.stderr)
                any_failure = True
                continue
        errors = validate_file(file_path, schema_cache[schema_path])
        if errors:
            print(f"FAIL: {file_path}", file=sys.stderr)
            for error in errors:
                print(error, file=sys.stderr)
            any_failure = True
        elif verbose:
            print(f"PASS: {file_path}")
    return 1 if any_failure else 0
```

### 2. Register the hook in `.pre-commit-config.yaml`

Use `pass_filenames: true` so pre-commit passes only the changed files:

```yaml
- id: validate-config-schemas
  name: Validate Config Files Against JSON Schemas
  description: >-
    Validates config/defaults.yaml, config/models/*.yaml, and
    tests/fixtures/config/tiers/*.yaml against their JSON schemas in schemas/
  entry: pixi run python scripts/validate_config_schemas.py
  language: system
  files: >-
    ^(config/defaults\.yaml|config/models/.+\.yaml|
    tests/fixtures/config/tiers/.+\.yaml)$
  pass_filenames: true
```

**Key**: `pass_filenames: true` means pre-commit passes only staged matched files as positional
args. The script receives them via `argparse` `nargs="*"` positional parameter.

### 3. Use `Draft7Validator.iter_errors()` not `jsonschema.validate()`

`iter_errors()` collects **all** violations in one pass, so every error is reported at once
rather than stopping at the first. This is critical for useful pre-commit feedback.

### 4. Cache loaded schemas

If multiple files share the same schema (e.g., all `config/models/*.yaml` use `model.schema.json`),
load the schema once and reuse via a `dict[Path, dict]` cache:

```python
schema_cache: dict[Path, dict[str, object]] = {}
if schema_path not in schema_cache:
    schema_cache[schema_path] = json.loads(schema_path.read_text())
```

### 5. Warn (not fail) for unknown paths

Files that don't match any schema pattern should produce a WARNING to stderr but return exit code 0.
This makes the hook future-safe when new file types are staged alongside existing ones.

### 6. Write comprehensive unit tests

Test all three public functions (`resolve_schema`, `validate_file`, `check_files`) plus
integration tests against real config files:

```python
class TestResolveSchema:
    def test_defaults_yaml_matches(self) -> None: ...
    def test_model_yaml_matches(self) -> None: ...
    def test_tier_fixture_yaml_matches(self) -> None: ...
    def test_unknown_path_returns_none(self) -> None: ...

class TestValidateFile:
    def test_valid_yaml_returns_no_errors(self, tmp_path: Path) -> None: ...
    def test_missing_required_field_returns_error(self, tmp_path: Path) -> None: ...
    def test_multiple_errors_all_returned(self, tmp_path: Path) -> None: ...

class TestMainIntegration:
    def test_defaults_yaml_validates(self) -> None: ...     # uses real schemas/
    def test_model_configs_validate(self) -> None: ...       # uses real config/models/
    def test_tier_fixture_configs_validate(self) -> None: ... # uses real fixtures
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
- Test count: 26 unit tests across 4 test classes
- Hook trigger: `pass_filenames: true` with regex covering all three config directories

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1439, issue #1382 | Follows wire-schema-validation (#1380/#1424) which wired the same schemas into the config loader |
