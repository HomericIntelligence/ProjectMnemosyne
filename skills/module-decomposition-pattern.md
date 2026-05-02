---
name: module-decomposition-pattern
description: 'Decompose large Python modules (1000+ lines) into focused sub-modules
  while preserving backward compatibility, updating all import sites or re-exporting
  from the original, and fixing mock patch targets in tests. Use when a single file
  has 4+ logical clusters of functions with distinct responsibilities.

  '
category: architecture
date: 2026-03-10
version: 2.0.0
user-invocable: false
---
# Skill: Module Decomposition Pattern

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-10 |
| Project | ProjectScylla |
| Objective | Decompose `scylla/e2e/llm_judge.py` (1,488 lines, 35 functions) into 4 focused modules + slimmed orchestrator |
| Outcome | Success - 142-line orchestrator + 4 modules, all 4,788 tests pass, all pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectScylla#1446 |

## When to Use

Use this skill when:
- A Python module exceeds ~500 lines with 4+ logical clusters of functions
- Functions within the module have distinct responsibilities (e.g., pipeline execution vs. log saving)
- Other modules use lazy imports (`from X import Y` inside function bodies) to access private functions
- The module has a large corresponding test file with many `patch()` targets
- You want to improve navigability without changing any behavior

## Key Decisions

### 1. Update import sites vs. re-export from original module

**Choose "update import sites"** (Option 2) when:
- There are a manageable number of import sites (< 20)
- Imports are lazy (inside function bodies), making updates safe
- You want to avoid the re-export anti-pattern

**Choose "re-export from original"** (Option 1) when:
- The module is a public API with many external consumers
- You cannot enumerate all import sites (e.g., third-party packages)
- `mypy` uses `implicit_reexport=false` (requires explicit `import X as X` syntax — see below)

#### The `import X as X` re-export pattern (required for mypy)

When `mypy` runs with `implicit_reexport=false`, a bare `from module import X` does NOT
re-export `X` — external consumers get `Module has no attribute 'X'` errors.

Use the explicit re-export syntax:

```python
# In the original file (e.g., stages.py)
from scylla.e2e.stage_finalization import (
    stage_cleanup_worktree as stage_cleanup_worktree,  # re-exported
    stage_finalize_run as stage_finalize_run,           # re-exported
    stage_write_report as stage_write_report,           # re-exported
)
```

This satisfies mypy AND keeps all existing consumer imports working.

### 2. Handle circular imports with TYPE_CHECKING

When decomposing, circular imports often arise (e.g., Module A defines a model, Module B returns it, Module A calls Module B). Solve with:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from original_module import MyModel

def my_function() -> MyModel:  # String annotation via __future__
    from original_module import MyModel  # Runtime import
    return MyModel(...)
```

### 3. Keep public API exports in the original module

Models and orchestrator functions that are part of the public API (`__init__.py` exports) stay in the original module. Only move private implementation functions.

### 4. Identify cohesive function groups first

Before writing any code, map all top-level functions to logical groups. Good decomposition boundaries:

| Pattern | Signal |
| --------- | -------- |
| Functions share a common prefix (e.g., `_build_*`, `_finalize_*`) | Extract to one module |
| Functions share a common type they operate on (`ProgressStep`, `ChangeResult`) | Extract together |
| Functions only called from one stage of a pipeline | Extract to that stage's module |
| Functions are pure helpers (no side effects) vs. I/O-heavy functions | Split on this boundary |

### 5. New module naming conventions

| Content | Module name pattern |
| --------- | --------------------- |
| Private helpers for `foo.py` | `foo_sections.py` or `foo_helpers.py` |
| Stage-specific logic extracted from `stages.py` | `stage_<topic>.py` |
| Hierarchical save functions | `foo_hierarchy.py` |
| Process metrics helpers | `stage_process_metrics.py` |

## Verified Workflow

### Step 1 - Map all import sites

Before writing any code, find every file that imports from the target module:

```bash
grep -rn "from package.module import" --include="*.py"
grep -rn 'patch("package.module.' --include="*.py"
```

Categorize each import into the target cluster (pipeline, context, execution, artifacts, etc.).

### Step 2 - Identify clusters and cross-dependencies

Group functions by responsibility. Check for cross-cluster calls:

```bash
grep -n "^def \|^class " module.py
```

Order extraction: start with modules that have no cross-cluster dependencies (leaf modules first).

### Step 3 - Create new modules one at a time

For each new module:
1. Write the file with moved functions and their imports
2. Update source import sites (`from new_module import func`)
3. Update test import sites (both `from` imports AND `patch()` targets)
4. Run tests: `pytest tests/unit/relevant/ -x -q`

### Step 4 - Update mock patch targets (CRITICAL)

`patch("old.module.func")` must change to `patch("new.module.func")`. Search for ALL occurrences:

```bash
grep -rn 'patch("package.old_module.' tests/
```

**Common mistake**: Only updating `test_old_module.py` but missing patch targets in `test_other.py` files that also mock functions from the decomposed module.

### Step 5 - Fix mypy type errors

Moving functions that return types defined in the original module often causes `no-any-return` errors. Fix with `TYPE_CHECKING` imports and proper return type annotations instead of `-> Any`.

### Step 6 - Final verification

```bash
pre-commit run --all-files
pytest tests/ -x -q
wc -l original_module.py new_module_*.py
```

---

### Re-export Approach (Alternative Workflow)

Use this when preserving all existing import paths (Option 1 from Key Decision #1).

#### Step 1 — Measure and map

```bash
wc -l scylla/e2e/stages.py scylla/e2e/run_report.py
grep -n "^def \|^class " scylla/e2e/stages.py
```

List all functions. Group them logically. Estimate line ranges.

#### Step 2 — Create the new module(s) first

Write the new module as a standalone file with:
- Its own module docstring explaining what it contains
- All required imports (NOT inherited from the original module)
- Verbatim copies of the extracted functions

**Critical**: The new module is self-contained. It cannot import from the original module
(circular import risk). If it needs a type defined in the original, use `TYPE_CHECKING`.

```python
# stage_process_metrics.py
"""Process metrics helpers extracted from stages.py."""

