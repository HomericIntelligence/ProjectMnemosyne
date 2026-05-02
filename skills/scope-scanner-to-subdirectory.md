---
name: scope-scanner-to-subdirectory
description: Pattern for refactoring a broad repository-wide Python file scanner to
  target a single subdirectory. Replaces EXCLUDED_PREFIXES deny-list approach with
  a Path.is_relative_to() allow-list helper. Covers implementation, test updates,
  and fixture migration when existing tests break due to new scope.
category: tooling
date: '2026-03-19'
version: 1.0.0
---
# Skill: scope-scanner-to-subdirectory

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-05 |
| Project | ProjectScylla |
| Objective | Restrict a repo-wide AST docstring-fragment scanner to `scylla/` only to reduce signal-to-noise |
| Outcome | Scanner now only processes `scylla/**/*.py`; 12 new scope tests added; all 4333 existing tests pass |
| PR | HomericIntelligence/ProjectScylla#1440 |
| Issue | HomericIntelligence/ProjectScylla#1399 |

## When to Use

Use this skill when:
- A scanner, linter, or auditing script currently uses a deny-list (`EXCLUDED_PREFIXES`) and you want to switch to an allow-list (single directory)
- You need to scope a `Path.rglob("*.py")` scan from "everything minus exclusions" to "one specific directory plus everything under it"
- Tests for a scanner are failing because fixture files are no longer within the scanner's scope after refactoring
- You want to extract the scope logic into a testable helper function

## Key Insight: Allow-List beats Deny-List for Single-Directory Scope

Deny-lists grow over time (`.pixi/`, `build/`, `node_modules/`, `tests/claude-code/`...) and are fragile — any new directory outside the target scope must be explicitly excluded.

Switching to an allow-list with `Path.is_relative_to()` is simpler, smaller, and self-documenting:

```python
# BEFORE: deny-list (fragile, grows over time)
EXCLUDED_PREFIXES = (".pixi/", "build/", "node_modules/", "tests/claude-code/")

def scan_repository(repo_root: Path) -> list[FragmentFinding]:
    for py_file in sorted(repo_root.rglob("*.py")):
        relative_str = str(py_file.relative_to(repo_root)).replace("\\", "/")
        if any(relative_str.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        all_findings.extend(scan_file(py_file, repo_root))

# AFTER: allow-list (simple, correct by construction)
def _is_scylla_file(path: Path, root: Path) -> bool:
    """Return True if path is a .py file under the scylla/ directory."""
    scylla_dir = root / "scylla"
    return path.suffix == ".py" and path.is_relative_to(scylla_dir)

def scan_repository(repo_root: Path) -> list[FragmentFinding]:
    for py_file in sorted(repo_root.rglob("*.py")):
        if not _is_scylla_file(py_file, repo_root):
            continue
        all_findings.extend(scan_file(py_file, repo_root))
```

## Verified Workflow

### 1. Replace the deny-list with an allow-list helper

Extract scope logic into a named helper function so it can be tested independently:

```python
def _is_scylla_file(path: Path, root: Path) -> bool:
    """Return True if path is a .py file under the scylla/ directory."""
    scylla_dir = root / "scylla"
    return path.suffix == ".py" and path.is_relative_to(scylla_dir)
```

`Path.is_relative_to()` is available in Python 3.9+. For older Python, use:
```python
try:
    path.relative_to(scylla_dir)
    return path.suffix == ".py"
except ValueError:
    return False
```

### 2. Update scan_repository to use the helper

```python
def scan_repository(repo_root: Path) -> list[FragmentFinding]:
    """Scan all Python files under scylla/ in the repository."""
    all_findings: list[FragmentFinding] = []
    for py_file in sorted(repo_root.rglob("*.py")):
        if not _is_scylla_file(py_file, repo_root):
            continue
        all_findings.extend(scan_file(py_file, repo_root))
    return all_findings
```

### 3. Export the helper so tests can import it

Import the helper directly in tests for unit testing:

```python
from scripts.check_docstring_fragments import _is_scylla_file
```

### 4. Add TestIsScyllaFile — unit tests for the helper

```python
class TestIsScyllaFile:
    def test_scylla_py_file_accepted(self, tmp_path: Path) -> None:
        scylla_dir = tmp_path / "scylla"
        scylla_dir.mkdir()
        py = scylla_dir / "module.py"
        py.touch()
        assert _is_scylla_file(py, tmp_path)

    def test_scripts_py_file_rejected(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        py = scripts_dir / "tool.py"
        py.touch()
        assert not _is_scylla_file(py, tmp_path)

    def test_non_py_file_in_scylla_rejected(self, tmp_path: Path) -> None:
        scylla_dir = tmp_path / "scylla"
        scylla_dir.mkdir()
        txt = scylla_dir / "README.md"
        txt.touch()
        assert not _is_scylla_file(txt, tmp_path)
```

### 5. Add TestScanRepositoryScope — integration tests

```python
class TestScanRepositoryScope:
    def test_scylla_file_with_fragment_is_found(self, tmp_path: Path) -> None:
        scylla_dir = tmp_path / "scylla"
        scylla_dir.mkdir()
        bad_py = scylla_dir / "module.py"
        bad_py.write_text('"""across multiple tiers."""\nx = 1\n')
        findings = scan_repository(tmp_path)
        assert len(findings) == 1

    def test_scripts_file_not_scanned(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        bad_py = scripts_dir / "tool.py"
        bad_py.write_text('"""across multiple tiers."""\nx = 1\n')
        findings = scan_repository(tmp_path)
        assert findings == []
```

### 6. Fix broken existing tests — move fixture files into scylla/

Existing tests that used `tmp_path / "bad.py"` (at the root of `tmp_path`) will now return no findings because root-level files are outside `scylla/`. Update them:

```python
# BEFORE (broken after scope change)
bad_py = tmp_path / "bad.py"
bad_py.write_text('"""across multiple tiers."""\nx = 1\n')

# AFTER (works with new scope)
scylla_dir = tmp_path / "scylla"
scylla_dir.mkdir()
bad_py = scylla_dir / "bad.py"
bad_py.write_text('"""across multiple tiers."""\nx = 1\n')
```

Also update any hard-coded path assertions:
```python
# BEFORE
assert parsed[0]["file"] == "bad.py"

# AFTER
assert parsed[0]["file"] == "scylla/bad.py"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Changes Made

| File | Change |
| ------ | -------- |
| `scripts/check_docstring_fragments.py` | Removed `EXCLUDED_PREFIXES`; added `_is_scylla_file()` helper; updated `scan_repository()` |
| `tests/unit/scripts/test_check_docstring_fragments.py` | Added `TestIsScyllaFile` (6 tests) + `TestScanRepositoryScope` (6 tests); fixed 4 existing `main()` tests |

### Test Run Results

| Suite | Count | Result |
| ------- | ------- | -------- |
| Targeted test file | 75 passed | Pass |
| Full unit test suite | 4333 passed, 1 skipped | Pass |
| Coverage | 75.17% | Pass (floor: 75%) |
| Pre-commit | All hooks | Pass |
| Live scan | `pixi run python scripts/check_docstring_fragments.py` | Exit 0 |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1399, PR #1440 | Docstring fragment scanner scoped to `scylla/` |
