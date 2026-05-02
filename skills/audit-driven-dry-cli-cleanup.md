---
name: audit-driven-dry-cli-cleanup
description: "Fix DRY violations and remove legacy CLI after strict repo audit. Use when: (1) audit identifies duplicate functions across modules, (2) legacy CLI needs removal with dependent module preservation, (3) doc consistency hooks need updating after content changes."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags: []
---

# Audit-Driven DRY Consolidation and Legacy CLI Removal

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Fix major issues from strict repo audit: DRY violations (5 duplicate functions), legacy CLI removal, CHANGELOG, stale README counts |
| **Outcome** | PR #1545 merged: -1063 lines, +67 added, 17 files changed. 4772 tests pass, 77.67% coverage. |

## When to Use

- Audit identifies duplicate private functions (`_has_valid_*`) across multiple modules
- Legacy CLI module needs removal but contains shared utilities used by other modules
- README has hardcoded counts that drift from reality
- Doc consistency pre-commit hooks need updating after content policy changes
- CHANGELOG has no version history

## Verified Workflow

### Quick Reference

```bash
# Find duplicate function definitions across a Python package
grep -rn "^def _function_name" package/ --include="*.py"

# Find all importers of a function to map the dependency graph
grep -rn "from.*import.*_function_name" package/ tests/ --include="*.py"

# Verify no references remain after deletion
grep -rn "old_module\.old_function\|old/module" . --include="*.py" --include="*.md"
```

### Detailed Steps

#### 1. Find DRY Violations

Identify duplicate function names:
```bash
grep -rn "^def " package/ --include="*.py" | \
  awk -F'def ' '{print $2}' | awk -F'(' '{print $1}' | \
  sort | uniq -d
```

For each duplicate, read ALL implementations to determine:
- Which is most thorough (JSON validation > file existence checks)
- Which uses shared helpers (e.g., `get_agent_result_file()` from paths.py)
- Which has logging
- The canonical version is the one already imported by the most consumers

#### 2. Consolidate DRY: Import Instead of Duplicate

For each duplicate function:

**Step A**: Map the dependency graph (who imports from where):
```bash
grep -rn "from.*import.*_has_valid_agent_result" package/ tests/
```

**Step B**: Identify the canonical module (most importers, best implementation).

**Step C**: In each file with a duplicate, replace the local definition with an import:
```python
# Delete the local def _has_valid_agent_result(): ... block
# Add import from canonical module
from package.canonical_module import _has_valid_agent_result
```

**Step D**: Update test imports that referenced the duplicate location:
```python
# Before:
from package.old_module import _has_valid_agent_result
# After:
from package.canonical_module import _has_valid_agent_result
```

**Step E**: If tests were written for the weaker implementation (e.g., file-existence-only check), update test fixtures to satisfy the canonical version (e.g., add required JSON fields).

#### 3. Remove Legacy CLI with Module Preservation

When a CLI module contains shared utilities:

**Step A**: Identify shared dependencies:
```bash
grep -rn "from package.cli" package/ --include="*.py"
```

**Step B**: Move shared modules to their domain home before deleting the CLI:
```bash
# progress.py used by e2e/orchestrator.py -> move to e2e/
cp package/cli/progress.py package/e2e/progress.py
```

**Step C**: Update all imports:
```bash
# Find and replace import paths
grep -rn "package.cli.progress" . --include="*.py"
# Update each occurrence
```

**Step D**: Remove CLI files and entry points:
- Delete `cli/main.py`, `cli/__init__.py`
- Remove `[project.scripts]` from pyproject.toml
- Delete test files for the removed CLI
- Move/update test files for preserved modules
- Run `pixi install` to regenerate lock file after pyproject.toml change

#### 4. Update Doc Consistency Hooks

When removing hardcoded values from docs, update the pre-commit hooks that enforce them:

```python
# Before: error when no count found
if not raw_matches:
    return ["README.md: No test count mention found"]

# After: accept missing count (users run pytest --collect-only)
if not raw_matches:
    return []
```

Update the corresponding test:
```python
# Before:
def test_no_test_count_in_readme_returns_error(self, ...):
    assert len(errors) == 1

# After:
def test_no_test_count_in_readme_is_acceptable(self, ...):
    assert len(errors) == 0
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Replace-all on result.json fixtures | Used replace_all to update `'{"exit_code": 0}'` in test fixtures | Some fixtures had different indentation; replace_all worked but ruff reformatted | Always run ruff format after bulk edits |
| Delete CLI dir before moving progress.py | Tried rmdir on cli/ before copying progress.py out | Directory not empty error | Copy shared modules out first, then delete the directory |
| Initial pre-commit run after DRY fix | Mypy failed because tests still imported from old module | Tests imported `_has_valid_agent_result` from `regenerate` (deleted) | Always check test imports after moving/deleting source functions |

## Results & Parameters

### PR #1545 Stats

| Metric | Value |
| -------- | ------- |
| Files changed | 17 |
| Lines removed | 1,063 |
| Lines added | 67 |
| Tests passing | 4,772 |
| Coverage | 77.67% |
| Pre-commit hooks | 23/23 pass |

### Functions Consolidated

| Function | Copies Before | Canonical Module | Copies After |
| ---------- | -------------- | ------------------ | ------------- |
| `_has_valid_agent_result()` | 3 (agent_runner, regenerate, rerun_judges) | `agent_runner.py` | 1 |
| `_has_valid_judge_result()` | 2 (judge_runner, regenerate) | `judge_runner.py` | 1 |

### Files Removed

| File | Reason |
| ------ | -------- |
| `scylla/cli/main.py` | Legacy Click CLI replaced by manage_experiment.py |
| `scylla/cli/__init__.py` | Only re-exported progress (moved to e2e/) |
| `scylla/cli/progress.py` | Moved to `scylla/e2e/progress.py` |
| `tests/unit/cli/test_cli.py` | Tests for removed CLI |
| `tests/unit/cli/__init__.py` | Empty test package |

### Weaker vs Stronger Implementation

When consolidating duplicates, the weaker `rerun_judges.py` version only checked file existence:
```python
# WEAK (deleted): only checks files exist
return agent_output.exists() and agent_result.exists()
```

The canonical `agent_runner.py` version validates JSON content:
```python
# STRONG (kept): validates JSON fields + token stats
data = json.loads(result_file.read_text())
required_fields = ["exit_code", "token_stats", "cost_usd"]
if not all(field in data for field in required_fields):
    return False
```

Tests that used the weak version needed fixture updates to include required JSON fields.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Strict repo audit major issues | PR #1545: DRY, CLI removal, CHANGELOG, README |
