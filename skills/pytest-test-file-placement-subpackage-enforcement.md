---
name: pytest-test-file-placement-subpackage-enforcement
description: Where a new pytest unit-test file must live when a repo pre-commit hook
  forbids bare test_*.py directly under tests/unit/, plus the Path(__file__).resolve().parents[N]
  REPO_ROOT depth adjustment and commit-hygiene checks when relocating a test deeper.
category: testing
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [pytest, test-structure, pre-commit, tests-unit, subpackage, repo-root, path-parents, file-placement, ci-gate, hephaestus]
---
# Pytest Test-File Placement: Sub-package Enforcement

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Add a repo-root config/docs presence regression test without tripping the "Check unit test structure" pre-commit gate |
| **Context** | ProjectHephaestus issue #1186 — adding `tests/unit/.../test_mcp_config.py` |
| **Verification** | verified-precommit (placement hook + ruff + markdownlint passed locally; full CI not observed) |

## Overview

ProjectHephaestus enforces a mirrored unit-test layout via a pre-commit hook named
**"Check unit test structure"**. The hook FAILS with:

```text
ERROR: test_*.py files found directly under tests/unit/. Move them into the appropriate sub-package.
```

So `tests/unit/test_*.py` is forbidden — every test must live in a sub-package that
mirrors the `hephaestus/` source tree (e.g. `tests/unit/validation/`,
`tests/unit/docs/`, `tests/unit/config/`).

This skill encodes three traps that compound when you add a new unit test:

1. **The placement trap** — a plan that says "model this on `tests/unit/test_import_surface.py`"
   implies a bare file under `tests/unit/`, which the hook rejects. (The cited file
   actually lives at `tests/unit/validation/test_import_surface.py`.)
2. **The parents-depth gotcha** — `REPO_ROOT = Path(__file__).resolve().parents[N]`
   depth changes when you move the file one directory deeper. Forget to bump `N` and
   `REPO_ROOT` silently points to the wrong directory.
3. **The commit-hygiene gotcha** — after `git add`-ing the wrong-location file, then
   `git rm` + recreating it correctly, the OLD path stays staged in the index and lands
   a duplicate in the commit. `git commit --amend` then re-runs hooks that may reformat
   the file and re-dirty the tree.

## When to Use This Skill

Invoke when:

- Adding a NEW unit test file to a ProjectHephaestus-style repo that enforces mirrored
  `tests/unit/<subpackage>/` layout.
- A plan or memory note cites a test path under `tests/unit/` and you are about to copy it.
- Writing a repo-root-scoped doc/config presence or drift regression test (asserts files
  like `.mcp.json`, `docs/mcp.md`, `AGENTS.md` exist at repo root).
- Computing or editing a `REPO_ROOT = Path(__file__).resolve().parents[N]` line.
- The "Check unit test structure" pre-commit hook fails on your new test.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis
> until CI confirms. Verification level is `verified-precommit`: the placement hook,
> ruff, and markdownlint passed locally via pre-commit, but full CI on the PR was not
> observed in this session.

### Step 1 — Find the mirrored sub-package BEFORE writing the file

Never trust a cited test path. Verify the real location and pick the sub-package that
mirrors the source area under test.

```bash
find tests/unit -name "test_<thing>.py"   # does the cited path actually exist here?
ls tests/unit/                            # sub-packages mirror hephaestus/
```

For a **repo-root doc/config presence** test, the canonical home in ProjectHephaestus
is `tests/unit/docs/` — that sub-package already holds repo-root doc-presence/drift
regression tests (e.g. `test_version_currency.py`).

### Step 2 — Compute `parents[N]` for REPO_ROOT from the FINAL location

```text
tests/unit/test_x.py        -> Path(__file__).resolve().parents[2]   # ../../  = repo root
tests/unit/<pkg>/test_x.py  -> Path(__file__).resolve().parents[3]   # ../../../ = repo root
```

Each directory level you add below `tests/unit/` adds **one** to `N`.

### Step 3 — Write the test at the sub-package path with the correct depth

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/unit/docs/test_x.py -> repo root


def test_mcp_config_files_present() -> None:
    assert (REPO_ROOT / ".mcp.json").exists()
    assert (REPO_ROOT / "docs" / "mcp.md").exists()
    assert (REPO_ROOT / "AGENTS.md").exists()
