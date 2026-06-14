---
name: testing-os-environ-pollution-local-vs-ci-false-failure
description: "A test passes in clean CI but fails ONLY on your local machine because your shell exported env vars that an os.environ.copy()-derived dict inherits, breaking an 'assert VAR not in env' check. Use when: (1) a pytest assertion of the form `assert \"X\" not in env` (env built via os.environ.copy()) is RED locally but GREEN in CI; (2) you ran pytest from inside a live automation loop that exports HEPH_LOOP_INDEX / HEPH_TOTAL_LOOPS / HEPH_PLANNER_MODEL / HEPH_REVIEWER_MODEL / HEPH_IMPLEMENTER_MODEL / HEPH_ADVISE_MODEL; (3) _phase_env / loop_runner tests fail locally with leaked HEPH_* keys; (4) any local-only red that CI shows green and you must decide environment-pollution vs real regression before touching code."
category: testing
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pytest
  - test-isolation
  - os-environ
  - environ-copy
  - env-pollution
  - local-vs-ci
  - false-failure
  - flaky
  - phase_env
  - loop_runner
  - heph-env-vars
  - env-minus-u
  - monkeypatch-delenv
---

# os.environ Pollution: Local-Only Test False-Failure vs Clean CI

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Diagnose a test that is GREEN in CI but RED locally because the running shell exported env vars an `os.environ.copy()`-derived dict inherits, breaking an `assert "X" not in env` check — and confirm it is pollution, not a regression, WITHOUT editing the test or production code |
| **Outcome** | Confirmed: failures were ambient-env pollution. `env -u <vars> pytest <nodeids>` went green; tests and production left untouched (correct action). |
| **Verification** | verified-local (diagnosis confirmed locally; affected tests are green in ProjectHephaestus CI, which already proves clean-env behavior) |

## When to Use

- A pytest assertion `assert "X" not in env` (where `env = os.environ.copy()` plus a few conditional keys) is RED locally but GREEN in CI.
- You ran `pytest` from inside a live automation loop that exports `HEPH_LOOP_INDEX`, `HEPH_TOTAL_LOOPS`, `HEPH_PLANNER_MODEL`, `HEPH_REVIEWER_MODEL`, `HEPH_IMPLEMENTER_MODEL`, `HEPH_ADVISE_MODEL`.
- `tests/unit/automation/test_loop_runner.py::test_phase_env_loop_index_only_for_drive_green` or `::test_phase_env_model_vars_only_when_non_empty` fail locally with leaked `HEPH_*` keys.
- Any local-only red that CI shows green — verify the environment delta (exported vars, PATH, installed tools) before suspecting a code bug.

## Verified Workflow

### Quick Reference

```bash
# Re-run ONLY the failing node ids with the suspect vars stripped from the environment.
# If they go green, it was ambient pollution — do NOT edit the test or production code.
env -u HEPH_LOOP_INDEX -u HEPH_TOTAL_LOOPS -u HEPH_PLANNER_MODEL \
    -u HEPH_REVIEWER_MODEL -u HEPH_IMPLEMENTER_MODEL -u HEPH_ADVISE_MODEL \
  pixi run python -m pytest \
  "tests/unit/automation/test_loop_runner.py::test_phase_env_loop_index_only_for_drive_green" \
  "tests/unit/automation/test_loop_runner.py::test_phase_env_model_vars_only_when_non_empty" \
  -v --no-cov

# See which suspect vars your shell is leaking in the first place:
env | grep -E '^HEPH_'
```

### Detailed Steps

1. **Confirm the divergence.** The test is green on the PR's CI run but red in your local full-suite run. That asymmetry is the tell — CI runners start from a clean environment; your shell may not.

2. **Read the function under test.** Look for `os.environ.copy()` as the base of the dict, with only *additive* conditional keys. The Hephaestus example is `hephaestus/automation/loop_runner.py::_phase_env`:

   ```python
   def _phase_env(cfg, loop_idx, trunk_sha, phase) -> dict[str, str]:
       env = os.environ.copy()                       # <-- inherits YOUR shell's vars
       if cfg.planner_model:
           env["HEPH_PLANNER_MODEL"] = cfg.planner_model
       # ... reviewer/implementer model vars only if non-empty ...
       if phase == "drive-green":
           env["HEPH_LOOP_INDEX"] = str(loop_idx)
           env["HEPH_TOTAL_LOOPS"] = str(cfg.loops)
       return env
   ```

   The tests assert that for the `plan`/`implement` phases those keys are ABSENT (`assert "HEPH_LOOP_INDEX" not in env`). That only holds when the ambient environment lacks them.

3. **Identify the polluter.** The automation loop runner exports exactly these `HEPH_*` vars. Running pytest from inside a live loop means `os.environ.copy()` picks them up, so the "not in" assertions fail. `env | grep -E '^HEPH_'` reveals them.

4. **Prove it with `env -u`.** Strip each suspect var and re-run only the failing node ids (Quick Reference). Both pass; the full suite (3521 passed, 19 skipped) also passes in the cleaned env. That is positive proof of pollution, not regression.

5. **Take the correct action: do nothing to the code.** Leave the tests and production `_phase_env` UNTOUCHED. Editing them to make the dirty-shell run green would be wrong and would mask the real (clean-env) contract that CI enforces.

6. **(Future hardening, out of scope for a CI fix.)** Make such tests environment-robust by having them `monkeypatch.delenv("HEPH_LOOP_INDEX", raising=False)` (and the other keys) before asserting absence. Note as a recommendation; do not bundle it into an unrelated CI-green PR.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Assumed the local red = a real regression introduced by the branch | The tests are green on the PR's own CI run; a branch regression would fail CI too | Local-only red + CI green is almost always environmental, not a code bug — check the env delta first |
| 2 | Considered editing the `_phase_env` tests to make the local run pass | The "not in" assertions encode the real clean-env contract; weakening them to fit a dirty shell hides the contract CI verifies | Never modify a test or production code to satisfy a polluted local environment |
| 3 | Considered adding `monkeypatch.delenv` to the tests as part of the #1058 CI-green PR | The CI failure was a trivial ruff-format drift; the env-pollution tests were never red in CI — bundling unrelated hardening contaminates scope | Keep the PR scoped to the actual CI failure; file env-robustness hardening separately |

## Results & Parameters

**Suspect var set leaked by the live automation loop:**

```text
HEPH_LOOP_INDEX, HEPH_TOTAL_LOOPS,
HEPH_PLANNER_MODEL, HEPH_REVIEWER_MODEL, HEPH_IMPLEMENTER_MODEL, HEPH_ADVISE_MODEL
```

**Decision rule:**

```text
test RED locally + GREEN in CI
  AND test asserts "X" not in <os.environ.copy()-derived dict>
  => re-run failing node ids under `env -u X ...`
       green  -> ambient env pollution; leave code AND test untouched
       red    -> investigate as a genuine regression
```

**Confirmed outcome (ProjectHephaestus, PR #1058 / issue #814):**

- Stripped-env re-run of both `_phase_env` node ids: PASS.
- Full suite under cleaned env: 3521 passed, 19 skipped.
- Action taken: none to `tests/unit/automation/test_loop_runner.py` or `hephaestus/automation/loop_runner.py`. The actual CI fix was an unrelated ruff-format drift.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1058 / issue #814 — driving CI to green; full local suite surfaced two false-red `_phase_env` tests | `env -u` re-run confirmed pollution; tests/production left untouched |
