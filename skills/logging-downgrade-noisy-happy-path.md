---
name: logging-downgrade-noisy-happy-path
description: "Downgrade noisy WARNING and ERROR log levels for happy-path scenarios that are not failures — to INFO when the message is still worth surfacing, or to DEBUG (verbose-only) when it describes a CORRECT automatic fallback the operator rarely needs to see. Use when: (1) a script checks for optional files/configs and logs WARNING when they're absent (but this is an acceptable skip path), (2) a validation function logs ERROR on format mismatch but continues successfully, (3) test suites log WARNING for expected fallback behavior, (4) any logging statement fires in scenarios that return True/success and are not genuine failures, (5) a benign fallback message logs at WARNING on every run or once per loop iteration and the user wants it shown only under -v/--verbose, (6) you need to downgrade WARNING->DEBUG so a benign-fallback message is silent by default but visible in verbose mode. KEY discriminator: keep genuinely-actionable misconfiguration (a human supplied a wrong value) at WARNING while downgrading the benign default (an unset value that falls back correctly) to DEBUG."
category: ci-cd
date: 2026-06-20
version: "1.1.0"
user-invocable: false
history: logging-downgrade-noisy-happy-path.history
verification: verified-ci
tags:
  - python
  - logging
  - observability
  - happy-path
  - noise-reduction
  - TDD
  - capsys
  - happy-path-logging
  - verbose-gating
  - debug-level
---

# Logging: Downgrade Noisy Messages in Happy Path

## Overview

| Field | Value |
| ------- | ------- |
| **Theme** | Downgrade WARNING and ERROR log levels in happy-path scenarios where execution succeeds — to INFO when still worth surfacing, or to DEBUG (verbose-only) when the message describes a correct automatic fallback the operator rarely needs to see |
| **Scope** | Optional configuration files, absent CI matrices, acceptable fallback paths, benign env-var defaults, per-iteration cross-repo path warnings, tests for optional behavior |
| **Diagnostic strategy** | Ask: "Does this code path return success (True, 0, success)?" If yes, the log should not be WARNING/ERROR. Then ask: "Is this an automatic fallback that always works, or did a human supply something wrong?" Benign-fallback -> DEBUG (verbose-only); human-supplied-wrong -> keep WARNING |
| **Languages** | Python 3.10+ (but pattern applies to any language) |

## When to Use

- A script checks for an optional CI workflow file and logs WARNING when absent — but absence is OK, function returns True
- A validation function logs ERROR when a python-version matrix is missing — but missing matrix is acceptable, function returns True
- Test suites log WARNING during expected fallback behavior that exercises both success branches
- Any logging statement fires when execution succeeds but was labeled WARNING or ERROR
- Pre-commit hooks or CI scripts have noisy logs cluttering CI output for legitimate skip paths
- Monitoring/alerting systems trigger on WARNING but the scenario was never a failure
- A benign fallback message logs at WARNING (or INFO) on **every default run**, and the user asks to show it "only in verbose mode" — downgrade WARNING/INFO -> DEBUG so it is silent by default and visible under `-v`/`--verbose` (when `-v` maps to root log level DEBUG)
- A benign fallback message fires at WARNING **once per loop iteration** (e.g. once per issue processed) — per-iteration WARNING noise is an especially strong signal to downgrade to DEBUG
- An env var is unset and the code falls back to a correct default (the unset case is the normal case) — downgrade the "not set, using default" message to DEBUG, but keep the "set to a value that does not exist, falling back" message at WARNING (a human supplied a wrong path)
- A cross-repo / cross-context path is "not under repo_root" but the absolute path works fine and that situation is expected — downgrade to DEBUG

## Verified Workflow

### Quick Reference: Decision Tree

