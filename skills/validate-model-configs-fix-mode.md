---
name: validate-model-configs-fix-mode
description: "Use when: (1) adding --fix mode to a validation script that renames
  YAML files to match their model_id field; (2) centralizing hardcoded model-ID string
  literals into a shared constants.py module across executor/judge/e2e/config layers;
  (3) promoting a runtime validation warning to a hard pre-commit gate by reusing
  existing validation.py logic."
category: tooling
date: 2026-01-01
version: 2.0.0
user-invocable: false
tags:
  - model-id
  - constants
  - validation
  - pre-commit
  - fix-mode
  - consistency
---
# Skill: Validate Model Configs — Fix Mode, Centralized Constants & Consistency Hook

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-02-20 |
| **Category** | tooling |
| **Objective** | (1) Add `--fix` mode to validation script that renames YAML files to match `model_id`; (2) replace 9+ hardcoded model-ID literals with shared `constants.py`; (3) promote runtime warning to pre-commit gate |
| **Outcome** | ✅ Fix-mode script + 26 tests; ✅ constants.py single source of truth, 2442 tests passing; ✅ consistency hook blocks mismatching commits, 16 tests |
| **Context** | Issues #776 (fix mode), #851 (constants), #792 (hook); PRs #823, #974, #837 |
| **Absorbed** | centralize-model-id-constants (v1.0.0), enforce-model-config-consistency-hook (v1.0.0) on 2026-05-03 |

## When to Use This Skill

Use this skill when:

- ✅ A validation script only detects problems but can't auto-fix them
- ✅ You need to add a `--fix` flag that renames/patches files based on detected mismatches
- ✅ The fix involves a rename that could collide with an existing file
- ✅ You need interactive `[y/N]` confirmation with a `--yes` bypass for automation
- ✅ The fix script must integrate with existing validation helpers in `scylla/`
- ✅ A grep finds model-ID literals (e.g. `"claude-sonnet-4-5-20250929"`, `"claude-opus-4-5-20251101"`) in **multiple source layers** (executor, judge, e2e, config, CLI) — not just the CLI/orchestrator
- ✅ A prior partial refactor addressed CLI-level literals but missed executor/judge/e2e layers
- ✅ An audit issue lists 7+ locations that need the same constant
- ✅ The codebase has both an agent model and a judge model that are independently hardcoded
- ✅ You have a Python validation function that emits warnings at load time and need to block commits instead
- ✅ You want a pre-commit hook that delegates to existing library code rather than reimplementing logic
- ✅ You're adding a second CI check that enforces stricter rules than an existing check
- ✅ The existing validation is in `scylla/` and you want to call it from a `scripts/` entry point

**Don't use when:**

- The fix operation is destructive and cannot be safely checked for collisions
- The validation logic doesn't already exist in `scylla/config/validation.py`

**Contrast with `config-default-model-drift`**: That skill uses `config/defaults.yaml` + Pydantic
`DefaultsConfig` for runtime overrides. This skill uses a `constants.py` module for a zero-dependency,
import-time constant that can be referenced from any layer without loading YAML.

## Verified Workflow

### Part A — Add `--fix` Mode to Validation Script

#### 1. Locate Existing Validation Primitives

```bash
# Find existing validation helpers to reuse
grep -r "validate_filename" scylla/config/
# → scylla/config/validation.py: validate_filename_model_id_consistency, get_expected_filename
```

#### 2. Structure the Script

Key design decisions:
- **Separate concerns**: `_load_model_id`, `_collect_mismatches`, `_confirm_rename`, `_fix_mismatch`, `main()`
- **Exit codes**: 0 (clean/fixed), 1 (mismatches without --fix), 2 (I/O error or collision)
- **Collision guard**: check `target.exists()` before `Path.rename()` and return False if collision
- **Skip = not error**: user declining a rename returns `True` (not a failure)

```python
def _fix_mismatch(current: Path, target: Path, yes: bool) -> bool:
    if target.exists():
        print(f"ERROR: Cannot rename {current.name} → {target.name}: target already exists.", ...)
        return False
    print(f"Renaming: {current} → {target}")
    if not yes and not _confirm_rename(current, target):
        print(f"Skipped: {current.name}")
        return True  # Skipped is not an error
    current.rename(target)
    return True
```

