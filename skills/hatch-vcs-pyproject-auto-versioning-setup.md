---
name: hatch-vcs-pyproject-auto-versioning-setup
description: "Migrate a Python project from hardcoded version in pyproject.toml to hatch-vcs dynamic versioning from git tags, and update downstream tooling that assumed the static-version world. Use when: (1) the version string is hardcoded in pyproject.toml and a CI auto-tag workflow must bump it, (2) you want the version derived automatically from git tags at build/install time with no file edits needed, (3) an auto-tag workflow is creating bot commits on main that trigger infinite CI loops, (4) hatch-vcs is being added to pixi.toml pypi-dependencies unnecessarily, (5) post-migration, importlib.metadata.version() raises PackageNotFoundError because the import name differs from the distribution name, (6) a version-consistency or single-source check script grep's pyproject.toml for a version field that no longer exists."
category: ci-cd
date: "2026-05-24"
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: hatch-vcs-pyproject-auto-versioning-setup.history
tags:
  - hatch-vcs
  - hatchling
  - pyproject
  - auto-versioning
  - git-tags
  - dynamic-version
  - importlib-metadata
  - distribution-name
  - single-source-versioning
  - ci-cd
---

# hatch-vcs pyproject.toml Auto-Versioning Setup

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-24 |
| **Objective** | Replace a hardcoded `version = "X.Y.Z"` in `pyproject.toml` with `hatch-vcs` dynamic versioning so the auto-tag CI workflow only needs to push a git tag — no file edits, no bot commits — AND update downstream tooling (`__init__.py`, drift-check scripts, single-source-of-truth validators) that previously assumed the static-version world. |
| **Outcome** | hatch-vcs generates `_version.py` at install time from the most recent git tag; pyproject.toml declares `dynamic = ["version"]`; CI auto-tag workflow simplified to tag-push only; `__init__.py` looks up version by distribution name; consistency checks derive canonical version from `git describe`; single-source check validates the hatch-vcs invariant via `tomllib`. |
| **Verification** | verified-ci |
| **History** | [changelog](./hatch-vcs-pyproject-auto-versioning-setup.history) |

## When to Use

