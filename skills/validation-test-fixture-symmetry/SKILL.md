# Validation Test Fixture Symmetry

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #808 - Extract common validation test fixture pattern for loaders |
| **Follow-up from** | #733 |
| **Objective** | Eliminate asymmetry between tier and model config loader tests by making tier fixture tests go through the loader (not the validator directly) |
| **Outcome** | ✅ Success - Full symmetry achieved; 4 new tests via loader; 2396 tests pass |
| **Test Impact** | +4 new tests; 0 regressions; 74.19% coverage maintained |

## When to Use This Skill

Use this workflow when you see:

- **Asymmetric test patterns** — one loader calls the validator directly for fixture tests, another goes through the loader
- **Loader-level validation** that needs adding to a new config loader (tier, rubric, test, etc.)
- **`_`-prefixed test fixtures** that need to bypass name normalization **and** validation
- Code review / follow-up issues asking for consistency between config loaders

**Trigger phrases:**

- "Test fixture calls validation directly, not through loader"
- "Asymmetry between X config tests and Y config tests"
- "Add validation to load_X() analogous to load_model()"
- "Skip normalization / validation for test fixtures"

## Verified Workflow

### Phase 1: Understand the Asymmetry

1. **Read the existing symmetric loader** (e.g., `load_model()`) to see the pattern:

   ```python
   # In load_model():
   config = ModelConfig(**data)
   warnings = validate_filename_model_id_consistency(model_path, config.model_id)
   for warning in warnings:
       logger.warning(warning)
   return config
   ```

2. **Read the asymmetric loader** (e.g., `load_tier()`) — it lacks this validation call.

3. **Read the corresponding test** to confirm it calls the validator directly:

   ```python
   # BEFORE (asymmetric — calls validator directly):
   warnings = validate_name_model_family_consistency(config_path, name)
   assert not warnings
   ```

   vs the model test (goes through loader):

   ```python
   # SYMMETRIC — calls through loader:
   config = loader.load_model("_test-fixture")
   assert not caplog.records
   ```

### Phase 2: Add Validation Function

Add `validate_filename_X_consistency()` in `scylla/config/validation.py` following the same pattern as the existing validator:

```python
def validate_filename_tier_consistency(config_path: Path, tier: str) -> list[str]:
    """Validate config filename matches tier identifier.

    Args:
        config_path: Path to tier config file
        tier: tier field from config (normalized, e.g., "t0")

    Returns:
        List of warning messages (empty if valid)

    """
    filename_stem = config_path.stem

    # Skip validation for test fixtures (prefixed with _)
    if filename_stem.startswith("_"):
        return []

    if filename_stem == tier:
        return []

    return [
        f"Config filename '{filename_stem}.yaml' does not match tier "
        f"'{tier}'. Expected '{tier}.yaml'"
    ]
```

**Key invariants to preserve:**
- Returns `list[str]` (empty = valid, non-empty = warnings)
- Skips validation for `_`-prefixed filenames
- No exceptions — only warnings

### Phase 3: Update the Loader

In `load_tier()` (or analogous method), make **two** changes:

