# Validate Tier ID / Filename Consistency

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Category** | testing |
| **Objective** | Fix silent key/value disagreement when `load_all_tiers()` stores configs under filename keys without verifying the `tier` field inside each config matches |
| **Outcome** | ✅ `ConfigurationError` raised immediately on mismatch; 2398 tests pass; 74.16% coverage |
| **Issue** | #807 (follow-up from #733) |
| **PR** | #945 |

## When to Use

Use this skill when:

- A `load_all_*()` function globs files and stores results by filename stem, but the loaded object has an ID field that could disagree with that stem.
- A caller trusts either the dict key or the object's own ID field and the two could silently diverge.
- You see patterns like: `result[filename_stem] = self.load_X(filename_stem)` where `load_X` may use the file body's ID field instead of the filename stem.
- A related individual loader (`load_tier`, `load_model`) normalizes the identifier and you need to ensure the aggregation layer applies the same normalization before comparing.

## Problem Pattern

**Root Cause**: `load_all_tiers()` used the filename stem as the dict key, but `load_tier()` injected `tier` into the YAML data only when the key was absent. If `tier: t1` was declared in `t0.yaml`, `load_tier("t0")` returned a config with `config.tier == "t1"` while the caller stored it under key `"t0"`. Silent disagreement.

```python
# BEFORE — silent mismatch possible
for tier_file in sorted(tiers_dir.glob("t*.yaml")):
    tier_name = tier_file.stem        # "t0"
    result[tier_name] = self.load_tier(tier_name)
    # If t0.yaml has `tier: t1`, result["t0"].tier == "t1" — caller gets bad data
```

## Verified Workflow

### 1. Identify the aggregation pattern

Look for `load_all_*()` methods that:
- Glob files and extract a key from the filename stem.
- Call an individual `load_*()` method that may use body-level ID fields.
- Store results as `result[stem] = loaded_object`.

```bash
grep -n "glob\|stem\|result\[" scylla/config/loader.py
```

### 2. Determine normalization used by the individual loader

Read the individual `load_*()` to find how it normalizes the identifier:

```python
# In load_tier():
tier = tier.lower().strip()
if not tier.startswith("t"):
    tier = f"t{tier}"
```

### 3. Apply the same normalization in the aggregation check

Add a post-load guard **after** calling the individual loader, **before** storing:

```python
for tier_file in sorted(tiers_dir.glob("t*.yaml")):
    tier_name = tier_file.stem              # e.g., "t0"
    tier_config = self.load_tier(tier_name)

    # Apply same normalization as load_tier() to compute expected
    expected = tier_name.lower().strip()
    if not expected.startswith("t"):
        expected = f"t{expected}"

    if tier_config.tier != expected:
        raise ConfigurationError(
            f"Tier ID mismatch in {tier_file}: "
            f"filename implies '{expected}' but config declares tier='{tier_config.tier}'"
        )

    result[tier_name] = tier_config
```

**Key decisions**:
- Reuse the individual loader's normalization exactly — do not invent a new one.
- Error message must name both the filename path and the conflicting field value.
- Guard goes between `load_tier()` call and `result[...] =` assignment.
- No new helpers, classes, or abstractions needed.

### 4. Write tests with `tmp_path` (not shared fixtures)

Use pytest's `tmp_path` fixture for the mismatch test to avoid polluting the shared fixtures directory and breaking existing count assertions:

```python
def test_load_all_tiers_mismatched_id_raises(self, tmp_path: Path) -> None:
    """load_all_tiers() raises ConfigurationError when filename and config.tier disagree."""
    tiers_dir = tmp_path / "config" / "tiers"
    tiers_dir.mkdir(parents=True)

    # File named t0.yaml but declares tier: t1
    (tiers_dir / "t0.yaml").write_text(
        "tier: t1\nname: Mismatch Test\ndescription: Intentionally mismatched\n"
        "uses_tools: false\nuses_delegation: false\nuses_hierarchy: false\n"
    )

    loader = ConfigLoader(base_path=tmp_path)
    with pytest.raises(ConfigurationError, match="t0") as exc_info:
        loader.load_all_tiers()

    assert "t1" in str(exc_info.value)


def test_load_all_tiers_consistent_ids(self) -> None:
    """All dict keys returned by load_all_tiers() equal their config.tier value."""
    loader = ConfigLoader(base_path=FIXTURES_PATH)
    tiers = loader.load_all_tiers()

    for key, config in tiers.items():
        assert key == config.tier, f"Key {key!r} does not match config.tier {config.tier!r}"
```

