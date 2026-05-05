---
name: python-repo-modernization
description: 'Bring a Python utility package from C+ to production-grade quality in one session: fix package re-exports, raise test coverage to 75%+, create integration smoke tests, harden CI/CD pipeline, and produce an installable wheel. Also covers implementing a multi-phase audit plan when an existing audit report has Critical/Major findings. Use when: a shared utility repo is functional but not yet consumable by downstream projects, or an audit report exists with graded findings.'
category: tooling
date: 2026-03-13
version: 1.1.0
user-invocable: false
absorbed: [python-repo-audit-implementation]
---

# python-repo-modernization

Systematic upgrade of a Python utility package to production-consumable quality, covering package integrity, documentation, testing, CI/CD hardening, pre-commit polish, and wheel publishing — executed as a single structured session against an implementation plan.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-13 |
| Objective | Bring ProjectHephaestus (shared utility lib) from C+ to production-grade so ProjectScylla/Odyssey can consume it |
| Outcome | Success — 372 tests passing, 76% coverage, wheel builds and imports correctly |
| Source Repo | ProjectHephaestus (HomericIntelligence ecosystem) |
| Commit | `20dbdfb` on branch `skill/tooling/python-repo-modernization` |

## When to Use

- A shared utility repo scores C or lower on package integrity (subpackages have empty `__init__.py` with no re-exports)
- Coverage is below 75% with several modules under 25%
- The package has never been consumed by a downstream repo — it's aspirational only
- CI matrix has a single element (`[unit]`) or no integration tests
- `docs/index.md` or similar file links to pages that don't exist
- `pre-commit-hooks` version is stale (>1 major version behind)
- Version fallback is hardcoded in source (`__version__ = "0.3.0"` in except clause)

## Verified Workflow

### Phase 1: Fix Package Integrity (do first — blocks everything)

**Step 1**: Audit all `__init__.py` files for empty subpackages:

```bash
grep -rn "^$\|^\"\"\"" hephaestus/*/\__init__.py | grep -v "from \."
```

**Step 2**: Add re-exports to each empty subpackage `__init__.py`. Pattern:

```python
# hephaestus/io/__init__.py
"""Input/output utilities."""

from .utils import (
    ensure_directory,
    load_data,
    read_file,
    safe_write,
    save_data,
    write_file,
)

__all__ = [
    "ensure_directory",
    "load_data",
    "read_file",
    "safe_write",
    "save_data",
    "write_file",
]
```

**Step 3**: Fix top-level `__init__.py` — import from subpackage modules, add all symbols to `__all__`.

**Step 4**: Fix version fallback — use `"unknown"` not a hardcoded version string:

```python
try:
    __version__ = _pkg_version("hephaestus")
except PackageNotFoundError:
    __version__ = "unknown"   # NOT "0.3.0"
```

**Step 5**: Fix any docstring/behavior mismatches (e.g., a function says it raises `FileNotFoundError` but actually returns a fallback value).

**Step 6**: Rename unhelpful exports like `main` to something descriptive:

```python
# Before:
from .pr_merge import main
__all__ = ["main"]

# After:
from .pr_merge import main as merge_prs, detect_repo_from_remote, local_branch_exists
__all__ = ["merge_prs", "detect_repo_from_remote", "local_branch_exists"]
```

### Phase 2: Fix Documentation (quick wins)

**Step 1**: Read `docs/index.md` — remove every link to a non-existent page. Replace with a subpackage index:

```markdown
## Subpackages
- **package.utils** — one-line description
- **package.config** — one-line description
...
```

**Step 2**: Audit `CLAUDE.md` for stale references:
- `requirements.txt` / `requirements-dev.txt` → remove (Pixi-based repo)
- Non-existent directories (`helpers/`) → remove
- Wrong Python version (`3.8+`) → fix to actual minimum (`3.10+`)

### Phase 3: Testing (most work, highest impact)

**Step 1**: Create `tests/conftest.py` with shared fixtures before expanding any test files:

```python
@pytest.fixture
def tmp_config_yaml(tmp_path):
    config = {"database": {"host": "localhost", "port": 5432}}
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config))
    return config_file

@pytest.fixture
def mock_git_repo(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    return tmp_path
```

