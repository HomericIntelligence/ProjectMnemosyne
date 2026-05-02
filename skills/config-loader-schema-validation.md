---
name: config-loader-schema-validation
description: 'TRIGGER CONDITIONS: Fixing a config loader method that bypasses schema
  validation by calling _load_yaml() directly instead of routing through a validated
  loader method. Use when a load() merge path or similar aggregation method skips
  Pydantic validation on a required config file.'
category: architecture
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# config-loader-schema-validation

How to fix a ConfigLoader method that bypasses schema validation on a required config file by routing it through the validated loader method instead of calling the raw YAML loader directly.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-07 |
| Objective | Ensure `load()` in ConfigLoader applies Pydantic schema validation to defaults.yaml |
| Outcome | Success — routed through `load_defaults()`, removed duplicated dict-mapping logic |
| Issue | HomericIntelligence/ProjectScylla#1436 |
| PR | HomericIntelligence/ProjectScylla#1462 |

## When to Use

- A loader method that merges multiple config layers calls `_load_yaml()` on a required file directly instead of going through the dedicated typed loader method
- You need to ensure schema validation, filename consistency checks, and Pydantic model construction are uniformly applied
- A raw dict is being manually mapped to top-level keys when typed attribute access on a validated model would be simpler and safer

## Verified Workflow

### 1. Identify the bypass

Look for a pattern like this in the merge/load method:

```python
# BAD: bypasses schema validation
defaults_path = self.base_path / "config" / "defaults.yaml"
defaults_data = self._load_yaml(defaults_path)

# Manual key mapping from raw dict
if "evaluation" in defaults_data:
    eval_cfg = defaults_data["evaluation"]
    if "runs_per_eval" in eval_cfg:
        config_data["runs_per_tier"] = eval_cfg["runs_per_eval"]
```

### 2. Replace with the validated loader method

```python
# GOOD: routes through load_defaults() for schema validation
defaults = self.load_defaults()

config_data: dict[str, Any] = {
    "runs_per_tier": defaults.evaluation.runs_per_tier,
    "timeout_seconds": defaults.evaluation.timeout,
    "max_cost_usd": defaults.max_cost_usd,
    "judge": defaults.judge,
    "adapters": defaults.adapters,
    "cleanup": defaults.cleanup,
    "output": defaults.output,
    "logging": defaults.logging,
    "metrics": defaults.metrics,
}
```

The validated method (`load_defaults()`) already handles:
- Pydantic schema validation (field types, bounds, required fields)
- Filename consistency checks
- JSON schema validation
- `ConfigurationError` on missing or malformed file

### 3. Write tests covering the new validation path

Add a test class that confirms `load()` now participates in validation:

```python
class TestLoadMergedConfigSchemaValidation:
    def test_load_raises_on_invalid_defaults_schema(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        # runs_per_eval exceeds max of 100 — Pydantic should reject
        (config_dir / "defaults.yaml").write_text("evaluation:\n  runs_per_eval: 9999\n")

        loader = ConfigLoader(str(tmp_path))
        with pytest.raises(ConfigurationError, match="Invalid defaults configuration"):
            loader.load(test_id="any", model_id="any")

    def test_load_raises_on_missing_defaults(self, tmp_path: Path) -> None:
        loader = ConfigLoader(str(tmp_path))
        with pytest.raises(ConfigurationError, match="not found"):
            loader.load(test_id="any", model_id="any")
```

### 4. Watch for noqa comment stripping by ruff-format

If the original function had `# noqa: C901  # comment` on the `def` line, ruff-format may strip the `# noqa: C901` annotation (treating the comment as trailing context). After running pre-commit, check if the noqa tag survived:

```bash
pre-commit run --all-files
# If ruff-check reports E501 on the def line, restore the noqa tag manually:
# def load(...) -> ScyllaConfig:  # noqa: C901
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Files changed:**
- `scylla/config/loader.py` — replaced 30-line raw dict block with 12-line typed attribute dict
- `tests/unit/config/test_config_loader.py` — added `TestLoadMergedConfigSchemaValidation` (3 tests)

**Test counts (ProjectScylla):**
- Before: 4458 unit tests passing
- After: 4566 unit tests passing (+108 from this and concurrent work)
- Coverage: 75.84% (threshold: 75%)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | PR #1462, issue #1436 | Config loader defaults validation bypass fix |
