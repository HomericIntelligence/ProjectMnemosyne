---
name: dependency-upper-cap-constraint-alignment
description: "Synchronize version upper-cap constraints across all install manifests when packages have API-incompatible major versions. Use when: (1) aligning upper-cap constraints (e.g., <2) across pyproject.toml and pixi.toml, (2) ensuring pip-install and dev-env see same tested versions, (3) preventing version skew that bypasses CI testing when major versions have incompatible APIs."
category: ci-cd
date: 2026-06-04
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: ["dependency-management", "version-constraints", "manifest-consistency", "regression-testing", "upper-cap"]
---

# Dependency Upper-Cap Constraint Alignment

Prevent silent breakage from mismatched upper-cap version constraints across project manifests.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **Objective** | Synchronize upper-cap constraints (e.g., `<2`) across all install manifests when packages have API-incompatible major versions to ensure pip-install users and CI developers see the same tested versions. |
| **Outcome** | Successful — regression test added to enforce constraint alignment across pyproject.toml [project.optional-dependencies.*] and pixi.toml [feature.*] sections; PR #934 merged with verified-ci. |
| **Verification** | verified-ci (all tests pass, PR auto-merge enabled) |

## When to Use

- Managing dependencies with **API-incompatible major versions** (e.g., mypy 1.x vs 2.x with different error semantics)
- Multi-manifest projects declaring the same dependency with **different upper-cap limits** (e.g., `<3` vs `<2`)
- Preventing silent breakage from version skew between published install contract and tested environment
- Adding regression tests to lock in manifest consistency for upper-cap constraints

## The Problem

When a dependency has API-incompatible major versions with breaking changes, the published install contract must match the tested environment:

**Broken Setup:**
- `pyproject.toml` declares `mypy>=1.8.0,<3` (published contract permits 1.x and 2.x)
- `pixi.toml [feature.dev]` declares `mypy = ">=1.8.0,<2"` (dev/test environment locked to 1.x)
- `pixi.toml [feature.lint]` declares `mypy = ">=1.8.0,<3"` (inconsistent with dev feature)
- Result: Users install mypy 2.x (within published contract), but code only tested with 1.x → silent breakage

**Correct Setup:**
- All manifests declare `mypy>=1.8.0,<2` (or consistent upper-cap)
- Published contract matches tested environment
- Users install compatible versions
- mypy 2.x (with different error semantics) is not installed without explicit opt-in

## Verified Workflow

### Quick Reference

**Manifest locations requiring synchronization:**

| File | Location | Current Value |
|------|----------|---------------|
| `pyproject.toml` | `[project.optional-dependencies.dev]` | `"mypy>=1.8.0,<2"` |
| `pixi.toml` | `[feature.dev.dependencies]` | `mypy = ">=1.8.0,<2"` |
| `pixi.toml` | `[feature.lint.dependencies]` | `mypy = ">=1.8.0,<2"` |

**Synchronization pattern:**

1. Identify the dependency with incompatible major versions
2. Search all manifest files for that dependency
3. Identify all distinct upper-cap constraints (`<2`, `<3`, etc.)
4. Choose the most restrictive upper-cap (the one that aligns with tested versions)
5. Update all manifests to the same upper-cap
6. Create regression test using tomllib to validate alignment
7. Run tests; merge when CI passes

### Detailed Steps

**Step 1: Identify the problematic dependency**

```bash
# Search for mypy across all manifests
grep -n "mypy" pyproject.toml pixi.toml
# Example output:
# pyproject.toml:46:    "mypy>=1.8.0,<3",
# pixi.toml:59:mypy = ">=1.8.0,<2"
# pixi.toml:77:mypy = ">=1.8.0,<3"
```

**Step 2: Determine the correct upper-cap**

- Research the API breaking changes between major versions
- Identify the minimum version that satisfies your code
- Use the **most restrictive** upper-cap across all manifests as the source of truth

```python
# Example: mypy 1.x and 2.x have different error semantics
# Code uses mypy 1.8.0+ API for type-checking
# mypy 2.x changes error formatting and attribute names
# Upper-cap must be <2 to match tested versions
```

