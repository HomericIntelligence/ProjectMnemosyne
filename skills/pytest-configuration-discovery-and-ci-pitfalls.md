---
name: pytest-configuration-discovery-and-ci-pitfalls
description: "Use when: (1) CI Python test job hangs until timeout with no explicit failure — hang signature from asyncio daemon tasks blocking epoll; (2) pytest warns 'ignoring pytest config in pyproject.toml!' or pytest.ini coexists with pyproject.toml causing dual-config conflicts; (3) test collection count is suspiciously low or ImportError on a scripts/ module — conftest.py missing sys.path guard; (4) slim 'pip install pytest' CI jobs silently inherit addopts from pyproject.toml and fail because pytest-cov or other plugins in addopts are not installed; (5) developers run bare pytest and only unit tests are discovered because tests/integration/ is not in testpaths; (6) CI test counts differ from local collection counts — marker-based selection (-m unit, -m integration) inconsistency; (7) a CI matrix has patterns referencing renamed or deleted test files — stale pattern detection; (8) pytest-watch dependency must be replaced with an alternative watcher dependency; (9) test is flaky only in the full suite due to class-level patch.object or hardcoded calendar dates/Unix timestamps; (10) coverage gate fires for a partial test run (e.g. pytest -m integration) but full-suite coverage is fine; (11) a ModuleNotFoundError fires when patching a scripts/ module not on sys.path during single-file pytest runs — add sys.path guard to conftest.py; (12) a test file PASSES when run via explicit path but contributes ZERO coverage in CI because it lives OUTSIDE testpaths and is never collected by the default run — verify COLLECTION with --collect-only, not just that the file passes; (13) deciding whether a sys.path.insert hack in a test is redundant given pythonpath already makes the dir importable as a namespace package."
category: testing
date: 2026-06-21
version: "1.3.0"
user-invocable: false
history: pytest-configuration-discovery-and-ci-pitfalls.history
tags: [pytest, configuration, test-discovery, testpaths, markers, pytest-ini, pyproject-toml, addopts, pythonpath, conftest, sys-path, ci-matrix, stale-patterns, pytest-watcher, coverage, isolation, mock, collect-only, uncollected-tests, namespace-package]
---

# pytest Configuration, Discovery, and CI Pitfalls

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-21 |
| **Objective** | Canonical reference for pytest configuration, test-discovery, and CI pitfalls — dual-config conflicts, testpaths/marker discovery gaps, uncollected stray test files outside testpaths, addopts inheritance in slim CI jobs, stale matrix patterns, watcher dependency replacement, sys.path conftest fixes, and redundant sys.path.insert under pythonpath namespace packages |
| **Outcome** | Synthesised from 6 absorbed skills + uncollected-test-file detection; one general workflow for diagnosing config-shadowing, low collection counts, files silently never collected, partial-run coverage misfires, mock leakage, date bombs, and CI matrix hygiene |
| **Verification** | verified-ci (multiple projects); Step 11 (uncollected stray file) is **verified-ci** — ProjectHephaestus #1547 PR passed full CI (4532 tests passed) |

## When to Use

- CI Python test job hits `timeout-minutes` gate on every run with no explicit failure message (hang from dangling asyncio loop / collection failure)
- pytest log shows `configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)` — dual-config conflict
- Test collection count is suspiciously low (e.g., ~1691 vs ~3257 expected); `ImportError`/`ModuleNotFoundError` on a `scripts/` module at collection time
- Slim `pip install pytest` CI job crashes with `unrecognized arguments: --cov=...` or `ModuleNotFoundError: No module named 'yaml'` — `addopts` inherited from `pyproject.toml`
- Developers run bare `pytest` and only unit tests are discovered because `tests/integration/` is not in `testpaths`
- CI test counts differ from local collection counts — marker-based selection (`-m unit`, `-m integration`) inconsistency
- A CI matrix has `path`+`pattern` entries referencing renamed/deleted test files — stale pattern detection/removal
- `pytest-watch` (unmaintained, last 2018 release) must be replaced with an actively maintained watcher dependency
- A test is flaky only in the full suite due to class-level `patch.object(...__class__...)` or hardcoded calendar dates/Unix timestamps
- Coverage gate fires for a partial run (e.g. `pytest -m integration`) but full-suite coverage is fine
- `ModuleNotFoundError` fires when a `conftest.py` autouse fixture patches a `scripts/` module not on `sys.path` during single-file pytest runs
- A touched/moved/new test file PASSES via an explicit-path run (`pytest path/to/test_x.py`) but you have NOT confirmed the default CI run actually COLLECTS it — the file may live OUTSIDE `testpaths` and contribute zero coverage. Always verify with `--collect-only`, never trust "the tests pass"
- An audit flags a cosmetic `sys.path.insert(0, repo_root)` hack in a test, but the REAL latent defect is that the file is uncollected (outside `testpaths`); relocating the file into a configured testpath matters more than deleting the hack
- Deciding whether a `sys.path.insert` hack is redundant: it IS redundant when (a) the test already imports via the package-prefix form (e.g. `from scripts.show_prompt import ...`) AND (b) `pythonpath` already contains the repo root, since `pythonpath` makes the dir importable as a namespace package with no `__init__.py`

