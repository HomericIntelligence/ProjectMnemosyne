---
name: testing-integration-backstop-omitted-modules
description: "Prevent silent growth of coverage omit list by enforcing that omitted modules remain importable + console scripts work. Use when: (1) modules are intentionally omitted from coverage (live CLI/TTY), (2) want to catch import-time regressions, (3) need proof that entry points are functional."
category: testing
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [testing, integration, omit-list, backstop, smoke-test, console-scripts]
---

# Integration Smoke Test Backstop for Omitted Modules

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Prevent silent growth of coverage omit list by ensuring omitted modules remain importable and console scripts work end-to-end |
| **Outcome** | Successfully implemented in ProjectHephaestus issue #623; caught regression where omit list was silently added without notice |
| **Verification** | verified-local (16 integration tests pass; catches import-time regressions) |

## When to Use

- You have a coverage omit list (modules intentionally skipped because they use live CLI/TTY/process spawning)
- You want to prevent the omit list from growing without explicit approval
- You need proof that omitted modules are still importable (no silent import regressions)
- You want to verify console scripts don't hang, crash, or fail at invocation time
- You're worried that skipping coverage is masking broken code

## Verified Workflow

### Quick Reference

```bash
# 1. Create test_orchestration_smoke.py for import checks
# Parametrizes over all omitted modules
pytest tests/integration/test_orchestration_smoke.py -v

# 2. Create test_omit_allowlist.py to freeze the list
# Asserts omit list matches known-good set
pytest tests/integration/test_omit_allowlist.py -v

# Expected: 16 tests pass
# Expected: test_omit_allowlist fails if new modules added to omit list (signals growth)
```

### Detailed Steps

1. **Create test_orchestration_smoke.py** in `tests/integration/`:
   - Parametrize test over all 10 omitted modules from pyproject.toml
   - Test 1: Import each module (catches import-time regressions)
   - Test 2: For 4 console script modules, run `<script> --help` via subprocess with 5s timeout
     - Signals if script hangs, crashes, or fails to start
     - Runs without live session (subprocess isolation)
   - Test 3: For 2 script-less modules, verify they have callable `main()`
   - All tests should pass; if any fail, regression detected

2. **Create test_omit_allowlist.py** in `tests/integration/`:
   - Read pyproject.toml `[tool.coverage.run].omit` list
   - Freeze against known-good set of 10 modules + 2 globs
   - Assert current omit list matches frozen set (fails if new modules added)
   - Prevents silent growth (any addition requires explicit test update + review)

3. **Run tests as part of CI/local test suite**:
   ```bash
   pytest tests/integration/ -v
   ```
   - Part of standard test suite (runs after unit tests)
   - Catches regressions early

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| No backstop test (omit list grew 1 module) | Relied only on manual review of coverage reports | New module was added to omit list without notice; coverage report still looked good | Without explicit test, allowlist grows silently; frozen set prevents this |
| Running full test suite against omitted modules | Tried to unit test modules despite omit config | Some modules failed in unit test context (need live CLI/subprocess); defeats purpose of omit | Omit list exists for a reason (modules need live context); unit test smoke checks are sufficient |
| Complex console script validation | Tried to run actual interactive CLI workflows | Timeouts and hangs in test environment; unclear what failure means | Simple --help check is sufficient; proves entry point works without environment fragility |

## Results & Parameters

### Test Implementation Snippets

**test_orchestration_smoke.py:**
```python
import pytest
from hephaestus.discovery import discover_omitted_modules

OMITTED_MODULES = discover_omitted_modules()  # ["hephaestus.agents", "hephaestus.cli", ...]

@pytest.mark.parametrize("module_name", OMITTED_MODULES)
def test_omitted_module_importable(module_name):
    """Verify omitted modules remain importable (no import-time regressions)."""
    __import__(module_name)  # Raises ImportError if broken


CONSOLE_SCRIPTS = [
    ("hephaestus-validate", "hephaestus.validation.main"),
    ("hephaestus-check-coverage", "hephaestus.validation.coverage"),
]

@pytest.mark.parametrize("script_name,module", CONSOLE_SCRIPTS)
def test_console_script_help(script_name, module):
    """Run --help on each console script; 5s timeout."""
    import subprocess
    result = subprocess.run(
        [script_name, "--help"],
        timeout=5,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"{script_name} failed: {result.stderr}"


SCRIPT_LESS_MODULES = ["hephaestus.agents", "hephaestus.discovery"]

@pytest.mark.parametrize("module_name", SCRIPT_LESS_MODULES)
def test_script_less_module_has_main(module_name):
    """Verify modules without console scripts have callable main()."""
    mod = __import__(module_name, fromlist=["main"])
    assert hasattr(mod, "main") and callable(mod.main)
```

**test_omit_allowlist.py:**
```python
def test_omit_allowlist_frozen():
    """Assert omit list matches known-good frozen set (fails if new modules added)."""
    from hephaestus.config import load_pyproject
    
    config = load_pyproject()
    current_omit = set(config["tool"]["coverage"]["run"]["omit"])
    
    frozen_omit = {
        "hephaestus/agents/*",
        "hephaestus/cli/*",
        "hephaestus/discovery/*",
        # ... 7 more module paths + 2 globs
        "**/tests/**",
    }
    
    assert current_omit == frozen_omit, (
        f"Omit list changed. New: {current_omit - frozen_omit}, "
        f"Removed: {frozen_omit - current_omit}"
    )
```

### Expected Output

```
tests/integration/test_orchestration_smoke.py::test_omitted_module_importable[hephaestus.agents] PASSED
tests/integration/test_orchestration_smoke.py::test_omitted_module_importable[hephaestus.cli] PASSED
...
tests/integration/test_orchestration_smoke.py::test_console_script_help[hephaestus-validate] PASSED
tests/integration/test_orchestration_smoke.py::test_console_script_help[hephaestus-check-coverage] PASSED
...
tests/integration/test_omit_allowlist.py::test_omit_allowlist_frozen PASSED

16 passed
```

If a new module is added to omit list:
```
tests/integration/test_omit_allowlist.py::test_omit_allowlist_frozen FAILED
AssertionError: Omit list changed. New: {'hephaestus/new_module/*'}, Removed: set()
```

### Key Parameters

- **Console script timeout**: 5 seconds (sufficient for --help, fails fast on hangs)
- **Parametrize over all omitted modules**: Catches import regressions for any omitted module
- **Frozen set in test**: Explicit whitelist that must be updated to add modules (requires review)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | issue #623 (test: add per-module coverage floor + e2e backstop) | Implemented test_orchestration_smoke.py (10 modules, 4 scripts, 2 script-less) + test_omit_allowlist.py frozen set; 16 tests pass |

