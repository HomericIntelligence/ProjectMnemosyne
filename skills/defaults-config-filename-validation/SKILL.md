# Skill: defaults-config-filename-validation

## Overview

| Field     | Value                                                                             |
|-----------|-----------------------------------------------------------------------------------|
| Date      | 2026-02-22                                                                        |
| Issue     | #806                                                                              |
| PR        | #941                                                                              |
| Objective | Apply filename validation to `DefaultsConfig` loader, or document why it is skipped |
| Outcome   | Success — stem-only check added with explicit documentation of design decision    |

## When to Use

- You have a config loader that loads a well-known file (e.g. `defaults.yaml`) and want
  to add a consistency check, but the config model has no ID field to compare against
- You need to resolve a follow-up issue asking whether field-level filename validation
  is warranted for a config type without a natural ID field
- You want to document "validation intentionally skipped" in code rather than only in
  a GitHub issue comment
- You're following up on a prior validation implementation (like `validate_filename_model_id_consistency`)
  to achieve parity across all config loaders

## Verified Workflow

### 1. Understand the constraint

`DefaultsConfig` has no single ID field analogous to `ModelConfig.model_id`. So the
`validate_filename_model_id_consistency` pattern (filename stem == model_id) cannot be
applied literally. The question the issue poses is: either add *some* consistency check,
or explicitly document that validation is skipped.

**Decision**: Add a stem-only check (`config_path.stem == "defaults"`) that catches
gross misconfiguration (wrong file entirely), and document clearly in both the function
docstring and the caller why field-level validation is not applicable.

### 2. Add the validation function to `validation.py`

```python
def validate_defaults_filename(config_path: Path) -> list[str]:
    """Validate that the defaults config file is named 'defaults.yaml'.

    DefaultsConfig has no single ID field (unlike ModelConfig which has
    model_id), so field-level filename consistency is not applicable.
    This function checks only that the file stem is 'defaults' — catching
    accidental misconfiguration (e.g., loading the wrong file entirely).

    Args:
        config_path: Path to the defaults YAML file.

    Returns:
        List of warning strings; empty if validation passes.

    """
    warnings: list[str] = []
    if config_path.stem != "defaults":
        warnings.append(
            f"Defaults config loaded from unexpected filename "
            f"'{config_path.name}' (expected 'defaults.yaml'). "
            f"Note: DefaultsConfig has no ID field — filename consistency "
            f"validation is intentionally limited to stem check only."
        )
    return warnings
```

**Key design choices:**
- Returns `list[str]` (same contract as `validate_filename_model_id_consistency`)
- Warning message explicitly states why field-level validation is skipped
- No skip for `_`-prefixed fixtures (the defaults file is never a fixture)
- Case-sensitive stem check: `"defaults"` (not `"Defaults"`)

### 3. Call it in `ConfigLoader.load_defaults()`

Follow the exact same pattern used for model config validation:

```python
from .validation import (
    validate_defaults_filename,          # new import
    validate_filename_model_id_consistency,
    validate_model_config_referenced,
)

def load_defaults(self) -> DefaultsConfig:
    """Load global defaults configuration.

    Loads config/defaults.yaml. Note: DefaultsConfig has no model_id-style
    field, so field-level filename consistency validation (as applied to
    ModelConfig) is intentionally not performed. A stem-only check is
    applied to catch gross misconfiguration (wrong file entirely).
    ...
    """
    defaults_path = self.base_path / "config" / "defaults.yaml"
    data = self._load_yaml(defaults_path)

    # Validate filename stem only — DefaultsConfig has no ID field,
    # so model_id↔filename consistency checks are not applicable.
    for warning in validate_defaults_filename(defaults_path):
        logger.warning(warning)

    try:
        return DefaultsConfig(**data)
    except Exception as e:
        raise ConfigurationError(f"Invalid defaults configuration in {defaults_path}: {e}")
```

### 4. Write unit tests for `validate_defaults_filename`

Add a `TestValidateDefaultsFilename` class to `tests/unit/config/test_validation.py`:

```python
class TestValidateDefaultsFilename:
    @pytest.mark.parametrize("filename", ["defaults.yaml", "defaults.yml"])
    def test_standard_filename_no_warnings(self, tmp_path, filename):
        config_path = tmp_path / filename
        assert validate_defaults_filename(config_path) == []

    @pytest.mark.parametrize("filename", [
        "defaults-v2.yaml", "config.yaml", "my_defaults.yaml",
        "Defaults.yaml", "default.yaml",
    ])
    def test_nonstandard_filename_warns(self, tmp_path, filename):
        warnings = validate_defaults_filename(tmp_path / filename)
        assert len(warnings) == 1
        assert "defaults.yaml" in warnings[0]
        assert filename in warnings[0]

    def test_warning_message_explains_no_id_field(self, tmp_path):
        warnings = validate_defaults_filename(tmp_path / "wrong-name.yaml")
        assert "DefaultsConfig" in warnings[0]
        assert "no ID field" in warnings[0]
```

### 5. Write integration tests in the loader test file

Add `TestDefaultsFilenameValidation` to `tests/unit/test_config_loader.py`:

```python
class TestDefaultsFilenameValidation:
    def test_load_defaults_no_warnings_for_standard_path(
        self, tmp_path, caplog
    ):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "defaults.yaml").write_text("evaluation:\n  runs_per_eval: 1\n")
        loader = ConfigLoader(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            defaults = loader.load_defaults()
        assert isinstance(defaults, DefaultsConfig)
        assert not caplog.records

    def test_load_defaults_warns_for_nonstandard_filename(
        self, tmp_path, caplog
    ):
        # Since load_defaults() hard-codes config/defaults.yaml, test the
        # validation function directly to confirm warning behaviour.
        from scylla.config.validation import validate_defaults_filename
        nonstandard = tmp_path / "my_defaults.yaml"
        warnings = validate_defaults_filename(nonstandard)
        assert len(warnings) == 1
        assert "my_defaults.yaml" in warnings[0]
        assert "defaults.yaml" in warnings[0]
```

**Note on test design**: Because `load_defaults()` hard-codes `config/defaults.yaml`,
there is no easy way to trigger the warning through the public API without complex
monkeypatching. Test the validation function directly instead of trying to exercise the
warning path through the loader. The loader integration test covers the "no-warning"
happy path end-to-end.

## Failed Attempts

### Monkeypatching `load_defaults` to exercise the warning path

The first attempt used `monkeypatch.setattr(loader, "load_defaults", patched_load_defaults)`
with a custom function that called `validate_defaults_filename` on a non-standard path.
The patched function needed imports inside the closure, which triggered ruff violations:
- `F841` — unused variable `original_load_defaults`
- `N814` — CamelCase imported as constant (`DefaultsConfig as _DC`, `ConfigurationError as _CE`)

**Fix**: Replace the monkeypatch with a direct call to `validate_defaults_filename(nonstandard)`.
The loader's hard-coded path means the warning path can only be triggered by calling the
validation function directly. This is simpler and avoids the ruff issues entirely.

### Attempting field-level consistency check for DefaultsConfig

An early consideration was to add a check analogous to `validate_filename_model_id_consistency`,
comparing the filename against some field in `DefaultsConfig`. However, `DefaultsConfig` has
no single ID field. The nearest candidates were config section names (e.g. `evaluation`,
`output`) but those are structural keys, not identifiers. The stem-only check was the
minimal meaningful validation that could be applied.

## Results & Parameters

| Metric                   | Value                                           |
|--------------------------|-------------------------------------------------|
| Tests added              | 10 (8 unit + 2 integration)                     |
| Validation function      | `scylla.config.validation.validate_defaults_filename` |
| Stem checked             | `"defaults"`                                    |
| Warning logged via       | `logger.warning()` in `ConfigLoader.load_defaults()` |
| Pre-commit hooks changed | None (validation is runtime-only, not enforced at commit) |
| Design decision          | Stem-only check; field-level skipped (no ID field) |
