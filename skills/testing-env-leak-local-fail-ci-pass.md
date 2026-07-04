---
name: testing-env-leak-local-fail-ci-pass
description: "Diagnose tests that fail locally but pass in CI because the local environment differs: inherited variables copied by os.environ.copy(), stale console scripts resolved by PATH or shutil.which(), or sibling checkout artifacts. Use when local pytest is red, CI is green, and the failure could be ambient shell/PATH pollution rather than a code regression."
category: testing
date: 2026-06-11
version: "2.0.0"
user-invocable: false
verification: verified-local
history: testing-env-leak-local-fail-ci-pass.history
tags: [pytest, local-vs-ci, env-pollution, os-environ-copy, path-pollution, stale-console-script, heph-env-vars, shutil-which, false-failure, test-isolation]
---

# Testing: Local-Fail CI-Pass Environment Pollution

## Overview

Local red tests are not automatically code regressions when the same checks are green in CI. First verify whether the local process inherited state CI does not have: exported env vars, stale console-script binaries, sibling checkout packages, or a polluted PATH.

This skill consolidates the previous canonical memory plus three ProjectHephaestus local-fail/CI-pass memories. The durable rule is: prove the exact executable, import path, and inherited environment before editing production code or weakening tests.

| Field | Value |
|-------|-------|
| Date | 2026-07-04 |
| Objective | Generalize local-only pytest failure triage for env/PATH pollution while preserving issue-specific examples. |
| Outcome | Canonical skill replaces three narrower duplicate memories; source snapshots are preserved in history. |
| Verification | verified-local for this consolidation; source examples preserve their original verified-ci/local status in history. |

## When to Use

- A pytest failure is red locally but the same CI job is green.
- A test asserts `VAR not in env`, and the env dict is based on `os.environ.copy()`.
- Tests are run from inside an automation loop, shell wrapper, or long-lived terminal that may export project-prefixed variables.
- A `shutil.which()` or console-script test resolves a binary from a sibling checkout or stale virtual environment.
- You are tempted to edit code or relax assertions solely to satisfy a dirty local run.
- You need a decision rule for whether a local failure is environment divergence or a real regression.

## Verified Workflow

### Quick Reference

```bash
# 1. Compare local failure against CI before editing code.
gh pr checks <number>

# 2. Inspect inherited project vars that could pollute os.environ.copy().
env | grep -E '^(HEPH_|PROJECT_|APP_)'

# 3. Re-run failing node ids with suspect vars stripped.
env -u HEPH_LOOP_INDEX -u HEPH_TOTAL_LOOPS -u HEPH_PLANNER_MODEL \
    -u HEPH_REVIEWER_MODEL -u HEPH_IMPLEMENTER_MODEL -u HEPH_ADVISE_MODEL \
  pixi run python -m pytest <nodeid> -v --no-cov

# 4. Verify the executable/import path used by subprocess tests.
which <console-script>
cd /tmp && <venv-or-pixi-python> -c 'import pkg.module as m; print(m.__file__)'

# 5. Force current worktree binaries first when PATH is stale.
export PATH="$PWD/.pixi/envs/default/bin:$PATH"
hash -r
```

1. Confirm the asymmetry. If CI is green and only the local shell is red, classify the failure as environmental until proven otherwise.
2. Read the failing assertion. For `assert "X" not in env`, check whether the function starts with `os.environ.copy()` and only conditionally adds keys.
3. Inspect the ambient environment with `env | grep`. If the asserted-absent key is exported, re-run with `env -u` before changing anything.
4. For console-script or subprocess tests, verify both `which <binary>` and the module `__file__` from a neutral cwd. The current Python import path can differ from the console-script wrapper's import path.
5. If cleaned-env or worktree-first PATH makes the failure pass, leave production code and tests untouched. Record the local environment issue instead.
6. If the failure remains after env/PATH cleanup and CI is also red, then investigate as a genuine regression.
7. Future hardening is separate scope: use `monkeypatch.delenv(..., raising=False)` or `mock.patch.dict(os.environ, clear=True)` only when the task is to harden tests against ambient state.

### Worked Examples

| Example | Local Symptom | Authority Check | Correct Action |
|---|---|---|---|
| ProjectHephaestus #814 / PR #1058 | `_phase_env` tests asserted `HEPH_*` keys absent but local shell exported them. | `env -u HEPH_* pixi run python -m pytest ...` passed; CI unit tests were green. | Do not edit `_phase_env` or tests; classify as ambient env pollution. |
| ProjectHephaestus #723 / PR #1016 | `shutil.which()` found an older console script from a sibling checkout. | `which hephaestus-automation-loop` and neutral-cwd `__file__` showed stale root checkout code. | Put current worktree `.pixi/envs/default/bin` first on PATH and `hash -r`. |
| Long-lived automation-loop shell | Local tests inherited `HEPH_LOOP_INDEX`, model vars, and loop metadata. | `env | grep '^HEPH_'` exposed the pollution. | Strip vars for validation; keep code scoped to the actual CI failure. |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| Treat local-only red as a code regression | Started inspecting or editing production code because local pytest failed. | CI was green and the failing process inherited local-only state. | Compare CI first and prove env/PATH cleanliness before editing code. |
| Weaken absent-var assertions | Considered relaxing `assert VAR not in env` to satisfy a polluted shell. | The assertion describes the clean-env contract CI verifies. | Fix the local environment, not the test, unless the task is explicit test hardening. |
| Trust `python -c import` from cwd only | Imported the module from the worktree and assumed console scripts used the same code. | Console-script wrappers can load site-packages from another checkout. | Inspect the wrapper's interpreter/import path from a neutral cwd. |
| Re-run without scrubbing env | Repeated pytest in the same polluted shell. | The failure was deterministic only because the shell was consistently polluted. | Determinism in a dirty environment is not regression evidence. |
| Bundle future hardening into an unrelated CI fix | Considered adding `monkeypatch.delenv` while fixing unrelated formatting/CI drift. | That contaminates scope and hides the actual cause. | Record hardening separately unless it is the requested fix. |

## Results & Parameters

Use these parameters in PR notes when classifying a local failure:

```yaml
local_failure_classification:
  ci_status: green | red | unknown
  env_copy_detected: true | false
  suspect_vars: [HEPH_LOOP_INDEX, HEPH_TOTAL_LOOPS, HEPH_PLANNER_MODEL]
  scrub_command: env -u VAR ... pixi run python -m pytest <nodeid>
  executable_check: which <console-script>
  import_path_check: cd /tmp && <python> -c 'import module; print(module.__file__)'
  disposition: env_pollution | stale_path | genuine_regression
```

Canonical decision rule:

```text
local red + CI green + passes after env/PATH cleanup -> leave code and tests untouched
local red + CI red, or still red after cleanup -> investigate as a real regression
```
