---
name: dependency-manifest-single-source-of-truth
description: "Use when: (1) Python dependencies are declared in multiple manifests (pixi.toml, pyproject.toml, requirements*.txt) with divergent version constraints, (2) aligning floor constraints (e.g., >=9.0 vs >=9.0.0) or upper-cap constraints (e.g., <2 vs <3) across manifests for packages with API-incompatible major versions, (3) removing a duplicated version field from pixi.toml [workspace] that pyproject.toml already owns, (4) implementing semantic-version-aware (PEP 440) regression guards that detect manifest drift in CI, (5) ensuring pip-install users and pixi dev-env users see the same tested package versions."
category: ci-cd
date: 2026-06-13
version: "1.1.0"
user-invocable: false
history: dependency-manifest-single-source-of-truth.history
tags:
  - pixi
  - pyproject
  - requirements
  - dependencies
  - manifest-consistency
  - version-constraints
  - regression-guard
  - pep-440
  - drift-detection
  - ci-guardrail
---

# Dependency Manifest: Single Source of Truth

Keep Python dependency declarations consistent across `pixi.toml`, `pyproject.toml`, and
`requirements*.txt` so the published install contract always matches the tested environment.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Objective** | Eliminate dependency declaration drift (floors, upper-caps, duplicated version fields) across multiple manifests and enforce consistency with semantic-version-aware regression guards |
| **Outcome** | Successful — single source of truth per concern, drift-detection scripts/tests, and PEP 440 comparison that catches `9.0` vs `9.0.0` representation skew |
| **Verification** | verified-ci |

## When to Use

- Python dependencies are declared in multiple files (pixi.toml, pyproject.toml,
  requirements.txt, requirements-dev.txt) with divergent version constraints
- Pinned versions in requirements*.txt fall outside pixi.toml range constraints
  (e.g., `pytest==8.4.2` vs `<8`)
- Aligning **floor** constraints across manifests for API-incompatible majors
  (e.g., PyGithub `>=1.55` vs `>=2.9.1`)
- Aligning **upper-cap** constraints across manifests for API-incompatible majors
  (e.g., mypy `<3` vs `<2`)
- Floors/caps that are semantically equal but differ in string form (`9.0` vs `9.0.0`)
- `pixi.toml [workspace]` has a `version` field that duplicates `pyproject.toml [project] version`
- Unbounded `[pypi-dependencies]` entries that need an explicit `<next-major>` upper bound
- Adding regression tests / CI guardrails to lock in manifest consistency going forward

## The Core Problem

When the same dependency is declared in more than one manifest, the **published install
contract** (what pip users get) can drift from the **tested environment** (what pixi
developers and CI run). For packages with API-incompatible major versions, this produces
silent runtime breakage.

**Broken setup (floor skew):**

- `pyproject.toml`: `PyGithub>=1.55,<3` (published contract permits 1.x)
- `pixi.toml`: `pygithub = ">=2.9.1,<3"` (dev/test only ever runs 2.x)
- Result: pip users install 1.x, code only works on 2.x → silent failure.

**Broken setup (upper-cap skew):**

- `pyproject.toml`: `mypy>=1.8.0,<3` (permits 2.x)
- `pixi.toml [feature.dev]`: `mypy = ">=1.8.0,<2"` (tested on 1.x only)
- Result: pip users get mypy 2.x with different error semantics → silent breakage.

**Correct setup:** every manifest declares the same floor *and* the same cap; a regression
guard fails CI if any pair drifts (even across `9.0`/`9.0.0` representation differences).

## Verified Workflow

### Quick Reference

```bash
# 1. Audit: find divergent declarations of a dependency across every manifest
grep -nE "PyGithub|pygithub" pyproject.toml pixi.toml
grep -nE "mypy"             pyproject.toml pixi.toml

# 2. Pick the source-of-truth constraint:
#    - floors  -> use the HIGHEST floor across manifests
#    - caps    -> use the MOST RESTRICTIVE (lowest) cap across manifests
# 3. Update every manifest to match.

# 4. (Consolidation) make pixi.toml the single source; regenerate the pip mirrors
pixi install
pixi run python scripts/sync_requirements.py
pixi run python scripts/check_dep_sync.py
pixi run python scripts/sync_requirements.py --check

# 5. Add a semantic-version regression guard, then run it
pytest tests/unit -k "dependency_floor or upper_cap or version_consistency" -v
```