1. **Skip name normalization for `_`-prefixed paths** (so `_test-fixture` isn't mangled to `t_test-fixture`):

   ```python
   # Before:
   tier = tier.lower().strip()
   if not tier.startswith("t"):
       tier = f"t{tier}"

   # After:
   if not tier.startswith("_"):
       tier = tier.lower().strip()
       if not tier.startswith("t"):
           tier = f"t{tier}"
   ```

2. **Call the new validator after constructing the config** (mirroring `load_model()`):

   ```python
   try:
       config = TierConfig(**data)
   except Exception as e:
       raise ConfigurationError(f"Invalid tier configuration in {tier_path}: {e}")

   warnings = validate_filename_tier_consistency(tier_path, config.tier)
   for warning in warnings:
       logger.warning(warning)

   return config
   ```

3. **Import the new function** in `loader.py`:

   ```python
   from .validation import (
       validate_filename_model_id_consistency,
       validate_filename_tier_consistency,   # <-- add
       validate_model_config_referenced,
   )
   ```

### Phase 4: Write Tests via Loader

Add a `TestFilenameXConsistency` class that mirrors the existing `TestFilenameModelIdValidation` class exactly — all 4 tests go through the **loader**, not the validator directly:

```python
class TestFilenameTierConsistency:
    """Test validation of filename/tier consistency."""

    def test_filename_matches_tier_exact(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test validation passes when filename matches tier exactly."""
        tiers_dir = tmp_path / "config" / "tiers"
        tiers_dir.mkdir(parents=True)
        (tiers_dir / "t0.yaml").write_text("tier: t0\nname: Vanilla\n")

        loader = ConfigLoader(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            config = loader.load_tier("t0")

        assert config.tier == "t0"
        assert not caplog.records  # No warnings

    def test_filename_mismatch_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test validation warns when filename doesn't match tier field."""
        tiers_dir = tmp_path / "config" / "tiers"
        tiers_dir.mkdir(parents=True)
        (tiers_dir / "t1.yaml").write_text("tier: t0\nname: Vanilla\n")  # mismatch!

        loader = ConfigLoader(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            config = loader.load_tier("t1")

        assert config.tier == "t0"
        assert len(caplog.records) == 1
        assert "t1.yaml" in caplog.text
        assert "t0" in caplog.text

    def test_test_fixtures_skip_validation(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that _-prefixed fixtures skip validation (via loader, not direct call)."""
        tiers_dir = tmp_path / "config" / "tiers"
        tiers_dir.mkdir(parents=True)
        (tiers_dir / "_test-fixture.yaml").write_text("tier: t0\nname: Fixture Tier\n")

        loader = ConfigLoader(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            config = loader.load_tier("_test-fixture")

        assert config.tier == "t0"
        assert not caplog.records  # No warnings for test fixtures

    def test_warning_message_format(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning message includes both filename and tier field value."""
        tiers_dir = tmp_path / "config" / "tiers"
        tiers_dir.mkdir(parents=True)
        (tiers_dir / "t2.yaml").write_text("tier: t1\nname: Prompted\n")

        loader = ConfigLoader(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            loader.load_tier("t2")

        assert len(caplog.records) == 1
        warning_msg = caplog.records[0].message
        assert "t2.yaml" in warning_msg
        assert "t1" in warning_msg
```

### Phase 5: Verify and Commit

```bash
# Run targeted tests first
pixi run python -m pytest tests/unit/test_config_loader.py -v

# Run full suite to verify coverage threshold
pixi run python -m pytest tests/ --ignore=tests/claude-code -v

# Stage and commit (pre-commit will auto-format)
git add scylla/config/loader.py scylla/config/validation.py tests/unit/test_config_loader.py
git commit -m "feat(config): extract common validation test fixture pattern for loaders

Closes #808"

# Re-stage after ruff auto-format and commit again
git add scylla/config/loader.py scylla/config/validation.py tests/unit/test_config_loader.py
git commit -m "feat(config): ..."
```

## Failed Attempts & Lessons Learned

### ❌ Don't: Call the validator directly in tests for the asymmetric loader

**Why it fails:** This is the exact anti-pattern described in the issue. Calling the validator directly bypasses the loader, meaning if the loader's normalization or fixture-detection logic changes, the test won't catch it.

**✅ Do:** Always go through `loader.load_X()` in tests, using `caplog` to capture warning output.

### ❌ Don't: Forget to bypass normalization for `_`-prefixed fixture names

**Why it fails:** `load_tier("_test-fixture")` without the guard becomes `_test-fixture.lower().strip()` then `t_test-fixture` (since it doesn't start with `t`). The file `_test-fixture.yaml` won't be found.

**✅ Do:** Check `tier.startswith("_")` before normalization. The guard must come first.

### ❌ Don't: Amend the previous commit after ruff auto-formats

**Why it fails:** `--no-verify` is prohibited. If ruff formats a file, the pre-commit hook fails the commit. The files are modified-in-place. You must re-stage and create a **new** commit.

**✅ Do:** After a hook-caused commit failure, `git add` the auto-formatted files and run `git commit` again (same message is fine).

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `scylla/config/validation.py` | Added `validate_filename_tier_consistency()` (22 lines) |
| `scylla/config/loader.py` | Updated `load_tier()`: normalization guard + validation call + import |
| `tests/unit/test_config_loader.py` | Added `TestFilenameTierConsistency` (4 tests, ~60 lines) |

### Test Metrics

| Metric | Value |
|--------|-------|
| New tests added | 4 |
| Total tests | 2396 passed |
| Coverage | 74.19% (threshold: 73%) |
| Regressions | 0 |

### Pre-commit Hooks

```bash
# Hooks that auto-ran (ruff-format reformatted the test file)
- ruff-format-python  # Modified test file; required re-stage + re-commit
- ruff               # Passed
- mypy               # Passed
```

## Key Insights

1. **Symmetry between loader tests is a quality signal** — if one loader goes through the loader for fixture tests and another doesn't, it's a maintenance hazard. The fix is small but valuable.

2. **Name normalization must be fixture-aware** — any loader that normalizes input (lowercasing, prefixing) must skip normalization for `_`-prefixed fixture names, or the file lookup will fail.

3. **The `_` prefix convention is a first-class concept** — it appears in both `validation.py` (skip validation) and `loader.py` (skip normalization). Both must be consistent.

4. **`caplog` is the right tool for warning-based validation tests** — use `pytest.LogCaptureFixture` with `caplog.at_level(logging.WARNING)` and assert on `caplog.records` / `caplog.text`.

5. **Ruff auto-formats on commit failure** — after a ruff-caused failure, re-stage and commit. Don't amend.

## References

- Issue: #808 (follow-up from #733)
- PR: #950
- Files modified:
  - `scylla/config/validation.py`
  - `scylla/config/loader.py`
  - `tests/unit/test_config_loader.py`
- Related skills: `enforce-model-config-consistency-hook`, `validate-model-configs-fix-mode`

## Usage Examples

### Invoke this skill when you see

A follow-up issue saying:

> "The X config test calls the validator directly (not through the loader) due to normalization. The Y config equivalent calls through the loader. This asymmetry could confuse future contributors."

### Expected outcome

- New `validate_filename_X_consistency()` function in `validation.py`
- `load_X()` updated with normalization guard + validation call
- `TestFilenameXConsistency` class with 4 tests, all via loader

---

**Category:** testing
**Tags:** test-fixtures, symmetry, validation, loader, config, caplog, normalization, underscore-prefix
**Confidence:** High (verified on real codebase with 2396 tests)
