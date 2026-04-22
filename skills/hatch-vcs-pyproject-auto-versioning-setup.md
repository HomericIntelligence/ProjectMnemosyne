---
name: hatch-vcs-pyproject-auto-versioning-setup
description: "Migrate a Python project from hardcoded version in pyproject.toml to hatch-vcs dynamic versioning from git tags. Use when: (1) the version string is hardcoded in pyproject.toml and a CI auto-tag workflow must bump it, (2) you want the version derived automatically from git tags at build/install time with no file edits needed, (3) an auto-tag workflow is creating bot commits on main that trigger infinite CI loops, (4) hatch-vcs is being added to pixi.toml pypi-dependencies unnecessarily."
category: ci-cd
date: "2026-04-21"
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - hatch-vcs
  - hatchling
  - pyproject
  - auto-versioning
  - git-tags
  - dynamic-version
  - ci-cd
---

# hatch-vcs pyproject.toml Auto-Versioning Setup

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-21 |
| **Objective** | Replace a hardcoded `version = "X.Y.Z"` in `pyproject.toml` with `hatch-vcs` dynamic versioning so the auto-tag CI workflow only needs to push a git tag — no file edits, no bot commits. |
| **Outcome** | hatch-vcs generates `_version.py` at install time from the most recent git tag; pyproject.toml declares `dynamic = ["version"]`; CI auto-tag workflow simplified to tag-push only. |
| **Verification** | verified-precommit |

## When to Use

