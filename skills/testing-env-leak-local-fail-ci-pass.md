---
name: testing-env-leak-local-fail-ci-pass
description: "Use when: (1) a pytest test for an env-building helper that does os.environ.copy() then conditionally adds keys FAILS locally but PASSES in CI, (2) an assertion like `assert 'HEPH_X' not in env` fails only on your machine, (3) you are running tests from inside the automation loop (or any wrapper) that exports the very variables the test asserts are absent, (4) deciding whether a local-only test failure is a real bug or ambient shell environment pollution — re-run with `env -u <VAR>...` before changing any code or weakening an assertion."
category: testing
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pytest
  - test-isolation
  - environment-variables
  - os-environ-copy
  - local-fail-ci-pass
  - HEPH_
  - automation-loop
  - monkeypatch-delenv
---

# Skill: testing-env-leak-local-fail-ci-pass

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-06-11 |
| Objective | Diagnose pytest "absent env var" assertions that fail LOCALLY but pass in CI |
| Outcome | Success — identified as ambient shell pollution; code and tests left untouched |
| Verification | verified-ci — PR unit-test checks green; local pass confirmed after `env -u` strip |
| Category | testing |
| Repo / PR | ProjectHephaestus — issue #814 / PR #1058 |

### What Happened

Two tests in `tests/unit/automation/test_loop_runner.py` failed locally but were green in CI:

- `test_phase_env_loop_index_only_for_drive_green` — asserts `HEPH_LOOP_INDEX` / `HEPH_TOTAL_LOOPS` are NOT present in `loop_runner._phase_env(...)` output for the `plan` and `implement` phases (only `drive-green` should set them).
- `test_phase_env_model_vars_only_when_non_empty` — asserts `HEPH_PLANNER_MODEL` / `HEPH_REVIEWER_MODEL` / `HEPH_IMPLEMENTER_MODEL` are absent when the `LoopConfig` model fields are empty.

`loop_runner._phase_env()` (in `hephaestus/automation/loop_runner.py`) builds its result with `env = os.environ.copy()` and then only *adds* `HEPH_*` keys conditionally. The function is correct. The failure was an artifact: the test process was launched from INSIDE the automation loop, which exports `HEPH_LOOP_INDEX=1`, `HEPH_TOTAL_LOOPS=1`, `HEPH_PLANNER_MODEL`, `HEPH_REVIEWER_MODEL`, `HEPH_IMPLEMENTER_MODEL`, `HEPH_ADVISE_MODEL`, etc. Those inherited vars survive `os.environ.copy()` and appear in the returned dict, so the "not in env" assertions fired. CI passes because its shell has no `HEPH_*` exported.

The correct resolution was to change NOTHING — no code edit, no assertion weakening — and verify locally by stripping the leaking vars.

## When to Use

Trigger this skill when:

- A pytest test for a function that does `os.environ.copy()` (then conditionally sets keys) fails only locally and passes in CI.
- An `assert '<VAR>' not in env` style assertion fails on your machine but the same job is green in GitHub Actions.
- You are running the suite from inside the automation loop or any wrapper that exports `HEPH_*` (or any project-prefixed) variables.
- You are tempted to "fix" an env-helper or relax an assertion to make a local failure go away — stop and check for ambient pollution first.

## Verified Workflow

### Quick Reference

```bash
# Re-run the failing env-helper tests with the leaking vars stripped.
# If they now pass, the code/tests are fine — the failure was shell pollution.
env -u HEPH_LOOP_INDEX -u HEPH_TOTAL_LOOPS -u HEPH_PLANNER_MODEL \
    -u HEPH_REVIEWER_MODEL -u HEPH_IMPLEMENTER_MODEL -u HEPH_ADVISE_MODEL \
    pixi run python -m pytest tests/unit/automation/test_loop_runner.py -q --no-cov

# Confirm which project-prefixed vars your shell is leaking:
env | grep '^HEPH_'
```

### Diagnostic Steps

