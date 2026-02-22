# Skill: centralize-model-id-constants

## Overview

| Field       | Value                                                                              |
|-------------|------------------------------------------------------------------------------------|
| Date        | 2026-02-22                                                                         |
| Issue       | #851                                                                               |
| PR          | #974                                                                               |
| Objective   | Replace 9+ hardcoded model-ID string literals with a shared `constants.py` module |
| Outcome     | Success — single source of truth, all 2442 tests passing, 74.17% coverage         |
| Category    | architecture                                                                       |

## When to Use

Trigger this skill when:

- A grep finds model-ID literals (e.g. `"claude-sonnet-4-5-20250929"`, `"claude-opus-4-5-20251101"`)
  in **multiple source layers** (executor, judge, e2e, config, CLI) — not just the CLI/orchestrator
- A prior partial refactor (e.g. #793/#838) addressed CLI-level literals but missed executor/judge/e2e layers
- An audit issue lists 7+ locations that need the same constant
- The codebase has both an agent model and a judge model that are independently hardcoded

**Contrast with `config-default-model-drift`**: That skill uses `config/defaults.yaml` + Pydantic
`DefaultsConfig` for runtime overrides. This skill uses a `constants.py` module for a zero-dependency,
import-time constant that can be referenced from any layer without loading YAML.

## Verified Workflow

### 1. Scope the hardcoded literals

```bash
grep -rn "claude-sonnet\|claude-opus" scylla/ --include="*.py" \
  | grep -v "\.py:#\|>>>\|docstring\|help=\|description=\|example"
```

Categorize each hit as:
- **Functional default** (Pydantic `Field(default=...)`, dataclass field, function parameter default,
  runtime fallback in `data.get(...)`) → **replace with constant**
- **Documentation** (docstring example, help text, comment, pricing dict key) → **leave as-is**

### 2. Create `scylla/config/constants.py`

```python
"""Shared constants for ProjectScylla configuration.

This module is the single source of truth for default model IDs.
Import from here rather than hardcoding model strings at call sites.
"""

DEFAULT_AGENT_MODEL: str = "claude-sonnet-4-5-20250929"
DEFAULT_JUDGE_MODEL: str = "claude-opus-4-5-20251101"
```

**Critical**: No `scylla.*` imports in this file. Only stdlib-safe constants → zero circular import risk.

### 3. Export from `scylla/config/__init__.py`

```python
# Add at top of imports, before .loader and .models
from .constants import DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL

# Add to __all__
__all__ = [
    # Constants
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_JUDGE_MODEL",
    # ... rest of exports
]
```

### 4. Update each functional location

For each site, add the import and replace the literal:

```python
# executor/agent_container.py — dataclass field
from scylla.config.constants import DEFAULT_AGENT_MODEL
model: str = DEFAULT_AGENT_MODEL

# executor/judge_container.py — dataclass field
from scylla.config.constants import DEFAULT_JUDGE_MODEL
judge_model: str = DEFAULT_JUDGE_MODEL

# config/models.py — Pydantic Field (import alongside existing imports)
from scylla.config.constants import DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL
model: str = Field(default=DEFAULT_JUDGE_MODEL)          # JudgeConfig
default_model: str = Field(default=DEFAULT_JUDGE_MODEL)  # DefaultsConfig

# e2e/models.py — Pydantic Field with default_factory
from scylla.config.constants import DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL
models: list[str] = Field(default_factory=lambda: [DEFAULT_AGENT_MODEL])
judge_models: list[str] = Field(default_factory=lambda: [DEFAULT_JUDGE_MODEL])
# Also in .load() classmethod:
models=data.get("models", [DEFAULT_AGENT_MODEL]),
judge_models=data.get("judge_models", [DEFAULT_JUDGE_MODEL]),

# e2e/llm_judge.py — function parameter default
from scylla.config.constants import DEFAULT_JUDGE_MODEL
def run_llm_judge(..., model: str = DEFAULT_JUDGE_MODEL, ...):

# e2e/regenerate.py — runtime fallback
from scylla.config.constants import DEFAULT_JUDGE_MODEL
config.judge_models[0] if config.judge_models else DEFAULT_JUDGE_MODEL

# judge/evaluator.py — Pydantic Field
from scylla.config.constants import DEFAULT_JUDGE_MODEL
model: str = Field(default=DEFAULT_JUDGE_MODEL)

# cli/main.py — ReportData construction
from scylla.config import ConfigLoader, DEFAULT_JUDGE_MODEL
judge_model=DEFAULT_JUDGE_MODEL,
```

### 5. Write tests in `tests/unit/config/test_constants.py`

```python
"""Tests for scylla.config.constants module."""

import scylla.config.constants as constants_module
from scylla.config import DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL
from scylla.config.constants import DEFAULT_AGENT_MODEL as AGENT_MODEL_DIRECT
from scylla.config.constants import DEFAULT_JUDGE_MODEL as JUDGE_MODEL_DIRECT


class TestConstantsImportable:
    """Verify constants are importable from both the module and the package."""

    def test_importable_from_package(self) -> None:
        """Constants exported from scylla.config package are not None."""
        assert DEFAULT_AGENT_MODEL is not None
        assert DEFAULT_JUDGE_MODEL is not None

    def test_importable_from_module(self) -> None:
        """Constants importable directly from scylla.config.constants."""
        assert AGENT_MODEL_DIRECT is not None
        assert JUDGE_MODEL_DIRECT is not None

    def test_package_and_module_values_match(self) -> None:
        """Package re-export values match the module-level constants."""
        assert DEFAULT_AGENT_MODEL == AGENT_MODEL_DIRECT
        assert DEFAULT_JUDGE_MODEL == JUDGE_MODEL_DIRECT


class TestConstantValues:
    """Verify constant values are valid model ID strings."""

    def test_default_agent_model_is_string(self) -> None:
        """DEFAULT_AGENT_MODEL is a str instance."""
        assert isinstance(DEFAULT_AGENT_MODEL, str)

    def test_default_judge_model_is_string(self) -> None:
        """DEFAULT_JUDGE_MODEL is a str instance."""
        assert isinstance(DEFAULT_JUDGE_MODEL, str)

    def test_default_agent_model_contains_sonnet(self) -> None:
        """DEFAULT_AGENT_MODEL identifies a Sonnet-family model."""
        assert "sonnet" in DEFAULT_AGENT_MODEL.lower()

    def test_default_judge_model_contains_opus(self) -> None:
        """DEFAULT_JUDGE_MODEL identifies an Opus-family model."""
        assert "opus" in DEFAULT_JUDGE_MODEL.lower()


class TestNoCircularImports:
    """Verify constants.py has no scylla.* imports (prevents circular imports)."""

    def test_constants_module_has_no_scylla_imports(self) -> None:
        """constants.py must only use stdlib; no scylla.* imports allowed."""
        import inspect
        source = inspect.getsource(constants_module)
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert not stripped.startswith("from scylla"), (
                f"constants.py must not import from scylla.*: {line!r}"
            )
            assert not stripped.startswith("import scylla"), (
                f"constants.py must not import scylla.*: {line!r}"
            )
```

Note: ruff enforces `D102` (docstrings on public methods in test classes). Add a one-line docstring
to every test method or the pre-commit hook will fail.

### 6. Verify with grep

```bash
grep -rn "claude-sonnet-4-5-20250929\|claude-opus-4-5-20251101" scylla/ --include="*.py" \
  | grep -v "constants.py\|pricing.py\|#\|>>>\|help=\|\.yaml\|docstring"
```

Expected: zero results (only pricing dict keys and docstring examples remain).

### 7. Run pre-commit and tests

```bash
pre-commit run --files <all changed files>
pixi run python -m pytest tests/unit/ -v
```

## Failed Attempts

### Ruff D102 — missing docstrings on test methods

**What happened**: Initial test file had no per-method docstrings. Pre-commit ruff hook failed with
10 `D102 Missing docstring in public method` errors (one per test method in a class).

**Fix**: Add a one-line docstring to every test method. Test *classes* already had class docstrings
but ruff requires method-level docstrings too when the `D102` rule is enabled.

```python
# Wrong (fails ruff D102)
def test_importable_from_package(self) -> None:
    assert DEFAULT_AGENT_MODEL is not None

# Correct
def test_importable_from_package(self) -> None:
    """Constants exported from scylla.config package are not None."""
    assert DEFAULT_AGENT_MODEL is not None
```

### Import ordering — constants before loader/models

**What happened**: First attempt added the `from .constants import ...` line after `.models`.
Ruff reordered it alphabetically (`.constants` < `.loader` < `.models`), which also happens to be
the correct dependency order (constants has no deps, so importing it first is safe).

**Takeaway**: Always add stdlib-only constant modules as the first local import in `__init__.py`.

## Results & Parameters

| Parameter          | Value                                  |
|--------------------|----------------------------------------|
| Files changed      | 11                                     |
| Files created      | 2 (`constants.py`, `test_constants.py`) |
| Tests added        | 10                                     |
| Total tests        | 2442 (all passing)                     |
| Coverage           | 74.17% (threshold: 73%)                |
| Pre-commit hooks   | All passing                            |
| Hardcoded literals | 9 functional replacements              |

### Files Modified

| File                                    | Change                                              |
|-----------------------------------------|-----------------------------------------------------|
| `scylla/config/constants.py`            | **New** — `DEFAULT_AGENT_MODEL`, `DEFAULT_JUDGE_MODEL` |
| `tests/unit/config/test_constants.py`   | **New** — 10 tests                                 |
| `scylla/config/__init__.py`             | Export both constants                               |
| `scylla/config/models.py`              | `JudgeConfig.model`, `DefaultsConfig.default_model` |
| `scylla/executor/agent_container.py`    | `AgentContainerConfig.model`                        |
| `scylla/executor/judge_container.py`    | `JudgeContainerConfig.judge_model`                  |
| `scylla/e2e/models.py`                 | `ExperimentConfig` Field defaults + `load()` fallbacks |
| `scylla/e2e/llm_judge.py`              | `run_llm_judge()` parameter default                 |
| `scylla/e2e/regenerate.py`             | `effective_judge_model` fallback                    |
| `scylla/judge/evaluator.py`            | `JudgeConfig.model` Field default                   |
| `scylla/cli/main.py`                   | `ReportData.judge_model` value                      |

## Key Insights

1. **Two separate constants, not one**: The codebase has two distinct model roles — agent (Sonnet)
   and judge (Opus). Define `DEFAULT_AGENT_MODEL` and `DEFAULT_JUDGE_MODEL` separately; do not
   collapse to a single `DEFAULT_MODEL`.

2. **Docstring/data vs functional**: Pricing dict keys (`"claude-opus-4-5-20251101": ModelPricing(...)`)
   and docstring examples are intentionally left as literals. Replacing them with the constant would
   make the pricing dict non-literal and reduce readability without reducing fragility.

3. **Coverage gate interaction**: Running `pytest tests/unit/config/test_constants.py` alone triggers
   the coverage gate (3% vs 73% threshold) and fails. Run the full `tests/unit/` suite to validate.

4. **`config/models.py` circular import risk**: Adding `from scylla.config.constants import ...`
   inside `scylla/config/models.py` is safe because `constants.py` imports nothing from `scylla.*`.
   The dependency graph is: `constants.py` (stdlib only) → imported by `models.py`.

5. **Relation to `config-default-model-drift` skill**: The earlier skill addressed CLI-level literals
   using YAML config. This skill addresses the remaining executor/judge/e2e layer literals using a
   Python constants module. Both approaches coexist: `defaults.yaml` controls runtime model selection;
   `constants.py` provides the in-code fallback when no config is loaded.