#### 3. Module-Level Default Path (avoids import-time failure in tests)

```python
_REPO_ROOT = get_repo_root()
_CONFIG_MODELS_DIR = _REPO_ROOT / "config" / "models"

parser.add_argument("--models-dir", type=Path, default=_CONFIG_MODELS_DIR, ...)
```

#### 4. Test File Location for scripts/

Scripts live in `scripts/` (not a Python package). Tests must add the directory to `sys.path`:

```python
_SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_model_configs import _collect_mismatches, _fix_mismatch, main
```

Test file goes in `tests/unit/scripts/test_validate_model_configs.py` with `__init__.py`.

#### 5. Pre-commit Compliance

Ruff enforces D101/D102 (docstrings for public classes and methods) even in test files.
Every test class and test method needs a one-line docstring:

```python
class TestFixMismatch:
    """Tests for _fix_mismatch rename executor."""

    def test_renames_file_when_yes(self, tmp_path: Path) -> None:
        """Renames file without prompting when yes=True."""
        ...
```

#### 6. Verify Full Pre-commit Pass

```bash
pre-commit run --files scripts/validate_model_configs.py \
    tests/unit/scripts/test_validate_model_configs.py \
    tests/unit/scripts/__init__.py
```

All hooks must pass (Ruff Format, Ruff Check, Mypy, Trim Whitespace, etc.).

### Part B — Centralize Model ID Constants

#### 1. Scope the Hardcoded Literals

```bash
grep -rn "claude-sonnet\|claude-opus" scylla/ --include="*.py" \
  | grep -v "\.py:#\|>>>\|docstring\|help=\|description=\|example"
```

Categorize each hit as:
- **Functional default** (Pydantic `Field(default=...)`, dataclass field, function parameter default,
  runtime fallback in `data.get(...)`) → **replace with constant**
- **Documentation** (docstring example, help text, comment, pricing dict key) → **leave as-is**

#### 2. Create `scylla/config/constants.py`

```python
"""Shared constants for ProjectScylla configuration.

This module is the single source of truth for default model IDs.
Import from here rather than hardcoding model strings at call sites.
"""

DEFAULT_AGENT_MODEL: str = "claude-sonnet-4-5-20250929"
DEFAULT_JUDGE_MODEL: str = "claude-opus-4-5-20251101"
```

**Critical**: No `scylla.*` imports in this file. Only stdlib-safe constants → zero circular import risk.

#### 3. Export from `scylla/config/__init__.py`

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

#### 4. Update Each Functional Location

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

#### 5. Write Tests in `tests/unit/config/test_constants.py`

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

#### 6. Verify with grep

```bash
grep -rn "claude-sonnet-4-5-20250929\|claude-opus-4-5-20251101" scylla/ --include="*.py" \
  | grep -v "constants.py\|pricing.py\|#\|>>>\|help=\|\.yaml\|docstring"
```

Expected: zero results (only pricing dict keys and docstring examples remain).

#### 7. Run pre-commit and tests

```bash
pre-commit run --files <all changed files>
pixi run python -m pytest tests/unit/ -v
```

### Part C — Consistency Pre-commit Hook

#### 1. Identify the Existing Validation Function

The runtime warning lives in `scylla/config/validation.py`:

```python
def validate_filename_model_id_consistency(config_path: Path, model_id: str) -> list[str]:
    """Returns list of warning strings; empty means valid."""
    ...
```

The goal is to call this function from a `scripts/` entry point and exit 1 if any warnings are returned.

#### 2. Write a Thin Wrapper Script in `scripts/`

The script must add the repo root to `sys.path` before importing from `scylla/` — pre-commit
does not guarantee the repo root is on `sys.path`:

```python
# scripts/check_model_config_consistency.py
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scylla.config.validation import validate_filename_model_id_consistency
```

The script then:

1. Finds `*.yaml` files in `config/models/`, skipping `_`-prefixed fixtures
2. Loads `model_id` with `yaml.safe_load`
3. Calls `validate_filename_model_id_consistency(config_file, model_id)`
4. Collects all warning strings; exits 1 if any are non-empty

#### 3. Add the Pre-commit Hook Using `pixi run`

Because the script imports from `scylla/`, it must run inside the pixi environment:

