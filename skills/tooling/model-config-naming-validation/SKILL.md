# Skill: model-config-naming-validation

## Overview

| Field      | Value                                              |
|------------|----------------------------------------------------|
| Date       | 2026-02-19                                         |
| Issue      | #682                                               |
| PR         | #769                                               |
| Objective  | CI check that filename matches model_id in YAML configs |
| Outcome    | Success — 28 tests, all pre-commit hooks pass      |

## When to Use

- Adding a CI/pre-commit validation script for config file naming conventions
- Catching "filename stem doesn't match internal ID field" mismatches in YAML files
- Writing pytest tests for a standalone Python script in `scripts/`
- Importing from `scripts/` in tests (mypy module conflict resolution)

## Verified Workflow

### 1. Write the validation script

```python
# scripts/validate_model_configs.py
def find_model_configs(config_dir: Path) -> list[Path]:
    # Skip test fixtures prefixed with '_'
    return sorted(f for f in config_dir.glob("*.yaml") if not f.name.startswith("_"))

def check_filename_consistency(config: dict, file_path: Path) -> list[str]:
    model_id = config.get("model_id")
    stem = file_path.stem
    # Allow version suffixes: stem must be a prefix of model_id
    if model_id != stem and not model_id.startswith(stem + "-"):
        return [f"  Filename mismatch: stem='{stem}', model_id='{model_id}'"]
    return []
```

**Key design decisions:**

- Skip `_`-prefixed files (test fixtures) — avoids false positives from fixtures with toy values
- Allow version suffix pattern (`stem + "-"`) so `claude-sonnet-4-5.yaml` with `model_id: "claude-sonnet-4-5-20250929"` passes
- Use `yaml.safe_load` for parsing (requires `pyyaml` in pixi dependencies)
- Exit code 0 = all pass, 1 = any failure — correct for CI/pre-commit

### 2. Add `scripts/__init__.py` (CRITICAL for mypy)

When a test imports from `scripts.validate_model_configs`, mypy will error:

```
scripts/validate_model_configs.py: error: Source file found twice under different module names:
  "validate_model_configs" and "scripts.validate_model_configs"
```

**Fix**: `touch scripts/__init__.py` — makes `scripts/` a proper package so mypy resolves the module name consistently. This is required whenever any test file contains `from scripts.<module> import ...`.

### 3. Write tests in `tests/unit/scripts/`

Create `tests/unit/scripts/__init__.py` and `tests/unit/scripts/test_<name>.py`.

Use `tmp_path` pytest fixture for isolated file system operations:

```python
def write_yaml(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(textwrap.dedent(content))
    return path
```

Parametrize consistency checks across multiple valid/invalid cases:

```python
@pytest.mark.parametrize("filename,model_id", [
    ("claude-opus-4-1.yaml", "claude-opus-4-1"),             # exact match
    ("claude-sonnet-4-5.yaml", "claude-sonnet-4-5-20250929"), # version suffix
])
def test_consistent_configs_pass(self, filename, model_id, tmp_path):
    ...
```

### 4. Add pre-commit hook

```yaml
# .pre-commit-config.yaml
- id: validate-model-configs
  name: Validate Model Config Naming
  description: Ensure model config filenames match the model_id and required fields are present
  entry: python scripts/validate_model_configs.py config/models/
  language: system
  files: ^config/models/.*\.yaml$
  pass_filenames: false
```

**Important**: `pass_filenames: false` — the script takes the directory, not individual files. Without this, pre-commit would pass each changed YAML as an argument, breaking the script.

### 5. Commit flow

Pre-commit hooks auto-format with ruff on first commit attempt; files are modified. Re-stage the reformatted files and commit again — second attempt passes cleanly.

## Failed Attempts

### `--namespace-packages` mypy flag

Tried `mypy --namespace-packages` to resolve the "found twice" error without adding `__init__.py`. The flag did not resolve the issue. Root cause: mypy sees the file both as a top-level source (via `scripts/` path argument) and as `scripts.validate_model_configs` (via the test import).

**Fix**: `touch scripts/__init__.py` — the only reliable solution.

### Running only the new tests with `pytest tests/unit/scripts/`

This passes all 28 tests but reports 0% coverage and fails the `fail-under=73` threshold. Always run `pytest tests/` (full suite) to verify coverage. The new script tests don't add to the `scylla/` coverage source configured in `pyproject.toml`.

## Results & Parameters

| Metric          | Value                               |
|-----------------|-------------------------------------|
| Tests added     | 28                                  |
| Tests total     | 2233                                |
| Coverage        | 73.35% (threshold: 73%)             |
| Pre-commit hook | `validate-model-configs`            |
| Hook trigger    | `^config/models/.*\.yaml$`          |
| Fixtures skipped| Files prefixed with `_`             |

## Template: Validation Script

```python
#!/usr/bin/env python3
"""One-line description.

Usage:
    python scripts/validate_<thing>.py [dir]
"""
import sys
from pathlib import Path
import yaml

REQUIRED_FIELDS = ["field1", "field2"]

def find_configs(config_dir: Path) -> list[Path]:
    return sorted(f for f in config_dir.glob("*.yaml") if not f.name.startswith("_"))

def validate_config(file_path: Path) -> list[str]:
    try:
        config = yaml.safe_load(file_path.read_text())
    except yaml.YAMLError as e:
        return [f"  YAML parse error: {e}"]
    if not isinstance(config, dict):
        return [f"  Expected mapping, got {type(config).__name__}"]
    return [f"  Missing: '{f}'" for f in REQUIRED_FIELDS if f not in config]

def main() -> int:
    config_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "config/models")
    configs = find_configs(config_dir)
    failed = [f for f in configs if validate_config(f)]
    for f in failed:
        print(f"FAIL: {f}")
        for e in validate_config(f):
            print(e)
    print(f"\n{len(configs) - len(failed)}/{len(configs)} passed.")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
```