## Verified Workflow

### Quick Reference

```bash
# 1 — Detect pytest.ini shadowing pyproject.toml (dual-config conflict)
pytest --co -q 2>&1 | grep -E "configfile:|WARNING"
ls pytest.ini setup.cfg tox.ini 2>/dev/null
git rm pytest.ini            # if pyproject.toml [tool.pytest.ini_options] is authoritative

# 2 — Detect suppressed collection / low test count (pythonpath gap)
pytest --collect-only 2>&1 | grep ERROR
# Fix: pyproject.toml -> [tool.pytest.ini_options] pythonpath = [".", "scripts"]

# 3 — Discover integration tests under bare `pytest` (testpaths gap)
# pyproject.toml -> testpaths = ["tests/unit", "tests/integration"]
# Add `pytestmark = pytest.mark.integration` atop each integration file
pytest --collect-only -q | tail -1
pytest -m unit --collect-only -q | tail -1
pytest -m integration --collect-only -q | tail -1

# 4 — Slim pip CI job inheriting addopts (--cov) without pytest-cov
pip install pytest pytest-cov pyyaml          # Option A: install missing deps
pytest -o addopts= tests/test_x.py            # Option B: disable inherited addopts
pixi run pytest tests/test_x.py               # Option C (preferred): real env

# 5 — Coverage gate partial-run trap
grep -rn "fail_under\|cov-fail-under" pyproject.toml .github/workflows/ pytest.ini
# Fix: no fail_under in pyproject.toml; --cov-fail-under only on full-suite CI step

# 6 — Stale CI matrix patterns (reference 0 existing files)
grep -r "test_<name>" . --include="*.yml" --include="*.yaml" --include="*.toml"

# 7 — Replace unmaintained pytest-watch
# pixi.toml: pytest-watch = ">=4.2,<5"  ->  pytest-watcher = ">=0.4,<1"   (ptw CLI unchanged)

# 8 — YAML fixture timeout calibration: timeout = max(180, ceil(dur*3/60)*60)
grep -rn "timeout_seconds" tests/unit/
grep -rn "== 300" tests/unit/        # over-inflated fixtures / stale hardcoded assertions

# 9 — Class-level mock leakage / date-bomb detection
grep -rn "patch.object.*__class__" tests/
grep -rn "17[6-9][0-9]\{7\}\|18[0-2][0-9]\{7\}" tests/

# 10 — Stray test file outside testpaths is NEVER collected (passes on explicit run, 0 in CI)
#   PROVE collection — compare EXPECTED test count vs ACTUAL collected:
pixi run pytest --collect-only -q 2>/dev/null | grep -c "test_show_prompt.py::"   # 0 => NOT collected
pixi run pytest tests/test_show_prompt.py                                          # explicit path => 43 pass (masks the gap)
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep testpaths            # is the file's dir listed?
#   Fix: RELOCATE into a configured testpath, not just delete a cosmetic sys.path hack:
git mv tests/test_show_prompt.py tests/unit/scripts/test_show_prompt.py
pixi run pytest --collect-only -q 2>/dev/null | grep -c "test_show_prompt.py::"   # now 43

# 11 — Is a sys.path.insert hack redundant? (pythonpath namespace-package check)
grep -n "sys.path.insert" tests/<file>.py            # the hack
grep -n "^from scripts\.\|^import scripts\." tests/<file>.py   # package-prefix import already?
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep pythonpath          # contains "." (repo root)?
# If BOTH package-prefix import AND pythonpath=["."] => the sys.path.insert is redundant; remove safely.
```

### Detailed Steps

#### Step 1 — pytest.ini Silently Shadows pyproject.toml (dual-config conflict)

