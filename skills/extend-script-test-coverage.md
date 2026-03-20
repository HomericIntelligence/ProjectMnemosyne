---

---

name: "Extend Script Test Coverage to 50%+"
description: "Pattern for systematically adding mock-only unit tests to previously untested Python scripts — prioritizing by testability × impact to reach a coverage threshold"
category: testing
date: 2026-03-03
user-invocable: false
---
# Extend Script Test Coverage to 50%+

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-03 |
| Objective | Raise tested script count from 10/34 (29%) to ≥17/34 (≥50%) with mock-only pytest tests |
| Outcome | ✅ 22/34 scripts with tests (65%) — exceeded goal; 453 new tests across 13 files |
| Context | ProjectScylla issue #1162 — follow-up to #1113 which closed the manage_experiment.py gap |

## When to Use This Skill

Use this pattern when:

1. **A repo has many scripts with zero test coverage** and you need to close the gap systematically
2. **A coverage threshold audit** reveals that scripts/ folder is under-tested vs. the threshold
3. **A follow-up issue** extends a previous partial fix (e.g., "add tests for the remaining 17 scripts")
4. **You need to pick the highest-ROI test targets** when you can't test everything at once

**Trigger phrases**:
- "X% of scripts lack unit tests"
- "add tests for the remaining untested scripts"
- "script test coverage audit"
- "follow-up to close the test gap"

## Verified Workflow

### Step 1: Audit the Test Gap

Enumerate all scripts and existing test files to identify the gap:

```bash
# List all testable scripts (exclude shell scripts, __init__.py, README)
ls scripts/*.py scripts/**/*.py | grep -v __init__

# List existing test files for scripts
ls tests/unit/scripts/

# Compute: scripts without corresponding test file = gap
```

**Key output**: A ranked list of untested scripts.

### Step 2: Rank Scripts by Testability × Impact

Score each untested script on two axes and multiply:

| Axis | High (3) | Medium (2) | Low (1) |
|------|----------|-----------|---------|
| **Testability** | Pure functions, no subprocess | Some mocking needed | Subprocess-heavy, no helpers |
| **Impact** | Entry point / pre-commit hook | Frequently invoked | Rarely used utility |

Highest scores get tested first. Minimum viable target = half the total scripts.

### Step 3: Choose the Mock-Only Pattern

For every new test file:
- **No real filesystem writes** — use `tmp_path` or `io.StringIO` for in-memory content
- **No network calls** — mock `requests`, `urllib`, `gh` subprocess
- **No subprocess execution** — patch `subprocess.run`, `subprocess.check_output`
- **Import the module directly** — call functions, assert on return values

Example fixture for a script with a file-reading function:

```python
def test_parse_file(tmp_path):
    f = tmp_path / "input.txt"
    f.write_text("content")
    result = parse_file(str(f))
    assert result == expected_value
```

### Step 4: Test Helper Functions, Not Just `main()`

Each script's internal helper functions carry the highest test value. Structure:

```python
class TestHelperFunction:
    """Tests for the_helper_function() pure logic."""

    def test_happy_path(self):
        assert the_helper_function("valid input") == expected

    def test_edge_case(self):
        assert the_helper_function("") == default_value

    @pytest.mark.parametrize("inp,expected", [
        ("case1", "result1"),
        ("case2", "result2"),
    ])
    def test_parametrized(self, inp, expected):
        assert the_helper_function(inp) == expected
```

### Step 5: Handle Class-Based Scripts (e.g., MarkdownFixer)

For scripts that define a class, instantiate it in a fixture:

```python
@pytest.fixture
def fixer():
    return MarkdownFixer()

class TestMarkdownFixer:
    def test_fix_trailing_spaces(self, fixer):
        result = fixer.fix_trailing_spaces("line   \n")
        assert result == "line\n"
```

### Step 6: Handle Subprocess-Invoking Scripts (e.g., merge_prs.py)

Patch `subprocess.run` at the module level where it is imported:

```python
from unittest.mock import patch, MagicMock

def test_merge_pr_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Merged"

    with patch("scripts.merge_prs.subprocess.run", return_value=mock_result):
        result = merge_pr("123")

    assert result is True
```

### Step 7: Handle Agent Subdirectory Scripts

If the repo has `scripts/agents/*.py`, create a parallel subdirectory:

```
tests/unit/scripts/agents/__init__.py
tests/unit/scripts/agents/test_agent_utils.py
tests/unit/scripts/agents/test_validate_agents.py
```

Make sure the `__init__.py` exists to allow pytest discovery.

### Step 8: Run and Verify

```bash
pixi run python -m pytest tests/unit/scripts/ -v --tb=short
```

All tests should pass. Check that no test calls real external services.

### Step 9: Count and Report

```
Tested scripts before: N
Tested scripts after:  N+K
Total scripts:         M
Coverage:              (N+K)/M * 100%
Goal met:              YES / NO
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Priority Matrix Used (2026-03-03)

| Priority | Script | Testability | Impact | Score |
|----------|--------|-------------|--------|-------|
| 1 | `generate_changelog.py` | 3 | 3 | 9 |
| 2 | `check_type_alias_shadowing.py` | 3 | 3 | 9 |
| 3 | `validate_links.py` | 3 | 2 | 6 |
| 4 | `fix_markdown.py` | 3 | 2 | 6 |
| 5 | `check_readmes.py` | 3 | 2 | 6 |
| 6 | `merge_prs.py` | 2 | 3 | 6 |
| 7 | `check_coverage.py` | 2 | 2 | 4 |
| 8 | `check_tier_config_consistency.py` | 2 | 2 | 4 |
| 9 | `agents/agent_utils.py` | 3 | 3 | 9 |
| 10 | `agents/validate_agents.py` | 2 | 2 | 4 |
| 11 | `fix_table_underscores.py` | 3 | 1 | 3 |
| 12 | `common.py` | 3 | 1 | 3 |

### Test Count per File

| Test File | Script | Tests |
|-----------|--------|-------|
| `test_generate_changelog.py` | `generate_changelog.py` | 29 |
| `test_check_type_alias_shadowing.py` | `check_type_alias_shadowing.py` | 29 |
| `test_validate_links.py` | `validate_links.py` | 19 |
| `test_fix_markdown.py` | `fix_markdown.py` | 24 |
| `test_check_coverage.py` | `check_coverage.py` | 15 |
| `test_check_readmes.py` | `check_readmes.py` | 19 |
| `test_merge_prs.py` | `merge_prs.py` | 17 |
| `test_check_tier_config_consistency.py` | `check_tier_config_consistency.py` | ~20 |
| `agents/test_agent_utils.py` | `agents/agent_utils.py` | 348-line file |
| `agents/test_validate_agents.py` | `agents/validate_agents.py` | 290-line file |
| `test_fix_table_underscores.py` | `fix_table_underscores.py` | ~15 |
| `test_common.py` | `common.py` | ~10 |

### Coverage Impact

| Metric | Before | After |
|--------|--------|-------|
| Scripts with tests | 10/34 (29%) | 22/34 (65%) |
| New test files | 0 | 13 |
| New tests added | 0 | 453 |
| Total suite tests | ~3500 | ~3953 |
| Goal (≥50%) | ❌ | ✅ |

## Verified On

- ProjectScylla (2026-03-03): issue #1162, PR #1343
- Python 3.10+, pytest 7+, pixi environment
