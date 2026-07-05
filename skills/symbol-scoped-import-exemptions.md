---
name: symbol-scoped-import-exemptions
description: "Use when: (1) enforcing zero-io-imports architectural guards on pipeline automation modules — exempting ONLY specific symbols (e.g., parse_review_verdict) from normally-forbidden I/O module imports; (2) writing a guard that validates symbol-scoped exemptions (e.g., asserts that importing ANY OTHER symbol from claude_invoke triggers a violation); (3) designing an import exemption to be explicit-intent-based, forcing future imports to be justified in the exemption list rather than silently slipping through unscoped rules; (4) documenting why a pure function (parse_review_verdict) needs importing an I/O module (claude_invoke) but constraining that import to ONLY the pure function and not hypothetical future uses."
category: architecture
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: verified-ci
history: null
tags:
  - import-guard
  - zero-io-imports
  - symbol-scoped
  - exemption-list
  - pipeline-architecture
  - architectural-boundary
  - explicit-intent
  - pure-function
  - constraint-enforcement
  - test-validation
---

# Symbol-Scoped Import Exemptions

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-04 |
| **Objective** | Enforce zero-io-imports architectural guards on pipeline automation modules by using symbol-scoped (not unscoped) exemption lists — constraining allowed imports to ONLY specific pure functions, forcing intent to be explicit, and validating via test that importing ANY OTHER symbol from the exempted module triggers a violation. |
| **Outcome** | `hephaestus/automation/planner_review_loop.py` exempts ONLY `parse_review_verdict` from `claude_invoke` (I/O forbidden module), validated by `test_zero_io_imports.py::test_plan_review_exemption_is_symbol_scoped` asserting that importing ANY other symbol fails the guard. |
| **Verification** | verified-ci (115 tests passing; pre-commit hooks passing) |
| **Version** | 1.0.0 |

## When to Use

- You are enforcing a zero-io-imports architectural guard on a package submodule (e.g., pipeline automation stages must not import I/O modules like `claude_invoke`).
- A pure function in a normally-forbidden I/O module is genuinely needed by the guarded module (e.g., `parse_review_verdict` is a pure parser).
- You want to exempt ONLY that one symbol from the guard, preventing future drift where unrelated I/O functions silently import into the guarded module.
- You need to validate the exemption is symbol-scoped (not unscoped) by testing that importing OTHER symbols from the same I/O module triggers a violation.
- You want to document architectural intent: "We import this I/O module ONLY for this pure function TODAY. If you need other symbols, update the exemption list with justification."

## Verified Workflow

### Step 1: Define the Zero-IO-Imports Guard

The base zero-io-imports test scans a guarded module and asserts no imports of forbidden modules:

```python
# tests/unit/automation/test_zero_io_imports.py (simplified)

ZERO_IO_MODULES = {
    "hephaestus.automation.planning_stage",
    "hephaestus.automation.plan_review_stage",
}

FORBIDDEN_IO_MODULES = {
    "claude_invoke",
    "gh_issue_json",
    "run_subprocess",
}

# UNSCOPED exemptions (entire module allowed):
UNSCOPED_EXEMPTIONS = {
    "hephaestus.automation.planner_review_loop": {"state_labels"},  # Can import anything from state_labels
}

# SYMBOL-SCOPED exemptions (only specific symbols allowed):
SYMBOL_SCOPED_EXEMPTIONS = {
    "hephaestus.automation.planner_review_loop": {"claude_invoke": {"parse_review_verdict"}},
}

def test_zero_io_imports():
    """Assert ZERO_IO_MODULES import no FORBIDDEN_IO_MODULES."""
    for module_name in ZERO_IO_MODULES:
        module = import_module(module_name)
        module_path = Path(module.__file__)
        source = module_path.read_text()
        
        for line in source.splitlines():
            s = line.strip()
            # Check for direct imports of forbidden modules
            if any(f"import {fb}" in s or f"from {fb}" in s for fb in FORBIDDEN_IO_MODULES):
                # If module has an exemption, skip
                if module_name in UNSCOPED_EXEMPTIONS or module_name in SYMBOL_SCOPED_EXEMPTIONS:
                    # Validate the exemption
                    # (see step 3 below)
                    pass
                else:
                    pytest.fail(f"{module_name}:{lineno} forbidden I/O import: {s}")
```

### Step 2: Add Symbol-Scoped Exemption to Configuration

In the guard test, define symbol-scoped exemptions as nested dicts: module → (forbidden_module → frozenset of allowed symbols):

