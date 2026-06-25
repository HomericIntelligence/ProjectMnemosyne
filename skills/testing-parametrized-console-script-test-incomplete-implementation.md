---
name: testing-parametrized-console-script-test-incomplete-implementation
description: "Use when: (1) a PR adds a parametrized test that auto-discovers an entire set (e.g. every [project.scripts] entry, every module) and applies one assertion to each member; (2) an integration test like test_cli_entry_points.py::TestCLIVersionFlag::test_version_flag[<script>] fails post-merge with 'unrecognized arguments: --version' / exit 2 for a subset of scripts; (3) a REQUIRED check breaks on main because a new parametrized test expanded coverage faster than the implementation; (4) adding a new console script and needing to wire add_json_arg + add_version_arg so the existing sweep test still passes."
category: testing
date: 2026-06-22
version: "1.1.0"
history: testing-parametrized-console-script-test-incomplete-implementation.history
user-invocable: false
verification: verified-ci
tags: [testing, parametrize, console-scripts, project-scripts, cli-entry-points, version-flag, json-arg, auto-discovery, required-check, hephaestus]
---

# Parametrized "Apply X to All Console Scripts" Test vs Incomplete Implementation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Recognize that a parametrized test over an auto-discovered set is only as complete as the implementation that backs it, and fix the resulting broken REQUIRED check on main |
| **Outcome** | All 237 tests in `tests/integration/test_cli_entry_points.py` pass after wiring `add_version_arg(parser)` on the 3 missed scripts (PR #1174, green on main) |
| **Verification** | verified-ci |

## When to Use

- A PR adds a parametrized test that auto-discovers a whole set (every `[project.scripts]` entry, every module, every command) and applies one assertion per member
- `tests/integration/test_cli_entry_points.py::TestCLIVersionFlag::test_version_flag[<script>]` FAILS for some scripts with `error: unrecognized arguments: --version` and exit code 2
- A REQUIRED check breaks on `main` immediately after merging a "apply X to all console scripts" PR
- You are adding a new `[project.scripts]` entry and need to make the existing `--version` / `--json` sweep test pass
- Local pre-commit / spot checks were green but the full parametrized sweep was never run before merge

## Verified Workflow

### Quick Reference

```bash
# In each un-patched script's parser builder, alongside add_json_arg:
from hephaestus.cli.utils import add_version_arg, add_json_arg
add_json_arg(parser)
add_version_arg(parser)

# Verify a single script:
pixi run <script> --version   # exit 0, prints version

# Run the FULL parametrized sweep before merging:
pixi run pytest tests/integration/test_cli_entry_points.py
```

### Detailed Steps

#### The core insight

A parametrized "apply X to ALL console scripts" test is only as complete as the script list
it wires. When a PR adds such a test that auto-discovers an entire set (e.g. all
`[project.scripts]` entries), the **test coverage EXPANDS automatically** but the
**implementation does NOT**. A partial implementation makes the PR's OWN new test fail
post-merge — and if that test is a REQUIRED check, it breaks `main`.

The asymmetry is the trap:

- The test iterates over a discovered set (`[project.scripts]`) — adding a script grows the test.
- The implementation is hand-applied per script — adding a script does NOT grow the implementation.
- So a subset of un-patched scripts silently fails the test the same PR introduced.

#### Symptom

```text
tests/integration/test_cli_entry_points.py::TestCLIVersionFlag::test_version_flag[hephaestus-audit-prs] FAILED
tests/integration/test_cli_entry_points.py::TestCLIVersionFlag::test_version_flag[hephaestus-check-cli-tier-docs] FAILED
tests/integration/test_cli_entry_points.py::TestCLIVersionFlag::test_version_flag[hephaestus-check-repo-analyze-skills] FAILED
# error: unrecognized arguments: --version   (exit code 2)
```

This is a REQUIRED check, so the three failing params broke `main`.

#### Root cause

PR #1035 ("add -V/--version flag to all console scripts") added a parametrized test that
auto-discovers ALL `[project.scripts]` entries AND added the flag to most scripts — but
missed 3. The test discovers every script; the author only patched a subset, so the test
failed for the un-patched scripts.

#### Fix (PR #1174 — merged, green on main)

The shared helper `add_version_arg(parser)` already exists in `hephaestus/cli/utils.py`
(sibling of `add_json_arg`). Each missed script's parser-builder just imports it and calls
`add_version_arg(parser)` alongside the existing `add_json_arg(parser)`:

```python
from hephaestus.cli.utils import add_version_arg, add_json_arg

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)
    add_json_arg(parser)
    add_version_arg(parser)   # the missing call
    ...
    return parser
```

After the fix, all 237 tests in `test_cli_entry_points.py` pass. Verify each script with
`pixi run <script> --version` (exit 0, prints version).

#### Prevention / pattern

When a PR adds a parametrized test over an auto-discovered set ("for every console_script",
"for every module"), ALWAYS run the FULL parametrized test locally before merge:

```bash
pixi run pytest tests/integration/test_cli_entry_points.py
```

When adding a new console script later, the same test will catch a missing `--version` /
`--json`. The companion REQUIRED helpers `add_json_arg` and `add_version_arg` must BOTH be
wired on every `[project.scripts]` entry.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Partial implementation | PR #1035 added the parametrized `--version` test (auto-discovers all `[project.scripts]`) but only added the flag to a subset of scripts | The test auto-expands to ALL scripts; 3 un-patched scripts (`hephaestus-audit-prs`, `hephaestus-check-cli-tier-docs`, `hephaestus-check-repo-analyze-skills`) failed `--version` with exit 2, breaking a REQUIRED check on main | A parametrized test over an auto-discovered set is only as complete as the implementation; patch EVERY member or the test fails |
| Skipping the full local run | Relying on pre-commit / spot checks rather than running the whole parametrized suite | The failing params only surface when running the full `test_cli_entry_points.py` over every discovered script | Always run `pixi run pytest tests/integration/test_cli_entry_points.py` (full param sweep) before merge |
| New script forgot add_version_arg | `hephaestus-scaffold-subpackage` (PR #1570, issue #1554) wired `add_json_arg(parser)` but omitted the companion `add_version_arg(parser)` call | `TestCLIVersionFlag::test_version_flag[hephaestus-scaffold-subpackage]` would have failed with `error: unrecognized arguments: --version` exit 2 — caught by a code reviewer before merge | Both `add_json_arg` AND `add_version_arg` must be wired together; a reviewer or the full integration sweep is the last safety net when the author forgets one |

## Results & Parameters

**Failing scripts (3):** `hephaestus-audit-prs`, `hephaestus-check-cli-tier-docs`,
`hephaestus-check-repo-analyze-skills` — each failed `--version` with `error: unrecognized
arguments: --version` and exit code 2.

**Fix:** wire `add_version_arg(parser)` (from `hephaestus/cli/utils.py`) alongside the
existing `add_json_arg(parser)` in each missed script's parser builder.

**Result:** all 237 tests in `tests/integration/test_cli_entry_points.py` pass after the fix.

**Verification per script:**

```bash
pixi run hephaestus-audit-prs --version                 # exit 0, prints version
pixi run hephaestus-check-cli-tier-docs --version       # exit 0, prints version
pixi run hephaestus-check-repo-analyze-skills --version # exit 0, prints version
```

**Full sweep (run before merge):**

```bash
pixi run pytest tests/integration/test_cli_entry_points.py   # 237 passed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1035 introduced; PR #1174 fixed (green on main) | Parametrized `--version` sweep auto-discovered all `[project.scripts]`; 3 un-patched scripts broke a REQUIRED check; fixed by wiring `add_version_arg` on each |
| ProjectHephaestus | PR #1570, issue #1554 — new scaffold-subpackage script forgot add_version_arg; reviewer caught it pre-merge; fixed before landing | `hephaestus-scaffold-subpackage` had `add_json_arg` but no `add_version_arg`; inline PR review thread caught the omission; fix applied before merge |