1. Read the failing assertion. If it is `assert '<VAR>' not in env` (or similar "key absent") on the result of a function that does `os.environ.copy()`, suspect ambient pollution immediately.
2. Confirm the variable is exported in your shell: `env | grep '^HEPH_'` (or the relevant prefix). If the asserted-absent var is listed, that is your root cause.
3. Re-run the exact failing test with `env -u <VAR> ...` for each leaking var. If it now passes, the diagnosis is confirmed: local environment pollution, not a code or test bug.
4. Confirm CI is green for the same checks (`unit-tests`, `test (…, unit)`). Green CI + local-pass-after-unset = leave code and tests untouched.
5. Do NOT commit a "fix." There is nothing to fix in the helper or the tests.

### Key Rules

- `os.environ.copy()` copies the WHOLE ambient environment, including whatever the parent shell exported. A test asserting a key is absent will fail if that key is exported around the test process.
- Local-fail / CI-pass for an "absent var" assertion almost always means the developer shell is leaking the variable. CI runs clean.
- The fix is diagnostic, not code: re-run with `env -u`. Never weaken `assert X not in env` to make a polluted-shell failure disappear — that hides a real future regression.
- Running tests from inside the automation loop is the classic trigger: the loop exports `HEPH_LOOP_INDEX`, `HEPH_TOTAL_LOOPS`, and the per-agent `HEPH_*_MODEL` vars.
- RECOMMENDATION (not done in this session): to make such tests immune to ambient state, isolate the environment at test time with `monkeypatch.delenv("HEPH_LOOP_INDEX", raising=False)` (and siblings) or `mock.patch.dict(os.environ, {...}, clear=True)`. This is a future hardening, framed as advice — the session did not modify the tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | --------------- | --------------- | ---------------- |
| 1 | Assumed the two local test failures were real and considered editing `_phase_env()` to drop the `HEPH_*` keys | `_phase_env()` is correct; it only ADDS keys conditionally. The unwanted keys came from `os.environ.copy()` copying the polluted parent shell, not from the function | Read the function before "fixing" it — a copy-then-add helper cannot be blamed for keys it never set |
| 2 | Considered weakening the assertion (e.g. only checking keys the function explicitly sets) to make the local run green | That would mask a genuine future regression where the helper wrongly sets the var; CI was already green, proving the assertion is correct | Never relax a passing-in-CI assertion to silence a local-only failure |
| 3 | Re-ran the suite normally, expecting the failure to be deterministic | It reproduced every time locally because the leaking vars were exported by the surrounding automation loop, but never reproduced in CI | Determinism within a polluted shell is not evidence of a code bug; compare against a clean environment |
| 4 | (Resolution) Re-ran with `env -u HEPH_LOOP_INDEX … HEPH_ADVISE_MODEL` | Both tests passed with the vars stripped | Confirms ambient pollution; the correct action is to change nothing |

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Test file | `tests/unit/automation/test_loop_runner.py` |
| Tests affected | `test_phase_env_loop_index_only_for_drive_green`, `test_phase_env_model_vars_only_when_non_empty` |
| Function under test | `hephaestus/automation/loop_runner.py::_phase_env()` |
| Root-cause construct | `env = os.environ.copy()` inheriting exported `HEPH_*` vars |
| Leaking vars | `HEPH_LOOP_INDEX`, `HEPH_TOTAL_LOOPS`, `HEPH_PLANNER_MODEL`, `HEPH_REVIEWER_MODEL`, `HEPH_IMPLEMENTER_MODEL`, `HEPH_ADVISE_MODEL` |
| Trigger context | Running pytest from inside the automation loop that exports those vars |
| Verify command | `env -u HEPH_LOOP_INDEX -u HEPH_TOTAL_LOOPS -u HEPH_PLANNER_MODEL -u HEPH_REVIEWER_MODEL -u HEPH_IMPLEMENTER_MODEL -u HEPH_ADVISE_MODEL pixi run python -m pytest tests/unit/automation/test_loop_runner.py -q --no-cov` |
| Code/test change made | None — diagnosed as local environment pollution |
| CI status | Green (`unit-tests`, `test (ubuntu-latest, 3.10/3.11/3.12/3.13, unit)`) |
| Future hardening (advice) | `monkeypatch.delenv(..., raising=False)` or `mock.patch.dict(os.environ, clear=True)` to isolate from ambient env |
