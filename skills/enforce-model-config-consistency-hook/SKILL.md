# Skill: enforce-model-config-consistency-hook

## Overview

| Field     | Value                                                                 |
|-----------|-----------------------------------------------------------------------|
| Date      | 2026-02-20                                                            |
| Issue     | #792                                                                  |
| PR        | #837                                                                  |
| Objective | Promote runtime warning to hard pre-commit gate by reusing validation.py |
| Outcome   | Success — 16 tests, pre-commit hook blocks mismatching commits        |

## When to Use

- You have a Python validation function that emits warnings at load time and need to block commits instead
- You want a pre-commit hook that delegates to existing library code rather than reimplementing logic
- You're adding a second CI check that enforces stricter rules than an existing check
- The existing validation is in `scylla/` and you want to call it from a `scripts/` entry point

## Verified Workflow

### 1. Identify the existing validation function

The runtime warning lives in `scylla/config/validation.py`:

```python
def validate_filename_model_id_consistency(config_path: Path, model_id: str) -> list[str]:
    """Returns list of warning strings; empty means valid."""
    ...
```

The goal is to call this function from a `scripts/` entry point and exit 1 if any warnings are returned.

### 2. Write a thin wrapper script in `scripts/`

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

### 3. Add the pre-commit hook using `pixi run`

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

### 4. Distinguish from the existing `validate-model-configs` hook

There are now two complementary hooks:

| Hook | Script | Logic | Purpose |
|------|--------|-------|---------|
| `validate-model-configs` | `validate_model_configs.py` | Prefix match (`stem` is prefix of `model_id`) | Allows date-stamp suffixes |
| `check-model-config-consistency` | `check_model_config_consistency.py` | Exact or `:` → `-` normalization (from `validation.py`) | Enforces load-time contract |

Both hooks are complementary; the second is stricter for the load-time semantics.

### 5. Test structure

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

### Using `python` instead of `pixi run python` in hook entry

When `entry: python scripts/check_model_config_consistency.py` is used, the script cannot
import `scylla.config.validation` because the pixi venv packages are not available in the
pre-commit environment's `python`. Always use `pixi run python` for scripts that import
from the project's own packages.

### Forgetting `sys.path` injection

Without `sys.path.insert(0, str(_REPO_ROOT))`, running the script from an arbitrary CWD
(as pre-commit does) fails with `ModuleNotFoundError: No module named 'scylla'`. The repo
root injection is necessary because pre-commit's `language: system` does not add the CWD
to `sys.path`.

## Results & Parameters

| Metric               | Value                                       |
|----------------------|---------------------------------------------|
| Tests added          | 16                                          |
| Hook ID              | `check-model-config-consistency`            |
| Hook trigger         | `^config/models/.*\.yaml$`                  |
| Validation function  | `scylla.config.validation.validate_filename_model_id_consistency` |
| Fixtures skipped     | Files prefixed with `_`                     |
| Entry command        | `pixi run python scripts/check_model_config_consistency.py` |
