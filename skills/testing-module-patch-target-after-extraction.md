---
name: testing-module-patch-target-after-extraction
description: "After extracting a module from a god-class, unit tests must patch symbols at the NEW module's import binding, not the original. Use when: (1) refactoring a large module into collaborators, (2) tests fail with unexpected call counts after extraction, (3) mock side_effect lists are consumed incorrectly."
category: testing
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - python
  - testing
  - mock
  - patch
  - module-extraction
  - god-class
  - collaborator
  - refactoring
  - pytest
  - unittest-mock
---

# Testing: Module-Level Patch Target After Extraction

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Fix failing unit tests after extracting collaborator modules from a god-class |
| **Outcome** | Successful — CI gate passes with correct patch targets |
| **Verification** | verified-ci |

## When to Use

- After any module extraction refactor (god-class → collaborators)
- When tests fail with `StopIteration` or `AssertionError: Expected call not found` after a refactor
- When mock `side_effect` lists are consumed fewer times than expected
- When patches that "worked before the refactor" no longer intercept calls
- When `assert_called_once_with` shows 0 calls despite the code path executing

## Verified Workflow

### Quick Reference

```bash
# After extracting new_module.py from old_module.py:
# WRONG - patches the old binding
@patch("old_module.some_function")

# CORRECT - patches where the symbol is actually bound
@patch("new_module.some_function")
```

**Core rule**: Python binds a symbol in the module that imports it at import time. `patch("module.symbol")` intercepts lookups of `symbol` in `module`'s namespace — not in the module where `symbol` was originally defined.

### Detailed Steps

1. **Identify all symbols moved to the new module** — list every `from x import y` in the new collaborator file.

2. **Audit tests for the old module** — search for `@patch("old_module.<symbol>")` where `<symbol>` now lives in `new_module`.

   ```bash
   grep -rn 'patch("hephaestus.automation.ci_driver\.' tests/unit/automation/
   ```

3. **Check for split call paths** — a symbol may be called from BOTH the old module (still imported there) AND the new collaborator. Each import site requires its own patch:
   - `@patch("old_module.symbol")` — for calls made through the old module's namespace
   - `@patch("new_module.symbol")` — for calls made through the collaborator's namespace

4. **Pre-agent vs post-agent paths** — when a driver has pre-agent setup code AND post-agent cleanup code that call the same underlying function, each may import it at a different binding:

   ```python
   # ci_fix_orchestrator.py imports run() at module level
   from subprocess import run  # → bind: ci_fix_orchestrator.run

   # ci_driver.py also imports run() at module level
   from subprocess import run  # → bind: ci_driver.run

   # Tests for pre-agent calls must patch ci_fix_orchestrator.run
   # Tests for post-agent calls must patch ci_driver.run
   ```

5. **Direct vs delegated call paths** — when the driver delegates to a collaborator (`self._pr_discovery.discover_bot_prs()`), the collaborator's methods use symbols imported in the collaborator module, not the driver module:

   ```python
   # WRONG: patches driver binding, misses collaborator calls
   @patch("hephaestus.automation.ci_driver.get_repo_info")

   # CORRECT: patches where collaborator actually bound the symbol
   @patch("hephaestus.automation.pr_discovery.get_repo_info")
   ```

6. **Logger patches** — when a class moves to a new module, its logger is bound in the new module:

   ```python
   # WRONG after extracting PRDiscovery to pr_discovery.py:
   @patch("hephaestus.automation.ci_driver.logger")

   # CORRECT:
   @patch("hephaestus.automation.pr_discovery.logger")
   ```

7. **Run tests** with verbose output to confirm all call counts match expected:

   ```bash
   pixi run pytest tests/unit/automation/test_pr_discovery.py -v
   pixi run pytest tests/unit/automation/test_ci_driver.py -v
   ```

### Dual-patch pattern for split call paths

When a method chain splits across modules (e.g., pre-agent SHA snapshot moved to a collaborator while post-agent SHA read stays on the host):

```python
# WRONG — only patches the orchestrator's run:
with patch("hephaestus.automation.ci_fix_orchestrator.run", ...):
    driver._run_ci_fix_session(...)

# RIGHT — patches both lookup sites:
with (
    patch("hephaestus.automation.ci_fix_orchestrator.run", return_value=pre_sha),
    patch("hephaestus.automation.ci_driver.run", return_value=post_sha),
):
    driver._run_ci_fix_session(...)
```

### Systematic audit after any extraction

```bash
# 1. List all symbols imported in the new collaborator module
grep "^from\|^import" new_module.py

# 2. Find all test patches that reference the old module for those symbols
grep -rn 'patch("pkg.old_module\.' tests/

# 3. For each match, determine if the symbol now lives in new_module
#    If yes → retarget the patch

# 4. Also check for patches targeting the new module that reference symbols
#    still imported directly in old_module (dual-binding case)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Patch only `ci_driver.get_repo_info` | Patched at driver namespace after extracting `pr_discovery.py` | `pr_discovery.py` imported `get_repo_info` at its own module level; driver patch never intercepted collaborator calls | Python binds symbols at import time in the importing module's namespace |
| Patch only `ci_driver.run` for pre-agent path | Assumed all `run()` calls go through `ci_driver` namespace | `ci_fix_orchestrator.py` imports `run` independently; pre-agent call uses `ci_fix_orchestrator.run` binding | Each module that imports a symbol creates an independent binding |
| Single `side_effect` list for one patch | Assumed one `@patch` covers all call sites | Collaborator module had its own binding; side_effect consumed by only one path, leaving the other to call the real function | Count distinct import sites, not call sites |
| Left `@patch("ci_driver.logger")` after extraction | Assumed logger patch target unchanged | Logger is instantiated at module level in the new collaborator; the old binding was no longer the one emitting the warning | After extracting a class/function, grep all test patches for module-level logger, constant, and utility patches and retarget them |

## Results & Parameters

After applying correct patches, the pattern for extracted collaborators is:

```python
# Before extraction (god-class, all calls go through ci_driver):
@patch("hephaestus.automation.ci_driver.get_repo_info")
@patch("hephaestus.automation.ci_driver._gh_call")
def test_discover_bot_prs(self, mock_gh, mock_repo):
    ...

# After extraction (collaborator pr_discovery.py):
@patch("hephaestus.automation.pr_discovery.get_repo_info")   # collaborator binding
@patch("hephaestus.automation.pr_discovery._gh_call")         # collaborator binding
def test_discover_bot_prs(self, mock_gh, mock_repo):
    ...

# When BOTH driver and collaborator call the same symbol (dual-binding):
@patch("hephaestus.automation.ci_driver.gh_pr_checks")              # driver's poll loop
@patch("hephaestus.automation.ci_check_inspector.gh_pr_checks")     # collaborator's binding
def test_poll_loop(self, mock_inspector, mock_driver):
    ...
```

### Grep commands for the audit

```bash
# Find all patches in test files for a given module
grep -rn '@patch.*ci_driver\.' tests/unit/automation/ | grep -v "\.pyc"

# Find where a symbol is imported in the new collaborator modules
grep -rn "^from.*import.*get_repo_info\|^import.*get_repo_info" hephaestus/automation/*.py

# Identify dual-binding cases — symbol imported in both old and new module
grep -l "import get_repo_info\|from.*import.*get_repo_info" hephaestus/automation/*.py
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1292 (issue #1179) — decompose CIDriver into 4 collaborators (`pr_discovery.py`, `ci_check_inspector.py`, `ci_fix_orchestrator.py`, `post_merge_processor.py`) | verified-ci — 146 existing tests + 22 new tests pass |