- `pyproject.toml` has `version = "X.Y.Z"` hardcoded and a CI workflow bumps it on every merge, creating bot commits on `main`
- Auto-tag CI workflow is producing infinite trigger loops (commit triggers CI, CI commits, triggers CI...)
- You want `pip show <pkg>` / `importlib.metadata.version()` to reflect the latest git tag automatically
- A `hatch-vcs` entry was added to `pixi.toml [pypi-dependencies]` and needs to be removed (it's a build-time dep only)

## Verified Workflow

### 1. Update `pyproject.toml`

```toml
[build-system]
# Add hatch-vcs to build-system.requires — it is a BUILD-TIME dep, NOT a runtime dep
requires = ["hatchling>=1.27.0,<2", "hatch-vcs>=0.4.0,<1"]
build-backend = "hatchling.build"

[project]
name = "YourPackageName"
# Remove:  version = "0.7.0"
# Add:
dynamic = ["version"]

# Add these two new sections:
[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "yourpackage/_version.py"
```

Replace `yourpackage` with the actual package directory (the one containing `__init__.py`).

### 2. Add generated file to `.gitignore`

```gitignore
# hatch-vcs generated version file (created at pip install / pixi install time)
yourpackage/_version.py
```

Do NOT commit `_version.py`. It is regenerated on every install.

### 3. Add generated file to ruff exclude (if using ruff)

In `pyproject.toml`:

```toml
[tool.ruff]
exclude = [
  # existing excludes ...
  "yourpackage/_version.py",   # hatch-vcs generated — not human-authored
]
```

Without this, ruff will lint or format the generated file and may fail CI.

### 4. Verify `__init__.py` already uses `importlib.metadata`

If the package already reads version from installed metadata, no changes are needed:

```python
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("your-dist-name")
except PackageNotFoundError:
    __version__ = "unknown"
```

If `__init__.py` hardcodes `__version__ = "X.Y.Z"`, switch it to the pattern above.
The dist name matches the `name` field in `pyproject.toml` (case-insensitive, hyphens/underscores normalized).

### 5. Remove hatch-vcs from `pixi.toml` (if added by mistake)

`hatch-vcs` must NOT appear in `[pypi-dependencies]` in `pixi.toml`.
pip/hatchling resolves it automatically from `[build-system].requires` during `pip install -e .`.
Adding it to pixi.toml is harmless but adds noise to the lock file.

```toml
# Remove this line from pixi.toml [pypi-dependencies] if present:
# hatch-vcs = ">=0.4.0,<1"
```

### 6. Simplify the auto-tag CI workflow

With hatch-vcs the workflow only needs to push a tag — no `pyproject.toml` bump, no commit to `main`:

```yaml
- name: Compute next patch version and push tag
  shell: bash
  run: |
    LATEST_TAG=$(git tag --list 'v*' --sort=-v:refname | head -1)
    if [ -z "${LATEST_TAG}" ]; then
      LATEST="0.7.0"   # bootstrap version — set to your last known release
    else
      LATEST="${LATEST_TAG#v}"
    fi
    MAJOR=$(echo "${LATEST}" | cut -d. -f1)
    MINOR=$(echo "${LATEST}" | cut -d. -f2)
    PATCH=$(echo "${LATEST}" | cut -d. -f3)
    TAG="v${MAJOR}.${MINOR}.$((PATCH + 1))"
    if git rev-parse "${TAG}" >/dev/null 2>&1; then
      echo "Tag ${TAG} already exists — nothing to do"
      exit 0
    fi
    git tag "${TAG}"
    git push origin "${TAG}"
```

Remove any steps that previously: read the version from `pyproject.toml`, bumped the patch number,
rewrote the file, and committed back to `main`.

### 7. Verify installation

```bash
# After pixi install or pip install -e .
python -c "import yourpackage; print(yourpackage.__version__)"
# Should print the version derived from the most recent git tag, e.g. "0.7.1"

# Check the generated file exists (it is local, not committed)
ls yourpackage/_version.py
```

## Key Insight: `_version.py` is generated at install time

When `pip install -e .` or `pixi install` runs, hatch-vcs writes `yourpackage/_version.py`
in the source tree containing the current version string. This file:

- Exists locally after install; does NOT exist in a fresh CI checkout until install runs
- Must be in `.gitignore` — never commit it
- Must be in `[tool.ruff] exclude` — ruff will lint/format it if it exists on disk
- Is NOT needed in `MANIFEST.in` or `[tool.hatch.build] artifacts` for development installs

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| Add `hatch-vcs` to `pixi.toml [pypi-dependencies]` | Added `hatch-vcs = ">=0.4.0,<1"` under `[pypi-dependencies]` in `pixi.toml` | Unnecessary; pip resolves it automatically from `[build-system].requires`. Adds noise to lock file but does not cause errors. | `hatch-vcs` is a build-time dep — declare it only in `[build-system].requires`, never in `pixi.toml` |
| Keep auto-tag workflow with `pyproject.toml` bump steps | Left steps in CI that read the version, incremented it, rewrote `pyproject.toml`, and committed back to `main` | Creates a bot commit on `main` on every CI pass, triggers infinite loop potential, and defeats the purpose of auto-versioning | With `hatch-vcs`, the workflow only needs to push a git tag — all file-edit/commit steps must be removed |
| Not adding `_version.py` to `.gitignore` | Omitted `yourpackage/_version.py` from `.gitignore` | Generated file gets accidentally staged and committed; ruff lints it on next pre-commit run and fails CI | Always add the generated `_version.py` to `.gitignore` immediately when enabling `hatch-vcs` |
| Not adding `_version.py` to ruff `exclude` | Left `_version.py` out of `[tool.ruff] exclude` | ruff reformats the generated file on every pre-commit run, causing spurious diffs or CI failures | Add `yourpackage/_version.py` to `[tool.ruff] exclude` alongside the `.gitignore` entry |

## Results & Parameters

### Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `yourpackage` | The package directory (contains `__init__.py`) | `hephaestus` |
| `your-dist-name` | The `name` field in `pyproject.toml` | `HomericIntelligence-Hephaestus` |
| Bootstrap version | Last known release version for tag-list fallback | `"0.7.0"` |
| `hatchling` version pin | Tested range | `>=1.27.0,<2` |
| `hatch-vcs` version pin | Tested range | `>=0.4.0,<1` |

### Expected Outcomes

After completing the migration:

- `pyproject.toml` has `dynamic = ["version"]` and no `version = "X.Y.Z"` line
- `[tool.hatch.version]` and `[tool.hatch.build.hooks.vcs]` sections added
- `yourpackage/_version.py` exists locally after `pixi install` / `pip install -e .` but is NOT committed
- `importlib.metadata.version("your-dist-name")` returns the version from the most recent git tag
- Auto-tag CI workflow no longer commits to `main` — only pushes a tag
- `hatch-vcs` is NOT present in `pixi.toml [pypi-dependencies]`

## Relationship to `versioning-consistency-release-workflow`

The [`versioning-consistency-release-workflow`](./versioning-consistency-release-workflow.md)
skill covers the static versioning pattern: `pyproject.toml` holds the canonical version,
`importlib.metadata` reads it at runtime, and a pre-commit hook guards against drift.

This skill replaces the "canonical version lives in `pyproject.toml`" part: with `hatch-vcs`,
the canonical version lives in git tags and `pyproject.toml` declares `dynamic = ["version"]`.
The `importlib.metadata` runtime pattern stays the same.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Branch `5047-separate-dev-production-deps` | `version = "0.7.0"` removed; `dynamic = ["version"]` added; auto-tag workflow simplified to tag-push; pre-commit passes locally |
