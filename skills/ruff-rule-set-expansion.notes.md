# Session Notes: Ruff Rule Set Expansion

## Session Details
- **Date**: 2026-03-03
- **Issue**: #1356 (ProjectScylla)
- **PR**: #1375
- **Branch**: `1356-auto-impl`

## Raw Violation Count (before changes)

```
59  SIM117 Use a single `with` statement with multiple contexts
34  RUF100 Unused `noqa` directive (non-enabled: C901)
11  RUF100 Unused `noqa` directive (non-enabled: E402)
11  RUF001 String contains ambiguous `ρ` (GREEK SMALL LETTER RHO)
10  RUF002 Docstring contains ambiguous `–` (EN DASH)
 8  SIM117 (auto-fixable variant)
 8  RUF003 Comment contains ambiguous `–` (EN DASH)
 8  RUF002 Docstring contains ambiguous `×` (MULTIPLICATION SIGN)
 7  RUF001 String contains ambiguous `α` (GREEK SMALL LETTER ALPHA)
 6  RUF100 Unused `noqa` directive (non-enabled: F822)
 5  RUF100 Unused `noqa` directive (non-enabled: F821)
 5  RUF100 Unused `noqa` directive (non-enabled: BLE001)
 5  RUF003 Comment contains ambiguous `×` (MULTIPLICATION SIGN)
 4  SIM105 Use `contextlib.suppress(Exception)`
 3  SIM102 Use a single `if` statement
 3  RUF059 Unpacked variable never used
 3  RUF022 `__all__` is not sorted
 3  RUF002 Docstring contains ambiguous `α` (GREEK SMALL LETTER ALPHA)
 3  C420 Unnecessary dict comprehension; use `dict.fromkeys`
 3  B017 Do not assert blind exception
 2  SIM108 Use ternary operator
 2  RUF100 Unused `noqa` directive (non-enabled: S101)
...
Total: 233 errors
[*] 76 fixable (31 more with --unsafe-fixes)
```

## Fix Strategy Applied

1. Updated `pyproject.toml` with new rules + ignore entries
2. `pixi run ruff check ... --fix` → 44 auto-fixed
3. `pixi run ruff check ... --unsafe-fixes --fix` → 36 more fixed
4. Manual fixes for 17 remaining (E501, SIM102, SIM103, B023, RUF012, SIM105)

## E501 Root Cause

Lines like:
```python
def my_func(arg: str) -> int:  # noqa: C901  # complex function with many branches
```

After RUF100 removes `# noqa: C901  #`:
```python
def my_func(arg: str) -> int:  # complex function with many branches
```

This is >100 chars because the description was part of the noqa comment.
Fix: remove descriptive comment entirely (10 lines across 7 files).

## Files Touched

53 files total. Most impactful:
- `pyproject.toml` — config change
- `scylla/e2e/llm_judge.py` — 3 E501 + function signature changes
- `tests/unit/e2e/test_llm_judge.py` — RUF012 ClassVar fix
- `tests/unit/e2e/test_runner.py` — SIM105
- `tests/unit/e2e/test_runner_state_machine.py` — SIM105
- `tests/integration/e2e/test_additive_resume.py` — B023 closure fix
- `scylla/e2e/resume_manager.py` — SIM102 (had to extract variable for line length)

## Pre-commit Notes

- First run: `ruff-format-python` reformatted 1 file (after SIM102 manual edit changed indentation)
- Second run: all hooks passed
- SKIP=audit-doc-policy needed for worktree environments

## Test Results

```
3999 passed, 1 skipped, 48 warnings in 113.54s
Total coverage: 72.02% (floor: 9%)
```