**Step 2**: Run coverage to find lowest-coverage modules:

```bash
pixi run pytest tests/unit --override-ini="addopts=" \
  --cov=<package> --cov-report=term-missing -q 2>&1 | grep -E "^\S.*\d+%"
```

**Step 3**: For each module under 50%, write tests covering:
- Happy path for every public function
- Error/exception paths
- Edge cases (empty input, None, zero, boundary values)
- Mock external calls (subprocess, network, filesystem) using `unittest.mock.patch`

**Step 4**: Create `tests/integration/test_package_import.py` — verifies every `__all__` symbol imports:

```python
@pytest.mark.parametrize("symbol", hephaestus.__all__)
def test_top_level_symbol_importable(self, symbol):
    mod = importlib.import_module("hephaestus")
    assert hasattr(mod, symbol), f"hephaestus.{symbol} not found"
```

**Step 5**: Raise the coverage threshold in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov-fail-under=75",   # was 50
    "--cov-report=term-missing",
    # Remove --cov-report=html from default addopts (slow, use on demand)
]

[tool.coverage.report]
fail_under = 75   # was 50
```

### Phase 4: CI/CD Hardening

Expand `test.yml` matrix from `[unit]` to `[unit, integration]`:

```yaml
strategy:
  fail-fast: false
  matrix:
    test-type: [unit, integration]

- name: Run unit tests
  if: matrix.test-type == 'unit'
  run: |
    pixi run pytest tests/unit --override-ini="addopts=" -v \
      --cov=<package> --cov-report=xml --cov-fail-under=75

- name: Build wheel smoke test
  if: matrix.test-type == 'integration'
  run: |
    pixi run python -m build
    pip install dist/<package>-*.whl --force-reinstall
    python -c "import <package>; print(<package>.__version__)"
```

### Phase 5: Pre-commit Polish

```yaml
# Bump pre-commit-hooks
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0   # was v4.5.0

# Add shellcheck
- repo: https://github.com/shellcheck-py/shellcheck-py
  rev: v0.10.0.1
  hooks:
    - id: shellcheck
      files: \.sh$

# Add version consistency check
- repo: local
  hooks:
    - id: check-python-version-consistency
      entry: python scripts/check_python_version_consistency.py
      language: system
      pass_filenames: false
```

Add additional ruff security rules to `pyproject.toml`:

```toml
select = [..., "S102", "S105", "S106"]  # exec, hardcoded passwords, hardcoded tokens
```

### Phase 6: Verify Package Publishing

```bash
# Build
pixi run python -m build

# Smoke test in pixi env
pixi run pip install dist/<package>-*.whl --force-reinstall
pixi run python -c "import <package>; print(<package>.__version__)"
pixi run python -c "from <package> import <symbol1>, <symbol2>; print('OK')"
```

Bump classifier from Alpha to Beta once all phases pass:

```toml
classifiers = [
    "Development Status :: 4 - Beta",   # was 3 - Alpha
    ...
]
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `system/__init__.py` re-exporting `SystemInfo` | Added `from .info import SystemInfo` | `SystemInfo` class doesn't exist in `info.py` — only free functions | Always grep for the actual class/function names before writing re-exports: `grep -n "^class \|^def " module.py` |
| Adding `--cov-report=html` to default `addopts` | Left `--cov-report=html` in | Generates htmlcov/ directory on every test run — noisy and slow | Remove from `addopts`; use on-demand via `--cov-report=html` flag |
| `test_download_mnist_success` mocking decompress_gz | Mocked `download_with_retry=True` and `decompress_gz=True` | `download_mnist` calls `gz_path.unlink()` after decompress, but the gz file was never created (mocked away) | When mocking a method that succeeds, also create the side-effect artifacts it would have produced (the gz file on disk) |
| Writing `Write` tool call to GitHub Actions workflow | Used `Write` tool | Pre-commit hook blocked it with security reminder (workflow injection warning) | Use `Edit` tool to modify workflow files — it only changes the diff, triggering the same hook but with a narrower scope |

## Results & Parameters

### Final Coverage Numbers

