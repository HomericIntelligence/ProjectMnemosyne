---
name: pytest-configuration-and-isolation-pitfalls
description: "Use when: (1) CI Python test job hangs until timeout with no explicit failure, (2) pytest warns 'ignoring pytest config in pyproject.toml!' or a pytest.ini coexists with pyproject.toml, (3) test collection count is suspiciously low or ImportError on a scripts/ module, (4) coverage gate fires for a partial test run (e.g., pytest -m integration) but full-suite coverage is fine, (5) a test is flaky only in the full suite and uses class-level patch.object, (6) YAML fixture timeouts are far too conservative and inflate CI job duration, (7) a test suddenly fails in CI with no code changes and references hardcoded calendar dates or Unix timestamps."
category: testing
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: pytest-configuration-and-isolation-pitfalls.history
tags: [pytest, configuration, isolation, coverage, mock, fixture, timeout, date-bomb, pythonpath, fail-under]
---

# pytest Configuration and Isolation Pitfalls

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Canonical reference for pytest setup/configuration problems that cause mysterious test failures independent of the code under test |
| **Outcome** | Synthesised from 6 absorbed skills; covers pytest.ini shadowing, pythonpath gaps, coverage gate misfires, mock state leakage, fixture timeout over-inflation, and date-bomb tests |
| **Verification** | verified-ci (multiple projects) |

## When to Use

- CI Python test job hits `timeout-minutes` gate on every run with no explicit failure message
- pytest log shows `configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)`
- Test collection count is artificially low (e.g., ~1691 vs ~3257 expected); `ImportError` on a `scripts/` module at collection time
- Coverage gate fires with "Required test coverage of X% not reached" from a partial-run job (e.g., `-m integration`) while full-suite coverage is fine
- A test is **flaky only in the full suite**, passes in isolation, and the test class uses `patch.object(instance.__class__, ...)`
- Batch E2E runs finish but YAML fixture `timeout_seconds` values are far too conservative, causing job-level timeouts
- A test was passing for weeks or months and suddenly fails with no code changes; the test references a specific calendar date or hardcoded Unix timestamp

## Verified Workflow

### Quick Reference

```bash
# 1 — Detect pytest.ini shadowing pyproject.toml
pytest --co -q 2>&1 | grep "configfile:"
ls pytest.ini setup.cfg tox.ini 2>/dev/null
git rm pytest.ini  # if pyproject.toml [tool.pytest.ini_options] is authoritative

# 2 — Detect suppressed test collection (pythonpath gap)
pixi run pytest --collect-only 2>&1 | grep ERROR
# Fix: add the missing directory to pythonpath in pyproject.toml
# [tool.pytest.ini_options] pythonpath = [".", "scripts"]

# 3 — Detect coverage gate partial-run trap
grep -rn "fail_under\|cov-fail-under" pyproject.toml .github/workflows/ pytest.ini setup.cfg 2>/dev/null
# Fix: remove fail_under from pyproject.toml; put --cov-fail-under only on the full-suite CI step

# 4 — Detect class-level mock state leakage
grep -rn "patch.object.*__class__" tests/
# Fix: add autouse teardown fixture with patch.stopall() to the leaking class

# 5 — Detect date-bomb tests
grep -rn "17[6-9][0-9]\{7\}\|18[0-2][0-9]\{7\}" tests/
grep -rn '"[A-Z][a-z]* [0-9]\{1,2\},\? [0-9]\{1,2\}[ap]m"' tests/
```

### Pitfall 1 — pytest.ini Silently Shadows pyproject.toml

**Root cause**: pytest's config-file precedence gives `pytest.ini` absolute priority; when it exists, all `[tool.pytest.ini_options]` in `pyproject.toml` are completely ignored — including `pythonpath`, `asyncio_mode`, and `addopts`. A missing `pythonpath` causes `ModuleNotFoundError` at collection; in `asyncio_mode = auto` the dangling event loop makes pytest hang forever.

```bash
# Check which config is active
pytest --co -q 2>&1 | grep -E "configfile:|WARNING"

# Audit both files
cat pytest.ini
grep -A 20 '\[tool.pytest.ini_options\]' pyproject.toml

# Fix: delete pytest.ini
git rm pytest.ini
git commit -m "fix(test): remove pytest.ini — pyproject.toml is authoritative config"

# Verify
pytest --co -q 2>&1 | head -20  # should show: configfile: pyproject.toml (no WARNING)
```

**Config precedence (highest to lowest)**:

```
pytest.ini          ← WINS — completely silences pyproject.toml
pyproject.toml      ← [tool.pytest.ini_options] ignored if pytest.ini exists
setup.cfg           ← [tool:pytest] section
tox.ini             ← [pytest] section
```

### Pitfall 2 — Missing Directory on pythonpath Suppresses Collection

**Root cause**: `scripts/` (or any non-standard directory) not listed in `[tool.pytest.ini_options] pythonpath` causes `ImportError` at collection. pytest silently skips the failing file — test count drops with no obvious error unless you inspect `--collect-only` output.