Decision rules:

| Concern | Source-of-truth rule | Why |
| --------- | ---------------------- | ----- |
| Floor (`>=`) | Highest floor wins | Lower floors permit untested old majors |
| Upper-cap (`<`) | Lowest (most restrictive) cap wins | Higher caps permit untested new majors |
| `[workspace] version` | Delete it; `pyproject.toml [project] version` owns it | Optional in pixi; removal beats syncing |
| Unbounded `[pypi-dependencies]` | Add `<(installed_major + 1)` | Bound to a tested major without downgrading |

### Detailed Steps

#### 1. Consolidate into pixi.toml as single source of truth

Map every package across `pixi.toml`, `pyproject.toml [project.dependencies]` /
`[project.optional-dependencies]`, `requirements.txt`, and `requirements-dev.txt`.
Identify missing packages, version conflicts (pinned version outside pixi range), and
ghost references (CI/Dockerfiles pointing at non-existent files).

Add missing packages to `pixi.toml`, grouped with inline comments, then strip the
duplicated declarations from `pyproject.toml` (keep `[tool.*]` config sections):

```toml
# pyproject.toml header after stripping duplicate deps:
# Dependencies are managed in pixi.toml (single source of truth).
# This file provides project metadata and tool configuration only.
```

Generate the pip mirrors from pixi-resolved versions (`scripts/sync_requirements.py`
reads `pixi list --json`) and add a CI guardrail (`scripts/check_dep_sync.py`) that
validates: every requirements package exists in pixi.toml, pinned versions satisfy pixi
ranges, and pyproject.toml has no leftover `[project.dependencies]`.

#### 2. Align FLOOR constraints across manifests (API-incompatible majors)

Use the **highest** floor as the source of truth. Example — PyGithub 1.x and 2.x are
API-incompatible and the code uses `Repository.stargazers_count` (2.9.1+):

```toml
# pyproject.toml [project.optional-dependencies.github]
"PyGithub>=2.9.1,<3",

# pixi.toml [dependencies]
pygithub = ">=2.9.1,<3"
```

#### 3. Align UPPER-CAP constraints across manifests

Use the **most restrictive** cap as the source of truth. Watch for multiple pixi feature
sections declaring the same dependency (e.g., `[feature.dev]` and `[feature.lint]`) — all
must agree. Example — mypy 1.x vs 2.x have different error semantics:

```toml
# pyproject.toml [project.optional-dependencies.dev]
"mypy>=1.8.0,<2",

# pixi.toml [feature.dev.dependencies]
mypy = ">=1.8.0,<2"

# pixi.toml [feature.lint.dependencies]
mypy = ">=1.8.0,<2"
```

#### 4. Dedup a duplicated [workspace] version

A `[workspace] version` in `pixi.toml` is optional metadata. Delete it instead of syncing
it, leaving `pyproject.toml [project] version` as the only source. Verify with
`pixi install --locked` (pixi does not require the field). Extend an existing
version-consistency check to detect re-introduction:

```diff
 [workspace]
 name = "project-hephaestus"
-version = "0.4.0"
 description = "Shared utilities and tooling for the HomericIntelligence ecosystem"
```

```python
# stdlib-only regex extraction (no tomllib dependency needed for this check):
r'\[project\]\s*\n(?:.*\n)*?version\s*=\s*"([^"]+)"'    # pyproject [project] version
r'\[workspace\]\s*\n(?:.*\n)*?version\s*=\s*"([^"]+)"'  # pixi [workspace] version -> None if absent
```

#### 5. PEP 440 semantic comparison guards (avoid string-equality traps)

Raw string comparison reports false drift because `"9.0" != "9.0.0"`, and naive
`split('.')` tuple comparison mishandles pre-releases/dev versions. Normalize with
`packaging.version.Version` before comparing, and extract versions with a robust PEP 508
helper rather than ad-hoc regex:

```python
from packaging.version import Version

assert "9.0" == "9.0.0"                  # False  ← trap: undetected drift
assert Version("9.0") == Version("9.0.0")  # True  ← safe

def _find_dep(specifier_string: str, pkg_name: str) -> str | None:
    """Extract a version from a PEP 508 specifier (e.g. 'pytest>=9.0' -> '9.0')."""
    if pkg_name not in specifier_string:
        return None
    remainder = specifier_string[specifier_string.find(pkg_name) + len(pkg_name):]
    # Strip operators longest-first so '==' is not eaten as '=' + '='
    for op in ["~=", "==", "!=", ">=", "<=", "<", ">", "="]:
        if remainder.startswith(op):
            remainder = remainder[len(op):]
            break
    for stop in [",", ";", "[", "]", " "]:
        if stop in remainder:
            remainder = remainder[:remainder.find(stop)]
    return remainder.strip() or None
```

A floor-extraction helper for the simpler `>=` case (stops before the cap):

```python
def _floor(spec: str) -> str:
    """'PyGithub>=2.9.1,<3' -> '2.9.1'."""
    if ">=" not in spec:
        raise AssertionError(f"No '>=' floor in spec: {spec}")
    return spec.split(">=", 1)[1].split(",")[0].strip()
```

Compare both files against **each other** (never against a hardcoded constant — that makes
the test a tautology), and test **both** files in every guard:

```python
assert Version(_floor(pyproject_spec)) == Version(_floor(pixi_spec)), (
    f"PyGithub floor skew: pyproject={pyproject_spec} vs pixi={pixi_spec}"
)
```

#### 6. Add explicit upper bounds to unbounded [pypi-dependencies]

Set the cap to `<(installed_major + 1)`, NOT `<installed_major` — the latter **downgrades**
the package and can reintroduce breakage. After tightening a bound, `pixi lock` may report
"already up-to-date"; force re-resolution with `pixi update <pkg>`, then `pixi install`,
then run the full test suite (a downgraded minor may break on your Python version).

```toml
# altair 6.0.0 installed & working on Python 3.14:
altair = ">=5.0,<6"   # BAD  — downgrades to 5.5.0 (TypedDict(closed=True) breaks on 3.14)
altair = ">=5.0,<7"   # GOOD — keeps 6.0.0
```

#### 7a. Reuse existing `_find_dep` across new test classes (DRY)

When adding a new `TestXxxConsistency` class to an existing test file, do not copy-paste the
`_find_dep` static method. Call the already-defined version on the sibling class:

```python
class TestRuffConsistency:
    """Verify ruff floor is consistent across manifests."""

    @staticmethod
    def _find_dep(specifier_string: str, pkg_name: str) -> str | None:
        # Delegate to the sibling class — no duplication needed
        return TestPytestConsistency._find_dep(specifier_string, pkg_name)
```

Cross-class static-method delegation is valid Python. A reviewer will flag a verbatim copy
as a P4 DRY violation.

#### 7b. Locate the correct pixi.toml section before writing the guard

Tool-chain packages (ruff, mypy, pytest) may live in different `[feature.*]` sections. Verify
with a grep before writing the test assertion — do NOT assume the section name:

```bash
grep -n "ruff" pixi.toml
# ruff lives under [feature.shared.dependencies], NOT [feature.lint.dependencies]
```

The section determines the TOML key path used in the test:
`pixi["feature"]["shared"]["dependencies"]["ruff"]`.

#### 7c. No pixi re-solve needed when the lock already satisfies the new floor

When raising a floor (e.g., ruff `>=0.1.0` → `>=0.15`) and the current lock already
resolves a version ≥ the new floor, `pixi install` is a no-op. There is no need to run
`pixi update ruff` or `pixi lock` unless the new constraint explicitly excludes the locked
version.

#### 7. Lock it in (regression test + optional pre-commit)

