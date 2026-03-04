# Skill: Module Decomposition with Backward-Compatible Re-exports

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Project | ProjectScylla |
| Objective | Decompose large Python modules (>1,000 lines) into focused single-responsibility submodules while preserving all existing import paths |
| Outcome | Success — `stages.py` 1,534→855 lines, `run_report.py` 1,385→289 lines; 3,999 tests pass |
| Issue | HomericIntelligence/ProjectScylla#1359 |
| PR | HomericIntelligence/ProjectScylla#1392 |

## When to Use

Use this skill when:
- A Python module exceeds ~1,000 lines
- The module contains 2+ distinct logical groups of functions (e.g., "helpers" vs "orchestration")
- Downstream consumers import from the original module path (`from scylla.e2e.stages import X`)
- You cannot change consumer imports (too many files, or external API contract)
- `mypy` uses `implicit_reexport=false` (requires explicit `import X as X` syntax)

**Do NOT use** for class-internal methods — see `extract-method-to-private-methods` skill instead.

## Key Decisions

### 1. Identify cohesive function groups first

Before writing any code, map all top-level functions to logical groups. Good decomposition boundaries:

| Pattern | Signal |
|---------|--------|
| Functions share a common prefix (e.g., `_build_*`, `_finalize_*`) | Extract to one module |
| Functions share a common type they operate on (`ProgressStep`, `ChangeResult`) | Extract together |
| Functions only called from one stage of a pipeline | Extract to that stage's module |
| Functions are pure helpers (no side effects) vs. I/O-heavy functions | Split on this boundary |

### 2. New module naming conventions

| Content | Module name pattern |
|---------|---------------------|
| Private helpers for `foo.py` | `foo_sections.py` or `foo_helpers.py` |
| Stage-specific logic extracted from `stages.py` | `stage_<topic>.py` |
| Hierarchical save functions | `foo_hierarchy.py` |
| Process metrics helpers | `stage_process_metrics.py` |

### 3. The `import X as X` re-export pattern (required for mypy)

When `mypy` runs with `implicit_reexport=false`, a bare `from module import X` does NOT
re-export `X` — external consumers get `Module has no attribute 'X'` errors.

Use the explicit re-export syntax:

```python
# In the original file (stages.py)
from scylla.e2e.stage_finalization import (
    stage_cleanup_worktree as stage_cleanup_worktree,  # re-exported
    stage_finalize_run as stage_finalize_run,           # re-exported
    stage_write_report as stage_write_report,           # re-exported
)
```

This satisfies mypy AND keeps all existing consumer imports working.

### 4. Remove only the bodies, keep the re-exports

The original module should:
1. Remove the extracted function bodies verbatim
2. Add re-export imports (step 3 above)
3. Remove any top-level imports that are no longer used locally
4. Keep any imports still needed by remaining functions

**Danger**: Forgetting to remove now-unused top-level imports will cause ruff `F401` (unused import) errors.

### 5. Handle circular imports via TYPE_CHECKING

New modules that need to reference the original module's types (e.g., `RunContext` defined in `stages.py`) must use:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scylla.e2e.stages import RunContext  # only used for type hints
```

This avoids circular imports at runtime since `TYPE_CHECKING` is `False` at runtime.

## Verified Workflow

### Step 1 — Measure and map

```bash
wc -l scylla/e2e/stages.py scylla/e2e/run_report.py
grep -n "^def \|^class " scylla/e2e/stages.py
```

List all functions. Group them logically. Estimate line ranges.

### Step 2 — Create the new module(s) first

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

### Step 3 — Update the original file

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

### Step 4 — Verify imports before running tests

```bash
pixi run python -c "from scylla.e2e.stages import stage_finalize_run, RunContext; print('OK')"
pixi run python -c "from scylla.e2e.run_report import save_subtest_report; print('OK')"
```

### Step 5 — Run tests

```bash
pixi run python -m pytest tests/unit/ -x -q
```

### Step 6 — Run pre-commit (expect auto-fixes on first run)

```bash
SKIP=audit-doc-policy pre-commit run --files <all modified/new files>
# Ruff will auto-fix import order and unused imports — run again to confirm clean
SKIP=audit-doc-policy pre-commit run --files <all modified/new files>
```

**Expect 2 rounds**: ruff reformats on round 1, passes on round 2. Normal behavior.

### Step 7 — Verify final line counts

```bash
wc -l scylla/e2e/stages.py scylla/e2e/run_report.py
# Both must be < 1,000
```

## Results & Parameters

### Files created in ProjectScylla#1392

| New File | Lines | Extracted Content |
|----------|-------|-------------------|
| `scylla/e2e/stage_process_metrics.py` | 309 | `_get_diff_stat`, `_parse_diff_numstat_output`, `_load_process_metrics_from_run_result`, `_build_change_results`, `_build_progress_steps`, `_finalize_change_results`, `_finalize_progress_steps` |
| `scylla/e2e/stage_finalization.py` | 438 | `stage_execute_judge`, `stage_finalize_run`, `stage_write_report`, `stage_cleanup_worktree` |
| `scylla/e2e/run_report_sections.py` | 600 | All `_generate_*` and `_format_*` private helpers + `_get_workspace_files` |
| `scylla/e2e/run_report_hierarchy.py` | 599 | `save_run_report_json`, `save_subtest_report`, `save_tier_report`, `save_experiment_report`, `generate_tier_summary_table`, `generate_experiment_summary_table` |

### Before / After

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| `stages.py` | 1,534 | 855 | −44% |
| `run_report.py` | 1,385 | 289 | −79% |

### Ruff rules triggered

| Rule | Context | Fix |
|------|---------|-----|
| `F401` | Unused imports left after body deletion | Remove the import |
| `I001` | Import order changed by adding new re-exports | Ruff auto-fixes |

## Failed Attempts

### Attempt: Underestimating line count reduction

**What happened**: The plan predicted `stages.py` would reach ~900 lines after extracting
`stage_process_metrics.py` and `stage_finalization.py`. Actual result was 1,016 — still over 1,000.

**Root cause**: `stage_execute_judge` (183 lines) was not included in the plan's extraction list.

**Fix**: Also extracted `stage_execute_judge` into `stage_finalization.py`. This brought `stages.py`
to 855 lines.

**Lesson**: After the first extraction pass, re-measure with `wc -l` and check the largest remaining
functions with `grep -n "^def " file.py`. If still over 1,000, identify the next largest function
and extract it too.

### Attempt: Extracting without checking circular import risk

**What happened**: `stage_finalization.py` needed `RunContext` (defined in `stages.py`), which imports
from `stage_finalization.py`. This would have been a circular import.

**Fix**: Used `TYPE_CHECKING` guard:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scylla.e2e.stages import RunContext
```

With `from __future__ import annotations`, all type annotations are strings at runtime — no import
needed at runtime.

**Lesson**: Always check if new modules need types from the original module. If yes, use
`TYPE_CHECKING` + `from __future__ import annotations`.

### Attempt: Forgetting `import X as X` syntax for private functions

**What happened**: Initially used bare `from scylla.e2e.stage_process_metrics import _get_diff_stat`
in `stages.py`. This would fail mypy `implicit_reexport=false` for callers doing
`from scylla.e2e.stages import _get_diff_stat`.

**Fix**: Always use `import X as X` for re-exports:
```python
from scylla.e2e.stage_process_metrics import (
    _get_diff_stat as _get_diff_stat,
)
```

**Note**: Private functions (leading `_`) still need re-export if any other module imports them
from the original location. Check with `grep -r "from scylla.e2e.stages import" scylla/ tests/`.
