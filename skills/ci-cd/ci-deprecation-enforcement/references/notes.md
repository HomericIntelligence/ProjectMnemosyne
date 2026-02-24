# Notes: ci-deprecation-enforcement

## Session Context

- **Issue**: ProjectScylla #786
- **PR**: ProjectScylla #834
- **Parent skill**: `deprecation-warning-migration` (ProjectScylla #728 / ProjectMnemosyne)
- **Date**: 2026-02-20

## Key Observations

### grep -v patterns are not equivalent

`grep -v "# deprecated"` strips lines that start with a Python comment containing
"deprecated", e.g.:

```python
# This method is deprecated
```

It does NOT strip docstring "See also" bullets like:

```
- BaseExecutionInfo (core/results.py) - Legacy dataclass (deprecated)
```

Both filters are required:

```bash
| grep -v "# deprecated" \
| grep -v "(deprecated)" \
```

### __init__.py re-exports are not callers

When a deprecated symbol is re-exported from `__init__.py` for backward
compatibility, the grep step must exclude that file explicitly. It is not
a new caller — it is part of the deprecation shim itself.

### Sequence matters

1. Run grep chain locally, count must be 0 before you change to exit 1
2. If count > 0, identify each hit: real caller (must fix) vs safe ref (add exclusion)
3. Change step name, ::warning:: → ::error::, add exit 1
4. Mirror all new exclusions into the diagnostic grep (the second grep in the if block)

## Raw Grep Command Used

```bash
count=$(grep -rn "BaseExecutionInfo" . \
  --include="*.py" \
  --exclude-dir=".pixi" \
  | grep -v "scylla/core/results.py" \
  | grep -v "scylla/core/__init__.py" \
  | grep -v "# deprecated" \
  | grep -v "(deprecated)" \
  | grep -v "test_results.py" \
  | wc -l)
```