Place the guard under your tests tree (e.g.,
`tests/unit/scripts/test_dependency_floor_consistency.py`) and, optionally, wire a
pre-commit hook that runs it whenever a manifest changes:

```yaml
- repo: local
  hooks:
    - id: check-dependency-consistency
      name: Check dependency floor/cap consistency
      entry: pytest tests/unit/scripts/test_dependency_floor_consistency.py
      language: system
      files: (pyproject.toml|pixi.toml)
      pass_filenames: false
      always_run: true
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Raw string version comparison | `assert pyproject_floor == pixi_floor` with `"9.0"` vs `"9.0.0"` | `"9.0" != "9.0.0"` even though they are the same PEP 440 version; drift goes undetected | Normalize with `packaging.version.Version()` before comparing, never raw strings |
| `split('.')` tuple comparison | Parse `"9.0.0"`→`(9,0,0)`, pad with zeros | Fragile for pre-releases/dev/local versions (e.g., `9.0.0a1` vs `9.0a1`) | Delegate to `packaging.version.Version`, which handles PEP 440 edge cases |
| Naive regex `>=([0-9]+\.[0-9]+)` | Match only `X.Y` floors | Breaks on three-part versions and extras like `pytest-cov[toml]>=7.0` | Use a robust `_find_dep()` PEP 508 parser (operators longest-first, trims extras) |
| Hardcode the floor in the test | `assert Version("9.0") == Version(pixi_floor)` | Tautology; never catches real drift when the floor changes | Extract both floors from both files and compare them to each other |
| Check only one manifest | Assume pixi.toml follows pyproject.toml automatically | Maintainers edit one file and forget the other; drift accumulates silently | Parse and test every manifest in each guard |
| Bump only one manifest's cap | Set pixi.toml to `<2`, left pyproject.toml at `<3` | pip users still get the untested new major | All manifests must synchronize when declaring the same dependency |
| Cap at `<installed_major` | Set `altair = ">=5.0,<6"` while 6.0.0 was installed | Downgraded to 5.5.0, which broke on Python 3.14 (`TypedDict(closed=True)`) | Cap at `<(installed_major + 1)` and re-run tests after `pixi install` |
| `pixi lock` after tightening a bound | Expected lock to re-resolve to a newer allowed version | `pixi lock` reports "already up-to-date" if the locked version still satisfies the new constraint | Use `pixi update <pkg>` to force re-resolution, then `pixi install` |
| `parents[4]` for repo root in tests | Computed project root from test file depth | In a git worktree this resolved to `.worktrees/`, not the project root | Verify depth with `Path(...).parents[i]` loop; here `parents[3]` was correct |
| `from scripts.X import Y` / `sys.path.insert` | Import check scripts as a package | `scripts/` has no `__init__.py`; pytest import machinery conflicts with sys.path hacks | Load with `importlib.util.spec_from_file_location()` for scripts without `__init__.py` |
| Hand-inspecting manifests | Manual verification of consistency | Error-prone; inconsistencies surface only after release | Regression tests lock consistency in permanently |
| Defining a new `_find_ruff_dep` static method | Plan draft defined `_find_ruff_dep` as a verbatim copy of `TestPytestConsistency._find_dep` with `"ruff"` hardcoded | DRY violation — `_find_dep` already accepts a `name` parameter; reviewer flagged as MAJOR P4/DRY finding | Call the existing `TestPytestConsistency._find_dep(dev_deps, "ruff")` directly from the new class; cross-class static delegation is valid Python |
| Hardcoded sentinel floor test | `assert floor >= Version("0.15")` in a test body | Goes stale silently when the lock bumps to 0.16.x without updating the test | Use a cross-manifest consistency test (`pyproject_floor == pixi_shared_floor`) instead — self-updating and non-tautological |
| Running a single test file with coverage gate | `pixi run pytest tests/unit/scripts/test_dependency_floor_consistency.py` alone | Triggers `fail-under=80` coverage gate because only a tiny slice of hephaestus is exercised | Use `--no-cov` when running a single file in isolation; rely on the full suite for coverage reporting |

## Results & Parameters

### Auto-generated requirements.txt format

```text
# AUTO-GENERATED from pixi.toml — do not edit manually.
# Regenerate with: python scripts/sync_requirements.py
# These files exist for pip-only contexts (Docker, CI fallback).

