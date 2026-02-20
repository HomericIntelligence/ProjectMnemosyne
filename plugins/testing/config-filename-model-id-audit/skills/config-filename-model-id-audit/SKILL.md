---
name: "Config Filename / Model ID Audit"
description: "Audit and fix YAML config files where filename stems mismatch model_id fields"
category: testing
date: 2026-02-19
user-invocable: false
---
# Config Filename / Model ID Audit

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-02-19 |
| **Category** | testing |
| **Objective** | Audit all `config/models/*.yaml` files for filename/model_id mismatches and fix them |
| **Outcome** | ✅ SUCCESS — Renamed 3 files, zero validation warnings, 2214 tests pass |
| **Context** | Issue #732 — Follow-up from validation added in #692 |

## When to Use This Skill

Use this skill when:

- ✅ A filename/model_id validation was added and you need to audit existing files
- ✅ CI/logging emits warnings like `Config filename 'X.yaml' does not match model_id 'Y'`
- ✅ Model config files use short names (e.g., `claude-opus-4-5.yaml`) but `model_id` is versioned (e.g., `claude-opus-4-5-20251101`)
- ✅ You need to harden configs against silent lookup failures from ID mismatches

**Don't use when:**

- The mismatch is intentional (aliasing/shorthand config files)
- The validation logic is not yet in place (implement validation first)

## Verified Workflow

### 1. Discover Mismatches with Validation Script

Run the validation audit using the project's built-in loader:

```bash
pixi run python -c "
from scylla.config.loader import ConfigLoader
import logging
logging.basicConfig(level=logging.WARNING)
loader = ConfigLoader('.')
result = loader.load_all_models()
print('Loaded:', list(result.keys()))
"
```

**Expected warning format:**
```
WARNING:scylla.config.loader:Config filename 'claude-opus-4-5.yaml' does not match
model_id 'claude-opus-4-5-20251101'. Expected 'claude-opus-4-5-20251101.yaml'
```

> **Critical**: Pass `'.'` (project root), NOT `'config'`. The loader constructs
> `base_path / "config" / "models"` internally.

### 2. Rename Files with `git mv`

Use `git mv` (not `mv`) to preserve git history:

```bash
git mv config/models/claude-opus-4-5.yaml   config/models/claude-opus-4-5-20251101.yaml
git mv config/models/claude-sonnet-4-5.yaml config/models/claude-sonnet-4-5-20250929.yaml
git mv config/models/claude-haiku-4-5.yaml  config/models/claude-haiku-4-5-20250929.yaml
```

### 3. Verify Zero Warnings

Re-run the audit — expect no WARNING lines:

```bash
pixi run python -c "
from scylla.config.loader import ConfigLoader
import logging
logging.basicConfig(level=logging.WARNING)
loader = ConfigLoader('.')
result = loader.load_all_models()
print('Loaded:', list(result.keys()))
" 2>&1 | grep -v "^WARN "
```

### 4. Grep for Stale Model ID References in Source

Short-form IDs may be hard-coded elsewhere:

```bash
grep -rn "claude-opus-4-5[^-]" scylla/ --include="*.py"
grep -rn "claude-sonnet-4-5[^-]" scylla/ --include="*.py"
grep -rn "claude-haiku-4-5[^-]" scylla/ --include="*.py"
```

Update any found references to use the fully-qualified versioned ID.

### 5. Write Regression Tests

Create `tests/unit/config/test_loader.py`:

```python
import logging
from pathlib import Path

import pytest

from scylla.config.loader import ConfigLoader

_REPO_ROOT = Path(__file__).parent.parent.parent.parent


class TestLoadAllModels:
    def test_load_all_models_no_warnings(self, caplog: pytest.LogCaptureFixture) -> None:
        loader = ConfigLoader(_REPO_ROOT)
        with caplog.at_level(logging.WARNING, logger="scylla.config.loader"):
            models = loader.load_all_models()
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_messages == [], f"Unexpected validation warnings: {warning_messages}"
        assert len(models) > 0

    def test_all_models_have_matching_filename_and_model_id(self) -> None:
        loader = ConfigLoader(_REPO_ROOT)
        models = loader.load_all_models()
        for key, config in models.items():
            if key.startswith("_"):
                continue
            expected_stem = config.model_id.replace(":", "-")
            assert key == expected_stem

    @pytest.mark.parametrize("model_id", [
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20250929",
    ])
    def test_load_model_by_versioned_id(self, model_id: str) -> None:
        loader = ConfigLoader(_REPO_ROOT)
        config = loader.load_model(model_id)
        assert config is not None
        assert config.model_id == model_id

    @pytest.mark.parametrize("short_id", [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    ])
    def test_load_model_by_short_id_returns_none(self, short_id: str) -> None:
        loader = ConfigLoader(_REPO_ROOT)
        assert loader.load_model(short_id) is None
```

