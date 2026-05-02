---
name: parallel-test-generation-for-module-decomposition
description: "Parallel Test Generation for Module Decomposition"
category: architecture
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Parallel Test Generation for Module Decomposition

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-13 |
| **Objective** | Generate test files for 4 newly extracted modules in parallel using sub-agents |
| **Outcome** | 179 tests created across 4 files, all passing, PR merged |
| **Project** | ProjectScylla |
| **Issue** | #1446 |

## When to Use

- Decomposing a large module into multiple smaller modules
- Need to create independent test files for each extracted module
- Test files have no dependencies on each other (can be written in parallel)
- Each module has clear boundaries (distinct imports, functions, classes)

## Verified Workflow

1. **Audit stale references first**: `grep -r '@patch.*old_module\.' tests/` before writing tests
2. **Read all source modules** in parallel to understand the full API surface
3. **Launch parallel agents** (one per test file) with detailed prompts including:
   - Full list of functions/classes to test
   - Import paths
   - Convention examples from existing test files (docstrings, fixtures, mock patterns)
   - Target test count
4. **Fix lint/type issues** after agent output:
   - Run `ruff check --fix --unsafe-fixes` for auto-fixable issues
   - Fix mypy `type: ignore` comments separately
5. **Run full test suite** + pre-commit before committing

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Agent Prompt Template for Test File Generation

Key elements to include in agent prompts:
- **Module functions with signatures** (not just names)
- **Import statement** to copy-paste
- **Convention requirements**: `from __future__ import annotations`, `# noqa: S101`, type hints, `tmp_path` fixture
- **Test class grouping** pattern: one class per function/class
- **Mock target paths**: `scylla.e2e.module_name.subprocess.run` (not `subprocess.run`)
- **Target test count**: gives agents a scope signal

### Performance

| Agent | Tests | Duration |
| ------- | ------- | ---------- |
| test_build_pipeline.py | 73 | ~106s |
| test_judge_context.py | 46 | ~147s |
| test_judge_artifacts.py | 35 | ~99s |
| test_judge_execution.py | 25 | ~175s |
| **Total** | **179** | **~175s (wall clock, parallel)** |

### Post-Agent Fix Sequence

1. Remove duplicate docstrings (scan for consecutive `"""..."""` lines)
2. `ruff check --fix --unsafe-fixes` (handles RUF059, C408, etc.)
3. `ruff format` (formatting)
4. Verify `type: ignore` comments against pre-commit mypy
5. Run full test suite
6. Run pre-commit on all changed files
