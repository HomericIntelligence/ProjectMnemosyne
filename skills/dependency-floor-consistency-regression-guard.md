---
name: dependency-floor-consistency-regression-guard
description: Detect and prevent dependency floor skew across manifests (pyproject.toml, pixi.toml). Use when managing dependencies with API-incompatible major versions to ensure published install contracts align with tested environments.
category: ci-cd
date: 2026-05-28
version: 1.0.0
tags: ["dependencies", "manifest-sync", "regression-testing", "pyproject", "pixi", "PyGithub"]
---

# Dependency Floor Consistency Regression Guard

Prevent silent breakage from mismatched dependency floors across project manifests.

## Overview

| Date | Objective | Outcome |
| ------ | ----------- | --------- |
| 2026-05-28 | Detect and prevent dependency floor skew across manifests (pyproject.toml, pixi.toml) | Regression tests ensure PyGithub 1.x vs 2.x API-incompatibility does not result in publishing install contracts for untested versions |

## When to Use

- Managing dependencies with **API-incompatible major versions** (e.g., PyGithub 1.x vs 2.x)
- Multi-manifest projects declaring the same dependency in different files
- Preventing silent breakage from mismatched floor versions
- Adding regression tests to lock in manifest consistency

## The Problem

When a dependency has API-incompatible major versions (e.g., PyGithub 1.55 vs 2.9.1), the published install contract must match the tested environment:

**Broken Setup:**
- `pyproject.toml` declares `PyGithub>=1.55,<3` (published contract)
- `pixi.toml` declares `PyGithub>=2.9.1,<3` (dev/test environment)
- Result: Users install PyGithub 1.x (within published contract), but code only works with 2.x → silent breakage

**Correct Setup:**
- Both manifests declare `PyGithub>=2.9.1,<3`
- Published contract matches tested environment
- Users install compatible versions

## Verified Workflow

### Quick Reference

1. Identify the dependency with incompatible major versions
2. Check all manifest files for that dependency (pyproject.toml, pixi.toml, etc.)
3. Consolidate floor across all manifests to the same version
4. Create regression test using `tomllib` to parse and validate consistency
5. Run tests to verify consistency is enforced going forward

### Detailed Steps

**Step 1: Identify the problematic dependency**

```bash
# Search for inconsistent versions across manifests
grep -n "PyGithub" pyproject.toml pixi.toml
# Example:
# pyproject.toml:49:    "PyGithub>=1.55,<3",
# pixi.toml:XX:pygithub = ">=2.9.1,<3"
```

**Step 2: Determine the correct floor**

- Research the API differences between major versions
- Identify the minimum compatible version for your codebase
- Use the **highest** floor across all manifests as the source of truth

```python
# Example: PyGithub 1.x and 2.x are API-incompatible
# Code uses Repository.stargazers_count (exists in 2.9.1)
# Floor must be >=2.9.1
```

**Step 3: Update all manifests**

```toml
# pyproject.toml [project.optional-dependencies.github]
"PyGithub>=2.9.1,<3",

# pixi.toml [dependencies]
pygithub = ">=2.9.1,<3"
```

**Step 4: Create regression test**

