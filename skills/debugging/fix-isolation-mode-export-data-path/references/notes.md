# Raw Session Notes: fix-isolation-mode-export-data-path

## Session Context

- **Project**: ProjectScylla / 1196-auto-impl branch
- **Date**: 2026-03-02
- **Issue**: #1196 — "Fix test_figures.py conftest export_data import-order quirk"
- **PR**: #1303
- **Trigger**: `pytest tests/unit/analysis/test_figures.py` fails with
  `ModuleNotFoundError: No module named 'export_data'` in isolation,
  but passes when run as part of the full suite

## Investigation Timeline

1. Read issue #1196 — root cause already identified: `mock_power_simulations` autouse
   fixture patches `export_data.*` but `export_data` not on `sys.path` in isolation
2. Read `tests/unit/analysis/conftest.py` — confirmed the current fixture does NOT
   actually patch `export_data.*` (that was the planned fix, not yet applied)
3. Reproduced: `python -m pytest tests/unit/analysis/test_figures.py --override-ini="pythonpath=" -q`
   → `ModuleNotFoundError` confirmed
4. Verified `patch("export_data.mann_whitney_power")` fails when `scripts/` is absent from path
5. Applied fix: sys.path guard + extend fixture to patch `export_data.*`
6. Discovered ruff F401 removes bare `import export_data` — not needed anyway
7. Verified: all 385 analysis tests pass, all 3584 full-suite tests pass

## Key Diagnostic Commands

```bash
# Reproduce isolation failure
python -m pytest tests/unit/analysis/test_figures.py --override-ini="pythonpath=" -q

# Verify patch fails without sys.path
python -c "
import sys
sys.path = [p for p in sys.path if 'scripts' not in p]
from unittest.mock import patch
try:
    p = patch('export_data.mann_whitney_power', return_value=0.8)
    p.start()
    print('SUCCESS')
    p.stop()
except ModuleNotFoundError as e:
    print(f'FAILED: {e}')
"
# FAILED: No module named 'export_data'
```

## Timing Verification

```bash
# Before patch (test_export_data.py with unpatched export_data.* namespaces)
python -m pytest tests/unit/analysis/test_export_data.py --no-cov -q
# 27 passed in 23.84s  (dominated by other stats, power mock speeds up worst tests)

# Individual slowest test
python -m pytest tests/unit/analysis/test_export_data.py::test_helpers_compose_to_same_result --no-cov -q
# 1 passed in 4.72s  (calls compute_statistical_results multiple times)
```

## Why `import export_data` Was Removed by Linter

Ruff rule F401 (`unused-import`) removes any top-level import that isn't referenced
by name later in the file. Since `export_data` was only imported for the side effect
of having it in `sys.modules`, ruff removed it.

The fix doesn't need an explicit import — `patch("export_data.xxx")` internally calls
`importlib.import_module("export_data")`. As long as `scripts/` is on `sys.path`,
this import succeeds.

## Files Changed

```
tests/unit/analysis/conftest.py  (14 insertions, 4 deletions)
  - Added sys.path guard block (5 lines)
  - Updated fixture comment
  - Added 2 export_data.* patches
```

## Commit

```
a028049 fix(analysis): ensure export_data is importable before patching in conftest
```