### 5. Run and verify

```bash
# Tier-specific tests (note: coverage will show <73% in isolation — that's expected)
pixi run python -m pytest tests/unit/test_config_loader.py::TestConfigLoaderTier -v

# Full suite (coverage must meet threshold)
pixi run python -m pytest tests/ -v

# Pre-commit hooks
pre-commit run --all-files
```

**Expected results**:
- `test_load_all_tiers_mismatched_id_raises` — PASS
- `test_load_all_tiers_consistent_ids` — PASS
- All existing tests — PASS (no regressions)
- Coverage threshold met

## Failed Attempts

### Attempted: Creating a shared fixture file for the mismatch case

**What**: Considered placing `tmismatch.yaml` (with `tier: t99`) in `tests/fixtures/config/tiers/` to be picked up by the glob.

**Why it failed**: The existing `test_load_all_tiers` asserts `len(tiers) == 2`. Adding a file that triggers a `ConfigurationError` mid-iteration would break that test, and placing a valid but intentionally-mismatched fixture would change the count to 3.

**Resolution**: Use `tmp_path` in the mismatch test instead. Isolated loader with its own temp directory — no impact on shared fixtures.

### Pre-commit E501 line-too-long

**What**: First docstring attempt was 101 characters, exceeding the 100-char limit.

**Fix**: Shortened `"when filename stem and config.tier disagree"` to `"when filename and config.tier disagree"`.

**Pattern**: Always check docstring line length when the method name is already long (e.g., `test_load_all_tiers_mismatched_id_raises`).

## Results & Parameters

### Production change

**File**: `scylla/config/loader.py` — `load_all_tiers()` (lines 244–259)

```python
# Added after self.load_tier(tier_name) call:
expected = tier_name.lower().strip()
if not expected.startswith("t"):
    expected = f"t{expected}"

if tier_config.tier != expected:
    raise ConfigurationError(
        f"Tier ID mismatch in {tier_file}: "
        f"filename implies '{expected}' but config declares tier='{tier_config.tier}'"
    )
```

### Test changes

**File**: `tests/unit/test_config_loader.py` — `TestConfigLoaderTier` class

- Added `test_load_all_tiers_mismatched_id_raises` (uses `tmp_path`)
- Added `test_load_all_tiers_consistent_ids` (uses shared fixtures)

### Verification results

```
2398 passed, 8 warnings in 56.38s
Coverage: 74.16% (threshold: 73%)
Pre-commit: All checks passed
```

### PR

- **Branch**: `807-auto-impl`
- **PR**: #945
- **Commit**: `fix(config): Validate tier IDs in load_all_tiers() match filenames`
- **Auto-merge**: Enabled (--rebase)

## Key Learnings

1. **Validation belongs at the aggregation layer** — the individual `load_tier()` can only validate its own input; the aggregation layer `load_all_tiers()` must validate cross-cutting invariants (key == value.id).
2. **Reuse the same normalization** — copy the normalization from the individual loader verbatim to avoid false positives from capitalization or prefix differences.
3. **Use `tmp_path` for mismatch fixtures** — never add intentionally-broken fixtures to shared fixture directories if existing tests assert exact counts.
4. **Check docstring line length** — long test method names plus descriptive docstrings easily breach 100-char limits; shorten prose rather than the method name.

## Related Skills

- `fix-resource-prompt-consistency` — catching inconsistent field mapping at the aggregation layer (analogous pattern)
- `fix-yaml-config-propagation` — 4-stage pipeline tracing (YAML → parser → dataclass → executor)
- `validate-model-configs-fix-mode` — similar filename/field consistency validation for model configs
- `centralized-path-constants` — validation collocated with path logic