```
Does the code path execute successfully (returns True/0/success)?
├─ YES → It should NOT be WARNING/ERROR. Choose INFO vs DEBUG:
│   ├─ Is this an automatic fallback that ALWAYS works and the operator
│   │  rarely needs to see (e.g. unset env var -> correct default,
│   │  cross-repo absolute path that works)?
│   │   ├─ YES → DEBUG  (verbose-only: silent by default, shown under -v)
│   │   └─ NO  → INFO   (still worth surfacing on a normal run)
│   └─ Don't delete the log — preserve observability for troubleshooting
├─ DID A HUMAN SUPPLY SOMETHING WRONG? (e.g. PROJECTS_ROOT=X set to a
│  path that does not exist) → KEEP WARNING — that is a real, actionable
│  misconfiguration even if the code recovers via fallback
├─ NO (actual failure) → Keep WARNING/ERROR, but verify return code matches
└─ UNCERTAIN → Add a two-level caplog test; assert NOTHING at INFO and the
   message present at DEBUG (proves verbose-gating, not just "warning gone")
```

**The INFO-vs-DEBUG rule, stated plainly:** when `-v`/`--verbose` maps to
root log level DEBUG and the default level is INFO, `logger.info(...)` still
prints on every default run. If the user's ask is "only show this in verbose
mode," INFO is wrong — use `logger.debug(...)`. DEBUG is the only level that
achieves true verbose-gating for benign-fallback messages.

**The discriminator (KEY nuance):** within the SAME function, keep
genuinely-actionable misconfiguration at WARNING while downgrading the benign
default. The test: "is this an automatic fallback that always works, or did a
human supply something wrong?" Benign-fallback -> DEBUG; human-supplied-wrong
-> WARNING.

### Step-by-Step Pattern

#### 1. Identify Noisy Happy-Path Logs

**Symptom**: CI output flooded with WARNING messages that occur on every run, but the script still passes.

```python
# BEFORE (noisy)
def check_ci_matrix_coverage(repo_root: Path) -> bool:
    ci_workflow = repo_root / ".github" / "workflows" / "test.yml"
    if not ci_workflow.exists():
        print(f"WARNING: CI workflow not found at {ci_workflow} — skipping matrix check")
        return True  # ← Returns SUCCESS
```

**Key insight**: If the function returns `True` (success), the log should not be `WARNING`.

---

#### 2. Use TDD to Verify Level Change

**Write test first** that will fail on current WARNING:

```python
def test_returns_true_when_no_ci_workflow(
    self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Returns True with INFO (not WARNING) when CI workflow file does not exist."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('"Programming Language :: Python :: 3.10",\n')

    # Call the function
    assert check_ci_matrix_coverage(tmp_path) is True

    # Verify log level, not log content
    captured = capsys.readouterr().out
    assert "INFO:" in captured
    assert "WARNING:" not in captured
```

Run test first — watch it fail because output contains `WARNING:`:

```
AssertionError: assert False
  where False = 'WARNING:' not in 'WARNING: CI workflow not found...'
```

---

#### 3. Downgrade the Log Level

**Never delete the log.** Downgrade instead:

```python
# AFTER (observability preserved, noise reduced)
def check_ci_matrix_coverage(repo_root: Path) -> bool:
    ci_workflow = repo_root / ".github" / "workflows" / "test.yml"
    if not ci_workflow.exists():
        print(f"INFO: CI workflow not found at {ci_workflow} — skipping matrix check")
        return True
```

Run test — now it passes:

```
✓ test_returns_true_when_no_ci_workflow PASSED
```

---

#### 4. Do Not Use logging Module for Simple Scripts

**Anti-pattern**: introduce `import logging` and `logging.getLogger()` for a single print statement:

```python
# WRONG — over-engineered for simple script
import logging
logger = logging.getLogger(__name__)

if not ci_workflow.exists():
    logger.warning("CI workflow not found...")
    return True
```

**Correct approach**: use plain `print()` with a consistent prefix:

```python
# RIGHT — simple, clear, testable with capsys
if not ci_workflow.exists():
    print(f"INFO: CI workflow not found...")
    return True
```

Reason: simple scripts don't need logging infrastructure; plain `print()` to stdout is testable with `capsys` and doesn't add dependencies.

---

#### 5. Apply to All Happy-Path Messages

If a function/method returns `True`/`success`/`0` and logs `WARNING` or `ERROR`, downgrade to `INFO`:

```python
# BEFORE
if not matrix_versions:
    print(f"WARNING: No python-version matrix found — skipping check")
    return True

# AFTER
if not matrix_versions:
    print(f"INFO: No python-version matrix found — skipping check")
    return True
```

