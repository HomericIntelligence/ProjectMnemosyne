---
name: model-id-normalization-resume-fix
description: "Add model ID normalization via Pydantic field_validator to handle legacy dot-notation and short aliases in saved experiment configs. Use when: (1) model IDs with old naming conventions persist in saved experiment configs and cause CLI failures on resume, (2) CLI argument defaults use short aliases with no expansion function."
category: architecture
date: 2026-03-24
version: "1.0.0"
user-invocable: false
tags:
  - model-ids
  - pydantic
  - normalization
  - resume
  - backward-compatibility
---

# Model ID Normalization for Experiment Resume

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-24 |
| **Issue** | Judge failures on experiment resume due to old model IDs in saved config |
| **PR** | #1541 |
| **Objective** | Add model ID normalization so old dot-notation and short aliases resolve to canonical full IDs |
| **Outcome** | Success — 4800 tests passing, 81.71% coverage, 1660 data files fixed |
| **Category** | architecture |

## When to Use

- Saved experiment configs contain model IDs from a prior naming convention (e.g., `opus-4.6` instead of `claude-opus-4-6`)
- CLI argument defaults use short aliases (e.g., `"sonnet"`) that are passed directly to the Claude CLI without expansion
- `ExperimentConfig.load()` on resume reads stale model IDs from `config/experiment.json`
- Any scenario where model IDs flow through multiple layers (CLI → config → checkpoint → judge) and need a single normalization chokepoint

## Verified Workflow

### Quick Reference

```python
# 1. Add normalize_model_id() to constants.py (zero scylla.* imports)
MODEL_ID_ALIASES: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5",
    "opus-4.6": "claude-opus-4-6",
    "sonnet-4.6": "claude-sonnet-4-6",
    "haiku-4.5": "claude-haiku-4-5",
}

def normalize_model_id(model_id: str) -> str:
    normalized = model_id.strip().lower()
    return MODEL_ID_ALIASES.get(normalized, model_id)

# 2. Add Pydantic field_validator on ExperimentConfig (the single chokepoint)
@field_validator("models", mode="before")
@classmethod
def _normalize_models(cls, v: list[str]) -> list[str]:
    return [normalize_model_id(m) for m in v]

# 3. Update CLI defaults to use centralized constants
parser.add_argument("--model", default=DEFAULT_AGENT_MODEL)
parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
```

### Detailed Steps

1. **Add `normalize_model_id()` to `scylla/config/constants.py`**: This module has zero `scylla.*` imports (enforced by test). The function maps short aliases and legacy dot-notation to canonical full IDs. Unknown IDs pass through — validation catches them later.

2. **Add Pydantic `field_validator` on `ExperimentConfig.models` and `judge_models`**: Use `mode="before"` so normalization runs before other validation. This is the single chokepoint — catches both fresh experiments (`ExperimentConfig(models=[...])`) and resumed ones (`ExperimentConfig.load()` at `runner.py:259`).

3. **Update CLI defaults in `manage_experiment.py`**: Change `default="sonnet"` to `default=DEFAULT_AGENT_MODEL` and `default=DEFAULT_JUDGE_MODEL`. Also add `normalize_model_id()` calls at CLI entry points for model validation that happens before `ExperimentConfig` construction.

4. **Normalize `--add-judge` entries**: Each `--add-judge` value must also pass through `normalize_model_id()` before dedup checks and validation.

5. **Export from `scylla/config/__init__.py`**: Add `normalize_model_id` to imports and `__all__` (sorted — ruff enforces `RUF022`).

6. **Fix saved experiment data**: Run a one-time Python script to walk all JSON files in the experiment directory, recursively replace old model ID strings, and re-save.

7. **Update test expectations**: Tests asserting `["sonnet", "opus"]` now expect `["claude-sonnet-4-6", "claude-opus-4-6"]`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Prior commit 8717d9ba | Updated model ID constants and YAML files to new naming convention | Old IDs baked into saved `experiment.json` survived — no normalization on load | Renaming constants is not enough when serialized configs persist on disk. Must add normalization at the deserialization boundary. |
| Prior commit 079a9926 | Added model validation that calls Claude CLI to check model IDs | Short aliases like `"sonnet"` failed validation because no expansion function existed, and the error message implied aliases were supported | If error messages mention a feature (short aliases), the feature must actually be implemented. |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Files changed | 8 |
| Tests added | 15 (11 normalize + 4 ExperimentConfig) |
| Tests updated | 7 assertions |
| Total tests | 4800 passing |
| Coverage | 81.71% (threshold: 75%) |
| Data files fixed | 1660 JSON files |
| Pre-commit hooks | All passing |

### Key Architecture Decisions

1. **Normalization in `constants.py`**: Zero `scylla.*` imports ensures no circular import risk. Enforced by existing test (`test_constants_module_has_no_scylla_imports`).

2. **Pydantic `field_validator` as the chokepoint**: `ExperimentConfig` is the single class through which all model IDs pass — both from CLI construction and from `ExperimentConfig.load()`. One validator catches both paths. No scatter-gunning across call sites.

3. **Unknown IDs pass through**: `normalize_model_id()` does NOT raise on unknown model IDs. The existing `validate_model()` function in `model_validation.py` handles rejection by calling the Claude CLI. This keeps normalization simple and decoupled from validation.

4. **Data fix is separate from code fix**: The one-time script to update saved JSON files is not committed to the repo — it's a migration, not ongoing code.

### Root Cause Chain

```
Experiment launched (March 18) with old model IDs
  → config/experiment.json saved with "opus-4.6", "sonnet-4.6", "haiku-4.5"
    → Commit 8717d9ba (March 23) updated constants but not saved configs
      → On resume, runner.py:259 loads ExperimentConfig from saved JSON
        → Old IDs passed to Claude CLI → "model not found" errors
          → All judges fail → zero-score consensus for every run
```

### Files Modified

| File | Change |
|------|--------|
| `scylla/config/constants.py` | Added `MODEL_ID_ALIASES`, `normalize_model_id()` |
| `scylla/config/__init__.py` | Exported `normalize_model_id` |
| `scylla/e2e/models.py` | Added `field_validator` on `models`, `judge_models` |
| `scripts/manage_experiment.py` | Changed CLI defaults, added normalization at entry points |
| `tests/unit/config/test_constants.py` | Added `TestNormalizeModelId` (11 tests) |
| `tests/unit/e2e/test_models.py` | Added `TestExperimentConfigModelNormalization` (4 tests) |
| `tests/unit/e2e/test_manage_experiment_run.py` | Updated 5 assertions |
| `tests/unit/e2e/test_manage_experiment_cli.py` | Updated 2 assertions |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Model ID normalization for experiment resume | PR #1541 |
