---
name: multi-domain-audit-remediation
description: 'Workflow for implementing a multi-domain production-grade audit remediation
  plan touching exception handling, logging hygiene, DRY violations, CI alignment,
  and documentation. Use when: (1) an audit report surfaces critical/major/minor issues
  across several independent dimensions simultaneously, (2) converting f-string logging
  anti-patterns and print() calls to structured logger calls across a library codebase,
  (3) consolidating duplicated file discovery logic into a shared utility.'
category: architecture
date: 2026-03-14
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | multi-domain-audit-remediation |
| **Category** | architecture |
| **Source** | ProjectHephaestus 2026-03-14 post-audit remediation v2 |
| **Trigger** | Audit report with critical/major/minor issues across multiple independent domains |

This skill captures the verified workflow for implementing a multi-domain audit remediation plan
in a Python library codebase. It covers the exact sequence for: narrowing broad `except Exception`
clauses, converting f-string logging anti-patterns to lazy `%s` format, replacing library-level
`print()` with `logger`, extracting a shared markdown file discovery utility to eliminate DRY
violations, aligning CI coverage thresholds, and updating documentation to match actual code.

## When to Use

- An audit scorecard surfaces findings across exception handling, logging, DRY, CI/CD, and docs
  simultaneously and you need to work through them in a safe order
- You have `logger.info(f"Found {count} files")` patterns across many files and need to convert
  them to `logger.info("Found %d files", count)` without breaking tests
- Library modules use `print()` for status output that should go through the logging framework
- The same file discovery loop is implemented in 3+ modules; you want to extract a shared utility
- CI `--cov-fail-under` threshold doesn't match `pyproject.toml`'s `fail_under` value
- README/scripts docs reference non-existent files or omit real ones

## Verified Workflow

### Quick Reference

```bash
# Check for f-string logging anti-patterns
grep -rn 'logger\.\(info\|warning\|error\|debug\)(f"' hephaestus/

# Check for print() in library code (not cli/utils.py or main())
grep -rn '^    print(' hephaestus/ | grep -v cli/utils | grep -v 'def main'

# Check broad except clauses
grep -rn 'except Exception' hephaestus/

# After changes: verify ruff noqa comments don't reference un-selected rules
pixi run ruff check hephaestus/ --select=BLE 2>&1 | head -5
# If BLE is not in pyproject.toml select list → don't add # noqa: BLE001

# Run full suite
pixi run pytest tests/unit -v
pre-commit run --all-files
```

### Step 1: Read all files before changing anything

Read every file in the audit's "Files to Modify" list before writing any edits. This prevents
mid-implementation surprises (circular imports, type mismatches, existing logger setup).

Key things to check in each file:
- Does it already import a logger? (If not, add `from hephaestus.logging.utils import get_logger` and `logger = get_logger(__name__)`)
- Does `sys` only appear for `sys.stderr` prints? (If yes, remove `import sys` when replacing those prints with logger)
- Is the file a CLI entry point (`main()` function)? (Keep `print()` in `main()` — those are user-facing)

### Step 2: Convert f-string logging (critical priority)

**Pattern to replace**:
```python
# BEFORE — deferred string interpolation bypassed; extra allocation per call
logger.info(f"Found {count} files in {path}")
logger.warning(f"  ✗ {message}")
logger.error(f"Error accessing repo {repo_name}: {e}")
```

**Pattern to use**:
```python
# AFTER — lazy evaluation, only interpolates if log level is active
logger.info("Found %d files in %s", count, path)
logger.warning("  ✗ %s", message)
logger.error("Error accessing repo %s: %s", repo_name, e)
```

Rules:
- Integer format: `%d`, float: `%.2f`, everything else: `%s`
- Never use `%s` for integers that need formatting (e.g. counts) — use `%d`
- When logging exceptions, always pass `e` as the last argument, not `str(e)`

### Step 3: Replace print() in library code

Distinguish three classes of `print()` calls:

| Class | Action |
| ------- | -------- |
| Library internal status (inside a class method or non-`main()` function) | Replace with `logger.info/warning/error` |
| CLI output in `main()` or `process_path()` | Replace with `logger.info/warning/error` if it's operational, keep as `print()` only for truly interactive terminal prompts |
| Progress bar (`print("\r...", end="", flush=True)`) | Keep as `print()` — this is a terminal UI pattern |

After removing `print()` from a file, check if `sys` is still used:
```python
# Only keep `import sys` if sys.exit() or sys.executable or sys.argv is still present
grep -n 'sys\.' hephaestus/markdown/link_fixer.py
```

### Step 4: Narrow broad except clauses

**Strategy by module type**:

| Module | Recommended exceptions |
| -------- | ---------------------- |
| File I/O (`open`, `read_text`, `write_text`) | `OSError` |
| YAML parsing | Keep `Exception` + add comment (yaml raises undocumented subtypes) |
| Subprocess | `subprocess.CalledProcessError`, `OSError` |
| GitHub API (PyGithub) | Keep `Exception` + comment (PyGithub raises many subtypes) |
| Retry utilities | Keep `Exception` + comment (intentional generic retry) |
| Gzip decompression | `(OSError, EOFError)` |
| Unicode file reads | `(OSError, UnicodeDecodeError)` |
| Path resolution | `(OSError, ValueError)` |

**Critical**: Before narrowing, check what the existing tests raise. Tests often use
`mock.side_effect = Exception("error message")`. If tests use bare `Exception`, either:
- Update the tests to raise the specific type you're narrowing to, OR
- Keep `Exception` with a justifying comment if the actual runtime exceptions are unpredictable