---

#### 6. Write Tests for Each Happy-Path Message

If there are multiple happy-path logs, add a test for each:

```python
def test_returns_true_when_no_ci_workflow(
    self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Returns True with INFO when CI workflow file does not exist."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('"Programming Language :: Python :: 3.10",\n')
    assert check_ci_matrix_coverage(tmp_path) is True
    captured = capsys.readouterr().out
    assert "INFO:" in captured
    assert "WARNING:" not in captured

def test_returns_true_when_no_matrix_in_workflow(
    self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Returns True with INFO when workflow has no python-version matrix."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('"Programming Language :: Python :: 3.10",\n')
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text("jobs:\n  test:\n    runs-on: ubuntu-latest\n")
    assert check_ci_matrix_coverage(tmp_path) is True
    captured = capsys.readouterr().out
    assert "INFO:" in captured
    assert "WARNING:" not in captured
```

---

#### 7. Choose INFO vs DEBUG: Verbose-Only Gating (PR #1557)

INFO is not always low enough. When `-v`/`--verbose` maps the root logger to
`DEBUG` and the default level is `INFO`, a `logger.info(...)` call **still
prints on every default run**. If the user's explicit ask is "only show these
unless verbose mode is specified," the correct level is `logger.debug(...)` —
visible under `-v`, silent by default.

```python
# Default run shows INFO and above; `-v`/`--verbose` lowers root to DEBUG.
# So for a benign-fallback message the operator should only see under -v:
logger.debug("PROJECTS_ROOT not set; falling back to default %s", default)
#       ^^^^^ DEBUG, not info() — info() would still print by default
```

**Rule:** benign automatic fallback the operator rarely needs to see ->
`DEBUG` (verbose-only). A success-path message still worth surfacing on a
normal run -> `INFO`. An actual failure -> `WARNING`/`ERROR`.

---

#### 8. The Discriminator: Benign-Fallback DEBUG vs Human-Misconfig WARNING

Within the **same function**, do not blanket-downgrade. Keep genuinely
actionable misconfiguration at `WARNING` while downgrading the benign default.

