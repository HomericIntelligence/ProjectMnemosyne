---
name: script-test-coverage-pattern
description: "Patterns for adding mock-only unit tests to Python utility scripts \u2014\
  \ covering subprocess-heavy, filesystem-heavy, and pure-function scripts in ProjectScylla.\
  \ Raises scripts/ test coverage from 29% to 65% (10/34 \u2192 22/34 scripts tested)."
category: testing
date: '2026-03-19'
version: 1.0.0
---
# Skill: script-test-coverage-pattern

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Project | ProjectScylla |
| Objective | Extend unit test coverage from 10/34 to ≥17/34 scripts (≥50% goal) using mock-only pattern |
| Outcome | 22/34 scripts tested (65%), 453 new tests across 13 new test files |
| PR | HomericIntelligence/ProjectScylla#1343 |
| Issue | HomericIntelligence/ProjectScylla#1162 |

## When to Use

Use this skill when:
- Adding tests to Python utility scripts that have no existing tests
- Scripts heavily use `subprocess.run`, filesystem operations, or external tools (gh CLI, git)
- You need to bring a scripts/ directory from low (<50%) to high (>50%) test coverage
- Scripts contain pure functions mixed with I/O-heavy entry points
- You want to test only the logic without actually running git/gh/network calls

## Key Insight: Test Strategy by Script Type

### Pure Functions (easiest)
Scripts like `fix_table_underscores.py`, `generate_changelog.py` contain pure functions:
- Import the function directly, call it, assert on the result
- No mocking needed at all

```python
from fix_table_underscores import fix_table_underscores

def test_escapes_bare_underscore():
    content = "column_name & value\n"
    result = fix_table_underscores(content)
    assert r"column\_name" in result
```

### Subprocess-Heavy Scripts (mock subprocess.run)
Scripts like `merge_prs.py`, `generate_changelog.py` call git/gh CLI:
- Mock `subprocess.run` at the module level, not at the stdlib level
- Return a `MagicMock` with `.returncode` and `.stdout` set

```python
from unittest.mock import MagicMock, patch

def test_successful_merge_returns_true():
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("merge_prs.subprocess.run", return_value=mock_result):
        result = merge_pr(42)
    assert result is True
```

### Filesystem-Heavy Scripts (use tmp_path fixture)
Scripts like `validate_links.py`, `check_readmes.py`, `check_type_alias_shadowing.py`:
- Use pytest's built-in `tmp_path` fixture
- Create real temp files/dirs for testing; pytest cleans up automatically

```python
def test_detects_violation_in_file(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("Result = DomainResult\n")
    violations = detect_shadowing(f)
    assert len(violations) == 1
```

### Class-Based Scripts (instantiate and test methods)
Scripts with classes like `MarkdownFixer` in `fix_markdown.py`:
- Instantiate the class with test parameters (verbose=False, dry_run=True)
- Test each method individually
- Use dry_run=True to avoid writing to disk

```python
def test_dry_run_does_not_write(tmp_path: Path) -> None:
    md = tmp_path / "test.md"
    original = "# Heading:\n\n\ncontent\n"
    md.write_text(original)
    f = MarkdownFixer(dry_run=True)
    f.fix_file(md)
    assert md.read_text() == original  # unchanged
```

### Subdirectory Scripts with Package Imports
Scripts in `scripts/agents/` (a sub-package with `__init__.py`):
- `scripts` is in `pythonpath` in `pyproject.toml`, so `agents` is importable as a package
- Import as `from agents.agent_utils import ...`
- Tests go in `tests/unit/scripts/agents/` with an `__init__.py`

```python
# tests/unit/scripts/agents/test_agent_utils.py
from agents.agent_utils import AgentInfo, extract_frontmatter_raw
```

## Verified Workflow

### 1. Audit Which Scripts Lack Tests

```bash
# List all script test files
ls tests/unit/scripts/test_*.py tests/unit/scripts/agents/test_*.py

# Compare against scripts/
ls scripts/*.py scripts/agents/*.py
```

### 2. Prioritize by Complexity + Testability

Prioritize scripts with:
1. Pure functions (no I/O) — easiest wins
2. Class-based design — test each method
3. Functions with simple mocked I/O
4. Avoid: scripts that are 90%+ argparse wiring with no testable logic

### 3. Check pyproject.toml for pythonpath

```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```

This means:
- Top-level scripts: `from generate_changelog import parse_commit`
- Sub-packages: `from agents.agent_utils import extract_frontmatter_raw`
- Full package path also works: `from scripts.check_unit_test_structure import find_violations`

### 4. Understand Script Behavior Before Writing Tests

Read the script's actual implementation to understand edge cases:
- What does the regex actually match? (e.g., `_fix_md040_code_language` modifies closing fences too)
- Does the function return a success value or raise?
- What are the error paths (missing file, bad YAML, non-zero returncode)?

### 5. Write Tests by Logical Function Group (not top-to-bottom)

```
class TestParseCommit:       # Unit test pure parsing
class TestCategorizeCommits: # Unit test business logic
class TestRunGitCommand:     # Mock subprocess
class TestGenerateChangelog: # Integration of the above
```

### 6. Use parametrize for Mapping Tables

Many scripts have `type → category` or `cmd → flag` mappings. Use `@pytest.mark.parametrize`:

```python
@pytest.mark.parametrize("commit_type,category", [
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("perf", "Performance"),
    ...
])
def test_type_to_category_mapping(self, commit_type, category):
    result = categorize_commits([f"abc|{commit_type}: msg|Author"])
    assert category in result
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Final Coverage Numbers

| Metric | Before | After |
|--------|--------|-------|
| Scripts tested | 10/34 (29%) | 22/34 (65%) |
| New test files | 0 | 13 |
| New tests | 0 | 453 |
| Total unit tests | ~3507 | 3960 |

### Scripts Covered in This Session

| Script | Test File | Test Count | Technique |
|--------|-----------|-----------|-----------|
| `generate_changelog.py` | `test_generate_changelog.py` | 29 | Mock subprocess + pure functions |
| `check_type_alias_shadowing.py` | `test_check_type_alias_shadowing.py` | 29 | tmp_path filesystem |
| `validate_links.py` | `test_validate_links.py` | 19 | tmp_path filesystem |
| `fix_markdown.py` | `test_fix_markdown.py` | 24 | Class methods + tmp_path |
| `check_coverage.py` | `test_check_coverage.py` | 15 | Mock + tmp_path XML |
| `check_readmes.py` | `test_check_readmes.py` | 19 | tmp_path filesystem |
| `merge_prs.py` | `test_merge_prs.py` | 10 | Mock subprocess.run |
| `common.py` | `test_common.py` | 7 | Patch get_repo_root |
| `fix_table_underscores.py` | `test_fix_table_underscores.py` | 13 | Pure function, no mocking |
| `check_tier_config_consistency.py` | `test_check_tier_config_consistency.py` | 14 | tmp_path YAML + mock |
| `agents/agent_utils.py` | `agents/test_agent_utils.py` | 29 | In-memory strings |
| `agents/validate_agents.py` | `agents/test_validate_agents.py` | 21 | In-memory strings |

### pyproject.toml pythonpath Configuration

```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```

This enables both:
- `from generate_changelog import parse_commit` (top-level scripts)
- `from agents.agent_utils import AgentInfo` (sub-packages)
- `from scripts.check_unit_test_structure import find_violations` (full path)
