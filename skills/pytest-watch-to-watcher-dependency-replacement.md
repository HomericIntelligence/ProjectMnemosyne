---
name: pytest-watch-to-watcher-dependency-replacement
description: "Replace the unmaintained pytest-watch (last release 2018) with pytest-watcher, a modern actively maintained fork. Removes deprecated docopt 0.6.2 transitive dependency while preserving ptw CLI compatibility. Use when: (1) pytest-watch is declared in pixi.toml, (2) docopt deprecation warnings appear, (3) pytest 9.x compatibility testing flags legacy dependencies."
category: tooling
date: 2026-06-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pytest
  - pytest-watcher
  - dependency
  - pixi
  - docopt
  - deprecation
---

# Dependency Replacement: pytest-watch → pytest-watcher

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **Issue** | #746 |
| **PR** | #921 |
| **Objective** | Replace unmaintained pytest-watch (last 2018 release, transitive docopt 0.6.2) with pytest-watcher (modern fork actively maintained for pytest 9.x) |
| **Outcome** | Success — ptw CLI unchanged, drop-in replacement, docopt removed from lockfile, all 3170 unit tests pass |
| **Verification** | verified-local (tests pass locally; CI validation pending) |

## When to Use

- Replacing an unmaintained test-related dependency with an active fork
- Removing deprecated transitive dependencies (docopt 0.6.2) while keeping developer UX unchanged
- Ensuring pytest tool compatibility across major pytest versions (9.x)
- Swapping dependencies where the old package has no new releases but forks exist with modern support

## Verified Workflow

### Prerequisites
- ProjectHephaestus uses pixi for environment management
- `pytest-watch = ">=4.2,<5"` is declared in `pixi.toml:[feature.dev.pypi-dependencies]`
- `ptw` is invoked via justfile recipe or command-line for file-change test re-running

### Quick Reference

```bash
# 1. Edit pixi.toml: swap dependency and update comment
# OLD:
#   pytest-watch = ">=4.2,<5"
# NEW:
#   pytest-watcher = ">=0.4,<1"

# 2. Resolve environment
pixi install

# 3. Restore editable install if pixi re-solve drops it (known issue)
pixi run dev-install

# 4. Verify ptw entry point
pixi run which ptw
pixi run ptw --help | head -5

# 5. Verify deprecated docopt is gone from lockfile
! grep -E '^name = "docopt"' pixi.lock && echo "PASS: docopt absent"

# 6. Run unit tests
pixi run pytest tests/unit -q

# 7. Commit with closing pattern
git commit -S -m "build(deps): replace pytest-watch with pytest-watcher

Swap pytest-watch (last release 2018, pulls deprecated docopt 0.6.2) for
pytest-watcher, the actively maintained modern fork.

Closes #746"

# 8. Push and create PR with state:implementation-go label
git push -u origin <branch>
gh pr create --title "..." --body "Closes #746..."
gh pr edit <PR#> --add-label state:implementation-go
gh pr merge --auto --squash <PR#>
```

### Detailed Steps

1. **Locate the old dependency declaration**
   - Search pixi.toml: `grep -n "pytest-watch" pixi.toml`
   - Confirm it's in `[feature.dev.pypi-dependencies]` section (PyPI, not conda-forge)

2. **Replace the dependency line and update comment**
   - Old: `pytest-watch = ">=4.2,<5"`
   - New: `pytest-watcher = ">=0.4,<1"`
   - Update adjacent comment to name pytest-watcher and reference issue (e.g., "see issue #746")
   - Rationale for `>=0.4,<1`: pytest-watcher 0.4.x is the current stable line with pytest 9.x support; major cap follows convention used in other PyPI entries

3. **Update any consumer references (e.g., justfile comment)**
   - Check justfile for references to "pytest-watch" in comments
   - Update comment text to "pytest-watcher"
   - **DO NOT** change the actual `ptw` invocation — the CLI name is identical

4. **Resolve the environment**
   - Run: `pixi install`
   - This regenerates `pixi.lock`, pulling pytest-watcher and removing pytest-watch + docopt

