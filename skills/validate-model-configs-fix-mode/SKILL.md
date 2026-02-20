# Skill: Validate Model Configs with --fix Mode

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-20 |
| **Category** | tooling |
| **Objective** | Add `--fix` mode to a validation script that renames YAML files to match their `model_id` field |
| **Outcome** | ✅ Script created with `--fix`, `--yes`, `--models-dir`, `--verbose` flags; 26 tests; all pre-commit hooks pass |
| **Context** | Issue #776 (follow-up from #682 / #594) |

## When to Use This Skill

Use this skill when:

- ✅ A validation script only detects problems but can't auto-fix them
- ✅ You need to add a `--fix` flag that renames/patches files based on detected mismatches
- ✅ The fix involves a rename that could collide with an existing file
- ✅ You need interactive `[y/N]` confirmation with a `--yes` bypass for automation
- ✅ The fix script must integrate with existing validation helpers in `scylla/`

**Don't use when:**

- The fix operation is destructive and cannot be safely checked for collisions
- The validation logic doesn't already exist in `scylla/config/validation.py`

## Verified Workflow

### 1. Locate Existing Validation Primitives

```bash
# Find existing validation helpers to reuse
grep -r "validate_filename" scylla/config/
# → scylla/config/validation.py: validate_filename_model_id_consistency, get_expected_filename
```

### 2. Structure the Script

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

### 3. Module-Level Default Path (avoids import-time failure in tests)

```python
_REPO_ROOT = get_repo_root()
_CONFIG_MODELS_DIR = _REPO_ROOT / "config" / "models"

parser.add_argument("--models-dir", type=Path, default=_CONFIG_MODELS_DIR, ...)
```

### 4. Test File Location for scripts/

Scripts live in `scripts/` (not a Python package). Tests must add the directory to `sys.path`:

```python
_SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_model_configs import _collect_mismatches, _fix_mismatch, main
```

Test file goes in `tests/unit/scripts/test_validate_model_configs.py` with `__init__.py`.

### 5. Pre-commit Compliance

Ruff enforces D101/D102 (docstrings for public classes and methods) even in test files.
Every test class and test method needs a one-line docstring:

```python
class TestFixMismatch:
    """Tests for _fix_mismatch rename executor."""

    def test_renames_file_when_yes(self, tmp_path: Path) -> None:
        """Renames file without prompting when yes=True."""
        ...
```

### 6. Verify Full Pre-commit Pass

```bash
pre-commit run --files scripts/validate_model_configs.py \
    tests/unit/scripts/test_validate_model_configs.py \
    tests/unit/scripts/__init__.py
```

All hooks must pass (Ruff Format, Ruff Check, Mypy, Trim Whitespace, etc.).

## Failed Attempts

### ❌ Missing Docstrings on Test Classes/Methods

**What happened:**
Initial test file had no docstrings on test classes or methods — names were
considered self-documenting.

**Why it failed:**
Ruff D101/D102 rules enforce docstrings on all public classes and methods,
including test classes. The pre-commit hook failed with 34 errors.

**Fix:**
Add a one-line docstring to every test class and every `test_*` method.
Helper methods (`_make_models_dir`) need docstrings too since they're technically
public (no leading underscore guard applied by ruff at class level).

### ❌ Forgetting `--no-cov` When Diagnosing Test Failures

**What happened:**
Running `pytest tests/unit/scripts/...` reported exit code 1 even though all
26 tests passed. The failure was a global coverage threshold (73%) not met.

**Why it failed:**
The project has `fail_under = 73` in `pyproject.toml`. Running only the new
test file in isolation drops total coverage to ~5%.

**Fix:**
Use `--no-cov` when running isolated test subsets:

```bash
pixi run python -m pytest tests/unit/scripts/ -v --no-cov
```

The coverage threshold is a pre-existing project-wide constraint; individual
sub-suite runs should use `--no-cov` to avoid false failures.

## Results & Parameters

### Files Created

```
scripts/validate_model_configs.py
tests/unit/scripts/__init__.py
tests/unit/scripts/test_validate_model_configs.py
```

### Test Results

```
26 tests collected — 26 passed in 0.16s
All pre-commit hooks: PASSED
```

### CLI Interface

```
python scripts/validate_model_configs.py [--fix] [--yes] [--models-dir PATH] [--verbose]

Exit codes:
  0  All configs OK (or all fixes applied)
  1  Mismatches found, --fix not passed
  2  Collision or I/O error during fix
```

### Test Coverage by Class

| Test Class | Scenarios Covered |
|------------|------------------|
| `TestLoadModelId` | valid file, missing field, bad YAML, non-dict YAML |
| `TestCollectMismatches` | no mismatch, mismatch, underscore skip, no model_id, multiple, colon normalize |
| `TestConfirmRename` | y, n, empty, uppercase N |
| `TestFixMismatch` | yes=True rename, interactive confirm, user denial (no error), collision |
| `TestMain` | exit 0, exit 1, fix+yes, collision, missing dir, underscore-skip, verbose, interactive |

## Related Skills

- `planning-implementation-from-issue` — General pattern for implementing GitHub issues
- `pytest-coverage-threshold-config` — Handling project-wide coverage thresholds

## References

- Issue #776: <https://github.com/HomericIntelligence/ProjectScylla/issues/776>
- PR #823: <https://github.com/HomericIntelligence/ProjectScylla/pull/823>
- `scylla/config/validation.py` — Reused validation primitives
