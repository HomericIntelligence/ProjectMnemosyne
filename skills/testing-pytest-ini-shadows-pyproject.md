---
name: testing-pytest-ini-shadows-pyproject
description: "TRIGGER CONDITIONS: (1) CI Python test job hangs until timeout with no visible failure, (2) pytest warns 'ignoring pytest config in pyproject.toml!', (3) tests fail with ModuleNotFoundError even though pythonpath is set in pyproject.toml, (4) asyncio tests hang indefinitely after import failure."
category: testing
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# pytest.ini Silently Shadows pyproject.toml Config

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Diagnose CI Python test job hanging until timeout; fix root cause |
| **Outcome** | Success — deleting `pytest.ini` restored `pyproject.toml` authority and tests collected correctly |
| **Verification** | verified-local (CI outcome pending at time of capture) |

## When to Use

- CI Python test job hits `timeout-minutes` gate on every run with no explicit failure message
- pytest log shows: `configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)`
- Tests fail with `ModuleNotFoundError` on `import src.*` even though `pythonpath = ["src"]` is in `pyproject.toml`
- asyncio-mode tests appear to hang indefinitely after a collection error
- A `pytest.ini` exists in the repo root alongside `pyproject.toml`

## Verified Workflow

### Quick Reference

```bash
# Check which config file pytest is actually using
pytest --co -q 2>&1 | grep "configfile:"

# Check precedence — if pytest.ini exists, pyproject.toml is ignored
ls pytest.ini setup.cfg tox.ini 2>/dev/null

# Fix: delete pytest.ini if pyproject.toml [tool.pytest.ini_options] is authoritative
git rm pytest.ini
```

### Detailed Steps

1. **Identify the shadowing**: Run pytest with collection-only and grep for the config file warning:

   ```bash
   pytest --co -q 2>&1 | grep -E "configfile:|WARNING"
   # If output contains: configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
   # → pytest.ini is active and pyproject.toml settings are completely ignored
   ```

2. **Audit what each file contains**: Compare `pytest.ini` to `[tool.pytest.ini_options]` in `pyproject.toml`:

   ```bash
   cat pytest.ini
   grep -A 20 '\[tool.pytest.ini_options\]' pyproject.toml
   ```

   Look for settings present in `pyproject.toml` but absent from `pytest.ini`, especially:
   - `pythonpath = ["src"]` — if missing, all `import src.*` fail at collection
   - `addopts` with coverage flags
   - `asyncio_mode`

3. **Confirm the hang mechanism**: With `pythonpath` missing, test collection fails with `ModuleNotFoundError`. In `asyncio_mode = auto`, failed imports leave dangling event loop tasks. Pytest waits for those tasks forever — the process never exits until the OS timeout kills it.

4. **Fix**: If `pyproject.toml` is the authoritative config (contains all necessary settings), delete `pytest.ini`:

   ```bash
   git rm pytest.ini
   git commit -m "fix(test): remove pytest.ini — pyproject.toml is authoritative config"
   ```

5. **Verify collection succeeds**:

   ```bash
   pytest --co -q 2>&1 | head -20
   # Should show: configfile: pyproject.toml (no WARNING)
   # All test modules should collect without ModuleNotFoundError
   ```

6. **Verify tests pass**:

   ```bash
   pytest -x
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Increase `timeout-minutes` | Raised CI job timeout from 10 to 20 minutes | Rejected by team — tests exceeding 10 min are considered buggy; and the root cause was not slow tests but infinite hang | Never mask a hang by increasing timeout; diagnose the hang |
| Inspect test source for slow `asyncio.sleep` | Found 3 tests with `asyncio.sleep(10.0)` — filed as issue #480 | These were not the cause of the CI timeout; they run fine once imports succeed | Collection failures cause hangs independent of test execution time |

## Results & Parameters

### pytest config precedence (highest to lowest)

```
pytest.ini          ← WINS — completely silences pyproject.toml
pyproject.toml      ← [tool.pytest.ini_options] ignored if pytest.ini exists
setup.cfg           ← [tool:pytest] section
tox.ini             ← [pytest] section
```

### Minimal pytest.ini that caused the issue

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

Note: `python_files`, `python_classes`, `python_functions` are pytest defaults — the file was functionally redundant except for `asyncio_mode`, which was also in `pyproject.toml`.

### Authoritative pyproject.toml config (after fix)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]        # CRITICAL — was absent from pytest.ini
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=keystone", "--cov-report=term-missing"]
```

### Failure cascade when `pythonpath` is missing

```
pytest collects test files
  → test file: from keystone.transport import MessageBus
  → ModuleNotFoundError: No module named 'keystone'
  → asyncio_mode = auto creates event loop for coroutine tests
  → import failure leaves event loop task dangling
  → pytest waits for event loop tasks to complete
  → process hangs indefinitely until OS timeout kills the job
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | CI `Python Tests` job hung on every run; branch `fix/security-scan-gitleaks-jq` | pytest.ini had no `pythonpath`, pyproject.toml had `pythonpath = ["src"]` |
