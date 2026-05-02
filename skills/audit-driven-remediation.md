---
name: audit-driven-remediation
description: 'Systematic implementation of findings from a strict repository audit.
  Use when: you have a graded audit report with major/minor findings to remediate
  across CI, source, docs, and packaging.'
category: tooling
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Audit-Driven Remediation Workflow

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-15 |
| **Category** | tooling |
| **Objective** | Implement all actionable findings from a strict 15-section repository audit |
| **Outcome** | All 3 major and 9 minor findings remediated; 366 tests passing, all linting clean |
| **Impact** | CI coverage expanded 6x (1 combo to 6), structured JSON logging added, API return types fixed, backwards compat policy documented |

## Overview

This skill captures the complete workflow for taking a structured audit report (with graded sections, specific file:line references, and severity classifications) and systematically implementing all fixes in a single coordinated pass.

The key insight is that audit findings span multiple dimensions (CI, source code, documentation, packaging) but should be implemented together to avoid cascading test failures and to produce a single coherent changelog entry.

## When to Use

- You have an audit report with section grades (A-F) and specific findings per section
- Findings are classified by severity (Critical/Major/Minor/Nitpick)
- Fixes span multiple file types: workflows, Python source, tests, docs, config
- You want to verify all changes pass CI validation before committing

**Trigger phrases:**

- "Implement the audit findings"
- "Fix the issues from the audit report"
- "Remediate the audit"
- "Apply fixes from the repository review"

## Verified Workflow

### Phase 1: Triage and Task Creation

1. **Parse the audit report** to extract all actionable findings
2. **Create a task per finding** with severity tag and section reference
3. **Set dependencies**: changelog and test tasks block on all code changes

Key principle: treat the audit as a specification. Each finding maps to one task.

```bash
# Identify finding types
# MAJOR -> must fix (CI gaps, missing policies, observability gaps)
# MINOR -> should fix (return types, unnecessary code, stale docs)
# NITPICK -> optional (naming, style preferences)
```

### Phase 2: Implement by Category

Work through findings grouped by type, not by severity. This avoids context switching:

**CI/CD changes first** (test.yml, release.yml):

```yaml
# Expand CI matrix from single to multi-version/OS
matrix:
  os: [ubuntu-latest, macos-latest]
  python-version: ["3.10", "3.11", "3.12"]

# Add tag-version consistency check
- name: Verify tag matches package version
  run: |
    TAG_VERSION="${GITHUB_REF_NAME#v}"
    PKG_VERSION=$(python -c "import re, pathlib; ...")
    [ "$TAG_VERSION" != "$PKG_VERSION" ] && exit 1
```

**Source code changes** (return types, unnecessary code):

```python
# Fix return type asymmetry: functions that raise on failure should return None
def write_file(filepath, content, mode="w") -> None:  # was -> bool
    ...
    # Remove: return True

def ensure_directory(path) -> None:  # was -> bool
    ...
    # Remove: return True
```

**New features** (structured logging):

```python
class JsonFormatter(logging.Formatter):
    """Output structured JSON log records for observability pipelines."""
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }, default=str)

# Add json_format parameter to existing functions
def setup_logging(level=logging.INFO, json_format=False) -> None:
    formatter = JsonFormatter() if json_format else logging.Formatter(LOG_FORMAT)
```

**Documentation and policy** (COMPATIBILITY.md, classifiers):

```markdown
# Backwards Compatibility Policy
## Current Status (v0.x)
- Minor versions (0.x.0) may introduce breaking changes
- Patch versions (0.x.y) contain only bug fixes
- Breaking changes documented in CHANGELOG.md
```

### Phase 3: Update Tests

For each source code change, update corresponding tests:

```python
# Return type change: remove assert on True, add assert on None
def test_returns_none(self, tmp_path):
    assert write_file(tmp_path / "f.txt", "data") is None

# New feature: add dedicated test class
class TestJsonFormatter:
    def test_output_is_valid_json(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(...)
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "INFO"
```

