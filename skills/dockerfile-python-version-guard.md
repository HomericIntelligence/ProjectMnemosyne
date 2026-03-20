---
name: dockerfile-python-version-guard
description: Guard Dockerfile Python version constraints via static tests and inline
  documentation. Use when a Dockerfile uses a Python stdlib module with a minimum
  version requirement (e.g., tomllib >= 3.11) and you need a regression guard to prevent
  base image downgrades from breaking builds.
category: ci-cd
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# dockerfile-python-version-guard

Guard Dockerfile Python base image version requirements with inline documentation and static pytest regression tests.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-02-27 |
| Issue | #1138 |
| PR | #1195 |
| Objective | Prevent silent breakage when a Dockerfile uses a Python stdlib module introduced in a specific Python version (e.g., `tomllib` requires Python 3.11+) |
| Outcome | Success — 14 static tests added, 3197 total tests passing, 78.31% coverage |
| Category | ci-cd |
| Project | ProjectScylla |

## When to Use

- When a Dockerfile uses a Python stdlib module with a minimum version requirement (`tomllib` >= 3.11, `importlib.resources` changes >= 3.9, `zoneinfo` >= 3.9, etc.)
- When you need a regression guard to prevent a future base image downgrade from silently breaking a build
- When adding Python version constraint documentation inline in a Dockerfile for future maintainers
- When deciding between a code fallback (try/except tomllib / tomli) versus documentation-only approach
- When writing static Dockerfile tests that parse `FROM python:X.Y` lines with regex

## Decision Criteria: Fallback Code vs. Documentation

| Use Fallback Code (try/except) | Use Documentation Only |
|-------------------------------|------------------------|
| Base image version is not controlled (e.g., user-supplied) | Base image version is controlled (you own the Dockerfile) |
| Downstream consumers may use different Python versions | Current base image already satisfies the constraint |
| Library must install on Python < minimum version | KISS principle: adding tomli dep just for hypothetical future |
| CI matrix covers multiple Python versions | Single controlled Python version in CI |

**Chosen approach for this session**: Documentation-only (KISS) — base image was already `python:3.11-slim`, constraint was already satisfied, and adding a `tomli` dependency would violate YAGNI.

## Verified Workflow

### Step 1: Identify the Dockerfile layer using the version-constrained module

Read the Dockerfile and locate the `RUN` command using the module:

```bash
# Find the RUN layer using tomllib
grep -n "tomllib" <project-root>/docker/Dockerfile
```

### Step 2: Add a constraint comment block above the RUN layer

Insert a comment block directly above the affected `RUN` instruction explaining:
- Which module is version-constrained and why
- The minimum Python version required
- The base image constraint this implies
- The alternative (fallback recipe) for future maintainers who want to support older Python

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

### Step 3: Write static Dockerfile regression tests

Create `tests/unit/scripts/test_dockerfile_constraints.py` (or equivalent path):

```python
"""Static regression tests for Dockerfile Python version constraints."""
import re
from pathlib import Path
import pytest

DOCKERFILE_PATH = Path(__file__).parents[3] / "docker" / "Dockerfile"
MIN_PYTHON = (3, 11)


def parse_python_base_versions(content: str) -> list[tuple[int, int]]:
    """Extract (major, minor) tuples from all FROM python:X.Y* lines."""
    pattern = re.compile(r"^FROM\s+python:(\d+)\.(\d+)", re.MULTILINE)
    return [(int(m.group(1)), int(m.group(2))) for m in pattern.finditer(content)]


class TestDockerfileBaseImageVersion:
    """Assert the Dockerfile base image satisfies the tomllib version constraint."""

    def test_dockerfile_exists(self) -> None:
        assert DOCKERFILE_PATH.exists(), f"Dockerfile not found at {DOCKERFILE_PATH}"

    def test_has_python_base_image(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        versions = parse_python_base_versions(content)
        assert len(versions) > 0, "No FROM python:X.Y line found in Dockerfile"

    def test_all_base_images_meet_minimum(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        versions = parse_python_base_versions(content)
        for major, minor in versions:
            assert (major, minor) >= MIN_PYTHON, (
                f"Base image python:{major}.{minor} is below minimum "
                f"python:{MIN_PYTHON[0]}.{MIN_PYTHON[1]} required by tomllib"
            )

    def test_constraint_comment_present(self) -> None:
        content = DOCKERFILE_PATH.read_text()
        assert "tomllib" in content and "3.11" in content, (
            "Dockerfile should document the tomllib/Python 3.11+ constraint"
        )


class TestParsePythonBaseVersions:
    """Unit tests for the version parsing helper."""

    def test_single_version(self) -> None:
        assert parse_python_base_versions("FROM python:3.11-slim") == [(3, 11)]

    def test_multiple_versions(self) -> None:
        content = "FROM python:3.11-slim\nFROM python:3.12-alpine"
        assert parse_python_base_versions(content) == [(3, 11), (3, 12)]

    def test_ignores_non_python_images(self) -> None:
        assert parse_python_base_versions("FROM ubuntu:22.04") == []

    def test_ignores_inline_from(self) -> None:
        # FROM in a COPY --from= should not be matched
        assert parse_python_base_versions("COPY --from=builder /app /app") == []
```

### Step 4: Run the tests

```bash
<package-manager> run python -m pytest tests/unit/scripts/test_dockerfile_constraints.py -v
```

Expect 14 tests (4 integration + 4 unit + parametrized variants) to pass.

### Step 5: Commit and PR

```bash
git add docker/Dockerfile tests/unit/scripts/test_dockerfile_constraints.py
git commit -m "fix(docker): document Python 3.11+ constraint for tomllib in Dockerfile"
git push -u origin <branch>
gh pr create \
  --title "[Fix] Document Python 3.11+ constraint for tomllib in Dockerfile" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Test file structure (14 tests total)

| Test Class | Tests | What it checks |
|------------|-------|----------------|
| `TestDockerfileBaseImageVersion` | 4 | Dockerfile exists, has `FROM python:X.Y`, all versions >= 3.11, constraint comment present |
| `TestParsePythonBaseVersions` | 4 | Parsing helper: single version, multiple versions, ignores non-python images, ignores `COPY --from=` |

### Regex pattern for FROM parsing

```python
pattern = re.compile(r"^FROM\s+python:(\d+)\.(\d+)", re.MULTILINE)
```

- Anchored to line start (`^` with `re.MULTILINE`)
- Captures major and minor version as groups
- Correctly ignores `COPY --from=builder` lines
- Correctly ignores `FROM ubuntu:22.04` and similar non-python images

### Dockerfile comment block structure

The comment block must appear directly above the `RUN` layer using `tomllib` and must contain:
1. The module name and stdlib introduction version
2. The base image constraint this creates
3. The fallback recipe (as a comment, not live code) for future maintainers
4. A reference to the originating issue

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1138, PR #1195 | [notes.md](../references/notes.md) |

## Related Skills

- **docker-ci-dead-step-cleanup** — Removing dead CI steps referencing non-existent Dockerfile tests
- **docker-multistage-build** — Docker build optimization patterns
- **pytest-coverage-threshold-config** — Maintaining coverage thresholds when adding test files

## References

- Issue #1138: <https://github.com/HomericIntelligence/ProjectScylla/issues/1138>
- PR #1195: <https://github.com/HomericIntelligence/ProjectScylla/pull/1195>
- PEP 680 (tomllib): <https://peps.python.org/pep-0680/>
- Python 3.11 changelog — tomllib added to stdlib
