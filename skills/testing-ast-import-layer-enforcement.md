---
name: testing-ast-import-layer-enforcement
description: "Enforce import layer boundaries in Python packages using AST-level CI tests. Use when: (1) you've fixed a circular import and want to prevent regressions, (2) you have a strict layering rule (module A must never import from module B) and need it enforced in CI, (3) you want to catch both direct and lazy/function-local imports that violate architecture boundaries."
category: testing
date: 2026-04-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - python
  - ast
  - import-boundary
  - circular-imports
  - layer-enforcement
  - ci
  - testing
---

# Testing: AST Import Layer Enforcement

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-29 |
| **Objective** | After fixing a circular import (`hephaestus.github` importing from `hephaestus.automation`), add a CI regression gate that fails immediately if the forbidden import edge is reintroduced |
| **Outcome** | Four-test suite catches both runtime cycle failures and the structural AST invariant; no regression possible without a red CI build |
| **Verification** | verified-local (ProjectHephaestus PR #308 — CI pending) |

## When to Use

- You have just fixed a circular import and want to prevent it from coming back silently
- You have a layering rule like "package X must never import from package Y" that needs CI enforcement
- A previous import cycle caused a hard-to-diagnose startup failure and you need structural protection
- You want to catch lazy imports (`def foo(): from X import Y`) that would still cause runtime cycles

## Verified Workflow

### Quick Reference

```python
# tests/unit/test_no_import_cycles.py

import ast
import pathlib
import subprocess
import sys

import hephaestus.github  # import the package to get __file__ for path resolution


def test_planner_imports_cleanly() -> None:
    """Original failure repro — must pass in a fresh subprocess (sys.modules contamination)."""
    r = subprocess.run(
        [sys.executable, "-c", "from hephaestus.automation.planner import main"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"planner import failed:\n{r.stderr}"


def test_packages_import_in_either_order() -> None:
    """Both import orders must succeed (order-dependent cycles)."""
    for code in [
        "import hephaestus.github, hephaestus.automation",
        "import hephaestus.automation, hephaestus.github",
    ]:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode == 0, f"Import failed ({code}):\n{r.stderr}"


def test_console_script_entry_points_resolve() -> None:
    """Console-script targets still importable after removing __init__.py re-exports."""
    for module in ["hephaestus.github.fleet_sync", "hephaestus.github.tidy"]:
        r = subprocess.run(
            [sys.executable, "-c",
             f"import importlib; m = importlib.import_module('{module}'); assert callable(m.main)"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"{module} failed:\n{r.stderr}"


def test_github_package_does_not_import_automation() -> None:
    """AST-level layering invariant: hephaestus.github must never import from hephaestus.automation."""
    github_dir = pathlib.Path(hephaestus.github.__file__).parent
    offenders: list[str] = []
    for py in sorted(github_dir.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("hephaestus.automation"):
                offenders.append(f"{py}:{node.lineno}  from {node.module} import ...")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("hephaestus.automation"):
                        offenders.append(f"{py}:{node.lineno}  import {alias.name}")
    assert not offenders, "github -> automation import edge reintroduced:\n" + "\n".join(offenders)
```

### Detailed Steps

1. **Reproduce the original failure** with a subprocess test — ensures the cold-boot failure is
   captured before `sys.modules` is contaminated by previous test-process imports.

2. **Test both import orders** (package A first, then B; then B first, then A) — order-dependent
   cycles only appear when the lower-layer package loads first and the higher-layer package tries
   to complete initialization while the lower one is still partially initialized.

3. **Add the AST walk** over the package directory using `pathlib.Path(...).rglob("*.py")` and
   `ast.walk(tree)`. Check both `ast.ImportFrom` nodes (for `from X import Y` style) and
   `ast.Import` nodes (for `import X` style). Walk the full AST — not just top-level statements —
   so function-local imports are also caught.

4. **Use `__file__` from the imported package** to locate the source directory. This is portable
   across editable installs, wheel installs, and any layout where the package is importable.

5. **Run the test suite** with `pixi run pytest tests/unit -v` and confirm all 4 tests pass.

### Adapting to Other Projects

To enforce a different boundary (e.g., `mypackage.ui` must not import `mypackage.db`):

```python
import mypackage.ui

def test_ui_does_not_import_db() -> None:
    ui_dir = pathlib.Path(mypackage.ui.__file__).parent
    forbidden_prefix = "mypackage.db"
    offenders: list[str] = []
    for py in sorted(ui_dir.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(forbidden_prefix):
                offenders.append(f"{py}:{node.lineno}  from {node.module} import ...")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefix):
                        offenders.append(f"{py}:{node.lineno}  import {alias.name}")
    assert not offenders, f"ui -> db import edge detected:\n" + "\n".join(offenders)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test only one import order | `import hephaestus.github, hephaestus.automation` only | Order-dependent cycles pass when the "wrong" package loads first; failed only in the reverse order | Always test both A→B and B→A import orderings to catch order-dependent cycles |
| `importlib.import_module` inside test process | Used `importlib.import_module("hephaestus.automation.planner")` directly in the test function instead of a subprocess | If an earlier test (or module collection phase) triggered a partial import that left a broken half-loaded module in `sys.modules`, the re-import succeeds silently because Python returns the cached partial module | Use `subprocess.run([sys.executable, "-c", "..."])` for each import test — each subprocess starts with a clean `sys.modules` state |
| AST walk only at top-level statements | Used `for node in tree.body` instead of `ast.walk(tree)` | Missed function-local (`def foo(): from X import Y`) and class-body imports that also cause runtime cycles | `ast.walk(tree)` traverses all nodes recursively; always use it to catch imports at any nesting depth |

## Results & Parameters

### Test file location

```
tests/unit/test_no_import_cycles.py
```

### Four-test structure

| Test | What It Catches |
| ------ | ----------------- |
| `test_planner_imports_cleanly` | Original failure repro — cold-boot import failure |
| `test_packages_import_in_either_order` | Order-dependent circular imports |
| `test_console_script_entry_points_resolve` | Console-script targets broken by `__init__.py` cleanup |
| `test_github_package_does_not_import_automation` | Structural invariant — forbidden import edge at AST level |

### Key design properties

- **Subprocess isolation**: Each `subprocess.run` call spawns a fresh Python interpreter with an
  empty `sys.modules`, so the test accurately reflects cold-boot import behavior regardless of what
  the test runner has already loaded.
- **AST is purely syntactic**: The walk catches imports whether or not the module is currently
  importable. A file with syntax errors will raise `SyntaxError` on `ast.parse` — this is
  intentional (syntax errors are their own problem).
- **`rglob("*.py")` covers subpackages**: The walk recurses into nested `__init__.py` and submodules
  automatically.

### Subprocess pattern (reusable)

```python
def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #308 — fixed `hephaestus.github` → `hephaestus.automation` circular import | `pixi run pytest tests/unit -v` passed all 4 tests locally; CI pending |
