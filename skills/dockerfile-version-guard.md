---
name: dockerfile-version-guard
description: "Use when: (1) a Dockerfile pip install lacks a version specifier and needs pinning, (2) a Dockerfile Python base image version needs a regression guard against downgrades, (3) you need cross-validation between Dockerfile pins and pyproject.toml constraints, (4) SHA256 digest consistency across multi-stage build FROM lines must be enforced, (5) optional-dependency group names in pyproject.toml may drift from Dockerfile comment blocks"
category: ci-cd
date: 2026-04-07
version: "2.0.0"
user-invocable: false
tags:
  - dockerfile
  - pinning
  - version-guard
  - pyproject
  - digest
  - regression-test
---
# Dockerfile Version Guard

Consolidated patterns for pinning and guarding dependency versions in Dockerfiles to prevent
drift — covering pip package pinning, Python base image version guards, pyproject.toml
cross-validation, SHA256 digest consistency, and optional-dependency group drift detection.

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-04-07 |
| Objective | Prevent silent drift between Dockerfile pins and project configuration files |
| Outcome | Merged from 6 source skills |
| Sources | dockerfile-dep-pin, dockerfile-python-version-guard, dockerfile-pyproject-version-guard, dockerfile-build-dep-version-guard, dockerfile-digest-consistency-guard, dockerfile-optional-dep-drift-guards |

## When to Use

1. A Dockerfile has `pip install --no-cache-dir <package>` without a version specifier
2. A Dockerfile uses a Python stdlib module with a minimum version requirement (e.g., `tomllib` >= 3.11) and you need a regression guard against base image downgrades
3. A Dockerfile pins a package also declared in `pyproject.toml` and you want cross-validation
4. A Dockerfile uses multi-stage builds with SHA256-pinned base images and you want drift detection when one stage's digest is updated without updating all stages
5. A Dockerfile uses optional-dependency groups via `ARG EXTRAS` and you want to prevent silent drift between `pyproject.toml` group definitions and Dockerfile documentation

## Decision Criteria: Which version to pin to

| Source | When to use |
| -------- | ------------- |
| `pyproject.toml [build-system].requires` | Build backends (hatchling, setuptools, flit, etc.) |
| `pixi.toml` or `requirements.txt` locked version | Runtime/dev dependencies with an explicit lock |
| `pip index versions <package>` latest | When no lockfile exists and you want current stable |
| Leave unpinned | Almost never in a builder stage — undermines reproducibility |

## Decision Criteria: Fallback Code vs. Documentation (Python version constraints)

| Use Fallback Code (try/except) | Use Documentation Only |
| ------------------------------- | ------------------------ |
| Base image version is not controlled (user-supplied) | Base image version is controlled (you own the Dockerfile) |
| Downstream consumers may use different Python versions | Current base image already satisfies the constraint |
| Library must install on Python < minimum version | Single controlled Python version in CI |

## Verified Workflow

### Quick Reference

```bash
# Find unpinned pip installs
grep -n "pip install" docker/Dockerfile

# Check pyproject.toml build-system constraint
grep -A3 "\[build-system\]" pyproject.toml

# Find latest stable release
pip index versions <package>

# Count Python FROM lines
grep -c "^FROM.*python:" docker/Dockerfile

# Count optional-dep groups
grep -c "^\[project.optional-dependencies" pyproject.toml
```

### Step 1: Pin unpinned pip dependencies

Find unpinned installs:
```bash
grep -n "pip install" docker/Dockerfile
```

Determine the version:
```bash
# Check pyproject.toml
grep -A5 "\[build-system\]" pyproject.toml
# Or find latest stable
pip index versions hatchling
```

Replace:
```dockerfile
RUN pip install --no-cache-dir hatchling
```
With:
```dockerfile
# Pinned to match pyproject.toml [build-system].requires — see #<issue>
RUN pip install --no-cache-dir "hatchling==1.29.0"
```

Key points:
- Use `==` not `>=` or `~=` — exact pin ensures reproducibility
- Quote the specifier: `"hatchling==1.29.0"` avoids shell interpretation issues
- Reference the issue number in the comment

### Step 2: Guard Python base image version

When a Dockerfile uses `tomllib` (stdlib since Python 3.11) or other version-constrained stdlib modules, add a constraint comment block above the affected `RUN` instruction:

```dockerfile
# ── Python version constraint ──────────────────────────────────────────────────
# tomllib (stdlib since Python 3.11, PEP 680) is used below to parse pyproject.toml.
# The base image MUST remain python:3.11+ for this RUN step to succeed.
#
# If you ever need to support Python < 3.11, replace the python3 -c block below
# with the tomli backport:
#   pip install tomli
#   python3 -c "import tomli as tomllib; ..."
#
# Issue: https://github.com/<org>/<repo>/issues/<N>
# ───────────────────────────────────────────────────────────────────────────────
RUN python3 -c "import tomllib; ..."
```

Write static regression tests (`tests/unit/scripts/test_dockerfile_constraints.py`):

