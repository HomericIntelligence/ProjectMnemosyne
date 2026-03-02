---
name: "Skill: Verify Mypy Compliance for Test Annotations"
description: "Pattern for verifying and adding -> None return types and parameter type hints to test functions for mypy compliance"
category: testing
date: 2026-03-02
user-invocable: false
---
# Skill: Verify Mypy Compliance for Test Annotations

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-03-02 |
| **Objective** | Annotate all test functions in a test directory with `-> None` return types and parameter type hints for mypy compliance |
| **Context** | Part of #1120 quality audit — applied to `tests/unit/config/` (#1286), `tests/integration/` (#1288), and `tests/unit/analysis/` (#1285) |
| **Outcome** | ✅ All three directories made compliant; two were pre-completed (empty commits), one required actual annotation work (385 tests, 19 files) |
| **PRs** | #1314 (unit/config), #1317 (integration), #1319 (unit/analysis) |

## When to Use This Skill

Use this pattern when:

1. **A test directory needs mypy compliance** — test functions missing `-> None` return types
2. **CI mypy step is failing on test files** — missing annotations cause `error: Function is missing a return type annotation`
3. **Quality audit covers test annotation hygiene** — systematic annotation of all test methods
4. **Pre-commit mypy hook flags test files** — e.g. `tests/**/*.py` are in mypy's path

**Trigger phrases:**
- "annotate test functions for mypy compliance"
- "add -> None to test functions"
- "mypy error: Function is missing a return type annotation in test file"
- "add type hints to pytest test methods"

## Verified Workflow

### Step 1: Check if work is already done (FIRST — do this before any changes)

In codebases with parallel waves of annotation work, the annotations may already be present:

```bash
# Run mypy — fastest check
pixi run python -m mypy tests/<directory>/
# Success: no issues found in N source files → work is done

# Optional quick grep sanity check
grep -rn "def test_" tests/<directory>/ | grep -v "-> None"
# Empty output = all test functions already annotated
```

If mypy already reports `Success: no issues found`, **skip to the verification commit step**.

### Step 2 (if needed): Annotate standalone test functions

```python
# Before
def test_something():
    assert True

# After
def test_something() -> None:
    assert True
```

### Step 3 (if needed): Annotate test class methods (including `setUp` / `tearDown`)

```python
# Before
class TestFoo:
    def test_bar(self):
        ...
    def setUp(self):
        ...

# After
class TestFoo:
    def test_bar(self) -> None:
        ...
    def setUp(self) -> None:
        ...
```

### Step 4 (if needed): Annotate fixture functions and their parameters

Fixtures need both return types AND parameter types for the fixtures they consume:

```python
# Before
@pytest.fixture
def mock_criterion_scores():
    return {...}

@pytest.fixture
def mock_judges(mock_criterion_scores):
    return [...]

# After
@pytest.fixture
def mock_criterion_scores() -> dict[str, CriterionScore]:
    return {...}

@pytest.fixture
def mock_judges(mock_criterion_scores: dict[str, CriterionScore]) -> list[JudgeEvaluation]:
    return [...]
```

### Step 5 (if needed): Annotate test function fixture parameters

```python
# Before
def test_load_all_tiers_mismatched(self, tmp_path):
    ...

# After
from pathlib import Path

def test_load_all_tiers_mismatched(self, tmp_path: Path) -> None:
    ...
```

Common parameter annotations:
| Parameter | Type |
|-----------|------|
| `tmp_path` | `Path` |
| `capsys` | `pytest.CaptureFixture[str]` |
| `monkeypatch` | `pytest.MonkeyPatch` |
| `mocker` | `pytest_mock.MockerFixture` |
| `caplog` | `pytest.LogCaptureFixture` |
| `sample_runs_df` | `pd.DataFrame` |
| `sample_judges_df` | `pd.DataFrame` |
| `request` (indirect) | `pytest.FixtureRequest` |

### Step 6: Add necessary top-level imports

Imports for type annotations must be at module level (not inside functions):

```python
# Add ONLY what is needed for new type annotations
import pandas as pd          # for pd.DataFrame parameters
import numpy as np           # for np.ndarray parameters
from pathlib import Path     # for tmp_path: Path
from collections.abc import Generator  # for yield fixtures
```

**Critical**: If `pd.DataFrame` is used in function signatures but `import pandas as pd` is at module level in fixtures but not in the file header, ruff F821 will fire for the test functions.

### Step 7: Use parameterized generics (not bare `dict` / `list`)

