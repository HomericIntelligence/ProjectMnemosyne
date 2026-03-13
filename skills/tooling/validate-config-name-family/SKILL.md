# Skill: validate-config-name-family

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #775 |
| PR | #821 |
| Objective | Extend config validation to check the `name` field contains the model family (sonnet/haiku/opus) implied by the YAML filename |
| Outcome | Success — 30 new tests, all passing; full suite (2239 tests) green |

## When to Use

- Adding a new cross-field validation check to an existing validator module
- Checking that a human-readable label is consistent with a machine identifier derived from a filename
- Extending `ConfigLoader.load_model()` with an additional warning-level check
- Any time a "naming gap" is discovered where one field is validated but a related field is not

## Verified Workflow

### 1. Understand the existing pattern first

Read `scylla/config/validation.py` and `scylla/config/loader.py` before writing any code.
The existing `validate_filename_model_id_consistency()` is the reference pattern:

- Takes `(config_path: Path, field: str) -> list[str]`
- Skips `_`-prefixed test fixtures
- Returns warning strings (never raises)
- Caller in `loader.py` iterates and logs each warning

### 2. Add constants at module level

```python
KNOWN_FAMILIES: frozenset[str] = frozenset({"sonnet", "haiku", "opus"})
```

Place before all functions. Use `frozenset` for O(1) lookup and immutability.

### 3. Add a pure helper for family extraction

```python
def extract_model_family(filename_stem: str) -> str | None:
    for part in filename_stem.split("-"):
        if part.lower() in KNOWN_FAMILIES:
            return part.lower()
    return None
```

Splitting on `-` handles all real-world patterns:

- `claude-sonnet-4-5` → `sonnet`
- `claude-3-5-sonnet` → `sonnet`
- `claude-sonnet-4-5-20250929` → `sonnet`

### 4. Add the validator function

```python
def validate_name_model_family_consistency(config_path: Path, name: str) -> list[str]:
    warnings = []
    filename_stem = config_path.stem
    if filename_stem.startswith("_"):
        return warnings
    family = extract_model_family(filename_stem)
    if family is None:
        return warnings  # Unknown family — skip (no false positives)
    if family not in name.lower():
        warnings.append(
            f"name '{name}' does not contain expected model family "
            f"'{family}' (derived from filename '{filename_stem}')"
        )
    return warnings
```

### 5. Wire into loader.py

In `ConfigLoader.load_model()`, after the existing filename/model_id check:

```python
# Validate name/model family consistency
warnings = validate_name_model_family_consistency(model_path, config.name)
for warning in warnings:
    logger.warning(warning)
```

Update the import line to include both validators.

### 6. Write tests (TDD — write BEFORE implementing)

File: `tests/unit/config/test_validation.py`

Test classes:

- `TestExtractModelFamily` — known families, unknown families, empty string
- `TestValidateNameModelFamilyConsistency` — valid names, wrong family, unknown family, test fixture skipped, case-insensitive, empty name, warning message content

Use `tmp_path` fixture from pytest; no real YAML files needed (just `Path` objects).

### 7. Watch for broken existing tests

Adding a new validator to `load_model()` means any existing test that:

- Sets up a deliberate filename/model_id mismatch AND
- Has a known model family in the filename AND
- Has a name that doesn't match that family

...will now get an **extra** warning. Find tests asserting `len(caplog.records) == 1` for such scenarios and loosen to `>= 1`.

In this project the affected test was:
`tests/unit/test_config_loader.py::TestFilenameModelIdValidation::test_filename_mismatch_warns`

## Failed Attempts

None in this session — the approach was clear from the existing pattern. The only surprise was the pre-existing test asserting an exact warning count.

## Results & Parameters

### Files Changed

| File | Change |
|------|--------|
| `scylla/config/validation.py` | +`KNOWN_FAMILIES`, +`extract_model_family()`, +`validate_name_model_family_consistency()` |
| `scylla/config/loader.py` | Updated import, added call to new validator in `load_model()` |
| `tests/unit/config/test_validation.py` | New file, 30 parametrized tests |
| `tests/unit/test_config_loader.py` | Loosened `== 1` → `>= 1` in `test_filename_mismatch_warns` |

### Test Coverage

```
30 new tests added
2239 total tests — all passing
pre-commit: ruff, mypy, markdownlint, yamllint, shellcheck — all passing
```

### Design Decisions

- **Warning, not error** — matches existing pattern; loading continues even with mismatched names
- **Skip unknown families** — avoids false positives for non-Anthropic models (GPT, Gemini, etc.)
- **Case-insensitive** — `"claude HAIKU 4.5"` should pass for `claude-haiku-4-5.yaml`
- **Skip `_`-prefixed fixtures** — consistent with the existing validator
- **`frozenset` for KNOWN_FAMILIES** — immutable, O(1) lookup, self-documenting intent
