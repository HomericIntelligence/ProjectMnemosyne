---
name: review-worker-defaults-options-alignment
description: "Keep automation worker-count defaults aligned when rebasing across shared Pydantic option base-class refactors. Use when: (1) CI fails after a behavior PR rebases over shared options/base-model changes, (2) CLI parser defaults/help drift from Pydantic defaults, (3) tests need to pin shared option inheritance and parser defaults."
category: ci-cd
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - projecthephaestus
  - automation
  - ci-cd
  - pydantic
  - argparse
  - defaults
  - worker-options
  - regression-tests
---

# Review Worker Defaults Options Alignment

## Overview

| Field | Value |
| ----- | ----- |
| **Date** | 2026-06-27 |
| **Objective** | Fix ProjectHephaestus issue #1386 / PR #1617 after the branch was rebased across PR #1618's shared options refactor. |
| **Outcome** | Successful. The review-worker behavior was preserved by routing parser defaults/help and option-model defaults through the same shared worker-count source of truth. |
| **Verification** | verified-ci. The user stated PR #1617 was driven to green CI; this capture used local commit evidence because GitHub API access was unavailable in the sandbox. |
| **Evidence** | HEAD `d33f31fd37a467e2033bcccdb35e42b23a509cda`, `fix(automation): keep review worker defaults aligned`; dependency commit `c2cbd995` / PR #1618 introduced the shared option bases. |

## When to Use

- A behavior PR is rebased across a refactor that extracts shared Pydantic option base classes.
- CI fails because a CLI parser still carries a hard-coded default or help string that now has a shared constant.
- A worker-count default must stay identical across parser flags, Pydantic models, and serialized option dumps.
- A review-worker or driver CLI has a `--max-workers` flag and the model layer also has a worker-count field.
- A Python-version CI lane exposes a test helper dependency such as `tomllib` not existing before Python 3.11.

## Verified Workflow

### Quick Reference

```bash
# Confirm the rebase/refactor context.
git show --stat --oneline HEAD
git show --stat --oneline c2cbd995

# Find the shared worker-count source and every parser/model consumer.
rg -n "DEFAULT_WORKER_COUNT|WorkerOptionsBase|ParallelWorkerOptionsBase|VerboseParallelWorkerOptionsBase" \
  hephaestus/automation/models.py tests/unit/automation/test_models.py
rg -n "add_max_workers_arg|DEFAULT_WORKER_COUNT" \
  hephaestus/automation/_review_utils.py tests/unit/automation/test_review_utils.py

# Focused regression checks from PR #1617.
python -m pytest \
  tests/unit/automation/test_models.py \
  tests/unit/automation/test_review_utils.py \
  tests/unit/validation/test_mypy_incremental_config.py
```

### Detailed Steps

1. Identify the new source of truth introduced by the upstream refactor. In PR #1618, `hephaestus/automation/models.py` introduced `DEFAULT_WORKER_COUNT = 3`, `WorkerOptionsBase`, `ParallelWorkerOptionsBase`, and `VerboseParallelWorkerOptionsBase`, then made planner, implementer, reviewer, plan-reviewer, address-review, and CI-driver options inherit from those bases.

2. Do not repair the rebased behavior by re-adding literal defaults. In PR #1617, `hephaestus/automation/_review_utils.py` imported `DEFAULT_WORKER_COUNT` and changed `add_max_workers_arg()` so both the argparse default and help text derive from the shared constant instead of a hard-coded `3`.

3. Pin the Pydantic model contract, not only the runtime behavior. Add tests that prove shared worker option defaults, inheritance, constructor compatibility, and `model_dump()` compatibility all agree with `DEFAULT_WORKER_COUNT`. Also test that shared bases do not leak fields such as `state_dir` into models that should not have them.

4. Pin the parser contract separately. Add a regression test that builds a parser with `add_max_workers_arg()`, parses an omitted flag, and asserts both the parsed default and rendered help text use `DEFAULT_WORKER_COUNT`.

5. Fix incidental CI compatibility exposed by the same run without mixing it into the core design. PR #1617 also adjusted `tests/unit/validation/test_mypy_incremental_config.py` to fall back to `tomli` when `tomllib` is unavailable, preserving Python 3.10 test compatibility.

6. Run focused tests locally, then rely on the PR's required CI for end-to-end verification. The local evidence for this capture was the PR branch commit; the user confirmed PR #1617 reached green CI.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Restore the visible CLI default piecemeal | Treat the failure as an `add_max_workers_arg()` hard-coded `3` problem only | It leaves parser help/defaults able to drift from the model layer after a shared-options refactor | Route both parser defaults/help and model defaults through the same exported constant |
| Test only the command path | Assert behavior from one CLI without checking the shared Pydantic bases | The next refactor can break inherited fields, constructor compatibility, or `model_dump()` while the narrow command test still passes | Add model-contract tests for inheritance, defaults, absent fields, constructors, and dumps |
| Assume every CI lane has `tomllib` | Read TOML with the Python 3.11 stdlib module in a test helper | Python 3.10 CI lacks `tomllib`, so otherwise unrelated validation tests fail | Use `tomllib` when available and fall back to `tomli` for Python 3.10 |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Project** | ProjectHephaestus |
| **Issue / PR** | Issue #1386, PR #1617 |
| **Fix commit** | `d33f31fd37a467e2033bcccdb35e42b23a509cda` |
| **Commit subject** | `fix(automation): keep review worker defaults aligned` |
| **Upstream refactor dependency** | PR #1618 / commit `c2cbd995`, shared worker option base classes |
| **Core production file** | `hephaestus/automation/_review_utils.py` |
| **Core test files** | `tests/unit/automation/test_models.py`, `tests/unit/automation/test_review_utils.py` |
| **Ancillary compatibility file** | `tests/unit/validation/test_mypy_incremental_config.py` |
| **Verification level** | `verified-ci`; local capture used checked-out commit evidence because GitHub API access was unavailable |

The durable invariant is simple: if a parser flag and a Pydantic options model expose the same knob, they must share the same exported default source. For this PR, that meant:

```python
from .models import DEFAULT_WORKER_COUNT


def add_max_workers_arg(
    parser: argparse.ArgumentParser,
    *,
    default: int = DEFAULT_WORKER_COUNT,
    help_text: str = (
        f"Maximum number of parallel workers, 1-32 "
        f"(default: {DEFAULT_WORKER_COUNT})"
    ),
) -> None:
    ...
```

### Verified On

| Repo | Context | Status |
| ---- | ------- | ------ |
| ProjectHephaestus | PR #1617 / issue #1386, rebased across PR #1618 shared options refactor | verified-ci, per user confirmation; local evidence from commit `d33f31fd37a467e2033bcccdb35e42b23a509cda` |
