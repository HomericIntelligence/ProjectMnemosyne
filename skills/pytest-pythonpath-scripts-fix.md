---
name: pytest-pythonpath-scripts-fix
description: 'TRIGGER CONDITIONS: When analysis/scripts tests fail to collect due to ImportError on a scripts/ module, or when test count is suspiciously low (~1691 vs expected ~3199+), or when a pre-push hook runs fewer tests than a direct pytest invocation.'
category: testing
date: 2026-02-27
version: 1.0.0
user-invocable: false
---

# pytest-pythonpath-scripts-fix

Fix suppressed test collection caused by scripts/ not being on the pytest Python path.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-02-27 |
| Objective | Make all analysis unit tests that import `export_data` (a script in `scripts/`) collect and run under pytest, pre-push hooks, and CI |
| Outcome | Success |

## When to Use

- Analysis tests fail at collection time with `ModuleNotFoundError` for a module in `scripts/`
- Visible test count is artificially suppressed (e.g., ~1691 vs ~3257 expected)
- Pre-push hook or CI collects fewer tests than a direct local `pytest` run
- A test file has a manual `sys.path.insert` workaround pointing at `scripts/`
- You are auditing why coverage appears lower than expected

## Verified Workflow

1. **Identify the root cause**: Run `pixi run pytest --collect-only 2>&1 | grep ERROR` to see collection errors. Look for `ModuleNotFoundError` on a module that lives in `scripts/`.

2. **Check `pyproject.toml`**: Confirm `pythonpath` in `[tool.pytest.ini_options]` does NOT include `"scripts"`.

3. **Add `"scripts"` to `pythonpath`**:

```toml
# pyproject.toml — [tool.pytest.ini_options]
# Before
pythonpath = ["."]
# After
pythonpath = [".", "scripts"]
```

4. **Remove the manual workaround** in the test file (if present):

```python
# Remove these lines from the test file:
import sys
from pathlib import Path
# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
```

Also remove `sys` and `Path` from imports if they are no longer referenced elsewhere.

5. **Verify collection**:

```bash
pixi run pytest tests/unit/analysis/test_export_data.py -v --collect-only
# Expect: all test functions listed, no collection errors
```

6. **Verify full suite**:

```bash
pixi run pytest -x
# Expect: full test count collected, coverage threshold met
```

7. **Run pre-commit** to confirm no ruff/mypy/formatting regressions:

```bash
pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

```toml
# pyproject.toml — exact working config
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".", "scripts"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=scylla",
    "--cov-report=term-missing",
    "--cov-report=html",
    # ...
]
```

Test count before fix: ~1691 collected (collection errors silently suppressed)
Test count after fix: 3257 collected, 3257 passed
Coverage: 78.31% (threshold 75%)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1137, PR #1190 | [notes.md](pytest-pythonpath-scripts-fix.notes.md) |

## References

- Related skills: `pytest-coverage-threshold-config`, `mypy-scripts-coverage-extension`, `reenable-precommit-hook`
- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/1137