- `pyproject.toml` has `version = "X.Y.Z"` hardcoded and a CI workflow bumps it on every merge, creating bot commits on `main`
- Auto-tag CI workflow is producing infinite trigger loops (commit triggers CI, CI commits, triggers CI...)
- You want `pip show <pkg>` / `importlib.metadata.version()` to reflect the latest git tag automatically
- A `hatch-vcs` entry was added to `pixi.toml [pypi-dependencies]` and needs to be removed (it's a build-time dep only)
- After migrating to hatch-vcs, `import yourpackage` raises `PackageNotFoundError` because `__version__` is looking up the import name instead of the distribution name
- A drift-detection or single-source-of-truth script greps `pyproject.toml` for a version field that no longer exists once `dynamic = ["version"]` is set

## Verified Workflow

### Quick Reference

The four pieces that MUST change together when migrating to hatch-vcs:

- [ ] **1. `pyproject.toml`** — declare `dynamic = ["version"]`, add `[tool.hatch.version] source = "vcs"`, add `[tool.hatch.build.hooks.vcs] version-file = "<pkg>/_version.py"`, add `hatch-vcs` to `[build-system].requires`
- [ ] **2. `<pkg>/__init__.py`** — `_pkg_version("<distribution-name>")` (case-sensitive value from `[project].name`), **NOT** `_pkg_version("<import-name>")`. importlib.metadata does NOT normalize between the two
- [ ] **3. Drift / consistency scripts** — derive the canonical version from `git describe --tags --abbrev=0 --match 'v[0-9]*'` with `importlib.metadata` fallback. **Never** parse `pyproject.toml` for `[project].version` — the field is gone
- [ ] **4. Single-source-of-truth checks** — validate the invariant (`dynamic = ["version"]` present AND `[tool.hatch.version].source == "vcs"`) via `tomllib`, **NOT** by comparing version strings across files

Also: add `<pkg>/_version.py` to `.gitignore` and `[tool.ruff] exclude`. Remove `hatch-vcs` from `pixi.toml [pypi-dependencies]` if present.

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

### 4. Update `__init__.py` to use the DISTRIBUTION NAME (not import name)

```python
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    # CRITICAL: This is the [project].name value from pyproject.toml,
    # NOT the import package directory name.
    __version__ = _pkg_version("HomericIntelligence-Hephaestus")
except PackageNotFoundError:
    __version__ = "unknown"
```

**The most common mistake:** using the import name (e.g. `"hephaestus"`) instead of the distribution name (e.g. `"HomericIntelligence-Hephaestus"`). `importlib.metadata.version()` does NOT normalize between PyPI distribution names and import package names. It performs a PEP 503 normalized lookup against installed `*.dist-info` directories — and there is no such directory for the import name. You will get `PackageNotFoundError` and `__version__ == "unknown"` at every import.

The dist name is the **exact** value of the `name` field in `[project]` in `pyproject.toml` (PEP 503 normalization is applied, so case and `-`/`_` differences are tolerated, but the name itself must match).

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

### 8. Update downstream consistency / single-source checks

Any pre-existing tooling that assumed `pyproject.toml` holds a static `[project].version` will break. Update each pattern:

**Pattern A — Drift/consistency check that compared `pyproject.toml` version to `__init__.py` / `VERSION` / `SECURITY.md`:**

```python
# OLD — broken after hatch-vcs migration
# def _get_pyproject_version() -> str:
#     data = tomllib.loads(Path("pyproject.toml").read_text())
#     return data["project"]["version"]   # KeyError — field is dynamic now

# NEW — derive canonical version from git, with importlib.metadata fallback
import subprocess
from importlib.metadata import PackageNotFoundError, version as _pkg_version

def _get_canonical_version(dist_name: str) -> str:
    """Canonical version: latest git tag, or installed dist metadata as fallback."""
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return tag.lstrip("v")
    except subprocess.CalledProcessError:
        pass
    try:
        return _pkg_version(dist_name)
    except PackageNotFoundError:
        return "unknown"
```

**Pattern B — "Single source of truth" check that previously asserted one literal version string:**

After hatch-vcs, the "single source" is the **invariant** that pyproject delegates to VCS, not a string match. Validate via `tomllib`:

```python
import tomllib
from pathlib import Path

def check_single_source_invariant() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    project = data.get("project", {})
    dynamic = project.get("dynamic", [])
    assert "version" in dynamic, (
        "pyproject.toml [project].dynamic must include 'version' "
        "(hatch-vcs single-source invariant violated)"
    )
    assert "version" not in project, (
        "pyproject.toml [project] must NOT define a static 'version' "
        "field once 'version' is in [project].dynamic"
    )
    hatch_version = data.get("tool", {}).get("hatch", {}).get("version", {})
    assert hatch_version.get("source") == "vcs", (
        "[tool.hatch.version] source must be 'vcs' for hatch-vcs single-source versioning"
    )
```

**Pattern C — verification of script output.** When a check script prints a status line, verify it by reading the FULL output. Do not `tail -3` and claim a line is missing — earlier lines get truncated and you'll falsely report regressions. Quote the actual line from the script's stdout when claiming success or failure.

## Key Insight: `_version.py` is generated at install time

When `pip install -e .` or `pixi install` runs, hatch-vcs writes `yourpackage/_version.py`
in the source tree containing the current version string. This file:

- Exists locally after install; does NOT exist in a fresh CI checkout until install runs
- Must be in `.gitignore` — never commit it
- Must be in `[tool.ruff] exclude` — ruff will lint/format it if it exists on disk
- Is NOT needed in `MANIFEST.in` or `[tool.hatch.build] artifacts` for development installs

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | --------------- | --------------- | ---------------- |
| Add `hatch-vcs` to `pixi.toml [pypi-dependencies]` | Added `hatch-vcs = ">=0.4.0,<1"` under `[pypi-dependencies]` in `pixi.toml` | Unnecessary; pip resolves it automatically from `[build-system].requires`. Adds noise to lock file but does not cause errors. | `hatch-vcs` is a build-time dep — declare it only in `[build-system].requires`, never in `pixi.toml` |
| Keep auto-tag workflow with `pyproject.toml` bump steps | Left steps in CI that read the version, incremented it, rewrote `pyproject.toml`, and committed back to `main` | Creates a bot commit on `main` on every CI pass, triggers infinite loop potential, and defeats the purpose of auto-versioning | With `hatch-vcs`, the workflow only needs to push a git tag — all file-edit/commit steps must be removed |
| Not adding `_version.py` to `.gitignore` | Omitted `yourpackage/_version.py` from `.gitignore` | Generated file gets accidentally staged and committed; ruff lints it on next pre-commit run and fails CI | Always add the generated `_version.py` to `.gitignore` immediately when enabling `hatch-vcs` |
| Not adding `_version.py` to ruff `exclude` | Left `_version.py` out of `[tool.ruff] exclude` | ruff reformats the generated file on every pre-commit run, causing spurious diffs or CI failures | Add `yourpackage/_version.py` to `[tool.ruff] exclude` alongside the `.gitignore` entry |
| Use the **import name** with `importlib.metadata.version()` | `__version__ = _pkg_version("hephaestus")` in `hephaestus/__init__.py` when the installed distribution is `HomericIntelligence-Hephaestus` | `PackageNotFoundError`: `importlib.metadata` performs a PEP 503 normalized lookup against installed `*.dist-info` directories. The import package name is not the distribution name; there is no `hephaestus-*.dist-info` to find. `__version__` silently becomes `"unknown"` at every import. | `importlib.metadata.version()` requires the **distribution name** (the literal value of `[project].name`), not the import package directory name. The two are unrelated — never assume normalization across them |
| Parse `pyproject.toml` for `[project].version` in a drift-check script | `_get_pyproject_version()` did `tomllib.load(...)["project"]["version"]` after the migration | `KeyError`/`None` — once `dynamic = ["version"]` is set, `[project].version` no longer exists in pyproject.toml. Hatch-vcs deliberately removes it because the field is computed at build time. | After hatch-vcs migration, derive canonical version from `git describe --tags --abbrev=0 --match 'v[0-9]*'` with `importlib.metadata.version("<dist-name>")` as fallback. Never grep pyproject for a field hatch-vcs deliberately removed |
| Verify "the script printed line X" by reading `tail -3` of stdout | Claimed a single-source check was missing an output line based on the last 3 lines of its output | The relevant line was earlier in the output and got truncated by `tail`. I reported a false regression on a working script. | Verify script output by reading the FULL stdout (or grep for the expected line explicitly). Never assert a line is missing based on a truncated tail. Quote the actual matching line when claiming success or failure |

## Results & Parameters

### Key Parameters

| Parameter | Description | Example |
| ----------- | ------------- | --------- |
| `yourpackage` | The package directory (contains `__init__.py`) | `hephaestus` |
| `your-dist-name` | The `name` field in `pyproject.toml` — **use this literal value in `importlib.metadata.version()`** | `HomericIntelligence-Hephaestus` |
| Bootstrap version | Last known release version for tag-list fallback | `"0.7.0"` |
| `hatchling` version pin | Tested range | `>=1.27.0,<2` |
| `hatch-vcs` version pin | Tested range | `>=0.4.0,<1` |
| Canonical version source (post-migration) | git tag, parsed with `git describe --tags --abbrev=0 --match 'v[0-9]*'` | `v0.7.1` → `0.7.1` |

### Expected Outcomes

After completing the migration:

- `pyproject.toml` has `dynamic = ["version"]` and no `version = "X.Y.Z"` line
- `[tool.hatch.version]` and `[tool.hatch.build.hooks.vcs]` sections added
- `yourpackage/_version.py` exists locally after `pixi install` / `pip install -e .` but is NOT committed
- `importlib.metadata.version("<your-dist-name>")` returns the version from the most recent git tag
- `import yourpackage; print(yourpackage.__version__)` prints the same version (NOT `"unknown"`)
- Auto-tag CI workflow no longer commits to `main` — only pushes a tag
- `hatch-vcs` is NOT present in `pixi.toml [pypi-dependencies]`
- Drift/consistency scripts derive the canonical version from git, not from `pyproject.toml`
- Single-source-of-truth check validates the hatch-vcs invariant via `tomllib`, not a string compare

## Relationship to `versioning-consistency-release-workflow`

The [`versioning-consistency-release-workflow`](./versioning-consistency-release-workflow.md)
skill covers the static versioning pattern: `pyproject.toml` holds the canonical version,
`importlib.metadata` reads it at runtime, and a pre-commit hook guards against drift.

This skill replaces the "canonical version lives in `pyproject.toml`" part: with `hatch-vcs`,
the canonical version lives in git tags and `pyproject.toml` declares `dynamic = ["version"]`.
The `importlib.metadata` runtime pattern stays the same — but the lookup argument MUST be
the distribution name, and any drift check must derive its canonical from `git describe`,
not from parsing `pyproject.toml`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Branch `5047-separate-dev-production-deps` | `version = "0.7.0"` removed; `dynamic = ["version"]` added; auto-tag workflow simplified to tag-push; pre-commit passes locally |
| ProjectHephaestus | PR #434 | Fixed `hephaestus/__init__.py` to use distribution name `"HomericIntelligence-Hephaestus"` in `importlib.metadata.version()` instead of import name `"hephaestus"`; resolved `PackageNotFoundError`; merged via CI |
| ProjectHephaestus | PR #436 | Rewrote `scripts/check_version_single_source.py` to validate the hatch-vcs invariant (`dynamic = ["version"]` + `[tool.hatch.version].source == "vcs"`) via `tomllib` instead of comparing version strings across files; merged via CI |
| ProjectHephaestus | PR #438 | Replaced `_get_pyproject_version` in `hephaestus/version/consistency.py` with `_get_canonical_version` deriving from `git describe --tags --abbrev=0 --match 'v[0-9]*'` with `importlib.metadata` fallback; merged via CI |
