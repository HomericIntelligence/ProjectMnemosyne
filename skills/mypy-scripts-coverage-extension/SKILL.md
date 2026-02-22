# Mypy Scripts Coverage Extension Skill

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Issue** | #765 - Extend mypy hook to cover scripts/ with type checking |
| **Objective** | Remove the blanket `ignore_errors = true` mypy override for `scripts.*` so all scripts are type-checked in CI |
| **Outcome** | ✅ Success — single 4-line deletion in `pyproject.toml`, all 37 script files already type-clean |

## When to Use

Use this skill when:

- You want to extend mypy coverage from a module with a blanket `ignore_errors = true` override to
  full enforcement
- You have a `[[tool.mypy.overrides]]` block in `pyproject.toml` that suppresses a whole directory
  (e.g., `scripts.*`, `tests.*`) and want to promote it to full checking
- You are following up on a prior issue that added per-directory mypy suppression as a "we'll fix
  this later" placeholder
- You need to verify whether scripts are already type-clean before removing an override

## Key Insight: Triage First, Then Remove

Always run mypy against the directory **before** removing the override to measure actual error count:

```bash
# Temporarily remove the override from pyproject.toml, then:
pixi run mypy scripts/ 2>&1
# If "Success: no issues found" — just commit the removal, no script fixes needed
# If errors appear — fix them incrementally before removing the override
```

In this session the scripts were already clean — the override was a precautionary placeholder
from when mypy was first adopted, not the result of actual errors.

## Verified Workflow

### 1. Read the Issue and Understand Scope

```bash
gh issue view 765 --comments
```

The issue plan specified: evaluate which scripts can be type-checked, add incrementally, then
remove the `scripts.*` override. Read any existing plan comments before starting.

### 2. Find the Override in pyproject.toml

```bash
grep -n "scripts" pyproject.toml
# Output: module = "scripts.*"  and  ignore_errors = true
```

The full block to remove looks like:

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```

### 3. Remove the Override and Triage

Remove the 4-line `[[tool.mypy.overrides]]` block for `scripts.*`, then run:

```bash
pixi run mypy scripts/
```

If the output is `Success: no issues found in N source files`, no script modifications are
needed — proceed directly to step 4.

If errors appear, fix them per-file using proper type annotations. Only add narrow per-script
overrides (e.g., `module = "scripts.specific_script"`) as an absolute last resort.

### 4. Verify with Pre-commit Hook

```bash
pre-commit run mypy-check-python --all-files
# Expected: Passed
```

### 5. Run the Full Test Suite

```bash
pixi run python -m pytest tests/ -v
# Verify: all tests pass, coverage still above threshold (73%)
```

### 6. Commit and PR

Only two files change when the scripts are already clean:
- `pyproject.toml` — remove the 4-line override block
- `pixi.lock` — auto-updated sha256 of the scylla package (side effect of pyproject.toml change)

```bash
git add pyproject.toml pixi.lock
git commit -m "feat(mypy): Extend mypy coverage to scripts/ by removing blanket override"
gh pr create --title "feat(mypy): Extend mypy coverage to scripts/ ..." \
  --body "Closes #765"
gh pr merge --auto --rebase
```

## Failed Attempts

### No failures in this session

The scripts were already type-clean. The task completed as a pure configuration change
(4-line deletion) with no script modifications required. The triage step eliminated any
possibility of needing incremental fixes.

### Anticipated but Unnecessary Work

The issue plan predicted significant effort: per-script triage, incremental fixes for
`scripts/common.py`, `scripts/validate_model_configs.py`, etc., and possibly per-script
overrides for dynamic scripts. None of this was needed because the scripts were written
with type hints from the start.

**Lesson**: Always triage actual errors before assuming fixes are needed. The override
may be a placeholder rather than a signal of real type errors.

## Results & Parameters

```
Files checked (scripts/): 37 source files
Mypy result: Success: no issues found
pyproject.toml lines removed: 4
Script files modified: 0
Pre-commit result: Passed
Tests: 2396 passed, coverage 74.15% (above 73% threshold)
PR: https://github.com/HomericIntelligence/ProjectScylla/pull/939
```

### pyproject.toml Block Removed

```toml
[[tool.mypy.overrides]]
module = "scripts.*"
# Skip type checking for scripts - focus on source code first
ignore_errors = true
```

### Related Skills

- `mypy-living-baseline` — For tracking and enforcing error count reductions over time
  (use when errors exist; this skill is for when overrides are safe to remove entirely)