**`# noqa: BLE001` pattern**: Only works if `BLE` is in your ruff `select` list. Check first:
```bash
grep "select" pyproject.toml | grep BLE
```
If `BLE` is not selected, use a plain comment instead:
```python
except Exception as e:  # broad catch intentional: yaml has undocumented exception subtypes
```

### Step 5: Extract shared utilities (DRY fix)

When the same pattern appears in 3+ places, create a shared module:

```python
# hephaestus/markdown/utils.py
from pathlib import Path
from hephaestus.constants import DEFAULT_EXCLUDE_DIRS

def find_markdown_files(
    directory: Path, exclude_dirs: set[str] | frozenset[str] | None = None
) -> list[Path]:
    """Find all markdown files in a directory recursively."""
    if exclude_dirs is None:
        exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    return sorted(
        f for f in directory.rglob("*.md")
        if not any(part in exclude_dirs for part in f.parts)
    )
```

**Type signature gotcha**: If callers can pass `frozenset[str]` (common when the value comes
from a dataclass default), the signature must accept `set[str] | frozenset[str] | None`, not
just `set[str] | None`. mypy will catch this immediately.

Update `__init__.py` to export the new utility, then update all 3 callers.

### Step 6: Align CI coverage threshold

Check for threshold mismatches:
```bash
# pyproject.toml
grep "fail-under\|fail_under" pyproject.toml

# CI workflow
grep "cov-fail-under" .github/workflows/test.yml
```

If they differ, set both to the higher value (the pyproject.toml value is authoritative).

### Step 7: Update documentation

For README.md subpackage listings: list ALL subpackages in the directory tree section.

For scripts/README.md: list the ACTUAL files in the scripts/ directory, not what was there
originally. Verify with `ls scripts/*.py`.

For CONTRIBUTING.md references to non-existent files: either create the file or remove the
reference. Creating a minimal `CODE_OF_CONDUCT.md` using Contributor Covenant v2.1 is the
preferred approach.

### Step 8: Verify end-to-end

```bash
pixi run ruff check hephaestus/ tests/
pixi run ruff format --check hephaestus/ tests/
pixi run mypy hephaestus/
pixi run pytest tests/unit -v --tb=short
pre-commit run --all-files
```

All must pass before committing.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Added `# noqa: BLE001` to intentional broad except clauses | Used `except Exception as e: # noqa: BLE001` to suppress ruff warnings | `BLE` is not in the ruff `select` list — ruff flagged `RUF100` (unused noqa directive) | Always check `pyproject.toml` select list before adding noqa comments |
| Narrowed PyGithub API exceptions to `(OSError, KeyError)` | Changed `except Exception` to `(OSError, KeyError)` in pr_merge.py | 3 tests failed — tests use `mock.side_effect = Exception("API error")` which doesn't match the narrow type | When narrowing exceptions in GitHub API code, keep `Exception` with comment; API libraries raise unpredictable subtypes |
| Added `# noqa: BLE001` comment that was too long | `except Exception as e: # broad catch intentional: yaml raises undocumented exception subtypes` | Line exceeded 100-character limit → ruff E501 error | Keep inline comments short; truncate to stay within line length |
| Removed `sys` import from fixer.py after replacing stderr prints | Deleted `import sys` when `print()` calls to `sys.stderr` were replaced | `sys.exit(0)` in `main()` still requires `sys` | Always grep for all `sys.` usages before removing the import |
| Used `set[str] \| None` type for shared find_markdown_files | `def find_markdown_files(directory, exclude_dirs: set[str] \| None = None)` | mypy error: callers pass `frozenset[str]` from dataclass defaults | Use `set[str] \| frozenset[str] \| None` for exclude_dirs parameters |

## Results & Parameters

**Session outcome**: 24 files modified, 358 tests pass (7 new), 81.66% coverage, all pre-commit hooks green.

| Metric | Before | After |
| -------- | -------- | ------- |
| Tests passing | 351 | 358 |
| Coverage | 81.65% | 81.66% |
| Broad `except Exception` (unjustified) | 21 | 0 |
| F-string logging instances | 35 | 0 |
| `print()` in library code | 44 | 0 |
| Duplicated markdown discovery | 3 locations | 1 shared utility |

**Files modified** (summary):
- Source: `pr_merge.py`, `config_lint.py`, `structure.py`, `readme_commands.py`, `validation/markdown.py`, `fixer.py`, `link_fixer.py`, `downloader.py`, `helpers.py`, `system/info.py`, `version/manager.py`, `git/changelog.py`, `io/utils.py`, `utils/retry.py`
- New: `hephaestus/markdown/utils.py`, `CODE_OF_CONDUCT.md`
- Docs: `README.md`, `scripts/README.md`, `CONTRIBUTING.md`
- Config: `pyproject.toml` (typo fix), `.github/workflows/test.yml` (threshold), `.gitignore`
- `hephaestus/__init__.py` (design doc comment), `hephaestus/markdown/__init__.py` (export)

**CI threshold alignment**:
```yaml
# .github/workflows/test.yml — was 75, now matches pyproject.toml
--cov-fail-under=80
```

**Logging migration pattern** (copy-paste):
```python
# Add to any module that needs logger
from hephaestus.logging.utils import get_logger
logger = get_logger(__name__)

# F-string → lazy format
# BEFORE: logger.info(f"Processing {count} files in {path}")
# AFTER:  logger.info("Processing %d files in %s", count, path)
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Post-audit remediation v2 branch, 2026-03-14 | [notes.md](../references/notes.md) |