| Module | Before | After |
| -------- | -------- | ------- |
| `utils/helpers.py` | ~54% | 97% |
| `config/utils.py` | ~25% | 91% |
| `utils/retry.py` | ~16% | 94% |
| `datasets/downloader.py` | ~50% | 85% |
| `validation/structure.py` | ~50% | 96% |
| `github/pr_merge.py` | ~19% | 55% (main() is CLI entry point) |
| **TOTAL** | **61%** | **76%** |

### Test Count

| Suite | Count |
| ------- | ------- |
| Unit tests | 320 |
| Integration tests | 52 |
| **Total** | **372** |

### `pyproject.toml` coverage config (final)

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=<package>",
    "--cov-report=term-missing",
    "--cov-fail-under=75",
]

[tool.coverage.report]
fail_under = 75
branch = true
```

### Phase execution order (critical)

1. Package Integrity — must come first; broken imports block all testing
2. Documentation — quick wins, unblock understanding
3. Testing — most work, highest confidence impact
4. Package Publishing — validate the wheel
5. CI/CD — harden the pipeline
6. Pre-commit — polish
7. Integration proof (cross-repo) — ultimate validation

### `conftest.py` fixture checklist

- `tmp_config_yaml` — YAML config on disk
- `tmp_config_json` — JSON config on disk
- `tmp_text_file` — plain text file
- `tmp_json_data_file` — JSON data file
- `tmp_yaml_data_file` — YAML data file
- `mock_git_repo` — directory with `.git/HEAD` stub
- `sample_config` — in-memory dict with nested keys

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | v0.3.0 modernization — 7 phases in one session | [notes.md](python-repo-modernization.notes.md) |

## Audit-Driven Implementation Phases

Use this workflow when a repo audit report already exists with graded findings (Critical / Major / Minor) and you need to implement all Critical and Major findings systematically.

**Context**: ProjectHephaestus audit score B / 81% before implementation. 9 phases addressed all Critical + Major findings. Tests: 318 unit + 51 integration — all pass. Coverage: 76.22% (threshold: 75%).

### Quick Reference

```bash
# Phase order (by severity impact):
# 1. Critical security  — fix HTTP->HTTPS, sanitize inputs
# 2. DRY: subprocess    — consolidate N wrappers into one enhanced function
# 3. DRY: constants     — create constants.py, update all callers
# 4. Dead code          — remove no-ops, stub scripts, unexported functions
# 5. Error handling     — raise instead of return False
# 6. API completeness   — fix __init__.py exports
# 7. CI matrix          — add OS x Python version matrix
# 8. Packaging          — add [project.scripts] entry points
# 9. Polish             — .editorconfig, SECURITY.md

# Verify after each phase:
pixi run pytest tests/unit --override-ini="addopts=" -v --strict-markers \
  --cov=<package> --cov-fail-under=75
```

### Phase 1 — Critical Security Fix

Fix insecure URLs and sanitize user-controlled inputs before any other changes.

```python
# datasets/downloader.py — HTTP to HTTPS
super().__init__("https://yann.lecun.com/exdb/mnist")  # was http://

# utils/helpers.py — validate package name before passing to subprocess
import re
if not re.match(r'^[A-Za-z0-9_\-\.\[\],>=<!\s]+$', package_name):
    raise ValueError(f"Invalid package name: {package_name!r}")
```

### Phase 2 — DRY: Subprocess Wrappers

When multiple modules each define their own subprocess wrapper with slightly different APIs, consolidate into one enhanced function. Callers have different needs (timeout, dry_run, check=False) but use the same mechanism. Enhance the primary wrapper to support all call patterns, then update each caller to delegate.

```python
# utils/helpers.py — enhanced run_subprocess
def run_subprocess(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int | None = None,
    check: bool = True,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    if dry_run:
        print(f"[DRY-RUN] $ {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            check=check, timeout=timeout)
    return result
```

> **Critical**: Keep `run_subprocess` transparent (returning `CompletedProcess`). Write thin adapter wrappers per-module to handle semantic differences (e.g., `TimeoutExpired` → `(False, "")`, non-raising, dry_run). Don't swallow `TimeoutExpired` inside the main wrapper.

### Phase 3 — DRY: Shared Constants

Create a `constants.py` at the package root for values duplicated across 3+ files.

```python
# <package>/constants.py
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "venv", "__pycache__", ".tox", ".pixi",
    ".pytest_cache", "dist", "build", ".mypy_cache", ".eggs",
})
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

