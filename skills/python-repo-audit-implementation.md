---
name: python-repo-audit-implementation
description: 'Implements a multi-phase repository audit plan for Python packages.
  Use when: an audit report exists with Critical/Major findings, bringing a library
  to production-grade quality, or consolidating duplicate patterns across modules.'
category: tooling
date: 2026-03-13
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Repo** | HomericIntelligence/ProjectHephaestus |
| **Audit score before** | B / 81% |
| **Phases completed** | 9 (all Critical + Major findings) |
| **Tests before/after** | 318 unit + 51 integration — all pass |
| **Coverage** | 76.22% (threshold: 75%) |
| **PR** | HomericIntelligence/ProjectHephaestus#14 |

This skill documents implementing a comprehensive automated repo audit for a Python utility
library. The audit covered 15 sections and produced a prioritized findings list. The
implementation addressed all Critical and Major issues in 9 sequential phases.

## When to Use

- A repo audit report exists with graded findings (Critical / Major / Minor)
- A Python package needs to be brought to production-grade quality
- There are DRY violations across subprocess wrappers, shared constants, or format detection
- Error handling is inconsistent (some functions return False on failure, others raise)
- CI only tests one OS/Python version but supports multiple
- Dead code (no-op context managers, unexported helpers, stub scripts) needs removal
- Package lacks CLI entry points despite having `__main__` capable modules

## Verified Workflow

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
  --cov=hephaestus --cov-fail-under=75
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

When multiple modules each define their own subprocess wrapper with slightly different APIs,
consolidate into one enhanced function. Callers have different *needs* (timeout, dry_run,
check=False) but use the same *mechanism*. Enhance the primary wrapper to support all call
patterns, then update each caller to delegate.

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

# system/info.py — adapter that catches TimeoutExpired (callers expect tuple)
def run_command(cmd, capture_output=True, timeout=5):
    try:
        result = run_subprocess(cmd, timeout=timeout, check=False)
        return (result.returncode == 0, result.stdout.strip())
    except (_subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return (False, "")

# git/changelog.py — adapter returning empty string on non-zero exit
def run_git_command(args, cwd=None):
    result = run_subprocess(["git"] + args, cwd=str(cwd), check=False)
    return result.stdout.strip() if result.returncode == 0 else ""

# github/pr_merge.py — adapter with dry_run support
def run_git_cmd(cmd, dry_run=False, cwd=None):
    logger.info(f"$ {' '.join(cmd)}")
    run_subprocess(cmd, cwd=cwd, dry_run=dry_run)
```

> **Critical**: `system/info.py` tests expect `TimeoutExpired` to return `(False, "")`,
> NOT propagate. Catch it in the local `run_command` wrapper, not in `run_subprocess`.

### Phase 3 — DRY: Shared Constants

Create a `constants.py` at the package root for values duplicated across 3+ files.

```python
# hephaestus/constants.py
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "venv", "__pycache__", ".tox", ".pixi",
    ".pytest_cache", "dist", "build", ".mypy_cache", ".eggs",
})
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

Update all callers: `markdown/fixer.py`, `markdown/link_fixer.py`,
`validation/markdown.py`, `logging/utils.py`.

Also fix `save_data()` to call `_detect_format()` instead of duplicating format detection:
```python
# io/utils.py — save_data
try:
    fmt = _detect_format(filepath, format_hint)
except ValueError:
    fmt = "json"  # default for unknown extensions
```

### Phase 4 — Dead Code Removal

Remove no-op context managers and unexported helpers. Also delete stub scripts.

```bash
# Remove stub scripts (only contain TODO comments)
rm scripts/validate_links.py scripts/validate_structure.py \
   scripts/check_readmes.py scripts/lint_configs.py
```

Remove from `logging/utils.py`:
- `log_context` (no-op: `try: yield finally: pass`)
- `create_rotating_file_logger` (never exported)
- `contextmanager` import (now unused)

After removing `log_context`, update ALL these locations:
- `hephaestus/logging/__init__.py`
- `hephaestus/__init__.py`
- `tests/unit/logging/test_utils.py`
- `tests/integration/test_package_import.py` (has a `TOP_LEVEL_SYMBOLS` list)