```python
"""Static regression tests for Dockerfile Python version constraints."""
import re
from pathlib import Path
import pytest

DOCKERFILE_PATH = Path(__file__).parents[3] / "docker" / "Dockerfile"
MIN_PYTHON = (3, 11)


def _parse_python_base_versions(content: str) -> list[tuple[int, int]]:
    """Extract (major, minor) tuples from all FROM python:X.Y* lines."""
    pattern = re.compile(r"^FROM\s+python:(\d+)\.(\d+)", re.MULTILINE)
    return [(int(m.group(1)), int(m.group(2))) for m in pattern.finditer(content)]


class TestDockerfileBaseImageVersion:
    def test_dockerfile_exists(self) -> None:
        assert DOCKERFILE_PATH.exists()

    def test_has_python_base_image(self) -> None:
        versions = _parse_python_base_versions(DOCKERFILE_PATH.read_text())
        assert len(versions) > 0, "No FROM python:X.Y line found in Dockerfile"

    def test_all_base_images_meet_minimum(self) -> None:
        for major, minor in _parse_python_base_versions(DOCKERFILE_PATH.read_text()):
            assert (major, minor) >= MIN_PYTHON, (
                f"python:{major}.{minor} is below minimum python:{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
            )

    def test_constraint_comment_present(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        assert "tomllib" in content and "3.11" in content
```

Regex note: `r"^FROM\s+python:(\d+)\.(\d+)"` with `re.MULTILINE` — anchored to line start, ignores `COPY --from=builder` and non-python images.

### Step 3: Cross-validate pins against pyproject.toml

Add tomllib import with Python 3.10 backport (do NOT add `# type: ignore[no-redef]` — mypy on Python >=3.11 flags it as `unused-ignore`):

```python
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PYPROJECT_TOML = Path(__file__).parents[3] / "pyproject.toml"
```

Add helper functions (stdlib-only, no new deps):

```python
def _parse_pkg_specifier(requires: list[str], pkg: str) -> str | None:
    """Return the specifier string for pkg from build-system.requires, or None."""
    for req in requires:
        if req.lower().startswith(pkg.lower()):
            return req
    return None


def _version_tuple(v: str) -> tuple[int, ...]:
    """Convert '1.29.0' to (1, 29, 0). Also handles bare major like '2' -> (2,)."""
    return tuple(int(p) for p in v.split("."))
```

Add cross-validation tests:

```python
def test_pyproject_pkg_requirement_parseable(self) -> None:
    with PYPROJECT_TOML.open("rb") as f:
        data = tomllib.load(f)
    requires: list[str] = data.get("build-system", {}).get("requires", [])
    spec = _parse_pkg_specifier(requires, "hatchling")
    assert spec is not None, "hatchling not found in [build-system].requires"

def test_pkg_version_matches_pyproject(self) -> None:
    with PYPROJECT_TOML.open("rb") as f:
        data = tomllib.load(f)
    requires = data.get("build-system", {}).get("requires", [])
    spec = _parse_pkg_specifier(requires, "hatchling")
    assert spec is not None

    content = DOCKERFILE.read_text()
    match = re.search(r"pip install.*?hatchling==(\d+\.\d+\.\d+)", content)
    assert match is not None, "Could not find hatchling==X.Y.Z in Dockerfile"
    pinned_t = _version_tuple(match.group(1))

    lower_match = re.search(r">=(\d+\.\d+\.\d+)", spec)
    assert lower_match, f"No >= lower bound in: {spec!r}"
    lower_t = _version_tuple(lower_match.group(1))

    upper_match = re.search(r"<(\d+(?:\.\d+)*)", spec)
    upper_t = _version_tuple(upper_match.group(1)) if upper_match else None

    assert pinned_t >= lower_t
    if upper_t is not None:
        assert pinned_t < upper_t
```

Design notes:
- Two tests, not one — separates "pyproject.toml is parseable" from "versions agree"
- Regex `<(\d+(?:\.\d+)*)` handles both `<2` and `<2.0.0`
- Tuple comparison handles mixed-length tuples: `(1, 29, 0) < (2,)` is `True` in Python

### Step 4: Enforce SHA256 digest consistency across multi-stage builds

Add a digest-parsing helper:

```python
def _parse_python_base_digests(dockerfile_content: str) -> list[str]:
    """Extract SHA256 digest strings from Python base image FROM lines."""
    digests: list[str] = []
    for line in dockerfile_content.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("FROM"):
            continue
        if not re.search(r"python:", stripped, re.IGNORECASE):
            continue
        match = re.search(r"@(sha256:[a-f0-9]{64})", stripped, re.IGNORECASE)
        if match:
            digests.append(match.group(1))
    return digests
```

Key: strict 64-hex requirement prevents partial/truncated hash matches.

Add consistency tests:

```python
class TestDockerfileBaseImageDigestConsistency:
    def test_all_python_from_lines_have_sha256_digest(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        versions = _parse_python_base_versions(content)
        digests = _parse_python_base_digests(content)
        assert versions
        assert len(digests) == len(versions), (
            f"Expected {len(versions)} SHA256 digest(s), found {len(digests)}"
        )

    def test_builder_and_runtime_digests_are_identical(self) -> None:
        digests = _parse_python_base_digests(DOCKERFILE_PATH.read_text())
        assert len(digests) >= 2, "Expected at least 2 digest pins (builder + runtime)"
        assert len(set(digests)) == 1, "SHA256 digests differ: " + ", ".join(digests)
```

`len(set(digests)) == 1` is the cleanest consistency check.

### Step 5: Guard optional-dependency group drift

When a Dockerfile uses `tomllib` to install optional-dep groups via `ARG EXTRAS`, prevent drift between `pyproject.toml` group definitions and the Dockerfile comment block:

```python
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject_optional_groups() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text())
    return list(data.get("project", {}).get("optional-dependencies", {}).keys())


def test_dockerfile_documents_all_optional_dep_groups(
    dockerfile_text: str,
    pyproject_optional_groups: list[str],
) -> None:
    """Every optional-dep group in pyproject.toml must appear in Dockerfile comment."""
    missing = [g for g in pyproject_optional_groups if g not in dockerfile_text]
    assert not missing, (
        f"Groups not documented in Dockerfile: {missing}. "
        "Add them to the Layer 2 comment block."
    )


def test_dockerfile_comment_groups_exist_in_pyproject(
    dockerfile_text: str,
    pyproject_optional_groups: list[str],
) -> None:
    """Every group name in the Dockerfile comment must exist in pyproject.toml."""
    # Matches: "#   <name>  —" or "#   <name>  -"
    comment_groups = re.findall(r"#\s{3,}(\w+)\s+[—-]", dockerfile_text)
    stale = [g for g in comment_groups if g not in pyproject_optional_groups]
    assert not stale, (
        f"Stale group names in Dockerfile comment (not in pyproject.toml): {stale}"
    )
```

The regex `r"#\s{3,}(\w+)\s+[—-]"` matches comment lines where a group name is followed by an em-dash (—) or hyphen (-). Adjust to match your actual Dockerfile comment format.

### Step 6: Run and commit

```bash
# Quick check on test file
<package-manager> run python -m pytest tests/unit/e2e/test_dockerfile.py -v --no-cov

# Full suite to verify no regressions
<package-manager> run python -m pytest tests/ -q

# Pre-commit on modified files
pre-commit run --files tests/unit/e2e/test_dockerfile.py docker/Dockerfile

# Commit and PR
git add docker/Dockerfile tests/unit/e2e/test_dockerfile.py
git commit -m "fix(docker): pin and guard dependency versions in Dockerfile"
git push -u origin <branch>
gh pr create --title "fix(docker): pin and guard dependency versions" --body "Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `type: ignore[no-redef]` on tomli fallback | Added `# type: ignore[no-redef]` to the `else: import tomli as tomllib` line | mypy with `warn_unused_ignores=true` on Python >=3.11 flags it as unused — tomllib imported successfully so the ignore is never used | Omit the comment; bare `import tomli as tomllib` in the else-branch is sufficient |
| Running only the test file for coverage check | `pixi run python -m pytest tests/unit/e2e/test_dockerfile.py` | Produces 0% source coverage, triggering `--cov-fail-under` failure | This is not a real failure — run the full `tests/unit/` suite to verify the threshold is met |
| Short hash in digest regex | Used `[a-f0-9]+` instead of `[a-f0-9]{64}` | Matched partial/truncated hashes | Strict 64-hex requirement prevents false positives |
| Optional-dep comment with different separator | Used `:` instead of em-dash `—` or `-` in the comment format | `r"#\s{3,}(\w+)\s+[—-]"` didn't match | Adjust the character class to your actual separator, or standardize on em-dash |
| Upper bound regex `<(\d+\.\d+\.\d+)` | Assumed upper bound always has three version components | `pyproject.toml` may specify `<2` (bare major) | Use `<(\d+(?:\.\d+)*)` to handle both `<2` and `<2.0.0` |
| Adding tomli as a new dependency | Proposed installing tomli unconditionally | Violates YAGNI when base image already satisfies Python 3.11+ constraint | Use documentation-only approach when you control the base image version |

## Results & Parameters

### Typical test counts per guard

| Guard | Tests Added |
| ------- | ------------ |
| Pip pin presence | 1 |
| Python base image version | 4 integration + 4 unit = 8 |
| pyproject.toml cross-validation | 2 |
| SHA256 digest consistency | 2 integration + ~8 unit = 10 |
| Optional-dep group drift | 3 |

### Pre-push hook behavior

Projects with pre-push hooks typically run the full pytest suite with coverage. Expect:
- Single new test file has negligible coverage impact on source tree
- Full suite coverage threshold must still be met (run full suite, not just new file)

### Layer cache benefit from pinning

Pinned deps mean Docker only re-fetches a package when the pin changes. Unpinned deps are re-resolved on every build that invalidates the layer cache, which can silently upgrade packages.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issues #1138/#1141/#1174/#1201/#1208, PRs #1195/#1203/#1294/#1305/#1308/#1342 | Merged from 6 skills |
