# Parallel Test Generation for Module Decomposition

| Field | Value |
|-------|-------|
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

## Failed Attempts

### 1. Regex-based auto-docstring insertion
**What:** Used regex to add docstrings to test methods missing them.
**Why it failed:** The regex `r'^( +)(def test_\w+...)` matched methods that already had docstrings from the agent, producing duplicate docstrings with mismatched indentation. Ruff reported `invalid-syntax: Unexpected indentation`.
**Fix:** Remove duplicate docstrings by scanning for consecutive docstring lines (ignoring blank lines between them).
**Lesson:** Check if docstring already exists before inserting. Better: instruct agents to include docstrings in the first place.

### 2. Bulk variable rename for RUF059 (unused unpacked vars)
**What:** `content.replace(', na,', ', _na,')` to prefix unused tuple elements with `_`.
**Why it failed:** Renamed the unpacking variable but not the `assert na is True` usage on later lines, creating `F821 Undefined name 'na'` errors.
**Fix:** Either rename both unpacking AND usage, or use `ruff --fix --unsafe-fixes --select RUF059` which handles it correctly.
**Lesson:** Never do partial renames with string replace. Use ruff's built-in unsafe fixes for RUF059.

### 3. Removing type: ignore comments preemptively
**What:** Removed `# type: ignore[arg-type]` and `# type: ignore[misc]` based on mypy reporting `unused-ignore`.
**Why it failed:** The `unused-ignore` was only reported in one mypy configuration; the `arg-type` errors were real when checked by pre-commit's mypy hook (different strictness settings).
**Fix:** Only remove `type: ignore` comments after verifying with the **pre-commit mypy hook**, not standalone mypy.
**Lesson:** Pre-commit mypy may have different settings than standalone mypy. Always verify removals against the hook.

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
|-------|-------|----------|
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