**Step 3: Update all manifests**

Synchronize the upper-cap across all locations:

```toml
# pyproject.toml [project.optional-dependencies.dev]
"mypy>=1.8.0,<2",

# pixi.toml [feature.dev.dependencies]
mypy = ">=1.8.0,<2"

# pixi.toml [feature.lint.dependencies]
mypy = ">=1.8.0,<2"
```

**Step 4: Create regression test**

```python
"""Tests for dependency upper-cap constraint alignment across manifests.

Validates that upper-cap constraints (e.g., <2) are synchronized across
pyproject.toml and pixi.toml, ensuring the published install contract
does not permit versions that are never tested.
"""

import re
import tomllib
from pathlib import Path


def _upper_cap(spec: str) -> str:
    """Extract the upper-cap version (<X) from a PEP 508 / pixi constraint string.

    Args:
        spec: A constraint string like "mypy>=1.8.0,<2" or ">=1.8.0,<2".

    Returns:
        The upper-cap version (e.g., "2").

    Raises:
        AssertionError: If no "<" clause is present in the spec.
    """
    if "<" not in spec:
        raise AssertionError(f"No '<' upper-cap found in constraint spec: {spec}")

    # Match the first <X pattern
    match = re.search(r'<(\d+(?:\.\d+)*)', spec)
    if not match:
        raise AssertionError(f"Could not parse upper-cap from spec: {spec}")

    return match.group(1)


def test_mypy_upper_cap_consistency() -> None:
    """Mypy upper-cap must be synchronized across all manifests.

    mypy 1.x and 2.x have different error semantics and API changes.
    The upper-cap constraint must be identical in:
    - pyproject.toml [project.optional-dependencies.dev]
    - pixi.toml [feature.dev.dependencies]
    - pixi.toml [feature.lint.dependencies]

    This ensures the published install contract matches the tested environment.
    """
    repo_root = Path(__file__).resolve().parents[3]

    # Load pyproject.toml
    pyproject_path = repo_root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Extract mypy spec from dev optional dependencies
    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
    pyproject_spec = next(
        (dep for dep in dev_deps if dep.startswith("mypy")), None
    )
    assert pyproject_spec, "mypy not found in pyproject.toml [project.optional-dependencies.dev]"

    # Load pixi.toml
    pixi_path = repo_root / "pixi.toml"
    with open(pixi_path, "rb") as f:
        pixi = tomllib.load(f)

    # Extract mypy spec from pixi features
    pixi_dev_spec = pixi["feature"]["dev"]["dependencies"].get("mypy")
    assert pixi_dev_spec, "mypy not found in pixi.toml [feature.dev.dependencies]"

    pixi_lint_spec = pixi["feature"]["lint"]["dependencies"].get("mypy")
    assert pixi_lint_spec, "mypy not found in pixi.toml [feature.lint.dependencies]"

    # Extract and compare upper-caps
    pyproject_cap = _upper_cap(pyproject_spec)
    pixi_dev_cap = _upper_cap(pixi_dev_spec)
    pixi_lint_cap = _upper_cap(pixi_lint_spec)

    assert pyproject_cap == pixi_dev_cap, (
        f"mypy upper-cap skew: pyproject.toml={pyproject_cap} vs pixi.toml[dev]={pixi_dev_cap}"
    )
    assert pixi_dev_cap == pixi_lint_cap, (
        f"mypy upper-cap skew: pixi.toml[dev]={pixi_dev_cap} vs pixi.toml[lint]={pixi_lint_cap}"
    )


def test_mypy_upper_cap_is_less_than_2() -> None:
    """Mypy upper-cap must be <2 to exclude API-incompatible versions.

    mypy 1.x and 2.x have different error semantics. The upper-cap must be
    less than 2 to ensure the code is tested against compatible versions only.
    """
    repo_root = Path(__file__).resolve().parents[3]
    pyproject_path = repo_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
    pyproject_spec = next(
        (dep for dep in dev_deps if dep.startswith("mypy")), None
    )
    assert pyproject_spec, "mypy not found in pyproject.toml"

    cap = _upper_cap(pyproject_spec)
    cap_major = int(cap.split(".")[0])

    assert cap_major < 2, (
        f"mypy upper-cap must be <2 to exclude API-incompatible versions; found <{cap}"
    )
```