### 6. Run Full Test Suite and Pre-commit

```bash
pixi run python -m pytest tests/unit/ -v 2>&1 | tail -5
pre-commit run --all-files
```

### 7. Commit, Push, PR

```bash
git add config/models/ scylla/ tests/unit/config/test_loader.py
git commit -m "fix(config): rename model config files to match model_id

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push -u origin <branch>
gh pr create --title "fix(config): rename model config files to match model_id" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| `ConfigLoader('config')` | Double-wraps the path: looks for `config/config/models/` | Always pass `'.'` or the repo root |
| Running audit script without `2>&1` | WARNING goes to stderr, not stdout — missed by script | Pipe both stdout+stderr when checking output |

### ❌ Attempt 1: Wrong `ConfigLoader` base path

**What was tried:**
```bash
python -c "from scylla.config.loader import ConfigLoader; loader = ConfigLoader('config'); ..."
```

**Why it failed:**
- `ConfigLoader` constructs `base_path / "config" / "models"` internally
- Passing `'config'` as base results in `config/config/models/` which doesn't exist
- Returns empty dict with no warnings — looks like success but finds nothing

**Lesson:**
Always verify `base_path` resolves to the project root. Use `ConfigLoader('.')` or
`ConfigLoader(Path(__file__).parent.parent...)`.

## Results & Parameters

### Files Renamed

| Before | After | model_id |
|--------|-------|---------|
| `config/models/claude-opus-4-5.yaml` | `claude-opus-4-5-20251101.yaml` | `claude-opus-4-5-20251101` |
| `config/models/claude-sonnet-4-5.yaml` | `claude-sonnet-4-5-20250929.yaml` | `claude-sonnet-4-5-20250929` |
| `config/models/claude-haiku-4-5.yaml` | `claude-haiku-4-5-20250929.yaml` | `claude-haiku-4-5-20250929` |

### Test Results

| Metric | Value |
|--------|-------|
| New tests added | 9 |
| Total tests passing | 2214 |
| Coverage | 73.35% (threshold: 73%) |
| Pre-commit hooks | All pass |

### Source References Updated

| File | Line | Before | After |
|------|------|--------|-------|
| `scylla/cli/main.py` | 88 | `--model claude-opus-4-5` | `--model claude-opus-4-5-20251101` |
| `scylla/cli/main.py` | 337 | `judge_model="claude-opus-4-5"` | `judge_model="claude-opus-4-5-20251101"` |
| `scylla/executor/judge_container.py` | 37 | docstring `claude-opus-4-5` | `claude-opus-4-5-20251101` |

## Key Insights

### 1. Validation Warnings Are Actionable

When a validator emits WARNING-level messages (not errors), they surface mismatches
that won't cause crashes but lead to silent failures (e.g., `load_model("claude-opus-4-5")`
returns `None` when caller expects the config).

### 2. Test Files Prefixed with `_` Are Exempt

The validation logic in `validate_filename_model_id_consistency` skips files whose
stem starts with `_`. Test fixtures like `_test-model.yaml` are intentionally exempt.
Mirror this in regression tests.

### 3. `caplog` for Warning Assertions

Use pytest's `caplog` fixture to assert no unexpected WARNING-level logs:
```python
with caplog.at_level(logging.WARNING, logger="scylla.config.loader"):
    models = loader.load_all_models()
warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
assert warning_messages == []
```

### 4. `git mv` Preserves History

Always use `git mv` (not shell `mv`) when renaming tracked files.
This shows `renamed:` in `git status` instead of delete+add, preserving blame history.

## Related Skills

- `resolve-skipped-tests` — Related pattern: fix underlying config issues
- `fix-tests-after-config-refactor` — Update test fixtures after structural changes
- `issue-preflight-check` — Verify issue context before starting work
