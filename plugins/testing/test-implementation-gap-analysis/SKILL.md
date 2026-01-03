# Test-Implementation Gap Analysis

## Overview

| Field | Value |
|-------|-------|
| Date | 2025-12-31 |
| Objective | Detect and fix gaps between test expectations and implementation |
| Outcome | SUCCESS - 756 tests passing, 0 warnings |
| Category | testing |
| Source Project | ProjectScylla |

## When to Use This Skill

Use this skill when:
- Tests fail with import errors for missing classes/functions
- Tests exist but implementation is a stub
- Auditing epic/milestone implementation completeness
- Pytest collection warnings appear for production classes
- Python version compatibility issues in tests

## Verified Workflow

### Step 1: Run Tests to Identify Scope

```bash
pixi run pytest tests/ -v --tb=short 2>&1 | tail -100
```

Look for:
- Import errors (missing classes/functions)
- NameError (undefined symbols)
- Test failures vs warnings count

### Step 2: Analyze Import Errors First

Import errors block test collection entirely. Fix these first:

```bash
# Find what tests expect vs what exists
grep -n "from scylla.module import" tests/unit/test_file.py
grep -n "class ExpectedClass" src/scylla/module.py
```

### Step 3: Compare Test Expectations to Implementation

Read test file to understand expected API:
```python
# Test expects these to exist
from module import (
    SomeClass,
    some_function,
    SOME_CONSTANT,
)
```

### Step 4: Implement Missing Components

Write implementation that satisfies test expectations:
- Match function signatures exactly
- Match class attributes and methods
- Match constant values if specified

### Step 5: Fix NameErrors in Existing Code

Common pattern - using wrong class name:
```python
# BEFORE (wrong)
pass_rate=Statistics(**data)

# AFTER (correct - class is actually SummaryStatistics)
pass_rate=SummaryStatistics(**data)
```

### Step 6: Fix Pytest Collection Conflicts

Production classes named `Test*` trigger pytest warnings:
```python
# BEFORE (triggers warning)
class TestOrchestrator:
    pass

# AFTER (no warning)
class EvalOrchestrator:
    pass
```

Rename cascade:
1. Rename class definition
2. Update all imports
3. Update __init__.py exports
4. Update __all__ lists
5. Update type hints
6. Update docstrings

### Step 7: Python Version Compatibility

Python 3.14 changed `subprocess.TimeoutExpired`:
```python
# BEFORE (fails on Python 3.14)
timeout_error = subprocess.TimeoutExpired(cmd="docker", timeout=60, stdout=b"partial")

# AFTER (works on all versions)
timeout_error = subprocess.TimeoutExpired(cmd="docker", timeout=60)
timeout_error.stdout = b"partial"
timeout_error.stderr = b""
```

### Step 8: Verify All Tests Pass

```bash
pixi run pytest tests/ --tb=short
# Should show: X passed, 0 warnings
```

## Failed Attempts

### 1. Using pytest filterwarnings for Test* classes
**What was tried**: Adding `filterwarnings` to pyproject.toml to suppress `PytestCollectionWarning`
```toml
filterwarnings = [
    "ignore::pytest.PytestCollectionWarning:scylla.*",
]
```
**Why it failed**: Warnings are raised from test file context, not the module being collected. Pattern didn't match.
**Solution**: Rename classes to avoid `Test*` prefix entirely.

### 2. Using replace_all without checking internal references
**What was tried**: Renamed class with `replace_all=true` on class definition only
**Why it failed**: Missed internal references within the same file (method return types, docstrings)
**Solution**: Run `replace_all` on entire file, then verify with grep.

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `src/scylla/judge/prompts.py` | Full implementation (~300 lines added) |
| `src/scylla/reporting/summary.py` | Fixed NameError |
| `tests/unit/cli/test_cli.py` | Fixed exit code expectations |
| `tests/fixtures/invalid/config/defaults.yaml` | Created missing fixture |
| `tests/unit/test_docker.py` | Fixed Python 3.14 compatibility |
| Multiple files | Renamed `Test*` classes to `Eval*` |
| `pixi.toml` | Fixed `[project]` -> `[workspace]` deprecation |

### Class Renames Applied

| Before | After | Files Updated |
|--------|-------|---------------|
| TestCase | EvalCase | 5 |
| TestOrchestrator | EvalOrchestrator | 4 |
| TestRunner | EvalRunner | 4 |
| TestSummary | EvalSummary | 4 |
| TestProgress | EvalProgress | 3 |
| TestResult | EvalResult | 3 |
| TestSummary (reporting) | EvaluationReport | 3 |

### Metrics

- **Before**: 718 passing, 6+ failing, 7 warnings, 1 import error
- **After**: 756 passing, 0 failing, 0 warnings, 0 errors

## Related Skills

- `pytest-production-class-conflicts` - Deep dive on Test* naming
- `python-version-compatibility` - Handling API changes across versions
- `stub-to-implementation` - Completing stub implementations
