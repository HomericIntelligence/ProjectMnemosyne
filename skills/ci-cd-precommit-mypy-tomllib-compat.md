---
name: ci-cd-precommit-mypy-tomllib-compat
description: "Fix CI pre-commit failures caused by mypy unused-ignore on Python version-dependent imports, ruff complexity/format rules, and coverage gaps. Use when: (1) mypy flags type:ignore as unused on CI Python but needed on older Python, (2) pre-commit hooks fail with ruff C901/RUF059/N817/format, (3) coverage drops below threshold after adding new modules."
category: ci-cd
date: 2026-03-23
version: "1.0.0"
user-invocable: false
tags:
  - mypy
  - ruff
  - pre-commit
  - tomllib
  - coverage
  - python-compat
---

# Fixing CI Pre-Commit Failures for Cross-Python-Version Packages

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Objective** | Fix CI pre-commit failures (mypy, ruff, coverage) after adding new validation modules to a PyPI package supporting Python 3.10-3.14 |
| **Outcome** | All CI checks passing after 3 fix iterations. Key insight: use importlib.import_module() for Python-version-dependent imports to avoid mypy unused-ignore issues entirely. |

## When to Use

- mypy reports `Unused "type: ignore" comment [unused-ignore]` on CI but the ignore is needed locally on a different Python version
- Pre-commit hooks fail with ruff formatting, unused imports, or complexity violations after adding new modules
- Coverage drops below threshold after adding new library modules (main() functions are untested)
- A package needs to support both Python 3.10 (no `tomllib`) and 3.11+ (has `tomllib`)

## Verified Workflow

### Quick Reference

```python
# WRONG: type:ignore that breaks on Python 3.12 CI but needed on 3.10
try:
    import tomllib  # type: ignore[no-redef]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

# RIGHT: importlib avoids all type:ignore issues
import importlib

tomllib = None
for _mod_name in ("tomllib", "tomli"):
    try:
        tomllib = importlib.import_module(_mod_name)
        break
    except ModuleNotFoundError:
        continue
```

```bash
# Fix ruff issues in order:
pixi run ruff format hephaestus/ tests/          # 1. Format first
pixi run ruff check . --select=F401,I001 --fix   # 2. Unused imports + sorting
pixi run ruff check . --select=RUF059 --fix --unsafe-fixes  # 3. Unused unpacked vars
pixi run ruff check . --select=C901              # 4. Check complexity manually
```

### Detailed Steps

1. **mypy unused-ignore on version-dependent imports**: When a package supports Python 3.10 (needs `tomli`) AND 3.11+ (has `tomllib`), the `try/except` import pattern requires `type: ignore` comments that mypy flags as unused on whichever Python version actually succeeds the import. Solution: use `importlib.import_module()` which needs no type annotations at all.

2. **Ruff format before lint**: Always run `ruff format` first because format changes can create or resolve lint issues. CI runs format check before lint.

3. **RUF059 unused unpacked variables**: When a function returns a tuple but a test only checks one element, prefix the unused variable with `_`. Use `--unsafe-fixes` to auto-apply. But be careful: if you rename `x` to `_x`, any remaining references to `x` become F821 (undefined name). Check for this.

4. **C901 complexity**: Extract helper functions to reduce cyclomatic complexity. Common pattern: extract loop bodies or conditional blocks into named functions (e.g., `_update_string_state()`, `_count_multiple_blank_lines()`).

5. **N817 CamelCase imported as acronym**: Rename `import defusedxml.ElementTree as ET` to `as ElementTree`.

6. **Coverage gaps from main() functions**: Add tests that monkeypatch `sys.argv` and call `main()` directly. For stdin-reading CLIs, also monkeypatch `sys.stdin` with `io.StringIO`.

7. **D301 backslashes in docstrings**: Use `r"""` raw docstring prefix when examples contain backslashes.

8. **SIM102 nested if**: Collapse `if a: if b:` into `if a and b:`. If the combined line exceeds 100 chars, extract a variable.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `type: ignore[no-redef]` on tomllib import | Added type:ignore to suppress mypy on tomli fallback | CI runs Python 3.12 where tomllib exists in stdlib, so mypy flags the ignore as unused | Use `importlib.import_module()` instead — zero type annotations needed |
| `type: ignore[import-not-found,no-redef]` broadened | Tried broadening the ignore codes to cover both Python versions | Still flagged as unused on 3.12 — the entire ignore comment is unnecessary when the import succeeds | The fundamental issue is that type:ignore is version-dependent; importlib sidesteps it |
| `@pytest.mark.skipif` with `pytest.importorskip` at class level | Used class-level decorator to skip test class when optional dep missing | `pytest.importorskip` raises Skipped at collection time, skipping entire module (0 tests collected) | Use `pytest.importorskip()` inside individual test methods instead |
| RUF059 rename then forget references | Renamed `versions` to `_versions` but left `assert versions == {}` on next line | F821 undefined name — the old variable name was still referenced | After any RUF059 rename, grep for remaining references to the old name |
| Format after lint fix | Fixed lint issues then expected format to be clean | Lint fixes (like removing imports) can change formatting | Always run format AFTER lint fixes, not before |

## Results & Parameters

### CI Fix Iteration Pattern

```
Iteration 1: Fix format + unused imports + mypy type:ignore + C901 + coverage
Iteration 2: Fix remaining RUF059 + F821 from variable renames
Iteration 3: Fix importlib approach for tomllib + D301 + SIM102 + E501
```

### Coverage Recovery Pattern

```python
# Test main() with monkeypatch
class TestMain:
    def test_clean_returns_zero(self, tmp_path, monkeypatch):
        (tmp_path / "file.py").write_text("x = 1\n")
        monkeypatch.setattr("sys.argv", ["cmd", "--repo-root", str(tmp_path)])
        assert main() == 0

    # For stdin-reading CLIs:
    def test_stdin_input(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["cmd"])
        monkeypatch.setattr("sys.stdin", io.StringIO('{"data": []}'))
        assert main() == 0
```

### Final Results

- Pre-commit: all hooks passing (ruff format, ruff check, mypy, complexity, shellcheck)
- Tests: 544 passed, 6 skipped
- Coverage: 82.36% (above 80% threshold)
- 3 commits to fix CI (could have been 1 with this knowledge)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #65 — CI fix iterations for v0.5.0 validation modules | [notes.md](./ci-cd-precommit-mypy-tomllib-compat.notes.md) |
