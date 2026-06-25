---
name: testing-module-patch-target-after-extraction
description: "After extracting a module from a god-class, unit tests must patch symbols at the NEW module's import binding, not the original. Use when: (1) refactoring a large module into collaborators, (2) tests fail with unexpected call counts after extraction, (3) mock side_effect lists are consumed incorrectly, (4) during rebase conflict resolution on test files after parallel cluster extraction — prefer HEAD's patch targets (main's version already has correct targets for the new module), (5) need to distinguish stdlib module-object patches (e.g. subprocess.run) from named-function patches — stdlib patches at old_module still intercept calls from new_module; named-function patches do NOT."
category: testing
date: 2026-06-15
version: "1.1.0"
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
  - subprocess
  - stdlib
  - rebase
  - cluster-extraction
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
- During rebase conflict resolution on test files after parallel cluster extraction — HEAD (main's version) already has correct patch targets for the new module; prefer HEAD for patch target conflicts
- When a patch at `old_module.stdlib_function` still works after extraction (stdlib module-object exception) but `old_module.named_helper` does NOT (named-function patches must follow the symbol to its new namespace)

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

### Stdlib module-object exception (patches that still work across extraction)

Not all patches need retargeting after extraction. **Stdlib module patches** continue to intercept calls from the new module without change:

```python
# STILL WORKS after extracting calls to new_module.py:
@patch("old_module.subprocess.run")   # patches the subprocess MODULE OBJECT in old_module's namespace
# → new_module imports 'import subprocess' and calls subprocess.run()
# → both reference the SAME underlying subprocess module object
# → the patch intercepts calls from new_module too
```

**Named-function patches** do NOT survive extraction:

```python
# BROKEN after extracting calls to new_module.py:
@patch("old_module.resilient_call")   # patches the 'resilient_call' name in old_module's namespace
# → new_module imported 'from old_module import resilient_call' at module load time
# → the name 'resilient_call' in new_module's namespace is a DIFFERENT binding
# → the patch at old_module.resilient_call does not intercept calls from new_module

# CORRECT — retarget to the new module:
@patch("new_module.resilient_call")
```

**Decision rule**:

| Patch form | Survives extraction? | Why |
|------------|---------------------|-----|
| `@patch("old_mod.subprocess.run")` | YES (usually) | Patches the `subprocess` module object; `new_mod` accesses the same object via `import subprocess` |
| `@patch("old_mod.named_function")` | NO | Patches a name binding in `old_mod`'s namespace; `new_mod` has its own binding created at import time |
| `@patch("old_mod.SomeClass")` | NO | Same as named-function — a class is a name binding |
| `@patch("old_mod.CONSTANT")` | NO | Module-level constants are bound by name at import |

**Audit command** — distinguish the two patterns:

```bash
# Find all patches in test files and classify:
grep -rn '@patch\|with patch' tests/ | grep -oP '"[^"]+"' | while read target; do
    # If it matches old_module.stdlib_module.method → likely safe
    # If it matches old_module.function_name → must retarget after extraction
    echo "$target"
done
```

### Preferred patch targets during rebase conflict resolution

When rebasing a test file after parallel cluster extraction, you may encounter a conflict where:
- `HEAD` (main) uses `@patch("new_module.resilient_call")` (correct)
- `REBASE_HEAD` (your branch) uses `@patch("old_module.resilient_call")` (stale)

**Rule: prefer HEAD for all patch target conflicts.** The PR that merged first (now on main) had its tests updated to point at the new module. Your branch's test file may have been written before the correct targets were determined.

```bash
# During rebase conflict in test files:
# Take HEAD's version for any patch target that references the old vs new module conflict:
git show HEAD:tests/unit/automation/test_new_module.py > tests/unit/automation/test_new_module.py
# Then verify that your branch's UNIQUE test classes are present; if not, merge them in manually
grep "^class " tests/unit/automation/test_new_module.py   # check all classes present
```

**Exception**: if your branch adds NEW test classes not present on HEAD, append those classes after taking HEAD's version — don't drop them.

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
| Retargeted `subprocess.run` patches after extraction | Moved `@patch("old_module.subprocess.run")` to `@patch("new_module.subprocess.run")` assuming all patches need moving | Both reference the same underlying `subprocess` module object; the original patch still intercepted calls from the new module | Apply the module-object exception: `import subprocess; subprocess.run()` patches work across module boundaries; only named-function patches (`from old_module import named_fn`) require retargeting |
| Took branch's patch targets during rebase conflict on test file | During an add/add rebase conflict, took REBASE_HEAD's version of patch targets instead of HEAD's | Branch's version used stale `old_module.*` targets; HEAD (main's already-merged PR) had already corrected them to `new_module.*` | During rebase conflict resolution on test files, prefer HEAD for patch target decisions; the first-to-merge PR already fixed them |

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
| ProjectHephaestus | PR #1360 (issue #1360) — parallel cluster extraction of `loop_repo_manager.py` from `loop_runner.py`. During rebase after #1361 merged: `subprocess.run` patches at `loop_runner.subprocess.run` still intercepted calls from `loop_repo_manager.py` (stdlib module-object exception); `loop_runner.resilient_call` patches did NOT intercept calls from `loop_repo_manager.py` (named-function, must retarget to `loop_repo_manager.resilient_call`). HEAD's test targets were already correct — preferred HEAD during conflict resolution. | verified-ci — 1747 tests passed after rebase |
