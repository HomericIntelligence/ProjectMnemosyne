---
name: ci-tests-agent-subprocess-claude-absent
description: "Automation/agent-orchestration unit tests pass locally but fail in CI because the dev machine has the `claude` CLI on PATH and CI does not — an unpatched agent call (invoke_claude_with_session / _run_advise / _run_learn) spawns a REAL claude subprocess. Use when: (1) you add an agent-invoking method to code under test, (2) a unit test reaches an invoke_claude_with_session / _run_advise / _run_learn call, (3) automation/orchestration tests are green locally but red in CI, (4) you are auditing fixtures that do not disable agent gates. Fix: default agent gates OFF in shared fixtures + reproduce CI locally by hiding ~/.local/bin (where claude lives) from PATH while keeping pixi + gh."
category: testing
date: 2026-05-28
version: "1.0.0"
user-invocable: false
tags:
  - testing
  - ci-cd
  - test-isolation
  - claude-cli
  - agent-orchestration
  - automation
  - subprocess
  - mock
  - fixtures
  - path
  - pixi
  - invoke-claude-with-session
  - flaky-ci
  - local-green-ci-red
---

# CI Tests: Agent Subprocess When `claude` Is Absent

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-28 |
| **Objective** | Stop automation/agent unit tests that pass locally from failing in CI because an unpatched agent call spawns a real `claude` subprocess that exists locally but not in CI |
| **Outcome** | Success — gated the new agent call OFF in the shared fixture, patched every agent-invoking method, added gated-behavior coverage; full automation suite passes with `claude` hidden from PATH (845 passed) and the PR cleared CI |
| **Verification** | verified-ci |

## When to Use

Use this skill when any of the following apply:

- You are **adding an agent-invoking method** (e.g. `_run_advise`, `_run_learn`, anything wrapping `invoke_claude_with_session`) to code that has unit tests.
- A unit test path **reaches** an `invoke_claude_with_session` / `_run_advise` / `_run_learn` call — confirm it is patched, or it will shell out to a real `claude`.
- Automation/orchestration tests are **"green locally but red in CI"** and the diff touched an agent/orchestration code path.
- You are **auditing test fixtures** that construct options/config and notice an agent gate (`enable_advise`, `enable_learn`, etc.) is not defaulted to `False`.
- A failing CI assertion is a downstream `assert_called_once()` (e.g. `mock_fix.assert_called_once()`) that never fires — an upstream agent call short-circuited before reaching the mocked step.

## Verified Workflow

### Quick Reference

```bash
# Reproduce the CI sandbox locally: hide ~/.local/bin (where `claude` lives)
# from PATH while KEEPING pixi's dir + gh on PATH.

# Build a PATH that has pixi + standard dirs but NOT ~/.local/bin:
CLEAN_PATH="$(dirname "$(which pixi)"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Confirm claude is hidden (this is the whole point):
PATH="$CLEAN_PATH" which claude || echo "claude hidden (good)"

# Run the suite exactly as CI would see it:
PATH="$CLEAN_PATH" pixi run pytest tests/unit/automation/ -q --no-cov
```

If the suite passes with `claude` hidden, it will pass in CI. **Do NOT blank out PATH
entirely** — that breaks `pixi` itself (pixi can live at `/tmp/pixi-.../bin/pixi`). Keep
pixi's directory on PATH and only drop `~/.local/bin`.

### Detailed Steps

1. **Recognize the failure mode.** The symptom is a test that is green on your machine
   and red in CI, on automation/orchestration code. The root cause is environmental, not
   logical: locally `claude` resolves (typically `~/.local/bin/claude`), so an unpatched
   agent call "succeeds enough" to pass; in CI `claude` is absent, so the same call
   errors / hangs / short-circuits and the test fails. Diagnose from the CI log — a
   downstream `mock.assert_called_once()` that never fired means an upstream agent call
   returned early before reaching the mocked step.

2. **Find every agent-invoking call on the test's path.** Grep the code under test for
   `invoke_claude_with_session`, `_run_advise`, `_run_learn`, or any helper that builds a
   `claude` subprocess. Every such call reached by a test must either be (a) behind a gate
   that the fixture defaults OFF, or (b) explicitly patched in the test.

3. **Default the new agent gate OFF in the shared fixture.** When you add a gate such as
   `enable_advise`, set it to `False` in the shared options/config fixture
   (`CIDriverOptions(..., enable_advise=False)`). The project's other fixtures (planner
   `_make_options`, etc.) already default `enable_*` gates to `False` for exactly this
   reason — follow suit for any new agent-invoking gate so existing tests never reach the
   new subprocess.

4. **Patch every agent-invoking method in tests that exercise that path.** A fix-path test
   that patches `_get_failing_ci_logs` and `_run_ci_fix_session` but NOT a newly-added
   `_run_advise` will hit a real `claude`. Patch the new method too.

5. **Add explicit coverage for the gated behavior.** Add tests proving:
   - When the gate is **enabled**, the agent method runs **once** and its findings reach
     the downstream call.
   - When the gate is **disabled**, the agent method is **skipped** and findings are empty.