from __future__ import annotations
import json
import subprocess
from pathlib import Path
from scylla.metrics.process import ChangeResult, ProgressStep  # direct imports

def _get_diff_stat(workspace: Path) -> dict[str, tuple[int, int]]:
    ...
```

#### Step 3 — Update the original file with re-exports

In the original file:
1. Add re-export imports at the top (after existing imports)
2. Delete the function bodies (use editor's exact text match)
3. Remove unused imports that the deleted functions relied on

```python
# stages.py — add re-exports
from scylla.e2e.stage_process_metrics import (
    _get_diff_stat as _get_diff_stat,
    _build_change_results as _build_change_results,
    ...
)

# stages.py — remove these (now unused by remaining code)
# import subprocess  ← still used by stage_generate_replay, keep it
# import dataclasses ← only used by extracted stage_finalize_run, remove it
```

**Tip**: After deleting function bodies, run `grep -n "ProcessMetrics\|dataclasses\." stages.py`
to verify which removed imports are still referenced.

**Danger**: Forgetting to remove now-unused top-level imports will cause ruff `F401` (unused import) errors.

#### Step 4 — Verify imports before running tests

```bash
pixi run python -c "from scylla.e2e.stages import stage_finalize_run, RunContext; print('OK')"
pixi run python -c "from scylla.e2e.run_report import save_subtest_report; print('OK')"
```

#### Step 5 — Run tests

```bash
pixi run python -m pytest tests/unit/ -x -q
```

#### Step 6 — Run pre-commit (expect auto-fixes on first run)

```bash
SKIP=audit-doc-policy pre-commit run --files <all modified/new files>
# Ruff will auto-fix import order and unused imports — run again to confirm clean
SKIP=audit-doc-policy pre-commit run --files <all modified/new files>
```

**Expect 2 rounds**: ruff reformats on round 1, passes on round 2. Normal behavior.

#### Step 7 — Verify final line counts

```bash
wc -l scylla/e2e/stages.py scylla/e2e/run_report.py
# Both must be < 1,000
```

## Results & Parameters

### Files created/modified (Issue #1446 — update import sites approach)

| File | Lines | Role |
| ------ | ------- | ------ |
| `llm_judge.py` (was 1,488) | 142 | Orchestrator: JudgeResult model + run_llm_judge() |
| `build_pipeline.py` (new) | 548 | BuildPipelineResult + 13 pipeline functions |
| `judge_context.py` (new) | 334 | 7 workspace context/assembly functions |
| `judge_execution.py` (new) | 259 | 3 judge execution/parsing functions |
| `judge_artifacts.py` (new) | 295 | 10 log/script saving functions |

### Import sites updated (Issue #1446)

| File | Import changed |
| ------ | --------------- |
| `stages.py` | 5 lazy imports |
| `stage_finalization.py` | 2 lazy imports |
| `rerun_judges.py` | 1 lazy import |
| `experiment_setup_manager.py` | 1 lazy import |
| `regenerate.py` | 1 lazy import |
| `judge_runner.py` | 1 TYPE_CHECKING import |
| `subtest_executor.py` | 2 imports |
| `__init__.py` | 0 (JudgeResult/run_llm_judge stayed) |

### Test files updated (Issue #1446)

| File | Changes |
| ------ | --------- |
| `test_llm_judge.py` | Import block rewritten (4 source modules), 12 patch targets updated |
| `test_stages.py` | 10 patch targets updated |
| `test_stage_finalization.py` | 2 patch targets updated |
| `test_experiment_setup_manager.py` | 4 patch targets updated |
| `test_baseline_regression.py` | 1 import updated |
| `test_subtest_executor.py` | 1 import updated |

### Files created in Issue #1359 / PR #1392 — re-export approach

| New File | Lines | Extracted Content |
| ---------- | ------- | ------------------- |
| `scylla/e2e/stage_process_metrics.py` | 309 | `_get_diff_stat`, `_parse_diff_numstat_output`, `_load_process_metrics_from_run_result`, `_build_change_results`, `_build_progress_steps`, `_finalize_change_results`, `_finalize_progress_steps` |
| `scylla/e2e/stage_finalization.py` | 438 | `stage_execute_judge`, `stage_finalize_run`, `stage_write_report`, `stage_cleanup_worktree` |
| `scylla/e2e/run_report_sections.py` | 600 | All `_generate_*` and `_format_*` private helpers + `_get_workspace_files` |
| `scylla/e2e/run_report_hierarchy.py` | 599 | `save_run_report_json`, `save_subtest_report`, `save_tier_report`, `save_experiment_report`, `generate_tier_summary_table`, `generate_experiment_summary_table` |

### Before / After (Issue #1359 / PR #1392)

| File | Before | After | Reduction |
| ------ | -------- | ------- | ----------- |
| `stages.py` | 1,534 | 855 | −44% |
| `run_report.py` | 1,385 | 289 | −79% |

### Ruff rules triggered

| Rule | Context | Fix |
| ------ | --------- | ----- |
| `F401` | Unused imports left after body deletion when using re-export approach | Remove the import |
| `I001` | Import order changed by adding new re-exports | Ruff auto-fixes |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1446 - llm_judge.py decomposition (update import sites) | [notes.md](../references/notes.md) |
| ProjectScylla | Issue #1359, PR #1392 - stages.py/run_report.py decomposition (re-export) | [notes.md](../references/notes.md) |