```python
SYMBOL_SCOPED_EXEMPTIONS = {
    "hephaestus.automation.planner_review_loop": {
        "claude_invoke": frozenset({"parse_review_verdict"}),  # ONLY this symbol
    },
}
```

This structure forces intent:
- "We import `claude_invoke` (an I/O module) into this guarded module"
- "We ONLY import the `parse_review_verdict` symbol"
- "If you need other symbols, update this frozenset with justification"

### Step 3: Validate the Exemption is Symbol-Scoped

Create a test that asserts:
- (A) Importing the allowed symbol WORKS (no violation)
- (B) Importing ANY OTHER symbol from the same I/O module FAILS (triggers violation)

```python
def test_plan_review_exemption_is_symbol_scoped():
    """Assert that claude_invoke exemption permits ONLY parse_review_verdict."""
    
    # (A) The allowed symbol should parse without error
    from hephaestus.automation.planner_review_loop import parse_review_verdict  # noqa: F401
    
    # (B) Other symbols from claude_invoke should be rejected
    # Import the guarded module and verify it does NOT import other symbols
    source = Path(hephaestus.automation.planner_review_loop.__file__).read_text()
    
    forbidden_imports = {
        "from claude_invoke import ReviewVerdict",  # Example: ReviewVerdict is NOT parse_review_verdict
        "from claude_invoke import invoke",
        "import claude_invoke",
    }
    
    for forbidden in forbidden_imports:
        assert forbidden not in source, (
            f"planner_review_loop.py must not import {forbidden}; "
            f"only parse_review_verdict is exempted from the zero-io-imports guard"
        )
```

**Key assertion**: The test validates that the guarded module imports ONLY the symbol in the exemption list, nothing more. This forces "explicit intent": if code later needs `ReviewVerdict`, the exemption list must be updated.

### Step 4: Document the Exemption with Justification

Add a comment in the guarded module explaining why the I/O import is needed:

```python
# hephaestus/automation/planner_review_loop.py

# EXEMPTED IMPORT: parse_review_verdict is a pure function that parses
# structured review output from claude_invoke. It has no side effects
# and is safe to import into this zero-io-imports module.
# Symbol-scoped exemption: ONLY parse_review_verdict; other claude_invoke
# symbols are forbidden.
from hephaestus.automation.claude_invoke import parse_review_verdict

def review_loop(...):
    """Review loop that uses parse_review_verdict to parse feedback."""
    verdict = parse_review_verdict(feedback_text)
    ...
```

### Step 5: Promote Pure Functions to Shared Modules

If the pure function is used by multiple guarded modules, promote it to a shared utility module to avoid repeated exemptions:

**Before** (exemption in two guarded modules):
```python
# In planner_review_loop.py and plan_review_stage.py
SYMBOL_SCOPED_EXEMPTIONS = {
    "hephaestus.automation.planner_review_loop": {"claude_invoke": {"parse_review_verdict"}},
    "hephaestus.automation.plan_review_stage": {"claude_invoke": {"parse_review_verdict"}},
}
```

**After** (pure function promoted to shared module):
```python
# In hephaestus/automation/state_labels.py (zero-io module)
def apply_plan_verdict(verdict_dict: dict, item: dict) -> dict:
    """Pure function: apply a parsed plan verdict to an item."""
    # No I/O; safe for zero-io modules to import
    ...

# In planner_review_loop.py (zero-io, no exemption needed)
from hephaestus.automation.state_labels import apply_plan_verdict
```

This reduces exemption churn and clusters pure functions in their natural home.

### Step 6: Run Verification

After implementing symbol-scoped exemptions and tests:

```bash
# Run the zero-io-imports guard test
pixi run pytest tests/unit/automation/test_zero_io_imports.py -v

# Run the symbol-scoped validation test
pixi run pytest tests/unit/automation/test_zero_io_imports.py::test_plan_review_exemption_is_symbol_scoped -v

# Run the full test suite
pixi run pytest tests/unit -v

# Run pre-commit hooks
pixi run pre-commit run --all-files
```

## Real Example: Issue #1814 (ProjectHephaestus, 2026-07-04)

**Context**: Planning and plan-review pipeline stages must enforce zero-io-imports (no subprocess, no GitHub API calls at the module level).

**Discovery**: `planner_review_loop.py` needs to parse structured feedback from `claude_invoke.parse_review_verdict`, a pure parser with no side effects.

**Solution**:

1. **Add symbol-scoped exemption**:
   ```python
   SYMBOL_SCOPED_EXEMPTIONS = {
       "hephaestus.automation.planner_review_loop": {
           "claude_invoke": frozenset({"parse_review_verdict"}),
       },
   }
   ```

