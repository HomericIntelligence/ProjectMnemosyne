# Skill: Config Filename/ID Validation Pattern

## Overview

| Field | Value |
|-------|-------|
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

## Failed Attempts

### Fixture test via loader with `_`-prefixed tier name

**Attempted:** `loader.load_tier("_test-fixture")` — mirroring how model fixture test uses `load_model("_test-fixture")`

**Why it failed:** `load_tier()` normalizes the tier name:

```python
tier = tier.lower().strip()
if not tier.startswith("t"):
    tier = f"t{tier}"  # "_test-fixture" → "t_test-fixture"
```

So it would look for `t_test-fixture.yaml` (not found) rather than `_test-fixture.yaml`.

**Fix:** Test the validation function directly instead of going through the loader. Import `validate_filename_tier_consistency` and call it with a manually constructed path.

### Pre-commit hook formatting failure

Ruff reformatted `tests/unit/test_config_loader.py` on first commit attempt. The pre-commit hook modifies files in place but the commit still fails. Re-stage and commit again — the second commit succeeds.

## Results & Parameters

### Files modified

| File | Change |
|------|--------|
| `scylla/config/validation.py` | Added `validate_filename_tier_consistency()` (+31 lines) |
| `scylla/config/loader.py` | Import + 7 lines in `load_tier()` |
| `tests/unit/test_config_loader.py` | Added `TestFilenameTierConsistency` class (+84 lines) |

### Test results

```
2213 passed, 8 warnings
Coverage: 73.38% (threshold: 73%)
```

### Pattern applicability

This exact pattern (validation function + loader call + 4 tests) can be applied to any
new config type with a filename-matching field. The only variation needed:

- If the ID has special characters (like `:`), add a normalization helper
- If the loader normalizes the ID before building the path, test the validation function
  directly for the `_`-prefix fixture case