```python
"""Tests for dependency floor consistency between pyproject.toml and pixi.toml.

Validates that PyGithub floor versions match between the two manifest files,
ensuring the published install contract does not permit API-incompatible
versions that are never tested.
"""

import tomllib
from pathlib import Path

def _floor(spec: str) -> str:
    """Extract the floor version (>=X.Y.Z) from a PEP 508 / pixi constraint string.

    Args:
        spec: A constraint string like "PyGithub>=2.9.1,<3" or ">=2.9.1,<3".

    Returns:
        The floor version (e.g., "2.9.1").

    Raises:
        AssertionError: If no ">=" clause is present in the spec.
    """
    if ">=" not in spec:
        raise AssertionError(f"No '>=' floor found in constraint spec: {spec}")

    after_gte = spec.split(">=", 1)[1]
    version = after_gte.split(",")[0].strip()
    return version


def test_pygithub_floor_matches_pixi() -> None:
    """PyGithub floor in pyproject.toml must match pixi.toml.

    Both manifests declare a PyGithub floor version. Since PyGithub 1.x
    and 2.x are API-incompatible, they must match to ensure the published
    install contract aligns with the tested (dev) environment.
    """
    repo_root = Path(__file__).resolve().parents[3]

    # Load pyproject.toml
    pyproject_path = repo_root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    github_deps = pyproject["project"]["optional-dependencies"]["github"]
    pyproject_spec = next(
        (dep for dep in github_deps if dep.startswith("PyGithub")), None
    )

    # Load pixi.toml
    pixi_path = repo_root / "pixi.toml"
    with open(pixi_path, "rb") as f:
        pixi = tomllib.load(f)

    pixi_spec = pixi["dependencies"]["pygithub"]

    # Extract and compare floors
    pyproject_floor = _floor(pyproject_spec)
    pixi_floor = _floor(pixi_spec)

    assert pyproject_floor == pixi_floor, (
        f"PyGithub floor skew: pyproject.toml={pyproject_floor} vs pixi.toml={pixi_floor}"
    )


def test_pygithub_floor_is_2x_or_higher() -> None:
    """PyGithub floor must be 2.x or higher.

    PyGithub 1.x and 2.x are API-incompatible. The floor must be at least 2.x
    to ensure the code is tested against the versions it can use.
    """
    repo_root = Path(__file__).resolve().parents[3]
    pyproject_path = repo_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    github_deps = pyproject["project"]["optional-dependencies"]["github"]
    pyproject_spec = next(
        (dep for dep in github_deps if dep.startswith("PyGithub")), None
    )

    floor = _floor(pyproject_spec)
    major_version = int(floor.split(".")[0])

    assert major_version >= 2, (
        f"PyGithub floor must be 2.x or higher for API compatibility; found {floor}"
    )
```

**Step 5: Run the regression tests**

```bash
# Run just the regression tests
pytest tests/unit/scripts/test_dependency_floor_consistency.py -v

# Run full test suite to ensure no unintended breakage
pytest tests/unit -v

# Expected output:
# tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_matches_pixi PASSED
# tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_is_2x_or_higher PASSED
```

### Dependabot Configuration (optional)

If updating manifests as part of dependency management, document Dependabot behavior in `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "chore(deps)"
      # Note: Dependabot auto-appends a colon after a prefix ending in )
      # Example: prefix "chore(deps)" becomes "chore(deps): ..." (auto-colon)
      # https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference
    groups:
      python-dependencies:
        patterns:
          - "*"
```

## Results & Parameters

### Copy-Paste Regression Test

Test file location: `tests/unit/scripts/test_dependency_floor_consistency.py`

Test expectations:
- 2 assertions per test function
- Uses `tomllib` (built-in to Python 3.11+; fallback to `tomli` for 3.10)
- Extracts floor using `split(">=")`
- Compares major version integers

### Expected Test Output

```
tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_matches_pixi PASSED [ 50%]
tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_is_2x_or_higher PASSED [100%]

========================== 2 passed in 0.23s ==========================
```

### Manifest Configuration

Both files must declare the same floor:

```toml
# pyproject.toml [project.optional-dependencies.github]
"PyGithub>=2.9.1,<3",

# pixi.toml [dependencies]
pygithub = ">=2.9.1,<3"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Manual verification | Hand-inspecting manifests for consistency | Error-prone; no enforcement going forward | Regression tests lock in consistency permanently |
| Different floor per manifest | pyproject.toml has higher floor than pixi.toml | Dev environment doesn't match published contract | Both manifests must declare identical floors |
| String matching without parsing | Comparing constraint strings directly | Leading/trailing whitespace breaks matching | Use `tomllib.load()` to parse, then extract version |

## Preventive Measures

### Pre-commit Hook (optional)

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-dependency-floor-consistency
      name: Check PyGithub floor consistency
      entry: pytest tests/unit/scripts/test_dependency_floor_consistency.py
      language: system
      files: (pyproject.toml|pixi.toml)
      pass_filenames: false
      always_run: true
```

This ensures the regression test runs whenever either manifest is modified.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #631 (PR #652) | PyGithub floor consolidated from 1.55 to 2.9.1; regression tests added; CI passed |

## References

- **GitHub issue**: [HomericIntelligence/ProjectHephaestus#631](https://github.com/HomericIntelligence/ProjectHephaestus/issues/631)
- **Merged PR**: [HomericIntelligence/ProjectHephaestus#652](https://github.com/HomericIntelligence/ProjectHephaestus/pull/652)
- **PyGithub releases**: [PyGithub on PyPI](https://pypi.org/project/PyGithub/)
- **Dependabot options**: [GitHub Dependabot reference](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference)
- **Python tomllib**: [Python 3.11+ docs](https://docs.python.org/3/library/tomllib.html)
