---
name: automation-lazy-exports-sdk-surface-pattern
description: "Pattern for extending public SDK surfaces with peer classes using lazy-loading infrastructure. Use when: (1) adding peer classes to __all__, (2) extending TYPE_CHECKING imports, (3) preventing eager-load regressions, (4) avoiding architectural restructuring."
category: architecture
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [sdk-surface, lazy-loading, public-interface, automation, phase-entrypoint, pola, isp]
---

# Automation Lazy-Exports SDK Surface Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-05 |
| **Objective** | Extend hephaestus.automation public surface with missing peer classes (PlanReviewer, AddressReviewer, CIDriver) without restructuring internals |
| **Outcome** | ✅ Exposed 3 peer classes + 3 Options classes via __all__; extended _PHASE_ENTRYPOINTS for preload guards; added surface-pinning test |
| **Verification** | verified-local |
| **Project** | ProjectHephaestus |
| **Issue** | [#775](https://github.com/HomericIntelligence/ProjectHephaestus/issues/775) |
| **PR** | [#968](https://github.com/HomericIntelligence/ProjectHephaestus/pull/968) |

## When to Use

Use this skill when:

1. **Adding peer classes to a package __all__** — You have classes from submodules that belong in the public SDK surface but don't exist in `__all__`
2. **Extending TYPE_CHECKING imports** — Adding conditional imports for type hints without eager loading
3. **Protecting against eager-load regressions** — New phase modules must be guarded in _PHASE_ENTRYPOINTS tuple for preload safety
4. **Avoiding architectural restructuring** — You want to extend the public surface without moving files or changing module organization
5. **Preventing silent surface omissions** — You need a test to catch future __all__ regressions automatically

## Verified Workflow

### Quick Reference

```bash
# 1. Extend TYPE_CHECKING imports (alphabetical order)
# In hephaestus/automation/__init__.py, add:
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from hephaestus.automation.address_reviewer import AddressReviewer, AddressReviewerOptions
    from hephaestus.automation.ci_driver import CIDriver, CIDriverOptions
    from hephaestus.automation.plan_reviewer import PlanReviewer, PlanReviewerOptions

# 2. Extend __all__ (alphabetically sorted)
__all__ = [
    "AddressReviewer",
    "AddressReviewerOptions",
    "Automation",
    "CIDriver",
    "CIDriverOptions",
    "PlanReviewer",
    "PlanReviewerOptions",
    # ... existing exports
]

# 3. Add to _LAZY_EXPORTS dict (alphabetically sorted)
_LAZY_EXPORTS = {
    "AddressReviewer": "hephaestus.automation.address_reviewer",
    "AddressReviewerOptions": "hephaestus.automation.address_reviewer",
    "CIDriver": "hephaestus.automation.ci_driver",
    "CIDriverOptions": "hephaestus.automation.ci_driver",
    "PlanReviewer": "hephaestus.automation.plan_reviewer",
    "PlanReviewerOptions": "hephaestus.automation.plan_reviewer",
    # ... existing entries
}

# 4. Extend _PHASE_ENTRYPOINTS tuple (guards against eager-load regressions)
_PHASE_ENTRYPOINTS = (
    "hephaestus.automation.address_reviewer",
    "hephaestus.automation.ci_driver",
    "hephaestus.automation.plan_reviewer",
    # ... existing entries
)

# 5. Add surface-pinning test (in tests/unit/automation/test_package_imports.py)
def test_public_surface_pins_expected_symbols() -> None:
    """Verify that peer classes are exposed in hephaestus.automation.__all__.
    
    Prevents silent omissions like issue #775 by asserting the public surface
    includes all expected classes.
    """
    from hephaestus.automation import __all__
    
    expected_symbols = {
        "AddressReviewer",
        "AddressReviewerOptions",
        "CIDriver",
        "CIDriverOptions",
        "PlanReviewer",
        "PlanReviewerOptions",
    }
    
    missing = expected_symbols - set(__all__)
    assert not missing, f"Missing peer classes in __all__: {missing}"

# 6. Run validation
pixi run pytest tests/unit/automation/test_package_imports.py -v
pixi run ruff format hephaestus/automation/__init__.py
pixi run ruff check hephaestus/automation/__init__.py
pixi run mypy hephaestus/automation/__init__.py
```

### Detailed Steps

1. **Identify peer classes needing exposure**
   - Scan submodules for classes and Options that should be in public SDK
   - Check existing __all__ for gaps
   - Verify they follow naming: `PeerClass` + `PeerClassOptions`

2. **Extend TYPE_CHECKING block**
   - Add conditional imports inside `if TYPE_CHECKING:` block
   - Preserve alphabetical order within the block
   - Import both class and Options variant together

3. **Update __all__ list**
   - Add all 6 entries: 3 classes + 3 Options
   - Sort alphabetically (case-sensitive: uppercase first)
   - Verify each name appears exactly once

4. **Extend _LAZY_EXPORTS dictionary**
   - Map class name → module path (string)
   - Add both class and Options to same module entry
   - Sort entries alphabetically by key

5. **Guard new phase modules in _PHASE_ENTRYPOINTS**
   - Add module paths to tuple (prevents eager-load at import time)
   - Tuple is used in `_auto_import_on_access()` to skip preload for new phases
   - Tuple order doesn't matter (it's just a membership check)

6. **Add surface-pinning test**
   - Create test in existing `test_package_imports.py` (DRY: don't create new test file)
   - Function name: `test_public_surface_pins_expected_symbols()`
   - Assert expected symbols are in `__all__`
   - Guard against silent future omissions like #775

7. **Validate and test**
   - Run full test suite: `pixi run pytest tests/unit/automation/ -v`
   - Run linting: `pixi run ruff check hephaestus/automation/`
   - Run formatter: `pixi run ruff format hephaestus/automation/`
   - Run type checker: `pixi run mypy hephaestus/automation/`
   - All 9 import tests should pass

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Create new test file (`test_package_surface.py`) | Created parallel test module to pin __all__ surface | DRY violation — existing `test_package_imports.py` already iterates __all__; creating parallel coverage duplicates logic | Always check for existing test coverage before creating parallel test files; extend existing tests when adding similar assertions |
| Restructure internals to put all reviewers in shared module | Proposed consolidating PlanReviewer, AddressReviewer, CIDriver into one `peer_classes.py` module | Unnecessary refactoring; existing lazy-loading infrastructure already handles multi-module exposure; YAGNI principle applies | Use existing patterns first; only restructure if the pattern can't be extended |
| Eager-load new phase modules in __init__.py | Added direct imports: `from .address_reviewer import AddressReviewer` | Defeats lazy-loading; increases import time; breaks the pattern established in hephaestus.automation | Respect existing lazy-loading design; use _LAZY_EXPORTS + __getattr__ for peer classes |

## Results & Parameters

### Final __all__ Export List (14 entries)

```python
__all__ = [
    "AddressReviewer",
    "AddressReviewerOptions",
    "Automation",
    "AutomationOptions",
    "CIDriver",
    "CIDriverOptions",
    "PlanReviewer",
    "PlanReviewerOptions",
    # ... existing 6 entries (ImportIssuesFetcher, etc.)
]
```

### _LAZY_EXPORTS Dictionary Structure

```python
_LAZY_EXPORTS = {
    "AddressReviewer": "hephaestus.automation.address_reviewer",
    "AddressReviewerOptions": "hephaestus.automation.address_reviewer",
    "Automation": "hephaestus.automation.automation",
    "AutomationOptions": "hephaestus.automation.automation",
    "CIDriver": "hephaestus.automation.ci_driver",
    "CIDriverOptions": "hephaestus.automation.ci_driver",
    "ImportIssuesFetcher": "hephaestus.automation.import_issues_fetcher",
    "PlanReviewer": "hephaestus.automation.plan_reviewer",
    "PlanReviewerOptions": "hephaestus.automation.plan_reviewer",
    # ... existing entries (9 total)
}
```

### _PHASE_ENTRYPOINTS Tuple (guards new phase modules)

```python
_PHASE_ENTRYPOINTS = (
    "hephaestus.automation.address_reviewer",
    "hephaestus.automation.ci_driver",
    "hephaestus.automation.plan_reviewer",
    # ... existing phase module entries
)
```

### Test Output (All Passing)

```
tests/unit/automation/test_package_imports.py::test_can_import_all_exports PASSED
tests/unit/automation/test_package_imports.py::test_can_import_lazy_exports PASSED
tests/unit/automation/test_package_imports.py::test_lazy_exports_dict_sorted PASSED
tests/unit/automation/test_package_imports.py::test_all_in_lazy_exports PASSED
tests/unit/automation/test_package_imports.py::test_lazy_exports_in_all PASSED
tests/unit/automation/test_package_imports.py::test_all_sorted_case_sensitive PASSED
tests/unit/automation/test_package_imports.py::test_no_circular_imports PASSED
tests/unit/automation/test_package_imports.py::test_phase_entrypoints_are_strings PASSED
tests/unit/automation/test_package_imports.py::test_public_surface_pins_expected_symbols PASSED
======================== 9 passed in 0.45s ========================
```

### Validation Command

```bash
# Run surface-pinning test in isolation
pixi run pytest tests/unit/automation/test_package_imports.py::test_public_surface_pins_expected_symbols -v

# Run full automation test suite
pixi run pytest tests/unit/automation/ -v

# Verify no linting errors
pixi run ruff check hephaestus/automation/__init__.py

# Verify type hints
pixi run mypy hephaestus/automation/__init__.py
```

## Key Learnings

1. **Reuse lazy-loading infrastructure** — Don't restructure for peer-class additions. The TYPE_CHECKING + _LAZY_EXPORTS + __getattr__ pattern scales to any number of peer classes without modification to the core mechanism.

2. **Extend _PHASE_ENTRYPOINTS for preload guards** — New phase modules must be added to the tuple to ensure they're skipped during `_auto_import_on_access()` preload. Omitting them can cause eager-load regressions and increased import time.

3. **Test-pin the public surface** — Add `test_public_surface_pins_expected_symbols()` to catch future __all__ omissions automatically. Issue #775 happened because there was no assertion on expected exports; a test prevents silent regressions.

4. **Alphabetical ordering is load-bearing** — TYPE_CHECKING imports, __all__, and _LAZY_EXPORTS keys must all be alphabetically sorted for consistency and ease of review. Use case-sensitive ordering (uppercase letters first).

5. **One test file per package level** — Don't create parallel test files for similar concerns (e.g., test_package_surface.py). Extend existing test_package_imports.py to keep test organization DRY and discoverable.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #775 fix — exposed PlanReviewer, AddressReviewer, CIDriver in hephaestus.automation __all__ | [PR #968](https://github.com/HomericIntelligence/ProjectHephaestus/pull/968) — all 9 import tests pass locally; automation suite 1081 tests pass |
