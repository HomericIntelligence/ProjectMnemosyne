---
name: tooling-shared-scripts-pypi-centralization
description: "Workflow for auditing cross-repo script duplication and centralizing shared Python validation scripts into a PyPI package with CLI entry points. Use when: (1) multiple repos have duplicated scripts/check_*.py or scripts/validate_*.py files, (2) planning to consolidate shared tooling into a library package, (3) porting standalone scripts to library modules with testable APIs."
category: tooling
date: 2026-03-22
version: "1.0.0"
user-invocable: false
tags:
  - pypi
  - deduplication
  - validation-scripts
  - cli-entry-points
  - cross-repo
---

# Centralizing Shared Python Scripts into a PyPI Package

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Objective** | Audit all HomericIntelligence repos for duplicated Python validation scripts and port them into ProjectHephaestus as first-class library modules with CLI entry points, published to PyPI |
| **Outcome** | Successfully ported 9 validation modules from ProjectScylla/Hephaestus scripts/ into `hephaestus.validation.*`, added 9 CLI entry points, bumped to v0.5.0. Filed tracking issues against 2 repos with duplicated code. |

## When to Use

- Multiple repositories contain duplicated `scripts/check_*.py` or `scripts/validate_*.py` files
- Standalone scripts need to become importable library modules with testable public APIs
- A shared PyPI package needs new modules with optional dependency extras
- Planning a cross-repo deduplication effort with tracking issues
- Converting scripts that use `sys.exit()` directly into testable functions that return structured data

## Verified Workflow

### Quick Reference

```bash
# 1. Audit repos for duplicated scripts
gh repo list <org> --limit 50 --json name,description
# Clone each, compare scripts/ directories

# 2. For each script, create a library module:
#    - Testable function returning structured data (tuple/dict)
#    - main() function that calls sys.exit() for CLI
#    - argparse with --repo-root, --verbose

# 3. Add CLI entry points to pyproject.toml:
# [project.scripts]
# hephaestus-check-foo = "hephaestus.validation.foo:main"

# 4. Add optional dependency extras:
# [project.optional-dependencies]
# toml = ["tomli>=2.0,<3;python_version<'3.11'"]
# schema = ["jsonschema>=4.0,<5"]

# 5. File tracking issues against repos with duplicated code
gh issue create --repo <org>/<repo> --title "chore: Replace duplicated scripts with <package>>=X.Y"
```

### Detailed Steps

1. **Audit phase**: Clone all ecosystem repos, list all `scripts/*.py` files, identify duplicates by comparing functionality (not just filenames — implementations may differ)

2. **Design module API**: Each script becomes a module with:
   - Public functions returning structured results (tuples, dicts) — NOT calling `sys.exit()`
   - A `main()` function that wraps the public API with argparse and `sys.exit()`
   - Reuse existing package utilities (e.g., `get_repo_root()`) instead of inline helpers

3. **Handle optional dependencies** with guarded imports:
   ```python
   try:
       import tomllib
   except ModuleNotFoundError:
       try:
           import tomli as tomllib
       except ModuleNotFoundError:
           tomllib = None
   ```
   Print clear install instructions when optional deps are missing.

4. **Implementation order matters**: Build standalone modules first (no new deps), then dep-dependent modules, then enhance existing modules, then integration

5. **Tests with `pytest.importorskip`**: For optional-dep-dependent tests, use `pytest.importorskip("jsonschema")` inside each test method rather than class-level decorators

6. **File tracking issues** against repos with duplicated code before implementation — reference the planned version. Update issues after publishing.

7. **Merge divergent implementations**: When two repos have different scripts for the same purpose, merge the best parts. E.g., Hephaestus checked pyproject.toml internal consistency (regex), Scylla checked pyproject.toml vs Dockerfile (tomllib). The merged module does both.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Class-level `@pytest.mark.skipif` with `pytest.importorskip` | Used `@pytest.mark.skipif(not pytest.importorskip(...))` on test class | `pytest.importorskip` raises `Skipped` exception at collection time, causing the entire module to be skipped (0 tests collected) | Use `pytest.importorskip()` inside individual test methods, not at class/module level |
| Lazy import of argparse inside helper function | Deferred `import argparse` to `_build_parser()` while using `argparse.ArgumentParser` in the return type annotation | `from __future__ import annotations` makes annotations lazy but ruff F821 still flags undefined names in annotations when the import is deferred | Import modules at top level if they appear in type annotations, even with `from __future__ import annotations` |
| Using `replace_all=false` with non-unique string | Tried to append code after `return issues` in markdown.py | String `return issues` appeared twice in the file | Provide more surrounding context to make the match unique, or use a different anchor point |

## Results & Parameters

### Module Structure Pattern

```python
"""Module docstring with Usage:: section."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from hephaestus.utils.helpers import get_repo_root

def check_something(repo_root: Path, verbose: bool = False) -> tuple[bool, dict]:
    """Testable public function — returns structured data, never calls sys.exit()."""
    ...
    return (passed, details)

def main() -> int:
    """CLI entry point — parses args, calls public function, returns exit code."""
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root or get_repo_root()
    passed, details = check_something(repo_root, verbose=args.verbose)
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
```

### pyproject.toml Optional Extras Pattern

```toml
[project.optional-dependencies]
toml = ["tomli>=2.0,<3;python_version<'3.11'"]
xml = ["defusedxml>=0.7,<1"]
schema = ["jsonschema>=4.0,<5"]
all = ["MyPackage[github,toml,xml,schema]"]
```

### Final Stats

- **9 new modules** in `hephaestus/validation/`
- **9 CLI entry points** added
- **3 optional dependency extras** (toml, xml, schema)
- **557 tests passed**, 6 skipped (optional dep tests)
- **Version bump**: 0.4.0 → 0.5.0
- **2 GitHub issues filed** for cross-repo adoption

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Porting shared validation scripts to PyPI package v0.5.0 | [notes.md](./tooling-shared-scripts-pypi-centralization.notes.md) |
| ProjectScylla | Source of 9 duplicated scripts, tracking issue #1537 | Scripts in scripts/ directory |
| ProjectOdyssey | Source of duplicated utilities, tracking issue #5061 | common.py, validation.py |
