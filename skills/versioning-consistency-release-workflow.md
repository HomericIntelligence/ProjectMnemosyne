---
name: versioning-consistency-release-workflow
description: "Establish single-source-of-truth version management with CI consistency checks, release workflow, and CHANGELOG fixes. Use when: (1) project has version declared in multiple files that can drift, (2) need to add automated release workflow triggered by git tags, (3) CHANGELOG references phantom version numbers."
category: ci-cd
date: '2026-03-25'
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - versioning
  - release
  - ci
  - changelog
  - DRY
---

# Version Consistency and Release Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Establish a single-source-of-truth version management system: eliminate hardcoded versions, add CI consistency checks, create a release workflow, fix aspirational CHANGELOG references, and document the versioning strategy. |
| **Outcome** | Successful — PR created with all tests passing and pre-commit hooks green. |
| **Verification** | verified-local |

## When to Use

- Project declares version in multiple files (e.g., `pyproject.toml`, `pixi.toml`, `__init__.py`, CLI) that can drift
- CLI hardcodes a version string instead of importing from a canonical source
- CHANGELOG references phantom future versions (e.g., "deprecated in v1.5.0, removed in v2.0.0") when no releases exist
- Need to add a GitHub Actions release workflow triggered by version tags
- Want CI to catch version drift before it reaches production
- Audit finding: no git tags, no GitHub releases, no documented versioning strategy

## Verified Workflow

### Quick Reference

```bash
# 1. Replace hardcoded CLI version with dynamic import
# In cli/main.py:
#   from mypackage import __version__
#   @click.version_option(version=__version__, prog_name="mypackage")

# 2. Create version consistency script
python3 scripts/check_version_consistency.py

# 3. Run tests
pixi run pytest tests/unit/scripts/test_check_version_consistency.py -v

# 4. After PR merges, tag the release
git tag v0.1.0 && git push origin v0.1.0
```

### Detailed Steps

1. **Eliminate hardcoded CLI version**: Import `__version__` from the package's `__init__.py` instead of hardcoding a version string in the CLI decorator. This is the core DRY fix — one fewer place to update on version bumps.

2. **Create a version consistency checker script**: A lightweight Python script that reads version strings from all declaration sites (e.g., `pyproject.toml`, `pixi.toml`, `__init__.py`) using regex — no TOML library needed. Exits non-zero if they disagree. Designed to run in CI before expensive test steps.

3. **Add CI step**: Add the consistency check to the test workflow so version drift is caught on every PR, before Pixi setup (since it only needs Python stdlib).

4. **Fix CHANGELOG phantom versions**: Replace references to non-existent versions (e.g., "deprecated in v1.5.0") with relative timeline language ("deprecated in current release, removed in a future major release"). Add a proper release section for the current version.

5. **Create release workflow**: A GitHub Actions workflow triggered by `v*` tags that validates the tag matches the package version in `pyproject.toml` before creating a GitHub release with auto-generated notes.

6. **Document versioning strategy**: Add a "Versioning and Releases" section to CONTRIBUTING.md covering: where version is declared, how to bump it, how to create a release, and CHANGELOG maintenance expectations.

7. **Update tests**: Replace hardcoded version assertions in CLI tests with dynamic `__version__` imports. Add parametrized tests for the consistency checker covering: all-match, single-mismatch, missing-file scenarios.

8. **Respect test structure conventions**: If the project enforces that test files must be in sub-packages (not directly under `tests/unit/`), place version consistency tests in `tests/unit/scripts/` to match the script being tested.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Test file at `tests/unit/test_version_consistency.py` | Placed test directly under `tests/unit/` | Pre-commit hook `check-unit-test-structure` requires tests in sub-packages | Always check project's test structure conventions before placing new test files |

## Results & Parameters

### Version Declaration Sites Pattern

```python
# pyproject.toml — canonical source
[project]
version = "0.1.0"

# pixi.toml — workspace version
[workspace]
version = "0.1.0"

# package/__init__.py — runtime access
__version__ = "0.1.0"

# CLI — derived (imports __version__)
from mypackage import __version__

@click.version_option(version=__version__, prog_name="mypackage")
```

### Consistency Script Pattern (no TOML library needed)

```python
def _read_toml_version(path: Path, table_key: str) -> str | None:
    text = path.read_text()
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_table = stripped == f"[{table_key}]"
            continue
        if in_table:
            match = re.match(r'^version\s*=\s*"([^"]+)"', stripped)
            if match:
                return match.group(1)
    return None
```

### Release Workflow Key Points

- Trigger on `push.tags: ["v*"]` — not on PR merge
- Validate tag version matches `pyproject.toml` version before creating release
- Use `gh release create` with `--generate-notes` for auto-generated release notes
- Pass `github.ref_name` via `env:` variable (not `${{ }}` interpolation in `run:`) for GH Actions security

### CHANGELOG Fix Pattern

Replace phantom version references:
- Before: "deprecated as of v1.5.0. It will be removed in v2.0.0."
- After: "deprecated. It will be removed in a future major release."

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1527 — Audit S10 versioning remediation | PR #1557: 8 files changed, 35 tests passing, all pre-commit hooks green |