Real example — `hephaestus/config/paths.py::resolve_projects_dir` (PR #1557):

```python
def resolve_projects_dir() -> Path:
    raw = os.environ.get("PROJECTS_ROOT")
    if raw is None:
        # Benign: unset is the NORMAL case and the default is correct.
        # The operator rarely needs to see this -> verbose-only.
        logger.debug("PROJECTS_ROOT not set; falling back to default %s", DEFAULT)
        return DEFAULT
    candidate = Path(raw)
    if not candidate.exists():
        # A human SET PROJECTS_ROOT to a path that does not exist -> real
        # misconfiguration worth surfacing. STAYS WARNING.
        logger.warning("PROJECTS_ROOT=%s does not exist; falling back to %s", raw, DEFAULT)
        return DEFAULT
    return candidate
```

**The test:** "Is this an automatic fallback that always works, or did a human
supply something wrong?" Automatic-fallback -> `DEBUG`. Human-supplied-wrong ->
`WARNING`. Both may recover via the same fallback — the level is decided by
*whose* mistake it is, not by whether the code recovers.

**Per-iteration noise is an especially strong DEBUG signal.** Second site in
PR #1557 — `hephaestus/automation/prompts/_shared.py::_relativize_path` logged
"Path ... is not under repo_root ...; injecting absolute path" at `WARNING`
**once per issue** (N times per loop). Cross-repo paths (e.g. the
Mnemosyne `marketplace.json` referenced from a Hephaestus run) are
EXPECTED and the absolute path works -> `DEBUG`. A benign message that fires
once per loop iteration is the loudest kind of noise and the clearest
downgrade candidate.

---

#### 9. Test the Level Change with Two-Level caplog (verified-ci technique)

A single "the WARNING is gone" assertion is not enough — it does not prove the
message is gated to verbose mode (it could be silently deleted, or downgraded
all the way to nothing). Lock the new contract at **two levels**:

1. **Negative at INFO** — assert the record is NOT captured at the default
   level: `assert caplog.records == []`.
2. **Positive at DEBUG** — assert the record IS captured under verbose:
   `caplog.records[0].levelno == logging.DEBUG`.

```python
import logging

def test_unset_projects_root_is_verbose_only(caplog, monkeypatch):
    monkeypatch.delenv("PROJECTS_ROOT", raising=False)

    # Negative: nothing at INFO (default run is silent)
    with caplog.at_level(logging.INFO, logger="hephaestus.config.paths"):
        resolve_projects_dir()
    assert caplog.records == []

    caplog.clear()

    # Positive: the message IS present at DEBUG (visible under -v)
    with caplog.at_level(logging.DEBUG, logger="hephaestus.config.paths"):
        resolve_projects_dir()
    assert caplog.records[0].levelno == logging.DEBUG

def test_wrong_projects_root_still_warns(caplog, monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path / "does-not-exist"))
    with caplog.at_level(logging.WARNING, logger="hephaestus.config.paths"):
        resolve_projects_dir()
    # The human-misconfig branch is preserved at WARNING.
    assert caplog.records[0].levelno == logging.WARNING
```

This proves **verbose-gating** (silent at INFO, present at DEBUG) rather than
merely "the warning is gone." Real examples shipped in PR #1557:
`tests/unit/config/test_paths.py` and
`tests/unit/automation/prompts/test_shared.py`.

> Note: pass the specific `logger="<logger.name>"` to `caplog.at_level` so the
> assertion is scoped to the logger under test and not polluted by other logs.

---

### Example: Issue #789 Full Diff

| Change | Location | Before | After |
| -------- | ----------- | --------- | ------- |
| Downgrade message 1 | Line 164 | `print(f"WARNING: CI workflow not found...` | `print(f"INFO: CI workflow not found...` |
| Downgrade message 2 | Line 171 | `print(f"WARNING: No python-version matrix...` | `print(f"INFO: No python-version matrix...` |
| Add test 1 | test_check_python_version_consistency.py | N/A (no test) | test_returns_true_when_no_ci_workflow with capsys |
| Add test 2 | test_check_python_version_consistency.py | N/A (no test) | test_returns_true_when_no_matrix_in_workflow with capsys |

**Result**: CI output has less noise; observability preserved via INFO level; 34 tests pass.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Delete the log entirely | Remove print statement for missing CI workflow | Removes observability; harder to debug why matrix check was skipped | Keep the log; downgrade the level instead |
| Introduce logging module for simple script | Import logging; use logger.warning() for single message | Over-engineering for a simple script; adds dependency bloat | Use plain print() for scripts; logging module for libraries |
| Test with string matching | `assert "WARNING" in output` | Does not enforce log level; a WARNING message with "WARNING" in text passes | Test both positive (INFO present) and negative (WARNING absent) assertions |
| Write only one test | Add test_returns_true_when_no_ci_workflow only | Second happy-path log (no matrix) was missed; incomplete coverage | Write a test for each distinct happy-path message |
| Assume print level from label text | Rely on prefix text "WARNING:" to signal log level | Text is just a string; doesn't control alerts or CI filters | Use logging module (if applicable) or be explicit in CI about what levels matter |
| Skip TDD; edit code blindly | Change WARNING to INFO without writing test first | Misses edge cases; hard to verify the downgrade worked | Write test first (TDD RED), watch it fail on old level, then downgrade (GREEN) |
| Downgrade to INFO when the user wanted verbose-only | Change WARNING -> INFO for a benign env-var fallback (PR #1557) | INFO still prints on every default run; the user asked for the message only under `-v`/`--verbose` | When `-v` maps root to DEBUG, use `logger.debug(...)` for benign fallbacks — DEBUG is the only level that is silent by default and visible under -v |
| Blanket-downgrade the whole function | Downgrade the misconfig case (PROJECTS_ROOT set to a non-existent path) to DEBUG along with the benign unset-default case | Lost a real, actionable signal — a human had supplied a wrong path and the operator never saw it | Apply the discriminator: benign automatic fallback -> DEBUG; human-supplied-wrong -> KEEP WARNING, even within the same function |

## Results & Parameters

### Log output before/after (issue #789)

```
# Before (noisy CI output):
WARNING: CI workflow not found at /repo/.github/workflows/test.yml — skipping matrix check
WARNING: No python-version matrix found in /repo/.github/workflows/test.yml — skipping matrix check

# After (preserved observability, reduced noise):
INFO: CI workflow not found at /repo/.github/workflows/test.yml — skipping matrix check
INFO: No python-version matrix found in /repo/.github/workflows/test.yml — skipping matrix check
```

### Test assertion patterns

```python
# Verify happy-path log level with capsys
captured = capsys.readouterr().out
assert "INFO:" in captured
assert "WARNING:" not in captured

# For logging module (if used):
def test_logs_info_not_warning(self, caplog):
    with caplog.at_level(logging.INFO):
        result = check_function()
    assert result is True
    # Check that no WARNING records were emitted
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 0

# Two-level caplog (verbose-gating contract — PR #1557):
# Prove the message is DEBUG-only, not just "the warning is gone".
def test_verbose_only(caplog):
    # Negative: nothing recorded at the default INFO level
    with caplog.at_level(logging.INFO, logger="my.logger.name"):
        call_function()
    assert caplog.records == []
    caplog.clear()
    # Positive: the message IS present at DEBUG (visible under -v)
    with caplog.at_level(logging.DEBUG, logger="my.logger.name"):
        call_function()
    assert caplog.records[0].levelno == logging.DEBUG
```

### Decision matrix for log level

| Scenario | Return Value | Log Level | Rationale |
| --------- | -------------- | ----------- | ----------- |
| CI workflow found, matrix matches | True | INFO/DEBUG | ✓ Success, no action needed |
| CI workflow not found | True | INFO | ✓ Success, acceptable skip path (still worth surfacing) |
| No matrix in workflow | True | INFO | ✓ Success, acceptable skip path |
| Env var unset, falls back to correct default | success | **DEBUG** | ✓ Benign automatic fallback; verbose-only — operator rarely needs it |
| Env var SET to a non-existent path, falls back | success | **WARNING** | ⚠ Human supplied a wrong value — actionable misconfig even though code recovers |
| Cross-repo path "not under repo_root", absolute path works (once per loop) | success | **DEBUG** | ✓ Expected cross-context case; per-iteration noise — verbose-only |
| Missing versions in matrix | False | WARNING | ✗ Actual failure, return False |
| Invalid YAML in workflow | False | ERROR | ✗ Actual failure, unable to continue |

**INFO vs DEBUG decision:** when `-v`/`--verbose` maps the root logger to
`DEBUG` (default `INFO`), `INFO` still prints on every default run. For a
benign-fallback message the user wants gated to verbose mode, use `DEBUG` — it
is the only level that is silent by default and shown under `-v`.

### Test coverage for happy-path logging

```python
# Minimum coverage: one test per happy-path print statement
# Each test should:
# 1. Set up scenario (missing file, empty matrix, etc.)
# 2. Call function and assert it returns True
# 3. Capture output with capsys
# 4. Assert "INFO:" in captured
# 5. Assert "WARNING:" not in captured
```

## Verified On

| Project | Issue | Context | Details |
| --------- | ------- | --------- | --------- |
| ProjectHephaestus | #789 | Downgrade in check_python_version_consistency.py | 34 tests pass, all CI pre-commit checks pass, merged |
| ProjectHephaestus | #789 | TDD approach with capsys | Both happy-path tests added before downgrade (RED), then downgrade applied (GREEN) |
| ProjectHephaestus | PR #1557 (Closes #1556, commit 5798d5a) | output.log noise cleanup — DEBUG (verbose-only) refinement over INFO | Merged with full CI green (verified-ci). `config/paths.py::resolve_projects_dir`: unset PROJECTS_ROOT -> DEBUG, wrong-path PROJECTS_ROOT -> stays WARNING (discriminator). `automation/prompts/_shared.py::_relativize_path`: per-issue cross-repo WARNING -> DEBUG |
| ProjectHephaestus | PR #1557 | Two-level caplog verbose-gating test | `tests/unit/config/test_paths.py` + `tests/unit/automation/prompts/test_shared.py`: assert `caplog.records == []` at INFO and `levelno == logging.DEBUG` at DEBUG — proves verbose-gating, not just "warning gone" |