```bash
# Diagnose
pixi run pytest --collect-only 2>&1 | grep ERROR

# Fix in pyproject.toml
# Before:  pythonpath = ["."]
# After:   pythonpath = [".", "scripts"]

# Remove manual workaround from test files (if present)
# Delete lines like: sys.path.insert(0, str(Path(__file__).parent / "scripts"))

# Verify
pixi run pytest tests/unit/analysis/test_export_data.py -v --collect-only
pixi run pytest -x
pre-commit run --all-files
```

**Diagnostic signal**: hook/CI test count (~1691) vs direct `pytest` count (~3257) diverge — always compare these when investigating coverage regressions.

### Pitfall 3 — Coverage fail\_under Fires on Partial Runs

**Root cause**: `[tool.coverage.report] fail_under = X` in `pyproject.toml` fires for **every** pytest invocation. A partial-run job (e.g., `pytest -m integration`) naturally covers fewer statements and trips the gate even when full-suite coverage is fine.

```bash
# Diagnose
grep -rn "fail_under\|cov-fail-under" pyproject.toml .github/workflows/ pytest.ini setup.cfg 2>/dev/null
pixi run pytest -m integration --cov | tail -25   # see partial-run coverage
pixi run pytest --cov | tail -25                  # see full-suite coverage

# Symptom in CI logs
# FAIL Required test coverage of 80.0% not reached. Total coverage: 78.52%
# (job name contains "Integration" or similar — partial-run trap)
```

**Fix — move gate to CI workflow, not pyproject.toml**:

```toml
# pyproject.toml — REMOVE fail_under; keep everything else
[tool.coverage.report]
precision = 2
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
# DO NOT put fail_under here
```

```yaml
# .github/workflows/ci.yml
- name: Unit tests (full suite, gated)
  run: pixi run pytest -m "not integration" --cov-fail-under=80
- name: Integration tests (no gate)
  run: pixi run pytest -m integration -v   # no --cov-fail-under
```

**Alternative for partial jobs**: pass `--no-cov` to disable coverage measurement entirely for the partial run.

### Pitfall 4 — Class-Level Patch Leaks Mock State Between Tests

**Root cause**: `patch.object(instance.__class__, "method", ...)` patches the **class**, not the instance. If a test fails mid-context-manager, the patch remains active for all subsequent tests — even in different classes — causing order-dependent failures.

```bash
# Find leaking patterns
grep -rn "patch.object.*__class__" tests/
```

**Fix — add autouse teardown with patch.stopall()**:

```python
from collections.abc import Generator
from unittest.mock import patch
import pytest

class TestWithClassLevelPatches:
    @pytest.fixture(autouse=True)
    def _isolate(self) -> Generator[None, None, None]:
        """Ensure no class-level mock state bleeds into subsequent tests."""
        yield
        patch.stopall()  # safe to call even when no patches are active
```

`patch.stopall()` stops all patches started via `patch()` or `patch.object()` that haven't been explicitly stopped. Move per-method `from unittest.mock import patch` imports to module level after adding this fixture.

### Pitfall 5 — YAML Fixture Timeouts Over-Inflated

**Root cause**: YAML test fixtures are often created with a generic default `timeout_seconds = 300` that is far too conservative. When many fixtures use this default, the cumulative job timeout is inflated (e.g., ~147,900s vs ~29,820s needed), causing CI jobs to time out at the pipeline level.

**Calibration formula**:

```
timeout_seconds = max(180, ceil(actual_duration * 3 / 60) * 60)
```

- Multiplier: 3× observed duration
- Granularity: round up to nearest 60s
- Floor: 180s minimum

```python
import math

def calibrate_timeout(actual_duration_seconds: float) -> int:
    raw = actual_duration_seconds * 3
    rounded = math.ceil(raw / 60) * 60
    return max(180, rounded)
```

```bash
# Collect observed durations
grep -r "duration_seconds" tests/fixtures/results/ | sort

# CRITICAL: check for hardcoded assertions referencing old default
grep -rn "timeout_seconds" tests/unit/
grep -rn "== 300" tests/unit/
# Update any hardcoded assertions to the new floor (180) or make data-driven

# Commit
git add tests/fixtures/
git commit -m "test(fixtures): calibrate timeout_seconds using 3x observed duration formula"
```

### Pitfall 6 — Date-Bomb: Hardcoded Timestamps That Expire

**Root cause**: Tests that hardcode a Unix epoch or calendar date string (e.g., `"May 8, 5pm"` / `1778284800`) with a fixed tolerance (e.g., `< 86400`) pass when written but detonate once the system clock moves past the tolerance window.

```bash
# Detect date bombs
grep -rn "17[6-9][0-9]\{7\}\|18[0-2][0-9]\{7\}" tests/
grep -rn "abs(.*parsed.*-.*[0-9]\{10\})" tests/
grep -rn '"[A-Z][a-z]* [0-9]\{1,2\},\? [0-9]\{1,2\}[ap]m"' tests/
```

**Fix — make tests temporally reflexive**:

```python
# BAD — date bomb
def test_parses_date():
    parsed = parse_date_string("May 8, 5pm")
    expected_epoch = 1778284800  # hardcoded!
    assert abs(parsed - expected_epoch) < 86400

# GOOD — temporally reflexive
from datetime import datetime, timedelta, timezone

def test_parses_date():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=2)
    input_str = future.strftime("%B %-d, %-I%p").lower()  # e.g., "may 12, 4pm"
    expected_epoch = future.timestamp()
    parsed = parse_date_string(input_str)
    assert abs(parsed - expected_epoch) < 86400
```

**Template for any relative-date parser test**:

```python
from datetime import datetime, timedelta, timezone

def test_parses_<unit>_relative():
    now = datetime.now(timezone.utc)
    target = now + timedelta(<offset>)
    input_str = target.strftime("<format>")
    expected = target.timestamp()
    parsed = parse_date_string(input_str)
    assert abs(parsed - expected) < <tolerance_seconds>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Increase CI `timeout-minutes` | Raised job timeout from 10 to 20 min to stop the hang | Rejected by team; root cause was not slow tests but infinite hang from dangling asyncio event loop | Never mask a hang by increasing timeout — diagnose it |
| Inspect test source for slow `asyncio.sleep` | Found tests with `asyncio.sleep(10.0)` and filed as issue | These were not the cause; they run fine once imports succeed | Collection failures cause hangs independent of test execution time |
| Lower `fail_under` to match partial-run coverage | Edited `pyproject.toml` from 80 to 78 | Next full-suite run still shows 96%; next partial run hits 78% again with no explanation | Don't lower the gate — fix the configuration so the gate only applies to full-suite runs |
| Remove `[tool.coverage.report]` entirely | Wholesale delete of the block | Removed `precision` and `exclude_lines` along with `fail_under` | Surgical fix: delete only the `fail_under` line, keep the rest of the block |
| Add teardown only to the wrong test class | Added `_isolate` fixture to `TestEvalOrchestratorEndToEnd` | The leak originates in `TestEvalOrchestratorWithFixture`; fixing the wrong class has no effect | `grep -rn "patch.object.*__class__"` to find the source, not the symptom class |
| Use `patch.object(instance, "method", ...)` to fix leakage | Would fix root cause | Out of scope — the test predated the session | Autouse `_isolate` fixture with `patch.stopall()` is the least-invasive fix |
| Increase date tolerance from 24h to 7 days | Widen the tolerance window on a hardcoded timestamp | Defers the failure by ~5 days; does not eliminate it | Tolerance widening is a band-aid; make the test temporally reflexive |
| `sys.path.insert` workaround in test file | Manual path manipulation at line 4-9 of test file | Works for direct runs but not for hooks or CI that don't inherit the same env | Fix belongs in `pyproject.toml pythonpath`, not in test source |

## Results & Parameters

### Authoritative pyproject.toml Config Reference

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = [".", "scripts"]   # include all non-standard source dirs
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=<package>", "--cov-report=term-missing"]
# No fail_under here — put --cov-fail-under only in CI workflow

[tool.coverage.run]
source = ["<package>"]

[tool.coverage.report]
precision = 2
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
# DO NOT add fail_under — it fires for every pytest invocation
```

### Coverage Gate Placement Reference

| Run command | Tests run | Typical cover | Gate-safe at `fail_under=80`? |
|-------------|-----------|---------------|-------------------------------|
| `pytest` | All | 96% | YES |
| `pytest -m "not integration"` | Unit only | 92% | YES |
| `pytest -m integration` | Integ only | ~78% | NO — partial-run trap |
| `pytest tests/foo.py::TestBar` | 5 tests | ~50% | NO — extreme partial-run |
| `pytest --cov-append` (cumulative) | Cumulative | 96% | YES |

### Fixture Timeout Calibration Table

| Observed Duration | Raw (3×) | Rounded to 60s | Final |
|-------------------|----------|----------------|-------|
| 28s | 84s | 120s | 180s (floor) |
| 45s | 135s | 180s | 180s |
| 72s | 216s | 240s | 240s |
| 150s | 450s | 480s | 480s |
| 300s | 900s | 900s | 900s |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | CI `Python Tests` job hung on every run; branch `fix/security-scan-gitleaks-jq` | pytest.ini missing `pythonpath`; pyproject.toml had `pythonpath = ["src"]` |
| ProjectScylla | Issue #1137, PR #1190 — scripts/ pythonpath gap | Test count dropped from 3257 to 1691; fixed by adding `"scripts"` to `pythonpath` |
| ProjectHermes | PR #475 — `fail_under = 80` added to pyproject.toml; integration-only CI jobs began failing at 78.52% | Worked around by adding integration tests; real fix deferred to follow-up |
| ProjectScylla | Issue #1131 — `patch.object.__class__` leaking mock state | 3799 tests all pass after autouse `_isolate` fixture added |
| ProjectHephaestus | PR #884 — 47 YAML fixture files with `timeout_seconds = 300` default | Total timeout sum reduced from ~147,900s to ~29,820s (~80% reduction) |
| ProjectHephaestus | PR #367 — `test_rate_limit.py` hardcoded epoch `1778284800` | Test began failing in CI after the system clock passed May 8, 2026 5pm UTC |
