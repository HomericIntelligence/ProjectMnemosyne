---
name: auto-init-py-generation
description: 'TRIGGER CONDITIONS: Auto-generating __init__.py files with __all__ exports
  for Python packages. Use when creating or updating package-level exports, especially
  with mypy implicit_reexport=false compliance.'
category: tooling
date: 2026-03-11
version: 1.0.0
user-invocable: false
tags:
- python
- mypy
- init
- exports
- ast
- code-generation
---
# auto-init-py-generation

How to auto-generate `__init__.py` files with proper `__all__` exports for Python packages, handling mypy strict mode (`implicit_reexport=false`) and re-export patterns.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-11 |
| Objective | Generate `__init__.py` with `__all__` for all subpackages in `scylla/` |
| Outcome | Success — 17 `__init__.py` files generated, all pre-commit hooks pass |
| Issues | HomericIntelligence/ProjectScylla#1359 |
| PRs | HomericIntelligence/ProjectScylla#1472 |

## When to Use

- Creating `__init__.py` files with `__all__` for a Python package tree
- Updating exports after adding/removing/renaming public symbols
- Ensuring mypy `implicit_reexport=false` compliance (requires `import X as X` pattern)
- Migrating from implicit to explicit exports in an existing codebase

## Verified Workflow

### 1. AST-Based Export Discovery

Use Python's `ast` module to parse each `.py` file and extract public symbols:

```python
import ast

def get_public_names(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text())
    names = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.append(target.id)
    return sorted(set(names))
```

### 2. Generate `__init__.py` with `__all__`

For each subpackage directory:
1. Collect all `.py` files (excluding `__init__.py`)
2. Extract public names from each module
3. Generate imports using `from .module import name as name` (the `as name` pattern satisfies `implicit_reexport=false`)
4. Build `__all__` list from all exported names

### 3. Key Pattern: Re-export for mypy

With `implicit_reexport=false`, bare `from .module import name` does NOT re-export. Must use:

```python
from .module import MyClass as MyClass  # explicitly re-exported
```

### 4. Handle Subpackage Re-exports

For packages with nested subpackages, also re-export the subpackage's public API:

```python
from .subpkg import SubClass as SubClass
```

### 5. Pre-commit Validation

Always run after generation:
```bash
pre-commit run --all-files  # ruff will sort imports, fix formatting
pixi run python -m pytest tests/ -x  # verify no import breakage
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

- **17 `__init__.py` files** generated across `scylla/` subpackages
- **~400 symbols** exported in total
- **Zero test failures** after generation
- **All pre-commit hooks pass** (ruff, mypy, black)

## Key Insights

1. **AST parsing > regex**: AST correctly handles multiline definitions, decorators, and nested scopes
2. **Sort exports alphabetically**: Makes diffs clean and review easy
3. **One import per line**: Easier to review and produces cleaner git diffs
4. **Run ruff after generation**: Let ruff handle import sorting (isort) rather than doing it manually
5. **Test immediately**: Import cycles or shadowing can surface — run tests right after generation
