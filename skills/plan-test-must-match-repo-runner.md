---
name: plan-test-must-match-repo-runner
description: "A plan's regression test must be written in the format the target repo's ACTUAL runner already executes — not a generic/familiar format (pytest by reflex). Detect the runner FIRST: grep the dependency manifest (pixi.toml / pyproject.toml / package.json) for the framework, and grep the task/recipe runner (justfile / Makefile / npm scripts) for what test/ci targets actually invoke. If the repo has no harness for your default test language, write the test in the idiom the repo DOES run and WIRE it into that runner; otherwise the test lands 'green by absence' and never executes in CI. Use when: (1) a plan adds a regression/unit test and you are about to reach for pytest/jest by default, (2) the target repo's pixi.toml/pyproject.toml declares no pytest/jest dependency, (3) `just test` / `just ci` invokes ctest or bash scripts or lint-only and runs no python tests, (4) you must pick a verification command and want it to be one the repo can actually run TODAY (e.g. `just e2e-test-*`, not a raw `pixi run pytest <path>` that errors), (5) you need to unit-test a python function in a repo with no python test harness (drive it from a bash test), (6) reviewing a plan and asking 'will this test actually run in CI, or just sit there green?'"
category: testing
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - testing
  - regression-test
  - test-runner-detection
  - green-by-absence
  - just
  - pixi
  - bash-test
  - e2e
  - shellcheck
  - pytest
  - verification-command
  - test-wiring
  - ci-gate
  - planning
  - unverified-assumptions
---