Update all callers across the affected modules. Also fix any `save_data()` that duplicates format detection — call `_detect_format()` instead.

### Phase 4 — Dead Code Removal

Remove no-op context managers (e.g., `try: yield finally: pass`), unexported helpers, and stub scripts (files containing only TODO comments). After removing any symbol, grep ALL `__init__.py` files AND test files for the removed name before running tests.

### Phase 5 — Error Handling Fix

Replace silent `return False` with proper exception propagation in I/O functions. Use `logger.warning()` instead of `print()` for import warnings.

### Phase 6 — API Completeness

Fix `__init__.py` exports for any subpackage missing symbols. After module changes are stable, ensure all public symbols are re-exported from the appropriate `__init__.py`.

### Phase 7 — CI Matrix Expansion

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12"]
    test-type: [unit, integration]

# Upload coverage only for one combination to avoid duplication
- name: Upload coverage
  if: matrix.test-type == 'unit' && matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
```

Pin release actions to SHA for supply-chain safety.

### Phase 8 — CLI Entry Points

Only add entry points for modules that already have a `main()` function:

```toml
# pyproject.toml
[project.scripts]
<package>-changelog = "<package>.git.changelog:main"
<package>-merge-prs = "<package>.github.pr_merge:main"
```

### Phase 9 — Final Polish

Add `.editorconfig` (utf-8, lf, 4-space indent for Python, 2-space for YAML/TOML, no trailing whitespace). Create `SECURITY.md` with email contact, supported versions table, and security considerations (no hardcoded secrets, safe deserialization opt-in, HTTPS-only downloads).

### Phase Ordering Rationale

Order by severity, then dependency (later phases must not break earlier ones):

1. Security — highest risk, smallest diffs, sets baseline
2. Subprocess DRY — no dependencies on constants yet
3. Constants — after subprocess; logging changes don't conflict
4. Dead code — after constants; removed functions not referenced by new constants
5. Error handling — after dead code; don't change functions about to be deleted
6. API exports — after module changes are stable
7. CI — independent; validates all prior changes across matrix
8. Packaging — independent; additive only
9. Polish — purely additive, always last

### Estimated Score Impact

| Section | Before | After (est.) |
| --------- | -------- | -------------- |
| Security | C+ (72%) | B+ (87%) |
| Safety & Reliability | C (70%) | B (82%) |
| Source Code Quality | B- (78%) | B+ (85%) |
| CI/CD | B+ (86%) | A- (90%) |
| Packaging | C+ (75%) | B (82%) |
| **Overall** | **B (81%)** | **B+ (86%)** |

### Audit-Phase Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Force single subprocess signature for all callers | Make `run_subprocess` return `(bool, str)` to match `run_command` API | `git/changelog.py` and `github/pr_merge.py` need different return types | Keep `run_subprocess` returning `CompletedProcess`; write thin adapter wrappers per-module |
| Remove `log_context` without checking all barrel files | Deleted from `logging/utils.py` and updated `logging/__init__.py` | `hephaestus/__init__.py` and integration tests also imported `log_context` | After removing any symbol, grep ALL `__init__.py` files AND test files for the removed name |
| Catch `TimeoutExpired` inside `run_subprocess` | Swallow `subprocess.TimeoutExpired` inside the main wrapper | `system/info.py` tests assert `(False, "")` return — timeout swallowed at wrapper level loses the exception for callers wanting to propagate it | Keep `run_subprocess` transparent; handle `TimeoutExpired` in the thin adapter wrapper |
| Eliminate all 4 subprocess wrappers entirely | Replace all 4 with identical direct calls to `run_subprocess` | Each wrapper had subtly different semantics: one needs dry_run, one needs non-raising, one needs `(bool, str)` | Don't eliminate the wrappers — make them thin delegates that handle semantic differences |

## References

- Related skills: `stale-script-cleanup`, `auto-init-py-generation`
- Pre-commit hooks reference: https://pre-commit.com/hooks.html
- Hatch build backend: https://hatch.pypa.io/latest/
