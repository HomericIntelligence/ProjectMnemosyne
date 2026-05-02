# wire-schema-validation — Session Notes

## Session Details

- **Date**: 2026-03-04
- **Branch**: `1380-auto-impl`
- **Issue**: HomericIntelligence/ProjectScylla#1380
- **PR**: HomericIntelligence/ProjectScylla#1424

## Files Changed

| File | Change |
| ------ | -------- |
| `scylla/config/loader.py` | Added `_validate_schema()`, wired into `load_defaults()`, `load_tier()`, `load_model()` |
| `tests/fixtures/config/defaults.yaml` | Fixed `evaluation.runs_per_tier` → `evaluation.runs_per_eval` (Pydantic alias mismatch) |
| `tests/unit/config/test_config_loader.py` | Added `TestSchemaValidation` class with 15 tests |

## Key Commands

```bash
# Run config loader tests only
pixi run python -m pytest tests/unit/config/test_config_loader.py -q --no-cov

# Check pre-commit
pre-commit run --files scylla/config/loader.py

# Run full unit suite
pixi run python -m pytest tests/unit/ -q --no-cov
```

## Test Results

- Config loader tests: 73 passed (58 original + 15 new)
- Full unit suite: 4341 passed, 1 skipped

## Critical Gotcha: Import Order and ruff-format

The first commit placed `_SCHEMAS_DIR` and `_validate_schema()` between stdlib/third-party imports and local imports:

```python
import jsonschema
import yaml

_SCHEMAS_DIR = Path(...)  # <- HERE, before local imports

def _validate_schema(...):
    ...raise ConfigurationError(...)  # ConfigurationError not yet imported!

from .models import (ConfigurationError, ...)
```

After `git commit`, the pre-commit `ruff-format` hook ran and reformatted the file — but because the constant and function were already between import groups, ruff left them there. The function then referenced `ConfigurationError` before it was defined at module load time.

**Fix**: Move `_SCHEMAS_DIR` and `_validate_schema` to after ALL imports (after `logger = logging.getLogger(__name__)`).

## Pydantic Alias Issue

`EvaluationConfig.runs_per_tier` has `Field(alias="runs_per_eval")`. The YAML key must be `runs_per_eval`. The test fixture `tests/fixtures/config/defaults.yaml` had used `runs_per_tier` (the Python attribute name), which passed before schema validation was added but fails after because the schema (correctly) only allows `runs_per_eval`.
