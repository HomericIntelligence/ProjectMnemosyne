---
name: versioning-consistency-release-workflow
description: "Establish single-source-of-truth version management with importlib.metadata, pre-commit consistency checks, and CHANGELOG fixes. Use when: (1) project has version declared in multiple files that can drift, (2) __init__.py hardcodes a version string instead of using importlib.metadata, (3) CHANGELOG references phantom version numbers, (4) skill templates generate aspirational version refs."
category: ci-cd
date: '2026-03-25'
version: "2.0.0"
user-invocable: false
verification: verified-local
history: versioning-consistency-release-workflow.history
tags:
  - versioning
  - release
  - ci
  - changelog
  - DRY
  - importlib-metadata
  - pre-commit
---

# Version Consistency and Release Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Establish a single-source-of-truth version management system: `pyproject.toml` is canonical, `importlib.metadata` reads it at runtime, pre-commit hook guards against drift, and CHANGELOG uses `[Unreleased]` convention. |
| **Outcome** | Successful — two PRs (#1557, #1562) across two issues (#1527, #1535), 4808+ tests passing, all pre-commit hooks green. |
| **Verification** | verified-local |
| **History** | [changelog](./versioning-consistency-release-workflow.history) |

## When to Use

- Project declares version in multiple files (e.g., `pyproject.toml`, `pixi.toml`, `__init__.py`, CLI) that can drift
- `__init__.py` hardcodes `__version__ = "X.Y.Z"` instead of using `importlib.metadata.version()`
- CLI hardcodes a version string instead of importing from a canonical source
- CHANGELOG references phantom future versions (e.g., "deprecated in v1.5.0, removed in v2.0.0") when no releases exist
- Skill templates or code generators produce aspirational version numbers in CHANGELOG entries
- Want a pre-commit hook to catch version drift before it reaches production
- Need to add a GitHub Actions release workflow triggered by version tags

## Verified Workflow

### Quick Reference

```bash
# 1. Switch __init__.py to importlib.metadata (single source of truth)
# In package/__init__.py:
#   from importlib.metadata import PackageNotFoundError, version as _get_version
#   try:
#       __version__: str = _get_version("mypackage")
#   except PackageNotFoundError:
#       __version__ = "0.0.0"

# 2. Replace hardcoded CLI version with dynamic import
# In cli/main.py:
#   from mypackage import __version__
#   @click.version_option(version=__version__, prog_name="mypackage")

# 3. Create version consistency pre-commit hook
python3 scripts/check_package_version_consistency.py --verbose

# 4. Run tests
pixi run pytest tests/unit/scripts/test_check_package_version_consistency.py -v

# 5. Verify
python -c "import mypackage; print(mypackage.__version__)"
```

### Detailed Steps

1. **Switch `__init__.py` to `importlib.metadata`**: Replace `__version__ = "0.1.0"` with `importlib.metadata.version("mypackage")`. Include a `PackageNotFoundError` fallback for editable/dev installs. This makes `pyproject.toml` the single authority — no more dual maintenance.

2. **Eliminate hardcoded CLI version**: Import `__version__` from the package's `__init__.py` instead of hardcoding a version string in the CLI decorator.

3. **Create a pre-commit consistency checker**: A Python script using `tomllib` (not regex) that validates:
   - `pixi.toml` `[workspace].version` matches `pyproject.toml` `[project].version`
   - `__init__.py` uses `importlib.metadata` (no hardcoded `__version__ = "..."` pattern)
   - `CHANGELOG.md` has no version references higher than the canonical version

4. **Register as pre-commit hook**: Trigger on changes to `pyproject.toml`, `pixi.toml`, `__init__.py`, `CHANGELOG.md`. Use `pass_filenames: false`.

5. **Fix CHANGELOG phantom versions**: Replace aspirational version references with `[Unreleased]` per keepachangelog.com convention. If deprecated classes have already been removed, change the section from "Deprecated" to "Removed".

6. **Fix root cause — skill templates**: If the phantom versions came from a code-generation skill template, update the template to use "a future major version" instead of hardcoded version numbers.

7. **Update tests**: Replace hardcoded version assertions in CLI tests with dynamic `__version__` imports. Add comprehensive tests for the consistency checker.

8. **Respect test structure conventions**: Place version consistency tests in `tests/unit/scripts/` to match the script being tested.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test file at `tests/unit/test_version_consistency.py` | Placed test directly under `tests/unit/` | Pre-commit hook `check-unit-test-structure` requires tests in sub-packages | Always check project's test structure conventions before placing new test files |
| Regex-based TOML parsing | Used `re.match(r'^version\s*=\s*"([^"]+)"')` to read TOML values | Fragile: breaks on inline comments, multi-line strings, or non-standard formatting | Use `tomllib` (stdlib since 3.11) for reliable TOML parsing; fall back to `tomli` for 3.10 |
| `if cond: return False; return True` pattern | Simple conditional in `check_init_uses_importlib()` | Ruff SIM103 requires direct condition return | Use `return not pattern.search(content)` for boolean-returning functions |

## Results & Parameters

### importlib.metadata Pattern (recommended)

```python
# package/__init__.py — read version from installed metadata
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

try:
    __version__: str = _get_version("mypackage")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback when package is not installed
```

### Consistency Script Pattern (with tomllib)

```python
import tomllib  # Python 3.11+; use tomli as fallback for 3.10

def get_pyproject_version(path: Path) -> str:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def get_pixi_version(path: Path) -> str:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["workspace"]["version"]

def check_init_uses_importlib(path: Path) -> bool:
    content = path.read_text()
    return not re.search(r'^__version__\s*=\s*["\'][\d.]+["\']', content, re.MULTILINE)

def find_aspirational_versions(changelog_path: Path, canonical: str) -> list[str]:
    content = changelog_path.read_text()
    canonical_tuple = tuple(int(p) for p in canonical.split("."))
    aspirational = []
    for match in re.finditer(r"\bv(\d+\.\d+\.\d+)\b", content):
        if tuple(int(p) for p in match.group(1).split(".")) > canonical_tuple:
            ref = f"v{match.group(1)}"
            if ref not in aspirational:
                aspirational.append(ref)
    return aspirational
```

### Pre-commit Hook Configuration

```yaml
- id: check-package-version-consistency
  name: Check Package Version Consistency
  description: Fails if package version in pyproject.toml, pixi.toml, or CHANGELOG.md are inconsistent
  entry: pixi run python scripts/check_package_version_consistency.py
  language: system
  files: ^(pyproject\.toml|pixi\.toml|package/__init__\.py|CHANGELOG\.md)$
  pass_filenames: false
```

### CHANGELOG Fix Pattern

Replace phantom version references:
- Before: "deprecated as of v1.5.0. It will be removed in v2.0.0."
- After (if still deprecated): "deprecated. It will be removed in a future major version."
- After (if already removed): Section header changes from "Deprecated" to "Removed"

### Skill Template Root-Cause Fix

Update any code-generation templates that produce CHANGELOG entries:
- Before: `"<Class> is deprecated and will be removed in v2.0.0."`
- After: `"<Class> is deprecated and will be removed in a future major version."`

### Release Workflow Key Points

- Trigger on `push.tags: ["v*"]` — not on PR merge
- Validate tag version matches `pyproject.toml` version before creating release
- Use `gh release create` with `--generate-notes` for auto-generated release notes
- Pass `github.ref_name` via `env:` variable (not `${{ }}` interpolation in `run:`) for GH Actions security

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1527 — Audit S10 versioning remediation | PR #1557: 8 files changed, 35 tests passing, all pre-commit hooks green |
| ProjectScylla | Issue #1535 — Reconcile version 0.1.0 with CHANGELOG refs | PR #1562: 8 files changed, 26 new tests, 4808 total passing, 77.50% coverage |
