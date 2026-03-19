# Raw Session Notes — pixi-pypi-upper-bounds

## Session Details

- **Date**: 2026-02-27
- **Project**: ProjectScylla
- **Issue**: #1119 — [Build] Add upper bounds to PyPI dependencies in pixi.toml
- **Branch**: `1119-auto-impl`
- **PR**: #1170

## Problem Statement

11 `[pypi-dependencies]` entries in `pixi.toml` had no upper bound (`<`), only lower bounds.
This means a `pip install --upgrade` or a fresh environment could silently pull in a future
major version with breaking changes.

Affected: `matplotlib`, `numpy`, `pandas`, `seaborn`, `scipy`, `altair`, `vl-convert-python`,
`krippendorff`, `statsmodels`, `jsonschema`, `defusedxml`

## What Happened

### Step 1 — Initial edit
Set all bounds to `<(installed_major)`. For altair, locked at `6.0.0`, set `>=5.0,<6`.

### Step 2 — pixi lock
Reported "already up-to-date". Lock still showed `altair 6.0.0` — seemed fine.

### Step 3 — pixi install + test
After reinstall, altair downgraded to `5.5.0`. Tests that import altair failed:
```
TypeError: _TypedDictMeta.__new__() got an unexpected keyword argument 'closed'
```
Root cause: altair `5.5.0` uses `TypedDict(closed=True)` — a PEP 728 feature not yet
available in CPython 3.14's `typing` module (available in `typing_extensions` only).
altair 6.x fixed this by using a compatibility shim.

### Step 4 — Fix altair bound
Changed to `>=5.0,<7`. Ran `pixi update altair` → resolved to `6.0.0`. All tests passed.

### Step 5 — pixi lock "already up-to-date" mystery
When `pixi.toml` constraint is `>=5.0,<6` and lock has `5.5.0`, lock thinks it's fine.
When constraint changes to `>=5.0,<7` and lock has `5.5.0`, lock also thinks it's fine.
Only `pixi update altair` forces a fresh resolution that picks the latest allowed version.

### Step 6 — Test path bug
First version of test used `Path(__file__).parents[4]` which in a worktree resolves to
`.worktrees/` directory, not the project root. Fixed to `parents[3]`.

## Final State

- All 11 packages have upper bounds
- altair: `>=5.0,<7` (not `<6`)
- 3209 tests passing, 78.36% coverage
- Regression test added: `tests/unit/config/test_pixi.py` (24 parametrized tests)

## Commands Used

```bash
# Check locked versions
grep -A2 "name: altair" pixi.lock

# Force re-resolution after constraint change
pixi update altair

# Reinstall after lock change
pixi install

# Verify installed version
pixi run python -c "import altair; print(altair.__version__)"

# Run tests
pixi run python -m pytest tests/ -q

# Verify path depth for test
python3 -c "from pathlib import Path; p = Path('/path/to/test.py'); [print(i, p.parents[i]) for i in range(6)]"
```