```yaml
# .pre-commit-config.yaml
- id: check-model-config-consistency
  name: Check Model Config Filename/model_id Consistency
  description: Fails if any config/models/*.yaml filename does not match its model_id field (uses scylla.config.validation)
  entry: pixi run python scripts/check_model_config_consistency.py
  language: system
  files: ^config/models/.*\.yaml$
  pass_filenames: false
```

**Key details:**

- `pixi run python ...` rather than plain `python ...` ensures the venv with `pyyaml` and project packages is active
- `pass_filenames: false` — the script scans the directory itself, not individual changed files
- `files: ^config/models/.*\.yaml$` — only trigger when model configs change

#### 4. Distinguish from the Existing `validate-model-configs` Hook

There are now two complementary hooks:

| Hook | Script | Logic | Purpose |
| ------ | -------- | ------- | --------- |
| `validate-model-configs` | `validate_model_configs.py` | Prefix match (`stem` is prefix of `model_id`) | Allows date-stamp suffixes |
| `check-model-config-consistency` | `check_model_config_consistency.py` | Exact or `:` → `-` normalization (from `validation.py`) | Enforces load-time contract |

Both hooks are complementary; the second is stricter for the load-time semantics.

#### 5. Test Structure for Consistency Hook

Tests go in `tests/unit/scripts/test_check_model_config_consistency.py`.
Use `tmp_path` and a `write_yaml` helper. Cover:

- Clean pass (exit 0)
- Mismatch (exit 1)
- Multiple mismatches all reported
- `_`-prefixed fixtures skipped
- Empty directory (exit 0)
- Non-existent directory (exit 1)
- Missing `model_id` field (exit 1)
- Invalid YAML (exit 1)
- Parametrized valid patterns
- `--verbose` prints passing file names

```python
def write_yaml(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(textwrap.dedent(content))
    return path
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fix-mode script (canonical) | Direct approach worked first try | N/A — solution was straightforward | Reusing existing `validate_filename` primitives from `scylla/config/validation.py` avoids reimplementing logic; collision guard + skip-not-error pattern is sufficient |
| Constants centralization (centralize-model-id-constants) | Direct approach worked first try | N/A — solution was straightforward | Running only the new test file triggers the coverage gate (3% vs 73% threshold); always run the full `tests/unit/` suite to validate |
| Consistency hook (enforce-model-config-consistency-hook) | Direct approach worked first try | N/A — solution was straightforward | `pixi run python ...` is required (not plain `python`) to ensure the venv with `pyyaml` and project packages is active for pre-commit hooks |
## Results & Parameters

### Fix-Mode Script

```
scripts/validate_model_configs.py
tests/unit/scripts/__init__.py
tests/unit/scripts/test_validate_model_configs.py
```

```
26 tests collected — 26 passed in 0.16s
All pre-commit hooks: PASSED
```

```
python scripts/validate_model_configs.py [--fix] [--yes] [--models-dir PATH] [--verbose]

Exit codes:
  0  All configs OK (or all fixes applied)
  1  Mismatches found, --fix not passed
  2  Collision or I/O error during fix