5. **Restore editable install (mitigation for known pixi issue)**
   - Per [pixi-env-resolve-drops-editable-install](https://github.com/HomericIntelligence/ProjectMnemosyne/blob/main/skills/pixi-env-resolve-drops-editable-install.md), pixi may wipe `pip install -e .`
   - Run: `pixi run dev-install`
   - This re-applies the editable install in O(seconds)

6. **Verify entry point and help**
   - Run: `pixi run which ptw`
   - Expected: path to ptw executable in .pixi environment
   - Run: `pixi run ptw --help | head -5`
   - Expected: pytest_watcher usage banner (shows it's the new package)

7. **Confirm docopt is gone**
   - Run: `! grep -E '^name = "docopt"' pixi.lock && echo "PASS" || echo "FAIL"`
   - Expected: PASS (docopt was a transitive of pytest-watch; pytest-watcher doesn't pull it)

8. **Run full unit test suite**
   - Run: `pixi run pytest tests/unit -q`
   - Expected: all tests pass (existing tests don't depend on pytest-watch implementation details)

9. **Create signed commit**
   - Follow conventional commits: `git commit -S -m "build(deps): replace pytest-watch with pytest-watcher"`
   - Include in body: rationale, version pin reasoning, docopt removal, test results
   - Close the issue with: `Closes #746` (literal keyword, capital C, no colon)

10. **Push and PR**
    - Push: `git push -u origin <branch>`
    - Create PR with body containing `Closes #746` on its own line
    - Add label: `state:implementation-go` (required before auto-merge)
    - Arm auto-merge: `gh pr merge --auto --squash`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Verify ptw CLI before pixi install | Checked if `ptw` would work without regenerating lock | Premature verification; need to know if the new package ships a `ptw` entry point | Run `pixi install` first, then verify CLI; pytest-watcher does ship `ptw` (drop-in confirmed) |
| Skip docopt check | Assumed docopt would remain if not directly pulled | Incorrect; docopt was a transitive of pytest-watch specifically | Always verify lock file for removed transitives; confirms the swap eliminated the deprecated dependency |

## Results & Parameters

### Dependency Configuration

**pixi.toml change:**
```toml
[feature.dev.pypi-dependencies]
# OLD:
pytest-watch = ">=4.2,<5"

# NEW:
# pytest-watcher (ptw) powers `just watch` — runs unit tests on file change for
# fast feedback during local development. Actively maintained fork of the
# unmaintained pytest-watch (last 2018 release; see issue #746). Not on
# conda-forge; ships from PyPI.
pytest-watcher = ">=0.4,<1"
```

### Lock File Delta

**Before:** pixi.lock includes:
```
name = "pytest-watch"
version = "4.2.0"

name = "docopt"
version = "0.6.2"
```

**After:** pixi.lock includes:
```
name = "pytest-watcher"
version = "0.4.x" (latest 0.4.x at resolution time)

# docopt absent
```

### Test Results

```
pixi run pytest tests/unit -q
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
...
================================ tests coverage ================================
Name                                              Stmts   Miss Branch BrPart   Cover
...
TOTAL                                              9362   1327   3064    313  84.66%
Required test coverage of 80% reached. Total coverage: 84.66%
================= 3170 passed, 18 skipped in 256.39s (0:04:16) =================
```

### CLI Verification

```bash
$ pixi run which ptw
/home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-746/.pixi/envs/default/bin/ptw

$ pixi run ptw --help | head -5
[ptw] Unable to initialize terminal state; interactive mode disabled
usage: pytest_watcher [-h] [--now] [--clear] [--notify-on-failure]
                      [--delay DELAY] [--runner RUNNER] [--patterns PATTERNS]
                      [--ignore-patterns IGNORE_PATTERNS] [--version]
                      path
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #746, PR #921 | Successfully replaced pytest-watch with pytest-watcher; docopt removed; all 3170 tests pass; ptw CLI works unchanged |
