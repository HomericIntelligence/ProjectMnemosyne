---
name: config-filename-validation
description: "Skill: Config Filename/ID Validation Pattern"
category: tooling
date: 2026-03-19
version: "2.0.0"
user-invocable: false
---
# Skill: Config Filename/ID Validation Pattern

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-02-19 |
| Issue | #733 (follow-up to #692) |
| PR | #795 |
| Objective | Add validation that tier config filenames match their `tier` field |
| Outcome | Success — 2213 tests pass, 73.38% coverage |
| Category | testing |

## When to Use

Apply this pattern when:

- A config dataclass has an ID/key field that should match its filename
- You want to catch silent mismatches between filename and config content
- You're adding a new config type that follows the same load/validate pattern
- A follow-up issue asks to mirror an existing validation pattern to a new config type
- A config has no ID field and you need a stem-only check or explicit documentation of why validation is skipped

Trigger conditions:

- "filename should match the X field"
- "prevent filename/ID mismatch"
- "consistent validation across all config types"
- "mirror the model config pattern"

## Verified Workflow

### 1. Add validation function to `scylla/config/validation.py`

For simple exact-match validation (no normalization needed):

```python
def validate_filename_tier_consistency(config_path: Path, tier: str) -> list[str]:
    """Validate that config filename matches the tier field."""
    warnings = []
    filename_stem = config_path.stem

    # Skip validation for test fixtures (prefixed with _)
    if filename_stem.startswith("_"):
        return warnings

    # Check exact match
    if filename_stem == tier:
        return warnings

    # Mismatch detected
    warnings.append(
        f"Config filename '{filename_stem}.yaml' does not match tier "
        f"'{tier}'. Expected '{tier}.yaml'"
    )
    return warnings
```

For IDs requiring normalization (e.g., `:` → `-` for model IDs), see
`validate_filename_model_id_consistency` — adds a `get_expected_filename()` helper
and checks both exact and normalized match.

### 2. Call validation in the loader after constructing the dataclass

In `scylla/config/loader.py`, update the relevant `load_X()` method:

```python
from .validation import validate_filename_model_id_consistency, validate_filename_tier_consistency

# After constructing the config object:
try:
    config = TierConfig(**data)
except Exception as e:
    raise ConfigurationError(f"Invalid tier configuration in {tier_path}: {e}")

# Validate filename/tier consistency
warnings = validate_filename_tier_consistency(tier_path, config.tier)
for warning in warnings:
    logger.warning(warning)

return config
```

Key decisions:

- **Warning, not error** — load succeeds even with mismatch (matches existing model config behavior)
- **After dataclass construction** — validate the actual field value, not raw YAML data
- **Use `config.tier` not `data["tier"]`** — field may have been normalized by validators

### 3. Write 4 test cases in `TestFilenameTierConsistency`

```python
class TestFilenameTierConsistency:
    def test_filename_matches_tier_exact(self, tmp_path, caplog):
        # exact match → no warnings

    def test_filename_mismatch_warns(self, tmp_path, caplog):
        # mismatch → 1 warning containing filename, tier field, expected filename

    def test_test_fixtures_skip_validation(self, tmp_path):
        # _-prefixed filename → import validation fn directly, no loader call needed
        from scylla.config.validation import validate_filename_tier_consistency
        config_path = tmp_path / "_test-fixture.yaml"
        warnings = validate_filename_tier_consistency(config_path, "t0")
        assert not warnings

    def test_warning_message_format(self, tmp_path, caplog):
        # assert exact message text contains filename and tier field
```

---

## Variation: No ID Field (Stem-Only Check)

When a config type has no single ID field analogous to `ModelConfig.model_id`, the
field-level filename consistency pattern cannot be applied literally. Instead, add a
stem-only check that catches gross misconfiguration (wrong file entirely) and explicitly
document in both the function docstring and caller why field-level validation is skipped.

This pattern was applied for `DefaultsConfig` in Issue #806 / PR #941.

### Add a stem-only validation function

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

### Call in the loader

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

### Parametrized test examples for stem-only validation

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

**Note on loader integration tests**: Because `load_defaults()` hard-codes `config/defaults.yaml`,
there is no easy way to trigger the warning through the public API without complex
monkeypatching. Test the validation function directly for the warning path. The loader
integration test covers the "no-warning" happy path end-to-end.

```python
class TestDefaultsFilenameValidation:
    def test_load_defaults_warns_for_nonstandard_filename(self, tmp_path, caplog):
        # Since load_defaults() hard-codes config/defaults.yaml, test the
        # validation function directly to confirm warning behaviour.
        from scylla.config.validation import validate_defaults_filename
        nonstandard = tmp_path / "my_defaults.yaml"
        warnings = validate_defaults_filename(nonstandard)
        assert len(warnings) == 1
        assert "my_defaults.yaml" in warnings[0]
        assert "defaults.yaml" in warnings[0]
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |

## Results & Parameters

### Files modified (Issue #733 / PR #795 — exact match)

| File | Change |
| ------ | -------- |
| `scylla/config/validation.py` | Added `validate_filename_tier_consistency()` (+31 lines) |
| `scylla/config/loader.py` | Import + 7 lines in `load_tier()` |
| `tests/unit/test_config_loader.py` | Added `TestFilenameTierConsistency` class (+84 lines) |

### Files modified (Issue #806 / PR #941 — stem-only)

| File | Change |
| ------ | -------- |
| `scylla/config/validation.py` | Added `validate_defaults_filename()` |
| `scylla/config/loader.py` | Import + validation call in `load_defaults()` |
| `tests/unit/config/test_validation.py` | Added `TestValidateDefaultsFilename` class |
| `tests/unit/test_config_loader.py` | Added `TestDefaultsFilenameValidation` class |

### Test results (Issue #733 / PR #795)

```
2213 passed, 8 warnings
Coverage: 73.38% (threshold: 73%)
```

### Tests added (Issue #806 / PR #941)

| Category | Count |
| ---------- | ------- |
| Unit tests for `validate_defaults_filename` | 8 |
| Integration tests in loader test file | 2 |
| Total | 10 |

### Pattern applicability

This exact pattern (validation function + loader call + 4 tests) can be applied to any
new config type with a filename-matching field. The only variation needed:

- If the ID has special characters (like `:`), add a normalization helper
- If the loader normalizes the ID before building the path, test the validation function
  directly for the `_`-prefix fixture case
- If the config has no ID field, use the stem-only check and document why field-level
  validation is not applicable
