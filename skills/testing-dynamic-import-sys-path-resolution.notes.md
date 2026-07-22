---
target_skill: testing-dynamic-import-sys-path-resolution
date: 2026-07-22
---

# Project-specific evidence: Pytest Dynamic-Import sys.path Resolution

## Project
- predictive-coding-mojo.

## Test surface
- `tests/test_collect_alexnet_regen_smoke.py` dynamic-loads `scripts/collect_alexnet_regen_smoke.py`
  via `importlib.util.spec_from_file_location`. The loaded script does
  `from optimizers import OPTIMIZER_NAMES` (a sibling module in `scripts/`).

## Pre-fix
- `pytest tests/ -q` reported 10 errors of `ModuleNotFoundError: No module
  named 'optimizers'` on the dynamic-loading test cases.

## Fix
- `pytest.ini`:
  ```ini
  [pytest]
  pythonpath = scripts
  ```
- `scripts/optimizers.py` (new SSoT file, 24 names, `__all__ = ["OPTIMIZER_NAMES"]`).

## Post-fix
- `pytest tests/ -q` rises from 113 passed to 123 passed; error count drops
  from 10 to 0.

## Caveat observed
- The fix is config-only; renaming the directory from `scripts/` to
  `src/` would break the `pythonpath = scripts` value. The fix is *only*
  stable when the directory name and the pythonpath value agree.