6. **Reproduce CI locally before pushing** using the Quick Reference snippet — run the
   automation suite with `claude` hidden from PATH. Only push once it is green under those
   conditions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Trusted the local green run for agent-invoking tests and pushed. | The local `claude` on PATH (`~/.local/bin/claude`) masked the missing-binary CI behavior — the call "succeeded enough" locally but errored/short-circuited in CI. | Re-run the suite with `claude` hidden from PATH before pushing; a local pass is not a CI pass for agent code. |
| 2 | Patched only the obvious downstream calls in a fix-path test (`_get_failing_ci_logs`, `_run_ci_fix_session`). | A newly-added upstream agent call (`_run_advise`) was left unpatched and hit a real `claude` subprocess; the downstream `mock_fix.assert_called_once()` never fired because advise short-circuited first. | Default agent gates OFF in shared fixtures AND patch every agent-invoking method on the test's path — not just the ones you remembered to add. |
| 3 | Blanked out PATH entirely (`PATH=""` / `PATH=/usr/bin`) to simulate "no claude". | `pixi` itself disappeared (it lived at `/tmp/pixi-.../bin/pixi`), so the suite could not even start — a false failure unrelated to the bug. | Keep pixi's directory (and `gh`) on PATH; only drop `~/.local/bin` where `claude` lives. |
| 4 | Added the new `enable_advise` gate but left it defaulting to `True` in the shared fixture. | Every pre-existing fix-session test suddenly reached the new agent call and went red in CI. | New agent-invoking gates default to `False` in the shared fixture; only the tests that specifically exercise the gate flip it on and patch the method. |

## Results & Parameters

### CLEAN_PATH reproduction recipe (copy-paste ready)

```bash
# Hide ~/.local/bin (claude) but keep pixi's dir + standard system dirs.
CLEAN_PATH="$(dirname "$(which pixi)"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Sanity check: claude must NOT resolve; pixi MUST resolve.
PATH="$CLEAN_PATH" which claude || echo "claude hidden (good)"
PATH="$CLEAN_PATH" which pixi   # must print pixi's path

# Run the automation suite the way CI sees it (no real claude available):
PATH="$CLEAN_PATH" pixi run pytest tests/unit/automation/ -q --no-cov
# Green here  ⇒  green in CI.
```

### Fixture pattern: default agent gates OFF

```python
# Shared fixture for CI-driver tests — agent gate defaults OFF so existing
# tests never reach a real `claude` subprocess.
def _make_ci_driver_options(**overrides):
    defaults = dict(
        # ... other options ...
        enable_advise=False,   # gate the agent call OFF by default
    )
    defaults.update(overrides)
    return CIDriverOptions(**defaults)
```

```python
# A test that specifically exercises advise flips the gate ON *and* patches
# every agent-invoking method on the path.
def test_advise_runs_once_and_findings_reach_fix(monkeypatch):
    opts = _make_ci_driver_options(enable_advise=True)
    driver = CIDriver(opts)
    with (
        patch.object(driver, "_run_advise", return_value="FINDINGS") as mock_advise,
        patch.object(driver, "_get_failing_ci_logs", return_value="logs"),
        patch.object(driver, "_run_ci_fix_session") as mock_fix,
    ):
        driver.run_fix_session()
    mock_advise.assert_called_once()           # advise ran exactly once
    assert "FINDINGS" in mock_fix.call_args.args  # its output reached the fix step

def test_advise_skipped_when_disabled():
    opts = _make_ci_driver_options(enable_advise=False)
    driver = CIDriver(opts)
    with (
        patch.object(driver, "_run_advise") as mock_advise,
        patch.object(driver, "_get_failing_ci_logs", return_value="logs"),
        patch.object(driver, "_run_ci_fix_session") as mock_fix,
    ):
        driver.run_fix_session()
    mock_advise.assert_not_called()            # gate OFF ⇒ no agent call
    # findings empty ⇒ downstream sees no advise output
    assert mock_fix.called
```

### Why "green locally / red in CI" happens here

| Dimension | Local default | CI default | Effect on an unpatched agent call |
| ----------- | -------------- | ------------ | ---------------------------------- |
| `claude` on PATH | Yes (`~/.local/bin/claude`) | No (binary absent) | Local: call resolves, test passes. CI: call fails/hangs/short-circuits, test fails. |
| `pixi` on PATH | Yes | Yes | Must stay on PATH locally too — do not blank PATH. |
| `gh` on PATH | Yes | Yes | Keep available when reproducing. |
| Agent gate (`enable_advise`) | Should default `False` in fixture | Same | If left `True`, every test reaches the subprocess. |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | GO/NOGO + advise-first work on the CI driver (PR #679; earlier #677) | Adding `_run_advise` to the fix path broke two `test_ci_driver.py` fix-session tests in CI but not locally; gating `enable_advise=False` in the shared fixture + patching `_run_advise` + adding gated-behavior coverage fixed it. 845 automation tests pass with `claude` hidden from PATH; the PR cleared CI. |
