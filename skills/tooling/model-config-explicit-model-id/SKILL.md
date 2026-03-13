# Skill: model-config-explicit-model-id

## Overview

| Field     | Value                                                             |
|-----------|-------------------------------------------------------------------|
| Date      | 2026-02-20                                                        |
| Issue     | #794                                                              |
| PR        | #839                                                              |
| Objective | Ensure `claude-opus-4-1.yaml` explicitly declares `model_id` and remove incorrect comment |
| Outcome   | Success — comment removed, model_id already explicit, 2266 tests pass |

## When to Use

- A `config/models/*.yaml` file is missing an explicit `model_id` field (loader was silently injecting it from the filename)
- A model YAML has a verbose/incorrect comment block about naming conventions that contradicts the project pattern
- Follow-up audit after a batch rename of model config files (e.g. post-#732)
- Investigating "silent inconsistency" where loader injects fields without user awareness

## Verified Workflow

### 1. Read the issue and check current file state

Before writing any code, read the YAML file to see if the `model_id` field is already declared. The issue may describe the *original* state at filing time, not the current state. If a previous PR (e.g. #732) already partially fixed the file, confirm what still needs doing.

```bash
cat config/models/claude-opus-4-1.yaml
```

### 2. Check loader injection code

Verify the loader's "inject model_id from filename" fallback at `scylla/config/loader.py`:

```python
# scylla/config/loader.py:277-278
if "model_id" not in data:
    data["model_id"] = model_id
```

If the YAML already has `model_id`, the loader does not inject it — no silent inconsistency remains.

### 3. Identify residual problem: incorrect comment

Even with `model_id` explicitly declared, `claude-opus-4-1.yaml` had a 7-line comment block claiming:

```yaml
# The filename MUST match the model_id field for ConfigLoader resolution.
```

This is incorrect. All other model files use versioned `model_id` values with simplified filenames (e.g. `claude-opus-4-5-20251101.yaml` with `model_id: "claude-opus-4-5-20251101"`). The comment was added when the filename/model_id coincidentally matched and is misleading.

### 4. Minimal fix: remove the incorrect comment block

Remove only the incorrect header comment block. Leave `model_id` and all other fields untouched.

**Before:**

```yaml
# Claude Opus 4.1 (Legacy) Model Configuration
#
# File naming convention:
#   - Filename: {model_id}.yaml (e.g., claude-opus-4-1.yaml)
#   - model_id: API identifier from provider (e.g., "claude-opus-4-1")
#   - name: Human-readable display name (e.g., "Claude Opus 4.1")
#
# The filename MUST match the model_id field for ConfigLoader resolution.
model_id: "claude-opus-4-1"
```

**After:**

```yaml
# Claude Opus 4.1 (Legacy) Model Configuration
model_id: "claude-opus-4-1"
```

### 5. Verify no validation warnings

```bash
pixi run python -m pytest tests/unit/config/test_loader.py -v
```

Key tests:

- `test_load_all_models_no_warnings` — confirms zero `logging.WARNING` records when loading all models
- `test_load_model_by_versioned_id[claude-opus-4-1]` — confirms the model loads with its declared `model_id`

### 6. Run full test suite

```bash
pixi run python -m pytest tests/ -v
```

The coverage failure (`3.29% < 73%`) when running `tests/unit/config/test_loader.py` alone is expected — the coverage threshold is computed across the entire codebase. Always run `tests/` (full suite) for final verification.

## Failed Attempts

### Checking for a versioned date suffix

The issue offered two resolution paths:

1. Explicitly declare `model_id: claude-opus-4-1`
2. Rename to `claude-opus-4-1-<date>.yaml` once the correct versioned API model ID is confirmed

Web search was unavailable to confirm the Anthropic API date suffix for `claude-opus-4-1`. Since option 1 was already satisfied (the field was present), option 2 was deferred — **do not rename** without confirming the exact versioned API identifier via Anthropic docs or API responses.

### Searching for versioned ID in codebase

No codebase references confirmed a `claude-opus-4-1-<date>` variant. The test in `tests/unit/config/test_loader.py:44-59` explicitly parametrizes `"claude-opus-4-1"` (not a versioned form) as the expected loadable ID, which confirmed option 1 was the correct resolution.

## Results & Parameters

| Metric           | Value                                  |
|------------------|----------------------------------------|
| Lines changed    | -7 (comment block removed)             |
| Tests passing    | 2266 / 2266                            |
| Pre-commit hooks | All passed (YAML lint, validate-model-config-naming) |
| PR               | #839                                   |
| Issue            | #794 (follow-up to #732)               |

## Pattern: Audit Model Config Consistency

When auditing model config files for `model_id` consistency, apply this checklist per file:

| Check | Command |
|-------|---------|
| Has explicit `model_id` field? | `grep "model_id" config/models/<file>.yaml` |
| Filename stem matches `model_id`? | Check `validate_filename_model_id_consistency()` rules |
| No misleading comments? | Read file header |
| No validation warnings? | `pixi run python -m pytest tests/unit/config/test_loader.py::TestLoadAllModels::test_load_all_models_no_warnings` |
