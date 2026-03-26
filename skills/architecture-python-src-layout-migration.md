---
name: architecture-python-src-layout-migration
description: "Pattern for migrating a Python project from flat layout (package/ at repo root) to src-layout (src/package/). Use when: (1) moving a Python package into src/ for ecosystem compliance, (2) updating all filesystem path references after a directory restructure, (3) fixing Path(__file__) navigations after adding a directory level."
category: architecture
date: '2026-03-25'
version: "2.0.0"
user-invocable: false
verification: verified-local
history: architecture-python-src-layout-migration.history
tags: [python, src-layout, migration, pyproject, hatchling, directory-restructure]
---

# Skill: Python Flat-to-Src-Layout Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Migrate a Python project from flat layout (`package/` at repo root) to src-layout (`src/package/`) |
| **Outcome** | Successful on 2 projects — validated across large (4782 tests) and small (384 tests) repos |
| **Verification** | verified-local (CI validation pending on PRs) |
| **History** | [changelog](./architecture-python-src-layout-migration.history) |

## When to Use

- Migrating a Python project from flat layout to src-layout for ecosystem consistency
- Performing a large-scale directory restructure that affects build config, CI, Docker, scripts, tests, and docs
- Updating `Path(__file__)` navigations after adding a directory level to the package hierarchy
- Updating pre-commit hook `files:` patterns after moving source directories
- Updating `.github/CODEOWNERS` source directory ownership after restructure

## Verified Workflow

### Quick Reference

```bash
# 1. Move the package (preserves git history)
mkdir -p src && git mv <package>/ src/<package>/

# 2. Update pyproject.toml
#    packages = ["src/<package>"]
#    force-include: "src/<package>/..." = "<package>/..."  (if applicable)
#    pythonpath = ["src", "scripts"]
#    --cov=src/<package>  (in addopts, if present)
#    source = ["src/<package>", ...]
#    mypy_path = "src"  (if applicable)

# 3. Regenerate pixi.lock (editable install SHA256 invalidated)
pixi install

# 4. Verify import resolution
python -c "import <package>; print(<package>.__file__)"
# Should print: .../src/<package>/__init__.py

# 5. Run tests
pytest tests/ -x

# 6. Run pre-commit
pre-commit run --all-files
```

### Detailed Steps

1. **Move the package**: `mkdir -p src && git mv <package>/ src/<package>/` — uses `git mv` to preserve full file history via `git log --follow`.

2. **Update `pyproject.toml`** (up to 8 changes depending on project):
   - `[tool.hatch.build.targets.wheel] packages = ["src/<package>"]`
   - `[tool.hatch.build.targets.wheel.force-include]` — source path changes, target stays same for wheel (if applicable)
   - `[tool.pytest.ini_options] pythonpath = ["src", "scripts"]` — change `"."` to `"src"`
   - `addopts --cov=src/<package>` (if `--cov` is in addopts; note: `--cov=<package>` using the installed package name also works)
   - `[tool.coverage.run] source = ["src/<package>", ...]`
   - `[tool.mypy] mypy_path = "src"` — so mypy resolves package imports (if applicable)
   - Update all comments referencing the old path

3. **Update `pixi.toml`**: Change lint/format task commands from `<package>` to `src/<package>`.

4. **Update `.pre-commit-config.yaml`** — THREE types of changes per hook:
   - `files:` regex patterns: `^<package>/` → `^src/<package>/`, `^(scripts|<package>)/` → `^(scripts|src/<package>)/`
   - `entry:` commands: paths in ruff/mypy/bandit commands
   - `description:` strings referencing the old path

5. **Update `.github/CODEOWNERS`**: Change `<package>/ @owner` to `src/<package>/ @owner`.

6. **Update CI workflows**: grep exclusion paths, `--cov=` values, trigger `paths:` patterns, timing probe paths.

7. **Update Dockerfile** (if applicable): `COPY` source paths. The target path inside the container may also change.

8. **Update `Path(__file__)` navigations** (if applicable): Each `.parent.parent.parent` (navigating to project root) gains one extra `.parent` since the package is one level deeper. Count: `src/<package>/<subpackage>/file.py` needs 4 `.parent` calls to reach project root.

9. **Update scripts**: Default path arguments (`default="<package>/"` → `default="src/<package>/"`), docstring examples, path construction helpers (`root / "<package>"` → `root / "src" / "<package>"`).