```

| Test Class | Scenarios Covered |
| ------------ | ------------------ |
| `TestLoadModelId` | valid file, missing field, bad YAML, non-dict YAML |
| `TestCollectMismatches` | no mismatch, mismatch, underscore skip, no model_id, multiple, colon normalize |
| `TestConfirmRename` | y, n, empty, uppercase N |
| `TestFixMismatch` | yes=True rename, interactive confirm, user denial (no error), collision |
| `TestMain` | exit 0, exit 1, fix+yes, collision, missing dir, underscore-skip, verbose, interactive |

### Constants Centralization

| Parameter | Value |
| -------------------- | ---------------------------------------- |
| Files changed | 11 |
| Files created | 2 (`constants.py`, `test_constants.py`) |
| Tests added | 10 |
| Total tests | 2442 (all passing) |
| Coverage | 74.17% (threshold: 73%) |
| Pre-commit hooks | All passing |
| Hardcoded literals | 9 functional replacements |

| File | Change |
| ----------------------------------------- | ----------------------------------------------------- |
| `scylla/config/constants.py` | **New** — `DEFAULT_AGENT_MODEL`, `DEFAULT_JUDGE_MODEL` |
| `tests/unit/config/test_constants.py` | **New** — 10 tests |
| `scylla/config/__init__.py` | Export both constants |
| `scylla/config/models.py` | `JudgeConfig.model`, `DefaultsConfig.default_model` |
| `scylla/executor/agent_container.py` | `AgentContainerConfig.model` |
| `scylla/executor/judge_container.py` | `JudgeContainerConfig.judge_model` |
| `scylla/e2e/models.py` | `ExperimentConfig` Field defaults + `load()` fallbacks |
| `scylla/e2e/llm_judge.py` | `run_llm_judge()` parameter default |
| `scylla/e2e/regenerate.py` | `effective_judge_model` fallback |
| `scylla/judge/evaluator.py` | `JudgeConfig.model` Field default |
| `scylla/cli/main.py` | `ReportData.judge_model` value |

### Consistency Hook

| Metric | Value |
| ---------------------- | --------------------------------------------- |
| Tests added | 16 |
| Hook ID | `check-model-config-consistency` |
| Hook trigger | `^config/models/.*\.yaml$` |
| Validation function | `scylla.config.validation.validate_filename_model_id_consistency` |
| Fixtures skipped | Files prefixed with `_` |
| Entry command | `pixi run python scripts/check_model_config_consistency.py` |

## Key Insights

1. **Reuse existing validation primitives**: The `scylla/config/validation.py` helpers
   (`validate_filename_model_id_consistency`, `get_expected_filename`) should be the single
   implementation point — both the fix-mode script and the consistency hook call into them rather
   than re-implementing logic.

2. **Two separate constants, not one**: The codebase has two distinct model roles — agent (Sonnet)
   and judge (Opus). Define `DEFAULT_AGENT_MODEL` and `DEFAULT_JUDGE_MODEL` separately; do not
   collapse to a single `DEFAULT_MODEL`.

3. **Docstring/data vs functional literals**: Pricing dict keys (`"claude-opus-4-5-20251101": ModelPricing(...)`)
   and docstring examples are intentionally left as literals. Replacing them with the constant would
   make the pricing dict non-literal and reduce readability without reducing fragility.

4. **Coverage gate interaction**: Running `pytest tests/unit/config/test_constants.py` alone triggers
   the coverage gate (3% vs 73% threshold) and fails. Run the full `tests/unit/` suite to validate.

5. **`config/models.py` circular import risk**: Adding `from scylla.config.constants import ...`
   inside `scylla/config/models.py` is safe because `constants.py` imports nothing from `scylla.*`.
   The dependency graph is: `constants.py` (stdlib only) → imported by `models.py`.

6. **`pixi run python` required in pre-commit**: Plain `python` in a `language: system` hook may not
   have `pyyaml` or the project packages available. Always use `pixi run python ...` to ensure the
   correct virtual environment is active.

7. **Two complementary hooks, not one**: `validate-model-configs` (prefix match, allows date-stamp
   suffixes) and `check-model-config-consistency` (exact/normalized match, enforces load-time
   contract) serve different enforcement levels. Both are needed.

8. **Relation to `config-default-model-drift` skill**: The earlier skill addressed CLI-level literals
   using YAML config. This skill addresses the remaining executor/judge/e2e layer literals using a
   Python constants module. Both approaches coexist: `defaults.yaml` controls runtime model selection;
   `constants.py` provides the in-code fallback when no config is loaded.

## Related Skills

- `planning-implementation-from-issue` — General pattern for implementing GitHub issues
- `pytest-coverage-threshold-config` — Handling project-wide coverage thresholds
- `config-default-model-drift` — Runtime model selection via `defaults.yaml` + Pydantic

## References

- Issue #776 (fix mode): <https://github.com/HomericIntelligence/ProjectScylla/issues/776>
- Issue #792 (consistency hook): <https://github.com/HomericIntelligence/ProjectScylla/issues/792>
- Issue #851 (constants): <https://github.com/HomericIntelligence/ProjectScylla/issues/851>
- PR #823 (fix mode): <https://github.com/HomericIntelligence/ProjectScylla/pull/823>
- PR #837 (consistency hook): <https://github.com/HomericIntelligence/ProjectScylla/pull/837>
- PR #974 (constants): <https://github.com/HomericIntelligence/ProjectScylla/pull/974>
- `scylla/config/validation.py` — Reused validation primitives
- `scylla/config/constants.py` — Single source of truth for default model IDs