pytest==8.4.2
pytest-cov==6.3.0
ruff==0.14.14
jinja2==3.1.6  # Template engine (paper scaffolding, code generation)
```

### Synchronized constraint lines

```toml
# Floor alignment (highest floor wins):
"PyGithub>=2.9.1,<3"   # pyproject.toml [project.optional-dependencies.github]
pygithub = ">=2.9.1,<3"  # pixi.toml [dependencies]

# Upper-cap alignment (most restrictive cap wins):
"mypy>=1.8.0,<2"       # pyproject.toml [project.optional-dependencies.dev]
mypy = ">=1.8.0,<2"    # pixi.toml [feature.dev.dependencies] AND [feature.lint.dependencies]
```

### Reference upper bounds applied (ProjectScylla)

```toml
[pypi-dependencies]
matplotlib = ">=3.8,<4"
numpy = ">=1.24,<3"
pandas = ">=2.0,<3"
seaborn = ">=0.13,<1"
scipy = ">=1.11,<2"
altair = ">=5.0,<7"          # <7 not <6 — altair 5.x breaks on Python 3.14
vl-convert-python = ">=1.0,<2"
krippendorff = ">=0.6.0,<1"
statsmodels = ">=0.14,<1"
jsonschema = ">=4.0,<5"
defusedxml = ">=0.7,<1"
```

### Semantic comparison examples

```python
from packaging.version import Version

assert Version("9.0") == Version("9.0.0")   # equal: same PEP 440 version
assert Version("7.0") == Version("7.0.0")   # equal
assert Version("9.0") != Version("9.1")     # different: minor bump
assert Version("7.0") != Version("7.0.1")   # different: patch bump
```

### importlib pattern for test imports (scripts without `__init__.py`)

```python
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_dep_sync", Path(__file__).resolve().parents[3] / "scripts" / "check_dep_sync.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_dep_sync = _mod.check_dep_sync
```

### Useful commands

```bash
grep -A2 "name: altair" pixi.lock                       # check locked version
pixi update altair                                       # force re-resolution after a bound change
pixi install                                             # apply lock changes to the active env
pixi run python -c "import altair; print(altair.__version__)"  # verify installed version
```

### Notes

- `tomllib` is stdlib in Python 3.11+ (fall back to `tomli` on 3.10); use it to parse
  manifests robustly instead of comparing raw constraint strings.
- Dependabot auto-appends a colon when `commit-message.prefix` ends in `)` (e.g.,
  `chore(deps)` → `chore(deps): ...`); document this in `.github/dependabot.yml`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4907, PR #5117 | Consolidated deps across pixi.toml, pyproject.toml, requirements.txt, requirements-dev.txt; 37 unit tests; 8 packages added |
| ProjectHephaestus | Issue #57, PR #111 | Removed duplicated `pixi.toml [workspace] version`; extended drift-detection script; 404 tests pass |
| ProjectHephaestus | Issue #631, PR #652 | PyGithub floor consolidated 1.55 → 2.9.1; regression test added; CI passed |
| ProjectHephaestus | Issue #748, PR #934 | mypy upper-cap unified to `<2` across pyproject + pixi dev/lint features; regression test added |
| ProjectHephaestus | Issue #785 | pytest 9.x / pytest-cov 7.x tight floors; PEP 440 semantic-version regression guard |
| ProjectScylla | Issue #1119, PR #1170 | Added `<next-major>` upper bounds to 11 unbounded `[pypi-dependencies]`; 3209 tests pass |
| ProjectHephaestus | Issue #1201, PR #1294 | Raised ruff floor `>=0.1.0` → `>=0.15` in both pyproject.toml and pixi.toml (`[feature.shared.dependencies]`); added `TestRuffConsistency` class reusing `TestPytestConsistency._find_dep`; 8 tests pass (2 new + 6 pre-existing); no pixi re-solve needed |
