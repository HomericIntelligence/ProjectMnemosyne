---
name: ci-pixi-workspace-version-dedup
description: "Remove duplicated project version from pixi.toml [workspace] and add drift detection to an existing version-consistency pre-commit script. Use when: (1) pixi.toml has a version field that duplicates pyproject.toml, (2) extending an existing check script to cover additional config files, (3) preventing accidental re-introduction of removed duplicate fields."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - version
  - deduplication
  - pre-commit
  - drift-detection
  - pyproject
---

# Remove Duplicated Version from pixi.toml and Add Drift Detection

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Eliminate duplicated `version` field from `pixi.toml` `[workspace]` section, making `pyproject.toml` the single source of truth |
| **Outcome** | Successful — version removed, drift detection added to existing script, 20 new tests pass |
| **Verification** | verified-local (404 tests pass at 82.13% coverage, pre-commit hooks pass) |

## When to Use

- `pixi.toml` has a `[workspace] version` that duplicates `pyproject.toml` `[project] version`
- You need to extend an existing pre-commit check script to cover additional config files
- You want to prevent accidental re-introduction of a removed duplicate field via CI
- The `version` field in `pixi.toml` is informational/optional and can safely be removed

## Verified Workflow

### Quick Reference

```bash
# 1. Remove version from pixi.toml [workspace]
# Delete the line: version = "X.Y.Z"

# 2. Verify pixi still works
pixi install --locked

# 3. Extend existing check script
# Add extract_project_version() and extract_pixi_workspace_version() functions
# Add check_pixi_version_drift() that catches re-introduction

# 4. Run tests
pixi run pytest tests/unit/scripts/ -v --no-cov
pixi run pre-commit run check-python-version-consistency --all-files
```

### Detailed Steps

1. **Remove `version` from `pixi.toml`**: The `[workspace] version` field is optional metadata in pixi. Removing it eliminates the duplication entirely. Verify with `pixi install --locked` — pixi does not require this field.

2. **Extend the existing check script** (`scripts/check_python_version_consistency.py`):
   - Add `extract_project_version(content) -> str | None` to parse `[project] version` from pyproject.toml
   - Add `extract_pixi_workspace_version(content) -> str | None` to parse `[workspace] version` from pixi.toml (returns `None` if absent)
   - Add `check_pixi_version_drift(repo_root) -> int` that returns 0 if pixi.toml has no version or versions match, 1 if drift detected
   - Refactor original `main()` logic into `check_python_versions(repo_root)` and update `main()` to call both checks

3. **Use regex, not tomllib**: The existing script uses stdlib-only regex parsing. Follow the same pattern — `re.search(r'\[workspace\]\s*\n(?:.*\n)*?version\s*=\s*"([^"]+)"', content)` works for simple TOML key extraction without adding dependencies.

4. **Leverage existing pre-commit hook**: The `check-python-version-consistency` hook already triggers on `^(pyproject\.toml|pixi\.toml|\.github/workflows/.*\.yml)$`, so no `.pre-commit-config.yaml` changes needed.

5. **Create unit tests** in `tests/unit/scripts/`: Use `tmp_path` fixture to create temporary config files. Test all paths: no version field, matching version, mismatched version, missing files. Use `monkeypatch` to override `get_repo_root()` for `main()` integration tests.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — first approach succeeded | Removed version + extended existing script | N/A | When a field is optional, removing it is always simpler than syncing it |

## Results & Parameters

### pixi.toml change

```diff
 [workspace]
 name = "project-hephaestus"
-version = "0.4.0"
 description = "Shared utilities and tooling for the HomericIntelligence ecosystem"
```

### Key regex patterns

```python
# Extract [project] version from pyproject.toml
r'\[project\]\s*\n(?:.*\n)*?version\s*=\s*"([^"]+)"'

# Extract [workspace] version from pixi.toml (returns None if absent)
r'\[workspace\]\s*\n(?:.*\n)*?version\s*=\s*"([^"]+)"'
```

### Expected script output (after removal)

```
OK: Python version is consistent at 3.10
  requires-python: 3.10
  mypy.python_version: 3.10
  ruff.target-version: 3.10
OK: pixi.toml has no workspace version (single source of truth in pyproject.toml)
```

### Test coverage

- 20 new unit tests in `tests/unit/scripts/test_check_python_version_consistency.py`
- Full suite: 404 tests pass, 82.13% coverage

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #57 — version duplication | PR #111: removed pixi.toml version, extended drift detection script |
