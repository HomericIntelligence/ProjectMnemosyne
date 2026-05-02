# Session Notes — lazy-clone-dependency

## Session Date
2026-03-03

## Issue
[ProjectScylla #1324](https://github.com/HomericIntelligence/ProjectScylla/issues/1324) — `plan_issues.py` was silently skipping the advise step when ProjectMnemosyne was absent.

## Symptom
```
2026-03-03 06:36:36 [WARNING] scylla.automation.planner: ProjectMnemosyne not found, skipping advise step
^C2026-03-03 06:36:43 [ERROR] scylla.automation.planner: Failed to plan issue #1322: Claude failed:
```

The planning continued but produced degraded output (no advise findings injected).

## Root Cause
`_run_advise()` at `scylla/automation/planner.py:333` had an early-return guard:
```python
if not mnemosyne_root.exists():
    logger.warning("... skipping advise step")
    return ""
```

## Fix Summary
1. Added `import fcntl` and `from pathlib import Path` to imports.
2. Added class-level `_mnemosyne_lock: threading.Lock = threading.Lock()`.
3. Added `_ensure_mnemosyne(mnemosyne_root: Path) -> bool` with double-locking (threading + fcntl).
4. Changed the guard in `_run_advise()` to call `_ensure_mnemosyne()` first.

## Test Count
- Before: 11 tests in `test_planner.py`
- After: 15 tests (added `TestEnsureMnemosyne` class with 4 tests + 1 updated test in `TestRunAdvise`)
- Full suite: 3119 tests, all passing.

## PR
https://github.com/HomericIntelligence/ProjectScylla/pull/1326

## Pre-commit Results
All hooks passed (ruff-format, ruff-check, mypy, security checks).

## Design Decisions
- Used `fcntl` (POSIX) rather than a cross-platform file lock library to keep dependencies minimal.
- Lock file at `<mnemosyne_root.parent>/.mnemosyne.lock` (not inside clone dest) so it survives a failed partial clone.
- Failures are non-fatal — `_ensure_mnemosyne` returns `False` and advise is skipped (same UX as before, but only after a genuine recovery attempt).