10. **Update test data** (if applicable): Tests that create `tmp_path / "<package>"` to simulate repo structure need `tmp_path / "src" / "<package>"` AND `mkdir(parents=True)` since the `src/` parent doesn't exist.

11. **Regenerate `pixi.lock`**: `pixi install` — the editable install SHA256 is invalidated by the source move.

12. **Comprehensive sweep**: Run `grep -rn '"<package>/' --include='*.py' --include='*.toml' --include='*.yaml' --include='*.yml' --include='*.md' .` and filter out `src/<package>`, `.pixi/`, and `build/` to catch remaining references.

13. **Update documentation**: CLAUDE.md, README.md, docs/README.md — directory structure diagrams, command examples, key file paths.

14. **Validate doc/config consistency**: If the project has consistency-checking scripts (e.g., `check_doc_config_consistency.py`), these will catch mismatches between `--cov=` in README and `pyproject.toml`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Test `mkdir()` without `parents=True` | Changed `tmp_path / "scylla"` to `tmp_path / "src" / "scylla"` but kept `mkdir()` | `FileNotFoundError` — `src/` parent directory doesn't exist in `tmp_path` | When adding a directory level to test fixtures, always add `parents=True` to `mkdir()` calls |
| Missing `--cov=` in README | Updated most README references but missed a `--cov=scylla` inside a code block | Pre-commit `check-doc-config-consistency` hook caught the mismatch | Run the full pre-commit suite, not just tests — consistency checkers catch documentation drift |
| Write-protected `.claude/` directory | Tried to update example paths in `.claude/agents/` and `.claude/shared/` files | Permission denied in don't-ask mode for `.claude/` directory edits | Agent config files under `.claude/` may be write-protected; these are informational-only and don't affect builds |
| Missed `description:` in pre-commit hooks | Updated `entry:` and `files:` in pre-commit hooks but forgot to update `description:` text | Description still referenced old path (cosmetic but inconsistent) | Pre-commit hooks have THREE path references: `entry:`, `files:`, and `description:` — check all three |

## Results & Parameters

### Key pyproject.toml Configuration (src-layout with hatchling)

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/<package>"]

# Only needed if the package has data files to force-include:
[tool.hatch.build.targets.wheel.force-include]
"src/<package>/data" = "<package>/data"

[tool.pytest.ini_options]
pythonpath = ["src", "scripts"]

[tool.mypy]
mypy_path = "src"

[tool.coverage.run]
source = ["src/<package>"]
```

### Scope of Changes by Project Size

| Category | Large Project (Scylla) | Small Project (Hephaestus) | Notes |
|----------|----------------------|---------------------------|-------|
| Build config | 3 files | 3 files | Always: pyproject.toml, pixi.toml, pixi.lock |
| Pre-commit | 7 hooks | 6 hooks | Scales with number of hooks referencing package path |
| CI workflows | 3 files | 0 files | CI uses `pixi run` + `pip install -e .` — resolves via pyproject.toml |
| Docker | 1 file | 0 files | Only if project has Dockerfile |
| Python source | 4 files | 0 files | Only if code uses `Path(__file__)` to find project root |
| Scripts | 5 files | 1 file | Only scripts with hardcoded package paths |
| Tests | 4 files | 0 files | Only tests simulating repo structure in tmp_path |
| Documentation | 12+ files | 3 files | CLAUDE.md, README.md, docs/ |
| CODEOWNERS | 0 files | 1 file | Missed in Scylla, caught in Hephaestus |
| **Total files** | **197** (incl. renames) | **46** (incl. renames) | |

### Import Behavior

Python import statements (`from <package>.foo import bar`) do **not** change — only filesystem path references. This is the primary benefit of src-layout: the package name is decoupled from the directory structure.

### Key Observation: Complexity Scales with Project Features

Simpler projects (no Dockerfile, no `Path(__file__)` navigations, CI that resolves through pyproject.toml) need far fewer changes. The core changes are always: `git mv`, pyproject.toml, pixi.toml, .pre-commit-config.yaml, and documentation. Steps 6-10 are conditional.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1523, PR #1555 | Migrated `scylla/` → `src/scylla/`, 4782 tests pass, 30 pre-commit hooks pass |
| ProjectHephaestus | Issue #41, PR #73 | Migrated `hephaestus/` → `src/hephaestus/`, 384 unit + 51 integration tests pass, 82% coverage |