# Plan Test Must Match the Repo's Real Runner

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING lesson that a regression test added in a plan must be written in the format the target repo's ACTUAL test runner already executes — discovered while planning a regression test for an Odysseus Myrmidon issue-number coercion function, after a prior plan that proposed a pytest module got a NOGO for being green-by-absence |
| **Outcome** | Plan only. Replaced the reflexive pytest module with a self-contained bash `e2e/test-*.sh` (matching the repo's existing `e2e/run-hello-world.sh` idiom) that drives the python function under test via a `python3` heredoc, wired into a new `just` recipe AND covered by `just lint`'s shellcheck sweep. The verification command became the runner invocation, not a raw framework call |
| **Verification** | unverified — the bash test was never executed and CI was never confirmed; the runner detection and the test idiom are reasoned from the repo's manifests/recipes, not from an executed run |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

- A plan adds a regression or unit test and you are about to reach for **pytest/jest by reflex** because that is your familiar default.
- The target repo's `pixi.toml` / `pyproject.toml` / `package.json` declares **no pytest/jest dependency** — so you cannot assume that framework even runs.
- `just test` / `just ci` (or the Makefile/npm equivalents) invokes **ctest, bash scripts, or lint-only** and runs no tests in your default language. (In this case: `just test` ran only submodule ctest suites; `just ci` = `lint validate-configs`; every existing test under `e2e/` was a bash script.)
- You must pick a **verification command** and want it to be one the repo can actually run TODAY (e.g. `just e2e-test-myrmidon-issue-number`), not a raw `pixi run pytest <path>` that errors because no pytest task/dep exists.
- You need to **unit-test a python function in a repo with no python test harness** — a bash test driving the function is a legitimate option.
- You are **reviewing a plan** and asking "will this test actually run in CI, or just sit there green-by-absence?"

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

The trap: writing the regression test in your familiar default format (a pytest module) when the target repo has no pytest dependency and no runner that executes `e2e/tests/*.py`. The file lands, looks like a test, passes review — and never runs. CI is green because the test was never collected, not because the code is correct. That is **green by absence**, and it is exactly what got the prior plan a NOGO.

The fix is to detect the repo's real runner FIRST, write the test in that idiom, and wire it into the runner so it is actually exercised.

1. **Grep the dependency manifest for the test framework.** Check `pixi.toml` / `pyproject.toml` / `package.json` for `pytest` / `jest` / etc. If it is NOT a declared dependency, do not assume it runs. (Here `pixi.toml` had no pytest task and no pytest dep.)
2. **Grep the task/recipe runner for what test/ci targets actually invoke.** Read `justfile` / `Makefile` / npm scripts. Here `just test` ran only submodule ctest suites; `just ci` = `lint validate-configs` (no python tests at all); every existing test under `e2e/` was a bash script and all related recipes invoked **system `python3`** directly.
3. **Write the test in the idiom the repo ALREADY executes.** Here: a self-contained bash `e2e/test-*.sh` matching `e2e/run-hello-world.sh` — `set -euo pipefail`, `SCRIPT_DIR` resolution, `pass`/`fail` helpers, color codes — driving the python function under test via a `python3 - <<'PY' ... PY` heredoc that uses `importlib.util.spec_from_file_location` (needed because the module filename is **hyphenated** and cannot be `import`ed).
4. **WIRE it into the runner explicitly AND get it onto an existing gate.** Add a `just` recipe (`just e2e-test-myrmidon-issue-number`). Here the new `*.sh` is *also* automatically covered by `just lint`'s shellcheck sweep over tracked shell scripts — so the file is exercised by two paths, not one.
5. **Make the primary verification command the RUNNER invocation** (`just e2e-test-myrmidon-issue-number`), not a raw framework call. The verification command must be one the repo can execute today.

### Quick Reference

```bash
# 1. Is the framework even a dependency? (no hit => do NOT write a pytest module)
grep -nE 'pytest|jest' pixi.toml pyproject.toml package.json 2>/dev/null

# 2. What do the test/ci targets ACTUALLY invoke?
grep -nE '^(test|ci|lint|e2e[-a-z]*):' justfile
grep -nA3 -E 'test:|ci:' Makefile 2>/dev/null

# 3. Match an EXISTING test's idiom (here: bash e2e scripts).
ls e2e/*.sh && head -20 e2e/run-hello-world.sh

# 4. Drive the python function from bash, passing inputs via env (shellcheck-clean):
ISSUE_NUMBER=42 SRC="$repo/path/to/module-with-hyphen.py" python3 - <<'PY'
import os, importlib.util
spec = importlib.util.spec_from_file_location("mod", os.environ["SRC"])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
# ... call mod.func(int(os.environ["ISSUE_NUMBER"])) and assert
PY

# 5. Verification command = the runner, not the framework:
just e2e-test-myrmidon-issue-number
```

Secondary reusable tactics:

- **Pass test inputs via env vars into the python heredoc** (`ISSUE_NUMBER=.. SRC=.. TASK_JSON=.. python3 - <<'PY'`) rather than string-interpolating into the script — keeps it shellcheck-clean and quoting-safe.
- **A bash test that drives a python function is a legitimate way to unit-test python** in a repo with no python test harness.

## Verified Workflow

*Not applicable* — unverified; no workflow was executed. Captured during a planning session; the bash test was never run and CI was never confirmed. The workflow above is a hypothesis to be confirmed by execution/CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Write the regression test as a pytest module — the familiar/default format | The repo declares no pytest dependency and no runner executes `e2e/tests/*.py`; the file would land green-by-absence and never run in CI (this is exactly what got the prior plan a NOGO) | Detect the repo's real runner BEFORE choosing the test format — grep the manifest and the recipe/task targets first |
| 2 | Assume `pixi run pytest <path>` is the verification command | `pixi.toml` has no pytest task and no pytest dep, so the command errors | The verification command must be one the repo can actually execute today — pick the runner invocation it already supports |
| 3 | Add a test file without wiring it into any recipe/CI gate | Silent non-execution — the file exists but no target ever invokes it | Every new test needs an explicit runner entry AND/OR coverage by an existing gate (here, shellcheck via `just lint`) |

## Results & Parameters

- **Created:** new skill `plan-test-must-match-repo-runner` (testing), version 1.0.0, `verification: unverified`.
- **Concrete case:** Odysseus Myrmidon issue-number coercion function. `just test` ran only submodule ctest suites; `just ci` = `lint validate-configs`; existing `e2e/` tests were all bash scripts (`e2e/run-hello-world.sh`); related recipes invoked system `python3`. The chosen test was a bash `e2e/test-*.sh` driving the python function via an `importlib.util.spec_from_file_location` heredoc (module filename hyphenated), wired into a new `just e2e-test-myrmidon-issue-number` recipe and covered by `just lint` shellcheck.

### Most Uncertain Assumptions / Risks for a Reviewer

- **UNVERIFIED:** the bash test was never executed and CI was never confirmed (`verification: unverified`). Specifically unconfirmed: that `int("42")` coercion + the `for source in (...)` loop behave exactly as asserted across all six cases; that `just lint`'s shellcheck passes the new script at `--severity=warning`; that **system `python3` is present in the CI/lint environment** (the plan relies on system python, not a pixi-managed interpreter).
- **ASSUMED** the consumer loop's `await msg.ack()` sits OUTSIDE the inner `try/except`, so a raised `ValueError` is logged-and-acked (no redelivery storm). A reviewer should re-read that boundary — the whole "raise instead of return a sentinel" decision depends on it.
- **ASSUMED** line numbers (425/473/532/585/678, 810-814, 18-22, 100) are drift-prone; the durable anchors are the literal expression string and the recipe/section names, not the numbers.
- **ASSUMED** GitHub issue numbers are always >= 1, so 0 is a safe "unset" sentinel (consistent with the existing `ISSUE_NUMBER=0` comment).

### Related Skills

- `architecture-executable-convention-guard-pattern` — complementary: turns a prose invariant into a runnable, blocking guard (exit-code/read-only/log-anchoring). RELATED but distinct: its lesson is about making an invariant runnable, NOT about choosing a test FORMAT that matches the repo's existing runner.
- `optional-scoped-discovery-pola-gate` — related discovery/least-privilege gating pattern.
- `silent-boundary-observability-exception-classification` — related: classifying exceptions at a boundary (the ack/raise decision above touches this).