```

### Step 4 — Run the structural gate explicitly

```bash
pre-commit run --files tests/unit/<pkg>/test_x.py   # "Check unit test structure" must Pass
```

### Step 5 — If you relocated a file, confirm the OLD path is gone from the index

If you ever staged the wrong-location copy, the old path can ride along into the commit.

```bash
git diff --cached --name-only          # OLD path must NOT appear
git show --stat HEAD                    # after commit: only the new path tracked
git rm --cached tests/unit/test_x.py   # if the old path is still staged
git commit --amend                      # re-runs hooks
```

### Step 6 — Re-check after any amend (hooks may rewrite files)

`git commit --amend` re-runs pre-commit; ruff may reformat the test (e.g. collapse a
wrapped assert) and leave the tree dirty.

```bash
git status                              # must be clean
# if hooks rewrote files: git add <file> && git commit --amend
```

### Quick Reference

```bash
# BEFORE writing a new unit test: find where the mirrored sub-package is.
find tests/unit -name "test_<thing>.py"          # verify a cited path actually exists
ls tests/unit/                                    # sub-packages mirror hephaestus/
# repo-root doc/config presence tests -> tests/unit/docs/

# Compute parents[N] for REPO_ROOT:
#   tests/unit/test_x.py        -> Path(__file__).resolve().parents[2]
#   tests/unit/<pkg>/test_x.py  -> Path(__file__).resolve().parents[3]

# Run the structural gate explicitly:
pre-commit run --files tests/unit/<pkg>/test_x.py   # "Check unit test structure" must Pass

# After relocating a file, confirm the OLD path is not still staged/committed:
git diff --cached --name-only
git show --stat HEAD
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Placed `test_mcp_config.py` directly under `tests/unit/` as the plan implied | pre-commit "Check unit test structure" hook failed: "test_*.py files found directly under tests/unit/. Move them into the appropriate sub-package." | Repo forbids bare test files in `tests/unit/`; they must mirror `hephaestus/` into a sub-package. |
| 2 | Trusted the plan's cited path `tests/unit/test_import_surface.py` | The file actually lives at `tests/unit/validation/test_import_surface.py`; the cited path was stale | Verify a cited test path with `find tests/unit -name <file>` before copying it. |
| 3 | Moved the file to `tests/unit/docs/` but kept `REPO_ROOT = parents[2]` | One extra directory level means repo root is now `parents[3]`; `parents[2]` points one level too shallow | Increment `parents[N]` by the number of directory levels added when relocating a test. |
| 4 | Committed after `git add` of the original path, then recreated under the sub-package | The old path stayed in the index and a duplicate test file landed in the commit | After relocating, `git rm --cached <old>` and verify with `git show --stat HEAD` that only the new path is tracked. |
| 5 | Ran `git commit --amend` to drop the duplicate | The amend re-ran pre-commit, which ruff-reformatted the test and left the tree dirty | After an amend that triggers hooks, re-check `git status`; re-stage and amend again if hooks rewrote files. |

## Results & Parameters

**Final correct file location**: `tests/unit/docs/test_mcp_config.py`

**REPO_ROOT line** (file is two levels below repo root under `tests/unit/docs/`):

```python
REPO_ROOT = Path(__file__).resolve().parents[3]
```

**Canonical home**: `tests/unit/docs/` is the canonical sub-package for repo-root
doc/config presence + drift regression tests in ProjectHephaestus, alongside
`test_version_currency.py`. Repo-root presence assertions (`.mcp.json`, `docs/mcp.md`,
`AGENTS.md`) belong there, not at the `tests/unit/` root.

**Parents-depth rule**:

| Test location | REPO_ROOT |
| ------------- | --------- |
| `tests/unit/test_x.py` | `parents[2]` |
| `tests/unit/<pkg>/test_x.py` | `parents[3]` |

**Gates that passed locally**: "Check unit test structure", ruff, markdownlint (via
pre-commit). Full CI on the PR was not observed in this session.

## Related Skills

- `move-loose-test-files` — Refactoring workflow for relocating EXISTING loose test
  files into mirrored sub-packages with `git mv` and `.parent`-chain fixture fixes.
- `pytest-configuration-discovery-and-ci-pitfalls` — pytest config/discovery
  (testpaths, addopts, conftest sys.path, markers); does NOT cover placement enforcement.
- `pre-commit-hooks-and-linting-config` — General pre-commit hook configuration.