**Root cause**: pytest's config-file precedence gives `pytest.ini` absolute priority. When it exists, all `[tool.pytest.ini_options]` in `pyproject.toml` are completely ignored — including `pythonpath`, `asyncio_mode`, `testpaths`, and `addopts`. A missing `pythonpath` then causes `ModuleNotFoundError` at collection; under `asyncio_mode = auto` the dangling event loop makes pytest hang forever (the classic "hangs until timeout, no failure" signature).

```bash
pytest --co -q 2>&1 | grep -E "configfile:|WARNING"   # which config is active?
cat pytest.ini
grep -A 20 '\[tool.pytest.ini_options\]' pyproject.toml
git rm pytest.ini                                      # pyproject.toml is authoritative
git commit -m "fix(test): remove pytest.ini — pyproject.toml is authoritative config"
pytest --co -q 2>&1 | head -20                         # should show configfile: pyproject.toml, no WARNING
```

**Config precedence (highest → lowest)**:

```
pytest.ini       ← WINS — completely silences pyproject.toml
pyproject.toml   ← [tool.pytest.ini_options] ignored if pytest.ini exists
setup.cfg        ← [tool:pytest] section
tox.ini          ← [pytest] section
```

Keep all pytest config in one place (`pyproject.toml`); avoid redundant `pytest.ini`/`setup.cfg` test sections.

#### Step 2 — Missing Directory on pythonpath Suppresses Collection (low test count)

**Root cause**: A non-standard source dir (e.g., `scripts/`) not listed in `[tool.pytest.ini_options] pythonpath` raises `ImportError` at collection. pytest silently skips the failing file — the test count drops with no obvious error unless you inspect `--collect-only`.

```bash
pytest --collect-only 2>&1 | grep ERROR
# pyproject.toml:  pythonpath = ["."]   ->   pythonpath = [".", "scripts"]
# Delete any manual sys.path.insert(...) workaround from individual test files
pytest -x
```

**Diagnostic signal**: hook/CI test count (~1691) vs direct `pytest` count (~3257) diverge — always compare these when investigating coverage regressions.

#### Step 3 — testpaths Gap Hides Integration Tests; Markers Enable Selection

