---
name: post-remediation-audit
description: "Execute a structured post-remediation audit to close remaining quality gaps after an initial cleanup round. Use when: preparing a repo for ecosystem integration, verifying CI/classifier/release-gate alignment, or ensuring all code quality gaps are resolved after a first-pass remediation."
category: ci-cd
date: 2026-03-14
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | post-remediation-audit |
| **Category** | ci-cd |
| **Scope** | Python package repositories with pyproject.toml + GitHub Actions CI |
| **Effort** | ~30 min (read → fix → verify) |
| **Risk** | Low — all changes are targeted and verifiable |

Closes the quality gap after a first-pass remediation by auditing CI matrix alignment, classifier accuracy, release workflow safety, undocumented CLI tools, and residual code smells. Produces a B+/A- grade repo ready for ecosystem integration.

## When to Use

- After applying an initial remediation commit and needing to verify nothing was missed
- When preparing a shared utilities library for integration across multiple dependent repos
- When CI tests only a subset of the declared Python version classifiers
- When a release workflow publishes to PyPI without a test gate
- When console_scripts entry points are not documented in README

## Verified Workflow

### Quick Reference

| Issue Type | File | Fix |
|------------|------|-----|
| Classifier/CI mismatch | `pyproject.toml` classifiers | Remove classifiers for untested Python versions |
| pytest version skew | `pyproject.toml` dev deps | Align to range tested in pixi.toml |
| Release without test gate | `.github/workflows/release.yml` | Add `test` job + `needs: test` on publish job |
| Undocumented CLI | `README.md` | Add CLI Commands section with table + examples |
| Bare `except Exception: pass` | Source file | Add inline comment justifying the broad catch |
| Redundant local import | Source file | Remove — use module-level import directly |
| Empty placeholder dirs | `scripts/` | `rmdir` the empty directories |

### Step 1 — Read current state in parallel

Read all relevant files simultaneously to minimize round-trips:

```python
# Read these in a single parallel batch:
# pyproject.toml          — classifiers, pytest version, console_scripts
# .github/workflows/release.yml  — check for test gate
# README.md               — check for CLI documentation
# hephaestus/system/info.py      — find bare except
# hephaestus/markdown/link_fixer.py  — find redundant imports
```

### Step 2 — Fix classifier mismatch

If CI matrix only tests Python 3.12 but classifiers declare 3.10/3.11:

```toml
# pyproject.toml — REMOVE untested versions
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",  # only what CI verifies
]
```

Rule: classifiers should reflect what CI actually tests, not aspirational support.

### Step 3 — Align pytest version range

```toml
# pyproject.toml dev deps — match pixi.toml lower bound
"pytest>=9.0,<10",   # was >=7.0,<10; pixi.toml uses >=9.0
```

### Step 4 — Add test gate to release workflow

Before the `build-and-publish` job, add a `test` job and declare `needs: test`:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v6
      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          pixi-version: v0.63.2
      - name: Cache pixi environments
        uses: actions/cache@v5
        with:
          path: |
            .pixi
            ~/.cache/rattler/cache
          key: ${{ runner.os }}-pixi-${{ hashFiles('pixi.lock') }}
          restore-keys: |
            ${{ runner.os }}-pixi-
      - name: Run tests
        run: pixi run pytest tests/unit

  build-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: test          # ← blocks publish on green tests
    steps:
      # ... existing build + pypi-publish steps
```

### Step 5 — Document CLI entry points

Add a "CLI Commands" section to README.md **after** the Python API usage section:

```markdown
## CLI Commands

Four command-line tools are installed as console scripts when you install the package:

| Command | Description |
|---|---|
| `hephaestus-changelog` | Generate a changelog from Git history |
| `hephaestus-merge-prs` | Automate merging of GitHub pull requests |
| `hephaestus-system-info` | Collect and display system/environment information |
| `hephaestus-download-dataset` | Download datasets with retry and progress reporting |

### Examples

```bash
hephaestus-system-info --json
hephaestus-system-info --no-tools
hephaestus-changelog --help
```
```

### Step 6 — Fix residual code smells

**Bare `except Exception: pass`** — add a justifying comment:
```python
except Exception:  # /etc/os-release parsing is best-effort; any failure is non-fatal
    pass
```

**Redundant local import** (import inside `__init__` when already at module level):
```python
# BEFORE — redundant
import re as _re
home_dir = _re.escape(str(Path.home().parent))

# AFTER — use module-level import directly
home_dir = re.escape(str(Path.home().parent))
```

**Empty placeholder directories** — remove them:
```bash
rmdir scripts/testing scripts/utilities
```

### Step 7 — Verify all checks pass

```bash
pixi run ruff check hephaestus/ tests/
pixi run mypy hephaestus/
pixi run pytest tests/unit -q
pre-commit run --all-files
```

All must be green before committing.

### Step 8 — Commit

Use a structured conventional commit message listing all audit items:

```
fix: post-remediation audit — classifier cleanup, release gate, CLI docs, and minor code quality

- Remove Python 3.10/3.11 classifiers (CI only tests 3.12)
- Align pytest version range to >=9.0,<10 in pyproject.toml
- Add test gate to release.yml (build-and-publish needs: test)
- Document 4 CLI console_scripts in README CLI Commands section
- Add justifying comment to bare except in system/info.py
- Remove redundant `import re as _re` in markdown/link_fixer.py
- Remove empty scripts/testing/ and scripts/utilities/ directories
- Raise CI coverage threshold to 80% (aligns with pyproject.toml)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `noqa: BLE001` on bare except | Added `# noqa: BLE001` to suppress ruff warning on `except Exception` | `BLE001` was not in the project's ruff `select` list — caused "unused noqa directive" error | Check `[tool.ruff.lint] select` before adding noqa codes; use plain comments when the rule isn't selected |
| Relative `cd` in Bash commands | Used `cd build/$$/ProjectMnemosyne` with relative paths | Shell PID `$$` expanded to empty string in tool invocation context | Always use absolute paths; capture `$$` into a variable first or use `$PPID`-style workarounds |

## Results & Parameters

### Outcome

- **Grade improvement**: 82% → 86% (+4 points) across 15 audit dimensions
- **Tests**: 358 passed, 81.65% coverage (above 80% threshold)
- **Linting**: ruff clean, mypy strict mode clean
- **Hooks**: All 19 pre-commit hooks pass

### Key Configuration Values

```toml
# pyproject.toml — aligned state
[project.optional-dependencies]
dev = [
    "pytest>=9.0,<10",   # matches pixi.toml
]

classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",  # only what CI tests
]

[tool.coverage.report]
fail_under = 80  # matches CI flag and pytest addopts

[tool.pytest.ini_options]
addopts = ["--cov-fail-under=80"]  # matches coverage.report
```

### Audit Checklist (copy-paste for future audits)

```markdown
- [ ] CI matrix Python versions match pyproject.toml classifiers
- [ ] pytest version range in dev deps matches pixi.toml lower bound
- [ ] Release workflow has `needs: test` before publish job
- [ ] All `console_scripts` documented in README with examples
- [ ] No unjustified `except Exception: pass` (add comment or narrow exception)
- [ ] No redundant local imports (check `__init__` methods especially)
- [ ] No empty placeholder directories in scripts/
- [ ] Coverage threshold consistent across pyproject.toml, pytest addopts, and CI
```