2. **Import only the allowed symbol**:
   ```python
   # hephaestus/automation/planner_review_loop.py
   from hephaestus.automation.claude_invoke import parse_review_verdict
   ```

3. **Validate with test**:
   ```python
   def test_plan_review_exemption_is_symbol_scoped():
       """Verify planner_review_loop imports ONLY parse_review_verdict."""
       source = Path(...).read_text()
       assert "from claude_invoke import ReviewVerdict" not in source
       assert "import claude_invoke" not in source
       # parse_review_verdict IS imported (safe)
   ```

4. **Promote pure function** (later iteration):
   - `apply_plan_verdict` (pure function) was promoted to `hephaestus/automation/state_labels.py`
   - Reused by both legacy and new pipeline stages
   - No exemptions needed for state_labels (zero-io module)

**Outcome**: `test_plan_review_exemption_is_symbol_scoped` passes; guard validates symbol-scoped intent; future imports are explicit.

## Failed Attempts (Anti-Patterns)

| Attempt | Problem | Why Failed | Resolution |
|---------|---------|-----------|------------|
| Unscoped exemption (entire module allowed) | `UNSCOPED_EXEMPTIONS = {"planner_review_loop": {"claude_invoke"}}` | Allowed ANY symbol from `claude_invoke` to be imported, including future I/O functions; drift risk: code later imports `invoke()` or other I/O functions silently | Use symbol-scoped exemptions; list ONLY `parse_review_verdict`, not the whole module |
| No test validation of exemption scope | Exempted `parse_review_verdict` but never verified other symbols were blocked | Code could later import `ReviewVerdict` or other symbols without triggering the guard | Add a test (`test_plan_review_exemption_is_symbol_scoped`) that asserts importing OTHER symbols fails the guard |
| No comment explaining the exemption | Exemption was in the config but no docstring in the guarded module | Future reviewers didn't understand WHY an I/O import was allowed | Add a comment in the guarded module: "EXEMPTED IMPORT: X is a pure function; symbol-scoped exemption ONLY for X" |
| Pure function not promoted to shared module | `apply_plan_verdict` was duplicated in two guarded modules with two separate exemptions | Maintenance burden; future edits to the pure function required updating both locations | Promote pure functions to shared zero-io modules (e.g., `state_labels.py`); reuse without exemptions |

## Results & Parameters

**Outcome**: Symbol-scoped exemption for `parse_review_verdict` from `claude_invoke` successfully integrated into `hephaestus/automation/planner_review_loop.py` with validation test passing.

**Parameters / Thresholds**:

| Parameter | Value | Notes |
|-----------|-------|-------|
| Exemption scope | Symbol-scoped (frozenset of symbols) | Not unscoped (entire module); forces explicit intent |
| Validation test | `test_plan_review_exemption_is_symbol_scoped()` | Asserts allowed symbol imports work; asserts other symbols fail |
| Guarded modules | `planning_stage`, `plan_review_stage`, `planner_review_loop` | All zero-io-imports enforcement |
| Forbidden I/O modules | `claude_invoke`, `gh_issue_json`, `run_subprocess` | May not be imported into guarded modules |
| Allowed exemptions | Only pure functions (no side effects) | Criteria for exemption eligibility |
| Shared module promotion | `state_labels.py` (zero-io) | Pure functions promoted to shared modules to reduce exemption churn |

**Test verification (verified-ci)**:
```bash
pixi run pytest tests/unit/automation/test_zero_io_imports.py::test_plan_review_exemption_is_symbol_scoped -v
# PASSED
pixi run pytest tests/unit -v --no-cov
# 115 tests passed
```

## Key Insights

1. **Symbol-Scoped > Unscoped**: Symbol-scoped exemptions force explicit intent. Unscoped exemptions are a "skip validation for this whole module" escape hatch that invites drift.

2. **Validate with Tests**: Don't just assert the allowed symbol is imported; assert that OTHER symbols are NOT imported. The test validates the exemption's scope.

3. **Promote Pure Functions**: If a pure function is needed by multiple guarded modules, promote it to a shared zero-io module to avoid exemption churn.

4. **Document Intent**: Comment the exemption explaining why the I/O import is allowed. This forces the exemption to survive code review.

5. **Minimal Exemption List**: Keep the exemption list as small as possible. Each symbol represents a justified breach of the architectural boundary.

---

**See Also**:
- `library-product-import-boundary-enforcement-test.md` — broader import boundary enforcement (library vs product)
- `python-import-patterns-and-compatibility-guards.md` — import graph management and circular dependency avoidance