**Root cause**: With `testpaths = ["tests/unit"]`, bare `pytest` discovers only unit tests; integration tests are silently skipped locally even though CI runs them via explicit paths. Expand `testpaths` to include all suites and add module-level markers so `-m unit` / `-m integration` filter cleanly.

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration"]   # was ["tests/unit"]
pythonpath = [".", "scripts"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=<package>", "--cov-report=term-missing"]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
```

Add to the **very top** of every `tests/integration/test_*.py` (before other imports):

```python
import pytest

pytestmark = pytest.mark.integration   # auto-applies to every test function in the file
```

Verify, and confirm CI is immune (explicit CLI paths override `testpaths`):

```bash
pytest --collect-only -q | tail -1            # e.g. 3406 items collected (unit + integration)
pytest -m unit --collect-only -q | tail -1    # e.g. 3188
pytest -m integration --collect-only -q | tail -1  # e.g. 218  (3188 + 218 = 3406)
grep -n "pytest" .github/workflows/*.yml       # e.g. `pytest tests/unit` overrides testpaths
```

ALL integration files must carry the marker; missing markers make `-m unit` leak integration tests. `testpaths` controls *discovery*, markers control *selection* — you need both. Do not use `testpaths = ["tests"]` expecting recursion into subdirs; list each directory explicitly.

#### Step 4 — Slim `pip install pytest` Inherits addopts from pyproject.toml

**Root cause**: `[tool.pytest.ini_options] addopts = "--cov=<pkg> --cov-report=xml"` is injected into **every** pytest invocation, including a lightweight matrix job that ran only `pip install pytest`. With pytest-cov (or pyyaml for tests that `import yaml`) absent, the job crashes with `unrecognized arguments: --cov=...` or `ModuleNotFoundError: No module named 'yaml'`.

```yaml
# Option A (quickest) — install all deps the addopts/tests require
- run: |
    pip install pytest pytest-cov pyyaml
    pytest tests/test_exporter.py

# Option B — override addopts inline (disables inherited flags; also disables coverage)
- run: |
    pip install pytest
    pytest -o addopts= tests/test_exporter.py

# Option C (most robust, zero dep-drift) — use the real project environment
- run: pixi run pytest tests/test_exporter.py
```

| Situation | Recommended Fix |
|-----------|----------------|
| Job must stay pip-only and needs coverage | Option A: add all missing deps |
| Job intentionally skips coverage | Option B: `-o addopts=` |
| Job can use pixi/poetry | Option C: `pixi run pytest` (always prefer) |
| `addopts` will keep accumulating deps | Option C to avoid dep-drift |

#### Step 5 — Coverage `fail_under` Fires on Partial Runs

**Root cause**: `[tool.coverage.report] fail_under = X` fires for **every** pytest invocation. A partial-run job (e.g. `pytest -m integration`) naturally covers fewer statements and trips the gate even when full-suite coverage is fine.

```toml
# pyproject.toml — REMOVE fail_under; keep the rest of the block
[tool.coverage.report]
precision = 2
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
# DO NOT add fail_under here
```

```yaml
# .github/workflows/ci.yml — gate ONLY the full / unit suite
- name: Unit tests (gated)
  run: pixi run pytest -m "not integration" --cov-fail-under=80
- name: Integration tests (no gate)
  run: pixi run pytest -m integration -v      # no --cov-fail-under; or pass --no-cov
```

> Coverage *threshold values* and floor-enforcement policy live in the coverage-config skill (PT02), not here.

#### Step 6 — Stale CI Matrix Patterns (reference deleted/renamed files)

**Root cause**: A CI matrix lists `path`+`pattern` entries; when a test file is renamed/deleted, the pattern can match zero files (dead reference). Detect via an inverse coverage check and remove the dangling token.

```bash
# Confirm the file is actually gone (do not trust the issue description)
ls <project-root>/tests/shared/core/test_<name>.mojo 2>/dev/null || echo "File does not exist"
# Find every reference
grep -r "test_<name>" . --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.mojo" -l
```

Add an inverse check to the coverage-validation script (warnings only — stale patterns are hygiene, not a blocker):

```python
def check_stale_patterns(ci_groups: Dict[str, Dict[str, str]], root_dir: Path) -> List[str]:
    """CI matrix patterns matching 0 existing test files."""
    stale = []
    for name, info in ci_groups.items():
        if not expand_pattern(info["path"], info["pattern"], root_dir):
            stale.append(name)
    return sorted(stale)
```

To remove a stale token, use the Edit tool (not `sed`) on the space-separated `pattern:` string — delete the token and its surrounding space — then re-grep to confirm no references remain. Exit code is unchanged: only the forward check (uncovered files) blocks CI.

#### Step 7 — Replace Unmaintained `pytest-watch` with `pytest-watcher`

**Root cause**: `pytest-watch` (last release 2018) pulls deprecated `docopt 0.6.2`. `pytest-watcher` is the actively maintained fork with pytest 9.x support and ships the identical `ptw` CLI (drop-in).

```toml
# pixi.toml [feature.dev.pypi-dependencies]
# OLD: pytest-watch = ">=4.2,<5"
# NEW: pytest-watcher = ">=0.4,<1"   # ptw CLI unchanged
```

```bash
pixi install                                   # regenerate lock; pulls pytest-watcher, drops watch+docopt
pixi run dev-install                           # restore editable install if pixi re-solve drops it
pixi run which ptw && pixi run ptw --help | head -5
! grep -E '^name = "docopt"' pixi.lock && echo "PASS: docopt absent"
pixi run pytest tests/unit -q                  # all tests still pass
```

Run `pixi install` *first*, then verify the `ptw` entry point; and always confirm the lockfile dropped the deprecated transitive (`docopt`). Do not change the `ptw` invocation in justfile recipes — only comments.

#### Step 8 — sys.path Guard in conftest.py for Single-File Runs

**Root cause**: `pyproject.toml` sets `pythonpath = [".", "scripts"]`, but `pythonpath` injection only happens reliably during a full collection pass from the project root. In single-file mode (`pytest tests/unit/analysis/test_figures.py`) pytest may parse the ini without fully processing `pythonpath`. An autouse fixture that calls `patch("export_data.something")` then raises `ModuleNotFoundError` at fixture setup (before any test body), because `patch()` internally does `importlib.import_module("export_data")`.

```python
# Top of tests/unit/analysis/conftest.py — below stdlib imports, before fixtures
import sys
from pathlib import Path

# Ensure scripts/ is importable when tests run in isolation.
# pyproject.toml sets pythonpath=[".", "scripts"] for full-suite runs, but
# rootdir detection may not inject it during single-file collection.
_scripts_dir = str(Path(__file__).parents[3] / "scripts")   # adjust .parents[N] for conftest depth
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
```

`.parents[N]` = directory levels from conftest up to project root (`tests/conftest.py` → `parents[1]`; `tests/unit/analysis/conftest.py` → `parents[3]`). The guard prevents duplicate entries on full-suite runs. Use the `sys.path` guard (no importable names) rather than a bare `import scripts_module` — ruff F401 strips an unused import, but the guard block survives. Once the guard is in place, do **not** use `create=True` on the patch — the module is fully importable.

#### Step 9 — YAML Fixture `timeout_seconds` Over-Inflated (calibrate from observed duration)

**Root cause**: YAML test fixtures are often created with a generic default `timeout_seconds = 300` that is far too conservative. When many fixtures inherit this default, the cumulative job timeout is inflated (e.g., ~147,900s vs ~29,820s actually needed), tripping a pipeline-level timeout long before any individual test is slow.

**Calibration formula** — 3× observed duration, rounded up to the nearest 60s, with a 180s floor:

```
timeout_seconds = max(180, ceil(actual_duration * 3 / 60) * 60)
```

- Multiplier: 3× observed duration (head-room for CI jitter / cold caches)
- Granularity: round up to the nearest 60s
- Floor: 180s minimum

```python
import math

def calibrate_timeout(actual_duration_seconds: float) -> int:
    raw = actual_duration_seconds * 3
    rounded = math.ceil(raw / 60) * 60
    return max(180, rounded)
```

```bash
# Collect observed durations from recorded results
grep -r "duration_seconds" tests/fixtures/results/ | sort

# CRITICAL: find hardcoded assertions / over-inflated fixtures pinned to the old default
grep -rn "timeout_seconds" tests/unit/
grep -rn "== 300" tests/unit/         # surfaces tests asserting the stale 300s default
# Update any hardcoded assertion to the new floor (180) or make it data-driven, then:
git add tests/fixtures/
git commit -m "test(fixtures): calibrate timeout_seconds using 3x observed duration formula"
```

The `grep -rn "== 300"` check is the key signal: it finds both over-inflated fixtures and tests whose assertions were pinned to the old generic default. Recalibrate the data and convert assertions to be data-driven rather than re-pinning a new magic number.

#### Step 10 — Class-Level Patch Leaks Mock State; Date-Bomb Tests

**Mock leakage**: `patch.object(instance.__class__, "method", ...)` patches the **class**, not the instance. If a test fails mid-context-manager the patch stays active for all subsequent tests — even in other classes — causing order-dependent flakiness that only appears in the full suite. Fix with an autouse teardown:

```python
class TestWithClassLevelPatches:
    @pytest.fixture(autouse=True)
    def _isolate(self):
        yield
        patch.stopall()   # stops any patch left active; safe when none are
```

Find the **source** class with `grep -rn "patch.object.*__class__" tests/`, not the symptom class.

**Date bombs**: tests that hardcode a Unix epoch or calendar string (`"May 8, 5pm"` / `1778284800`) with a fixed tolerance detonate once the clock passes the window. Make them temporally reflexive:

```python
from datetime import datetime, timedelta, timezone

def test_parses_date():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    input_str = future.strftime("%B %-d, %-I%p").lower()   # e.g. "may 12, 4pm"
    parsed = parse_date_string(input_str)
    assert abs(parsed - future.timestamp()) < 86400
```

#### Step 11 — Stray Test File OUTSIDE testpaths Is Silently Never Collected (verified-ci)

> **Verification:** This step is **verified-ci**. The `--collect-only` count (0) and the
> explicit-path run (43 passed) were both observed in ProjectHephaestus issue #1547; the
> relocation fix (`git mv tests/test_show_prompt.py tests/unit/scripts/test_show_prompt.py`)
> passed full CI with 4532 tests passing.

**Root cause**: `pyproject.toml` sets `testpaths = ["tests/unit", "tests/integration"]`. A
test file that sits at the top-level `tests/` dir (e.g. `tests/test_show_prompt.py`, 43
tests) is OUTSIDE both testpaths, so the **default** invocation (`pixi run pytest`, which
honors `testpaths`) never collects it — it contributes ZERO coverage in CI. The trap: an
explicit-path run (`pixi run pytest tests/test_show_prompt.py`) passes all 43 because an
explicit CLI path overrides `testpaths`, masking the gap. "The tests pass" is a lie about
coverage when collection was never verified.

**The discipline**: verify COLLECTION, not just that the file passes. Prove it by comparing
the EXPECTED test count against what the default run ACTUALLY collects:

```bash
# Default run honors testpaths — count collected occurrences of the file's node ids:
pixi run pytest --collect-only -q 2>/dev/null | grep -c "test_show_prompt.py::"
#   -> 0   PROVES the file is not collected by the default invocation
pixi run pytest tests/test_show_prompt.py          # explicit path: 43 passed (overrides testpaths — masks the gap)
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep testpaths   # is the dir listed?
```

A `0` (or any EXPECTED-vs-ACTUAL mismatch) is the smoking gun. Zero collected + green
explicit run = a file outside `testpaths`.

**The fix that matters is RELOCATION, not deleting a cosmetic hack.** If an audit only
flags a cosmetic `sys.path.insert(0, repo_root)` line in the file, that is the symptom, not
the defect. Move the file into a configured testpath so the default run collects it:

```bash
git mv tests/test_show_prompt.py tests/unit/scripts/test_show_prompt.py   # into a configured testpath
# Edit any in-file import that referenced the old location, in the SAME change.
pixi run pytest --collect-only -q 2>/dev/null | grep -c "test_show_prompt.py::"   # now 43 — collected
```

**Risks (verify before relocating)**:

- Confirm no other test/tool imports the file by its OLD path: `grep -rn "tests.test_show_prompt\|tests/test_show_prompt" .` (this is a grep-only check, not exhaustive).
- `git mv` AND the in-file import edit must BOTH land in the change, or history/imports break.
- The destination dir's existing `__init__.py`/`conftest.py` must not collide with the moved module name — unique names are low risk.

#### Step 11b — `sys.path.insert` Hack Is Redundant Under `pythonpath` Namespace Packages

`pythonpath = ["."]` in pytest config makes a directory like `scripts/show_prompt`
importable as a **namespace package** (no `__init__.py` required). So a
`sys.path.insert(0, repo_root)` hack in a test that imports via the package-prefix form
(`from scripts.show_prompt import ...`) is REDUNDANT — pytest has already put the repo root
on the path. Removing such a hack is SAFE when BOTH hold:

1. the import already uses the package-prefix form (`from scripts.<pkg> import ...`), AND
2. `pythonpath` already contains the repo root (`"."`).

```bash
grep -n "sys.path.insert" tests/<file>.py
grep -n "^from scripts\.\|^import scripts\." tests/<file>.py
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep pythonpath
# Both present => delete the sys.path.insert block; the package-prefix import still resolves.
```

This is the inverse of Step 8: Step 8 ADDS a `sys.path` guard for a `scripts/` module not on
the path during single-file runs; here the hack is REMOVABLE because `pythonpath` + the
package-prefix import already cover it. Note: removing the redundant hack is the COSMETIC
win; if the file is also uncollected (Step 11), relocation is the defect that actually
matters — do not stop at the hack.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Increase CI `timeout-minutes` | Raised job timeout 10→20 min to stop the hang | Root cause was an infinite hang from a dangling asyncio loop / collection failure, not slow tests | Never mask a hang by raising the timeout — diagnose collection/config first |
| `sys.path.insert` workaround in test file | Manual path manipulation at the top of a test file | Works for direct runs but not hooks/CI with a different env; ruff strips an unused bare import | Fix belongs in `pyproject.toml pythonpath`, or a `sys.path` guard block (no names) in `conftest.py` |
| Use `testpaths = ["tests"]` (parent dir) | Expected pytest to recurse into subdirectories | pytest treats `tests/` as one directory; subdirs not auto-discovered | List each directory explicitly: `["tests/unit", "tests/integration"]` |
| Expand testpaths but skip markers | Added integration dir to testpaths, omitted `pytestmark` | `pytest -m unit` still ran integration tests (no marker to filter on) | testpaths controls discovery, markers control selection — add both |
| Mark only some integration files | Marked 2 of 5 files | `-m unit` leaked the unmarked integration files | ALL integration files need the marker |
| `pip install pytest` alone in slim CI | Relied on minimal install | `pyproject.toml addopts=--cov` re-injected `--cov`; pytest-cov absent → `unrecognized arguments` | `addopts` is read regardless of env; install deps, `-o addopts=`, or use `pixi run` |
| `pip install pytest pytest-cov` (no pyyaml) | Added cov plugin only | Tests did `import yaml` → `ModuleNotFoundError: No module named 'yaml'` | Slim jobs must list every transitive the tests need, or use the real env |
| Lower `fail_under` to match partial run | Edited 80→78 in pyproject.toml | Next full run hits 96%, next partial run hits 78% again | Don't lower the gate — apply `--cov-fail-under` only to the full-suite CI step |
| Remove `[tool.coverage.report]` wholesale | Deleted the whole block | Lost `precision`/`exclude_lines` too | Surgical: delete only the `fail_under` line |
| Raise the YAML fixture `timeout_seconds` default | Bumped the generic `300` default higher to stop pipeline timeouts | Inflated the cumulative job timeout further (~147,900s) — fewer fixtures, same magic-number problem | Calibrate per fixture: `max(180, ceil(observed*3/60)*60)`; grep `== 300` for stale assertions |
| Add `_isolate` teardown to the wrong class | Added fixture to a class that didn't leak | Leak originates elsewhere; fixing the symptom class is a no-op | `grep` for `patch.object.*__class__` to find the source class |
| Widen date tolerance 24h→7d | Stretched the window on a hardcoded epoch | Defers the failure ~5 days; doesn't eliminate it | Make the test temporally reflexive, not the tolerance bigger |
| Verify `ptw` CLI before `pixi install` | Checked the entry point before re-solving the lock | Premature — the new package's entry point isn't installed yet | `pixi install` first, then verify `ptw`; pytest-watcher ships `ptw` |
| Confirm file deletion via background `find` / pre-deletion glob | Assumed the issue description was current | Output unavailable when needed; file was already gone | Verify existence synchronously with `ls`/glob before editing patterns |
| Trusted explicit-path run | Ran `pytest tests/test_show_prompt.py` → 43 passed → assumed the file was covered in CI | The file lived OUTSIDE `testpaths`, so the default run collected 0; an explicit CLI path overrides `testpaths` and masks the gap | Verify COLLECTION with `--collect-only` (compare EXPECTED vs ACTUAL count), never trust "the tests pass" |
| Deleted only the cosmetic `sys.path.insert` the audit flagged | Removed the hack the audit pointed at and called it done | The real latent defect was that the file was uncollected (outside testpaths); removing the hack left 43 tests still contributing zero coverage | RELOCATE the file into a configured testpath (`git mv`); the cosmetic hack is the symptom, not the defect |
| Added a new `__init__.py`-bearing dir and moved the file without checking import refs | `git mv` only, no in-file import edit / no old-path grep | An import referencing the old path (or a name collision in the destination) breaks history/imports | `git mv` + the in-file import edit must BOTH land; `grep` for old-path references first |

## Results & Parameters

### Authoritative pyproject.toml Reference

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests/unit", "tests/integration"]   # list every suite explicitly
pythonpath = [".", "scripts"]                      # include all non-standard source dirs
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=<package>", "--cov-report=term-missing"]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
# No fail_under here — put --cov-fail-under only in the full-suite CI step

[tool.coverage.report]
precision = 2
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
# DO NOT add fail_under — it fires for every pytest invocation
```

### Test-Discovery Expected Outputs (example)

| Command | Count | Notes |
|---------|-------|-------|
| `pytest --collect-only -q` | 3406 | all unit + integration |
| `pytest -m unit --collect-only -q` | 3188 | unit only |
| `pytest -m integration --collect-only -q` | 218 | integration only (3188 + 218 = 3406) |
| direct `pytest` vs hook/CI count | 3257 vs 1691 | divergence ⇒ pythonpath/config gap |

### Uncollected Stray Test File — Diagnostic (copy-paste)

```bash
# PROVE a touched/moved test file is collected by the DEFAULT run (honors testpaths):
pixi run pytest --collect-only -q 2>/dev/null | grep -c "<testfile>.py::"
# Expected: the file's real test count (e.g. 43).  ACTUAL 0 => file NOT collected (outside testpaths).

# Contrast — explicit path overrides testpaths and HIDES the gap:
pixi run pytest tests/<testfile>.py        # passes (e.g. 43 passed) even when default run collects 0

# Confirm the directory is/ isn't in testpaths:
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep testpaths

# Fix — relocate into a configured testpath, then re-prove collection:
git mv tests/<testfile>.py tests/unit/scripts/<testfile>.py
pixi run pytest --collect-only -q 2>/dev/null | grep -c "<testfile>.py::"   # now 43
```

| Command | Expected (collected) | Meaning |
|---------|----------------------|---------|
| `pytest --collect-only -q \| grep -c "test_show_prompt.py::"` (file outside testpaths) | `0` | NOT collected by default CI run |
| `pytest tests/test_show_prompt.py` (explicit path) | `43 passed` | Explicit path overrides testpaths — masks the gap |
| `pytest --collect-only -q \| grep -c "test_show_prompt.py::"` (after `git mv` into `tests/unit/scripts/`) | `43` | Now collected by the default run |

### Redundant `sys.path.insert` Under `pythonpath` (namespace package)

```bash
grep -n "sys.path.insert" tests/<file>.py                       # the hack
grep -n "^from scripts\.\|^import scripts\." tests/<file>.py      # package-prefix import?
grep -A2 '\[tool.pytest.ini_options\]' pyproject.toml | grep pythonpath   # contains "."?
```

| Condition | sys.path.insert verdict |
|-----------|-------------------------|
| package-prefix import (`from scripts.pkg import ...`) AND `pythonpath = ["."]` | REDUNDANT — safe to remove (`pythonpath` makes `scripts/pkg` importable as a namespace package, no `__init__.py` needed) |
| bare-name import (`import export_data`) AND dir not on path during single-file runs | NEEDED — use the conftest `sys.path` guard (Step 8) instead |

### Coverage Gate Placement

| Run command | Tests | Typical cover | Gate-safe at `fail_under=80`? |
|-------------|-------|---------------|-------------------------------|
| `pytest` | All | 96% | YES |
| `pytest -m "not integration"` | Unit | 92% | YES |
| `pytest -m integration` | Integ | ~78% | NO — partial-run trap |
| `pytest tests/foo.py::TestBar` | 5 | ~50% | NO — extreme partial run |

### sys.path Guard Depth

| conftest location | `.parents[N]` |
|-------------------|---------------|
| `tests/conftest.py` | `parents[1]` |
| `tests/unit/conftest.py` | `parents[2]` |
| `tests/unit/analysis/conftest.py` | `parents[3]` |

### Fixture Timeout Calibration Table

Formula: `timeout_seconds = max(180, ceil(actual_duration * 3 / 60) * 60)`

| Observed Duration | Raw (3×) | Rounded to 60s | Final |
|-------------------|----------|----------------|-------|
| 28s | 84s | 120s | 180s (floor) |
| 45s | 135s | 180s | 180s |
| 72s | 216s | 240s | 240s |
| 150s | 450s | 480s | 480s |
| 300s | 900s | 900s | 900s |

### pytest-watch → pytest-watcher Lock Delta

| Before | After |
|--------|-------|
| `pytest-watch 4.2.0` + transitive `docopt 0.6.2` | `pytest-watcher 0.4.x`; docopt absent |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | CI `Python Tests` job hung every run; branch `fix/security-scan-gitleaks-jq` | pytest.ini shadowed pyproject.toml `pythonpath` |
| ProjectScylla | Issue #1137, PR #1190 — scripts/ pythonpath gap | Test count dropped 3257 → 1691; fixed by adding `"scripts"` to `pythonpath` |
| ProjectScylla | Issue #1196, PR #1303 — single-file isolation `ModuleNotFoundError: export_data` | sys.path guard in conftest.py; 385 analysis + 3584 full-suite tests pass |
| ProjectScylla | Issue #1131 — `patch.object.__class__` leaking mock state | 3799 tests pass after autouse `_isolate` fixture |
| ProjectHephaestus | Issue #740, PR #925 — testpaths expansion + markers | Bare `pytest` discovers 3406 (3188 unit + 218 integration); 84.80% coverage |
| ProjectHephaestus | Issue #746, PR #921 — pytest-watch → pytest-watcher | docopt removed; 3170 tests pass; `ptw` CLI unchanged |
| ProjectHephaestus | PR #884 — 47 YAML fixture files with `timeout_seconds = 300` default | Calibrated via `max(180, ceil(dur*3/60)*60)`; total timeout ~147,900s → ~29,820s (~80% reduction) |
| ProjectHephaestus | PR #367 — `test_rate_limit.py` hardcoded epoch `1778284800` | Began failing once clock passed May 8 2026 5pm UTC; made temporally reflexive |
| ProjectArgus | CI "Test exporter" matrix — PRs #273, #289 | slim `pip install pytest pytest-cov` missing `pyyaml`; addopts `--cov` inherited |
| ProjectHermes | PR #475 — `fail_under = 80` in pyproject.toml | integration-only CI job failed at 78.52%; gate moved to full-suite step |
| ProjectOdyssey | Issue #3357, PR #4001 — stale CI pattern detection/removal | `check_stale_patterns()` added (13 tests pass); dangling matrix tokens removed |
| ProjectHephaestus | Issue #1547 — `tests/test_show_prompt.py` outside testpaths | **verified-ci**: `--collect-only` count `0`; explicit-path run `43 passed`; fix = `git mv` into `tests/unit/scripts/`; redundant `sys.path.insert` removed (import was package-prefix + `pythonpath=["."]`); PR passed full CI with 4532 tests |