```python
# WRONG — mypy complains: Missing type parameters for generic type "dict"
def mock_criterion_scores() -> dict:

# CORRECT
def mock_criterion_scores() -> dict[str, CriterionScore]:
```

### Step 8: Verify with pre-commit (catches both ruff and mypy)

```bash
pre-commit run --files tests/<directory>/*.py
# All hooks must pass: Ruff Format, Ruff Check, Mypy Type Check
```

### Step 9: Run tests to confirm no regressions

```bash
pixi run python -m pytest tests/<directory>/ -q
# N passed, M warnings
```

### Step 10: Create commit and PR

```bash
# Stage only the test files
git add tests/<directory>/
git commit -m "test(<scope>): annotate test functions in tests/<directory>/ for mypy compliance"

# Push and create PR
git push -u origin <branch-name>
gh pr create --title "[Test] Annotate tests/<directory>/ for mypy compliance" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Agent added `import pandas as pd` only as a comment/local import | Ruff F821 fires when `pd.DataFrame` appears in function signatures but `import pandas as pd` is not at module level | Always verify pre-commit hooks pass after using an agent for batch annotations — check that module-level imports were actually added |
| Agent used bare `dict` and `list` return types on fixtures | mypy `[type-arg]` error: Missing type parameters for generic type | Fixture return types must use fully parameterized generics: `dict[str, X]` not `dict`, `list[X]` not `list` |
| None — annotations were pre-existing in `tests/unit/config/` and `tests/integration/` | N/A | Always verify before making changes; parallel audit waves frequently pre-complete issues |

### Key insight: Parallel wave execution pre-completes issues

In this project, the February 2026 quality audit ran 35 LOW issues across 8 parallel waves. Issues #1286 (`tests/unit/config/`) and #1288 (`tests/integration/`) were already fully annotated when executed sequentially. The correct response is:

1. Run `mypy` to confirm clean state
2. Run `pytest` to confirm passing
3. Post a comment on the GitHub issue with the verification evidence
4. Create an **empty (verification) commit** with `git commit --allow-empty`
5. Push and open a PR to formally close the issue

**Never skip the verification step** — even if you suspect work is done, confirm with mypy before closing.

### Key insight: Always run pre-commit after agent-based batch annotation

When delegating bulk annotation to a subagent, the agent may:
- Miss module-level imports (adding imports only locally inside functions instead)
- Use bare generic types (`dict`, `list`) instead of parameterized ones (`dict[str, X]`, `list[X]`)
- Apply ruff formatting that differs from what pre-commit would apply

**Always run `pre-commit run --files <path>/*.py` after agent annotation work** and fix any issues manually.

## Results & Parameters

### Instance 1: `tests/unit/config/` (issue #1286)

| File | Test Count | Status |
|------|-----------|--------|
| `test_pricing.py` | 16 | ✓ Fully annotated (pre-existing) |
| `test_validation.py` | 31 | ✓ Fully annotated (pre-existing) |
| `test_pixi_upper_bounds.py` | 6 | ✓ Fully annotated (pre-existing) |
| `test_constants.py` | 10 | ✓ Fully annotated (pre-existing) |
| `test_models.py` | 77 | ✓ Fully annotated (pre-existing) |
| `test_config_validation.py` | 9 | ✓ Fully annotated (pre-existing) |
| `test_loader.py` | 4 | ✓ Fully annotated (pre-existing) |
| `test_config_loader.py` | 83+ | ✓ Fully annotated (pre-existing) |

```bash
pixi run python -m mypy tests/unit/config/
# Output: Success: no issues found in 9 source files
```

### Instance 2: `tests/integration/` (issue #1288)

| File | Source Files | Status |
|------|-------------|--------|
| `tests/integration/__init__.py` | empty | ✓ Compliant |
| `tests/integration/e2e/__init__.py` | empty | ✓ Compliant |
| `tests/integration/e2e/conftest.py` | helper functions | ✓ Fully annotated (pre-existing) |
| `tests/integration/e2e/test_additive_resume.py` | 15 test methods | ✓ Fully annotated (pre-existing) |
| `tests/integration/e2e/test_until_from_stepping.py` | multiple tests | ✓ Fully annotated (pre-existing) |

```bash
pixi run python -m mypy tests/integration/
# Output: Success: no issues found in 5 source files
```

### Instance 3: `tests/unit/analysis/` (issue #1285) — actual annotation work required

19 files, 385 tests across a large data-analysis test directory. All required annotation work.

| File | Tests | Changes |
|------|-------|---------|
| `conftest.py` | (fixtures) | Added return types + `Generator[None, None, None]` for yield fixtures |
| `test_apareto.py` | 8 | `-> None` to all test functions |
| `test_config.py` | 14 | `-> None` + parameter types |
| `test_cop_integration.py` | 4 | `-> None` + `pd.DataFrame` params |
| `test_dataframe_builders.py` | 17 | `-> None` + `dict[str, CriterionScore]`, `list[JudgeEvaluation]` fixture return types |
| `test_dataframes.py` | 15 | `-> None` + `pd.DataFrame` params |
| `test_degenerate_fixtures.py` | 24 | `-> None` + `np.ndarray`, `dict[str, np.ndarray]` params |
| `test_duration_integration.py` | 4 | `-> None` + `pd.DataFrame` params |
| `test_export_data.py` | 60 | `-> None` + `pd.DataFrame`, `Path` params |
| `test_figures.py` | 44 | `-> None` + `pd.DataFrame`, `Path` params; added `import pandas as pd` |
| `test_integration.py` | 5 | `-> None` + `pd.DataFrame` params |
| `test_loader.py` | 70 | `-> None` + `request: pytest.FixtureRequest` |
| `test_process_metrics_aggregation.py` | varies | `pd.DataFrame` params |
| `test_process_metrics_integration.py` | 5 | `pd.DataFrame`, `Path` params |
| `test_rubric_conflict.py` | 31 | `-> None` + fixture return types |
| `test_stats.py` | 40 | `-> None` to all |
| `test_stats_degenerate.py` | 22 | `-> None` + `np.ndarray`, `dict[str, np.ndarray]` |
| `test_stats_parametrized.py` | 16 | `-> None` to all class methods |
| `test_tables.py` | 35 | `-> None` + `pd.DataFrame`; added missing `import pandas as pd` |

**Post-agent fixes required:**
- `test_tables.py`: Agent said it added `import pandas as pd` but didn't persist it at module level → manual fix
- `test_dataframe_builders.py`: Agent used bare `dict`/`list` → manually changed to `dict[str, CriterionScore]` and `list[JudgeEvaluation]`

```bash
pre-commit run --files tests/unit/analysis/*.py
# All hooks passed after manual fixes
pixi run python -m pytest tests/unit/analysis/ -q
# 385 passed
```

### Note on `pyproject.toml` mypy overrides

After parallel annotation waves complete, the `[tool.mypy.overrides]` suppression for `tests.unit.*` becomes redundant. However, removing it is a separate concern — don't scope-creep into `pyproject.toml` cleanup when fixing annotation issues.

```toml
# This override was needed before annotation waves — may be stale after:
[[tool.mypy.overrides]]
module = "tests.unit.*"
disable_error_code = ["no-untyped-def"]
```

## Key Takeaways

1. **Always check before annotating** — run `mypy` first; parallel work may have already applied annotations.
2. **Empty commits are valid for verification** — `git commit --allow-empty` is the correct pattern when CI/issue closure requires a commit but no code changes are needed.
3. **`-> None` is the universal return type for test functions** — pytest test functions never return a meaningful value.
4. **Fixture parameter types matter** — `tmp_path: Path` is the most common; always add the `from pathlib import Path` import if needed.
5. **Always run pre-commit after agent annotation** — agents may miss module-level imports or use bare generics (`dict` vs `dict[str, X]`).
6. **Module-level imports are required for signature types** — if `pd.DataFrame` appears in function signatures, `import pandas as pd` must be at the top of the file, not just inside fixture bodies.
7. **Parameterized generics required** — `dict[str, X]` and `list[X]` not `dict` and `list` — mypy `[type-arg]` errors otherwise.
8. **Separate runs for `mypy` vs `pytest`** — mypy catches annotation errors, pytest catches logic errors; run both.
9. **Post evidence as issue comment first** — use `gh issue comment <number> --body "..."` to document verification before closing.
10. **Stale overrides** — when annotations are complete, `pyproject.toml` `no-untyped-def` overrides become no-ops but removing them is separate scope.

## Related Skills

- `testing/generate-tests` — general test generation patterns
- `testing/run-tests` — running tests with pixi
- `ci-cd/fix-ci-test-failures` — debugging CI failures

## References

- Issue #1285: Annotate test functions in tests/unit/analysis/ for mypy compliance
- Issue #1286: Annotate test functions in tests/unit/config/ for mypy compliance
- Issue #1288: Annotate test functions in tests/integration/ for mypy compliance
- Issue #1120: Parent quality audit tracking all annotation work
- PR #1314: Verification PR for issue #1286
- PR #1317: Verification PR for issue #1288
- PR #1319: Annotation PR for issue #1285