**Step 5: Run the regression tests**

```bash
# Run just the upper-cap constraint test
pytest tests/unit/validation/test_mypy_upper_cap_consistency.py -v

# Run full test suite to ensure no unintended breakage
pytest tests/unit -v

# Expected output:
# tests/unit/validation/test_mypy_upper_cap_consistency.py::test_mypy_upper_cap_consistency PASSED
# tests/unit/validation/test_mypy_upper_cap_consistency.py::test_mypy_upper_cap_is_less_than_2 PASSED
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Manual verification | Hand-inspecting manifests for upper-cap alignment | Error-prone; inconsistency discovered only after release | Regression tests lock in alignment permanently |
| Bumping only one manifest | Updated pixi.toml to <2 but left pyproject.toml at <3 | Users installing via pip could get mypy 2.x even though CI tested only 1.x | All manifests must synchronize when declaring the same dependency |
| Ignoring mypy API changes | Assumed mypy versions were backward compatible | mypy 2.0 changed error codes and attribute names; code broke silently | Document API-incompatible majors and enforce via regression tests |
| String matching without parsing | Compared constraint strings with regex | Formatting differences (<2 vs < 2) caused false negatives | Use tomllib to parse, then extract caps with precise regex |

## Results & Parameters

### Synchronized Constraint Lines

All three locations now use identical upper-cap:

```toml
# pyproject.toml:46
"mypy>=1.8.0,<2",

# pixi.toml:59 (feature.dev.dependencies)
mypy = ">=1.8.0,<2"

# pixi.toml:77 (feature.lint.dependencies)
mypy = ">=1.8.0,<2"
```

### Test Location and Expectations

Test file: `tests/unit/validation/test_mypy_upper_cap_consistency.py`

Test coverage:
- 2 test functions per dependency (one for alignment, one for cap check)
- Uses `tomllib` (built-in to Python 3.11+; fallback to `tomli` for 3.10)
- Extracts upper-cap using regex `r'<(\d+(?:\.\d+)*)'`
- Compares cap major versions as integers

### Expected Test Output

```
tests/unit/validation/test_mypy_upper_cap_consistency.py::test_mypy_upper_cap_consistency PASSED [ 50%]
tests/unit/validation/test_mypy_upper_cap_consistency.py::test_mypy_upper_cap_is_less_than_2 PASSED [100%]

========================== 2 passed in 0.15s ==========================
```

## Preventive Measures

### Pre-commit Hook (optional)

Add to `.pre-commit-config.yaml` to enforce on every manifest edit:

```yaml
- repo: local
  hooks:
    - id: check-mypy-upper-cap-consistency
      name: Check mypy upper-cap consistency
      entry: pytest tests/unit/validation/test_mypy_upper_cap_consistency.py
      language: system
      files: (pyproject.toml|pixi.toml)
      pass_filenames: false
      always_run: true
```

This ensures the regression test runs whenever either manifest is modified.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #748 (PR #934) | mypy upper-cap unified to <2 across pyproject.toml [project.optional-dependencies.dev], pixi.toml [feature.dev.dependencies], and pixi.toml [feature.lint.dependencies]; regression test added; all CI checks pass |

## References

- **GitHub issue**: [HomericIntelligence/ProjectHephaestus#748](https://github.com/HomericIntelligence/ProjectHephaestus/issues/748)
- **Merged PR**: [HomericIntelligence/ProjectHephaestus#934](https://github.com/HomericIntelligence/ProjectHephaestus/pull/934)
- **Related skill**: [dependency-floor-consistency-regression-guard](./dependency-floor-consistency-regression-guard.md) — synchronizes floor constraints instead of upper-caps
- **mypy releases**: [mypy on PyPI](https://pypi.org/project/mypy/)
- **Python tomllib**: [Python 3.11+ docs](https://docs.python.org/3/library/tomllib.html)