### Phase 5 — Error Handling Fix

Replace silent `return False` with proper exception propagation in I/O functions.

```python
# io/utils.py — write_file (before: caught Exception, returned False)
def write_file(filepath, content, mode="w") -> bool:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, mode) as f:
        f.write(content)
    return True  # raises OSError on failure — no try/except

# config/utils.py — use logger instead of print for import warnings
import logging
_logger = logging.getLogger(__name__)
# In except ImportError:
_logger.warning("PyYAML not available, YAML config support disabled")
```

### Phase 6 — Validation `__init__.py` Fix

```python
# validation/__init__.py
from hephaestus.validation.config_lint import ConfigLinter
from hephaestus.validation.markdown import (
    check_markdown_formatting, check_required_sections, count_markdown_issues,
    extract_markdown_links, extract_sections, find_markdown_files,
    find_readmes, validate_directory_exists, validate_file_exists, validate_relative_link,
)
from hephaestus.validation.structure import StructureValidator
```

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

Pin release action to SHA for supply-chain safety:
```yaml
# release.yml
uses: pypa/gh-action-pypi-publish@76f52bc884231f62b9e4905c3b51a7d2d4c89f09
```

### Phase 8 — CLI Entry Points

Only add entry points for modules that already have a `main()` function:

```toml
# pyproject.toml
[project.scripts]
hephaestus-changelog = "hephaestus.git.changelog:main"
hephaestus-merge-prs = "hephaestus.github.pr_merge:main"
hephaestus-system-info = "hephaestus.system.info:main"
hephaestus-download-dataset = "hephaestus.datasets.downloader:main"
```

### Phase 9 — Final Polish

```ini
# .editorconfig
root = true
[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
insert_final_newline = true
trim_trailing_whitespace = true
[*.py]
max_line_length = 100
[*.{yml,yaml,toml}]
indent_size = 2
[*.md]
trim_trailing_whitespace = false
```

Create `SECURITY.md` with email contact, supported versions table, and security
considerations (no hardcoded secrets, safe deserialization opt-in, HTTPS-only downloads).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Force single subprocess signature for all callers | Make `run_subprocess` return `(bool, str)` to match `run_command` API | `git/changelog.py` and `github/pr_merge.py` need different return types | Keep `run_subprocess` returning `CompletedProcess`; write thin adapter wrappers per-module |
| Remove `log_context` without checking all barrel files | Deleted from `logging/utils.py` and updated `logging/__init__.py` | `hephaestus/__init__.py` and integration tests also imported `log_context` — missed on first pass | After removing any symbol, grep ALL `__init__.py` files AND test files for the removed name before running tests |
| Catch `TimeoutExpired` inside `run_subprocess` | Swallow `subprocess.TimeoutExpired` inside the main wrapper | `system/info.py` tests assert `(False, "")` return — if timeout is swallowed at wrapper level, callers wanting to propagate it lose the exception | Keep `run_subprocess` transparent; handle `TimeoutExpired` in the thin adapter wrapper (`run_command` in `system/info.py`) |
| Eliminate all 4 subprocess wrappers entirely | Replace all 4 with identical direct calls to `run_subprocess` | Each wrapper had subtly different semantics: one needs dry_run, one needs non-raising, one needs `(bool, str)` | Don't eliminate the wrappers — make them thin delegates that handle semantic differences |

## Results & Parameters

### Test Results

```
369 passed (318 unit + 51 integration)
Coverage: 76.22% (threshold: 75%)
```

### Estimated Audit Score Improvements

| Section | Before | After (est.) |
| --------- | -------- | -------------- |
| Security | C+ (72%) | B+ (87%) |
| Safety & Reliability | C (70%) | B (82%) |
| Source Code Quality | B- (78%) | B+ (85%) |
| CI/CD | B+ (86%) | A- (90%) |
| Packaging | C+ (75%) | B (82%) |
| **Overall** | **B (81%)** | **B+ (86%)** |

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