### Phase 4: Validate Everything

Run the full validation stack in order:

```bash
# 1. Formatting (fast, catches import order issues)
pixi run ruff format --check <package>/ tests/ scripts/

# 2. Linting (catches unused imports, line length, etc.)
pixi run ruff check <package>/ tests/ scripts/

# 3. Type checking (catches return type mismatches)
pixi run mypy <package>/

# 4. Unit tests with coverage
pixi run pytest tests/unit --cov=<package> --cov-fail-under=80

# 5. Integration tests
pixi run pytest tests/integration

# 6. Structure check (if applicable)
pixi run python scripts/check_unit_test_structure.py
```

### Phase 5: Changelog and Commit

Write changelog AFTER all changes are validated, not before:

```markdown
## [0.x.y] - YYYY-MM-DD

### Fixed
- Changed write_file/safe_write/ensure_directory to return None instead of True

### Added
- Structured JSON logging via JsonFormatter class
- Tag-version consistency check in release workflow
- COMPATIBILITY.md documenting backwards compatibility policy

### Changed
- CI test matrix expanded: Python 3.10-3.12 on ubuntu + macOS
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Remove `cast()` with no type ignore | Removed `cast(str \| bytes, f.read())` and left bare `f.read()` | mypy reports `no-any-return` because `open()` with string `mode` returns `IO[Any]` | Use `# type: ignore[no-any-return]` instead of `cast()` when the actual return type is correct but mypy can't narrow it |
| Add noqa for security rule not in ruleset | Added `# noqa: S403` to suppress a security hook warning on an import | ruff flagged `RUF100` (unused noqa directive) because S403 isn't in the configured rule set | Check which ruff rules are actually enabled before adding noqa comments; security hooks are separate from ruff |
| Write logging formatter on one line | `def _make_formatter(json_format: bool = False, format_string: str \| None = None) -> logging.Formatter:` | ruff E501: line too long (102 > 100 chars) | Always check line length limit from `pyproject.toml` (100 chars in this project); break function signatures early |
| Use `type: ignore[return-value]` | First attempt to replace `cast()` used wrong mypy error code | mypy reported "Unused type: ignore comment" because the actual error code is `no-any-return`, not `return-value` | Read mypy's actual error message to get the right error code for targeted suppression |

## Results & Parameters

### Changes Made (v0.3.2)

| Category | Count | Examples |
| ---------- | ------- | --------- |
| CI/CD | 2 files | test.yml (3 Python versions x 2 OS), release.yml (tag-version check) |
| Source code | 3 files | io/utils.py (return types, cast removal), logging/utils.py (JsonFormatter), constants.py |
| Tests | 2 files | test_utils.py (io), test_utils.py (logging) |
| Documentation | 3 files | CHANGELOG.md, COMPATIBILITY.md, docs/README.md |
| Config | 1 file | pyproject.toml (classifiers) |

### Validation Results

```
366 passed in 136s
Coverage: 81.70% (threshold: 80%)
ruff check: All checks passed
ruff format: 83 files already formatted
mypy: Success (35 source files)
```

### Key Configuration

```toml
# pyproject.toml - ruff rules that caught issues during remediation
select = ["E", "F", "W", "I", "N", "D", "UP", "S101", "S102", "S105", "S106",
          "B", "SIM", "C4", "C901", "RUF"]
line-length = 100

# mypy strict mode settings that matter for return type changes
disallow_untyped_defs = true
warn_unused_ignores = true
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | v0.3.2 audit remediation (March 2026) | 3 major + 9 minor findings, all resolved |

## References

- Related skill: [quality-audit-implementation](../../quality-audit-implementation/) - Creating tracking issues from audits
- Related skill: [python-repo-audit-implementation](../../python-repo-audit-implementation/) - Running the audit itself
