# Orphan Config Detection

## Overview

| Field      | Value                                                           |
|------------|-----------------------------------------------------------------|
| Date       | 2026-02-20                                                      |
| Issue      | #777                                                            |
| PR         | #824                                                            |
| Objective  | Warn when a `config/models/*.yaml` file is not referenced by any experiment or test file |
| Outcome    | Success — 2220 tests pass, 73.4% coverage, pre-commit clean     |
| Category   | testing                                                         |

---

## When to Use

Apply this pattern when:

- You have a directory of "registered" resource configs (models, adapters, plugins, etc.) that experiments or tests must reference to be meaningful
- Orphaned/deprecated configs accumulate silently and confuse future developers
- You want to surface the warning automatically without a separate CI script (i.e., the check runs whenever the loader is invoked)
- The existing codebase already has a `validation.py` module with a similar convention (filename ↔ field consistency)

---

## Verified Workflow

### 1. Implement the validator function

Add to `scylla/config/validation.py`:

```python
_REFERENCE_EXTENSIONS = ("*.yaml", "*.py")

def validate_model_config_referenced(
    config_path: Path, search_roots: list[Path]
) -> list[str]:
    """Warn if model config file is not referenced by any file under search_roots."""
    stem = config_path.stem
    if stem.startswith("_"):        # skip test fixtures
        return []
    for root in search_roots:
        if not root.exists():
            continue
        for ext_pattern in _REFERENCE_EXTENSIONS:
            for f in root.rglob(ext_pattern):
                if f == config_path:  # don't count self
                    continue
                try:
                    if stem in f.read_text(encoding="utf-8", errors="ignore"):
                        return []
                except (OSError, PermissionError):
                    continue
    return [
        f"Model config '{config_path.name}' is not referenced by any file under "
        f"{[str(r) for r in search_roots]}. It may be orphaned."
    ]
```

Key design decisions:

- Returns `list[str]` (same shape as `validate_filename_model_id_consistency`) — stays consistent with existing conventions
- `_`-prefix skips test fixtures — consistent with the filename validator
- Does **not** count the file itself as a reference (self-reference trap avoided)
- Handles missing/unreadable roots gracefully

### 2. Wire into the bulk loader

In `load_all_models()` (loader.py), add a second pass **after** loading all models:

```python
search_roots = [self.base_path / "config", self.base_path / "tests"]
for model_file in sorted(models_dir.glob("*.yaml")):
    if model_file.name.startswith(".") or model_file.stem.startswith("_"):
        continue
    for warning in validate_model_config_referenced(model_file, search_roots):
        logger.warning(warning)
```

Do it as a **second pass** (not inline with loading) so all model files are checked regardless of whether they loaded successfully.

### 3. Write unit tests for the validator

File: `tests/unit/test_config_validation.py`

Cover these cases:

- Referenced in a config `.yaml` → no warning
- Referenced in a test `.py` → no warning
- Unreferenced → warning containing the filename
- `_`-prefixed fixture → no warning
- Empty `search_roots` → warning
- Non-existent search root → gracefully skipped, warning issued
- Self-reference doesn't count → warning still issued
- Warning message is informative (contains filename)

### 4. Write integration tests via the loader

File: `tests/unit/test_config_loader.py` — add `TestModelConfigOrphanValidation` class:

- `test_load_all_models_warns_unreferenced` — caplog captures WARNING with filename
- `test_load_all_models_no_warn_referenced` — no orphan warning when referenced
- `test_load_all_models_skips_test_fixtures` — `_`-prefixed files never warned

### 5. Run checks

```bash
pixi run python -m pytest tests/unit/test_config_validation.py tests/unit/test_config_loader.py -v
pre-commit run --files scylla/config/validation.py scylla/config/loader.py tests/unit/test_config_validation.py tests/unit/test_config_loader.py
```

---

## Failed Attempts

None on this task — the approach was straightforward given the existing codebase patterns.

---

## Results & Parameters

| Metric            | Value                          |
|-------------------|--------------------------------|
| New functions     | 1 (`validate_model_config_referenced`) |
| New test file     | `tests/unit/test_config_validation.py` (8 tests) |
| Modified files    | `scylla/config/validation.py`, `scylla/config/loader.py`, `tests/unit/test_config_loader.py` |
| Tests added       | 11 (8 unit + 3 integration)    |
| Total tests pass  | 2220                           |
| Coverage          | 73.4% (meets 73% threshold)    |
| Pre-commit result | All hooks pass                 |

---

## Key Conventions to Match

- Existing validators return `list[str]` (warnings), never raise
- `_`-prefixed files are test fixtures — always skip validation
- Warnings are emitted via `logger.warning()` in the loader, not in the validator itself
- Search roots: `config/` and `tests/` (covers both experiment YAMLs and test Python files)
- `_REFERENCE_EXTENSIONS = ("*.yaml", "*.py")` — extend this tuple if you add new file types
