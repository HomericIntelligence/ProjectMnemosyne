# Session Notes: pytest-pythonpath-scripts-fix

## Verified Examples

### Example 1: ProjectScylla — Issue #1137

**Date**: 2026-02-27
**Context**: Issue #1137 — Pre-push hook ran `pixi run pytest -x` with `pythonpath = ["."]`, causing `tests/unit/analysis/test_export_data.py` to fail at collection with `ModuleNotFoundError: No module named 'export_data'`. This silently suppressed 9 test functions and reduced visible count from ~3257 to ~1691.

**Root Cause**: `export_data` lives in `scripts/export_data.py`. pytest's `pythonpath` only included `"."` (repo root), not `"scripts/"`.

**Specific Commands Used**:

```bash
# Verify collection before fix
pixi run pytest tests/unit/analysis/test_export_data.py -v --collect-only
# → ERROR collecting (ModuleNotFoundError)

# Apply fix to pyproject.toml (pythonpath = [".", "scripts"])
# Remove sys.path.insert workaround from test file

# Verify collection after fix
pixi run pytest tests/unit/analysis/test_export_data.py -v --collect-only
# → 9 tests collected, no errors

# Full suite
pixi run pytest -x
# → 3257 passed, coverage 78.31%

# Pre-commit
pre-commit run --all-files
# → All hooks passed
```

**Specific Fix Applied**:

`pyproject.toml`:
```toml
# Before
pythonpath = ["."]
# After
pythonpath = [".", "scripts"]
```

`tests/unit/analysis/test_export_data.py`:
```python
# Removed lines 4-9:
import sys
from pathlib import Path
# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
```

**Links**:
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/1190
- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/1137
- Commit: d95de48

## Raw Findings

- The pre-push hook's comment explicitly says "coverage flags delegated to pyproject.toml" — this is the canonical signal that any path/coverage fix belongs in `pyproject.toml`, not in the hook script.
- The test file had a `sys.path.insert` workaround at line 9 that masked the bug for direct test runs but not for hooks that didn't set `PYTHONPATH`. Removing it after the `pyproject.toml` fix is required to avoid confusion.
- `pixi.lock` changed as a side effect of the pixi environment resolving — include it in the commit.
- The divergence between hook test count (~1691) and direct pytest count (~3257) is the diagnostic signal: always compare these two numbers when investigating coverage regressions.

## External References

- Related skills: `pytest-coverage-threshold-config`, `mypy-scripts-coverage-extension`, `reenable-precommit-hook`
- pytest pythonpath docs: https://docs.pytest.org/en/stable/reference/reference.html#confval-pythonpath
