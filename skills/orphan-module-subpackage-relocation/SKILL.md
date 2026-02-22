# Orphan Module Sub-Package Relocation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Move `scylla/orchestrator.py` (510 lines, `EvalOrchestrator`) from the package root into `scylla/e2e/orchestrator.py` to restore consistent sub-package structure |
| **Outcome** | Complete success — 2436 tests pass (74.15% coverage), all pre-commit hooks pass, PR #958 created and auto-merge enabled |
| **Category** | Architecture / Structural Refactor |
| **Related Issues** | #847 |

## When to Use This Skill

Use when:

- A module sits at the package root but logically belongs in an existing sub-package
- A code quality audit identifies structural inconsistencies
- Every other module lives in a sub-package but one exception exists
- Moving follows KISS/YAGNI — no new sub-packages needed, just relocation

**Triggers:**

- Quality audit finds "orphaned" module at root level
- Issue title contains "Relocate", "Move", or "Reorganize" for a single file
- Module imports heavily from one sub-package (clear fit)
- Issue proposes Option A (existing sub-package) vs Option B (new sub-package)

## Verified Workflow

### Phase 1: Pre-Flight Discovery

1. **Confirm no dynamic imports** that would break silently:

   ```bash
   grep -rn "importlib\|__import__" --include="*.py" scylla/
   ```

2. **Find all consumers** of the current module:

   ```bash
   grep -rn "from scylla.orchestrator\|import scylla.orchestrator" --include="*.py" .
   ```

3. **Run baseline tests** to confirm clean starting state:

   ```bash
   pixi run python -m pytest tests/ -v --tb=short -x
   ```

4. **Read current `__init__.py`** files for both the root package and target sub-package to understand what is already exported.

### Phase 2: Create New Location

Copy the file with no content changes:

```bash
cp scylla/orchestrator.py scylla/e2e/orchestrator.py
```

**Key insight**: The file content needs zero changes — all existing imports within the file remain valid because Python resolves them absolutely.

### Phase 3: Update All Consumers

For each file found in Phase 1, update the import path:

```python
# FROM (old location)
from scylla.orchestrator import EvalOrchestrator, OrchestratorConfig

# TO (new canonical location)
from scylla.e2e.orchestrator import EvalOrchestrator, OrchestratorConfig
```

Typical consumers for an orchestrator pattern:
- `scylla/cli/main.py` — CLI commands that instantiate the orchestrator
- `tests/unit/e2e/test_orchestrator.py` — unit tests (already in `e2e/` directory)

### Phase 4: Update Package Exports

**In `scylla/e2e/__init__.py`**, add import and `__all__` entries:

```python
# Add import (after existing imports from sub-modules)
from scylla.e2e.orchestrator import EvalOrchestrator, OrchestratorConfig

# Add to __all__
__all__ = [
    # ... existing entries ...
    # Orchestrator
    "EvalOrchestrator",
    "OrchestratorConfig",
    # ... more entries ...
]
```

**In `scylla/__init__.py`**, remove the stale root-level entry:

```python
__all__ = [
    "config",
    "executor",
    # ... other sub-packages ...
    # REMOVE: "orchestrator",   ← delete this line
    "cli",
]
```

### Phase 5: Verify Before Deletion

Run 3 smoke tests to confirm all access paths work:

```bash
# 1. Direct new canonical import
pixi run python -c "from scylla.e2e.orchestrator import EvalOrchestrator, OrchestratorConfig; print('OK')"

# 2. Re-export via sub-package __init__
pixi run python -c "from scylla.e2e import EvalOrchestrator; print('OK')"

# 3. CLI consumer still works
pixi run python -c "from scylla.cli.main import cli; print('OK')"
```

### Phase 6: Delete Old File

Use `git rm` (not plain `rm`) to track the deletion:

```bash
git rm scylla/orchestrator.py
```

### Phase 7: Final Verification

1. Confirm zero dangling references:

   ```bash
   grep -rn "from scylla.orchestrator\|import scylla.orchestrator" --include="*.py" .
   # Should produce no output
   ```

2. Run full test suite:

   ```bash
   pixi run python -m pytest tests/ -v --tb=short -x
   ```

3. Run pre-commit hooks:

   ```bash
   pre-commit run --all-files
   ```

### Phase 8: Commit and PR

Stage only implementation files (not `.claude-prompt-*.md` or other temp files):

```bash
git add scylla/e2e/orchestrator.py scylla/e2e/__init__.py scylla/__init__.py \
        scylla/cli/main.py tests/unit/e2e/test_orchestrator.py CLAUDE.md
```

Use conventional commit format with `git rm` already staged:

```
refactor(structure): Relocate scylla/orchestrator.py into scylla/e2e/

- Copy scylla/orchestrator.py → scylla/e2e/orchestrator.py (no content changes)
- Update all consumers to import from scylla.e2e.orchestrator
- Add re-exports to scylla/e2e/__init__.py
- Remove stale entry from scylla/__init__.__all__
- Delete scylla/orchestrator.py via git rm

Closes #<issue-number>
```

## Failed Attempts

### ❌ N/A — Plan from Issue Was Precise Enough

The issue comment included a 7-phase implementation plan with exact file paths, line numbers, and the exact `FROM/TO` import strings. No false starts occurred.

**Lesson**: When an issue has a detailed plan posted as a comment (with exact `FROM:` / `TO:` diffs), read the comments first with `gh issue view <N> --comments` before doing any exploration. The plan is the source of truth.

## Results & Parameters

### Files Changed

| File | Change |
|------|--------|
| `scylla/e2e/orchestrator.py` | Created (copied from root, no content changes) |
| `scylla/cli/main.py` | 1-line import update |
| `tests/unit/e2e/test_orchestrator.py` | 1-line import update |
| `scylla/e2e/__init__.py` | +2 import, +2 `__all__` entries |
| `scylla/__init__.py` | -1 `__all__` entry |
| `scylla/orchestrator.py` | Deleted via `git rm` |
| `CLAUDE.md` | Updated `e2e/` description line |

### Metrics

| Metric | Value |
|--------|-------|
| Tests passing | 2436 / 2436 |
| Coverage | 74.15% (threshold: 73%) |
| Pre-commit hooks | All passed |
| Dynamic imports found | 0 |
| Consumer files updated | 2 |
| Net line change | +7 / -4 (trivial) |

### Git Statistics

```
6 files changed, 7 insertions(+), 4 deletions(-)
rename scylla/{ => e2e}/orchestrator.py (100%)
```

Git correctly detected the copy+delete as a **rename** (100% similarity), which preserves full file history.

## Key Decisions

### Option A vs Option B: Always Prefer Existing Sub-Package

When an issue offers:
- **Option A**: Move into existing sub-package
- **Option B**: Create new sub-package

**Always choose Option A** (KISS/YAGNI) unless:
- No existing sub-package is semantically appropriate
- Future orchestration abstractions are explicitly planned and tracked
- The target sub-package is already overcrowded

### No Backward-Compat Shim Needed

The old `scylla.orchestrator` path is removed entirely (no `from scylla.orchestrator import ...` shim in the root `__init__.py`). This is correct because:
- Both consumers were internal (CLI + tests) — no public API surface
- Zero external packages depend on this import path
- A shim would create technical debt and mislead future readers

### Content Unchanged

The file is copied verbatim. This is important: the orchestrator's own imports (`from scylla.cli.progress import ...`, `from scylla.config import ...`, etc.) all use absolute paths and remain valid in the new location.

## When NOT to Use This Skill

- When moving requires content changes (e.g., the module uses relative imports)
- When the module has external consumers (PyPI packages, other repos)
- When the destination sub-package doesn't exist and Option B is warranted
- When the module is truly shared between multiple sub-packages (consider `core/` or `common/`)

## Related Skills

- **dry-refactoring-workflow** — General DRY refactoring patterns
- **quality-audit-implementation** — Acting on code quality audit findings
- **planning-implementation-from-issue** — Reading detailed plans from issue comments

## Key Takeaways

1. **Read `gh issue view --comments` first** — detailed plans are often posted there
2. **`git rm` preserves history as a rename** — git detects 100% similarity automatically
3. **No content changes needed** — absolute imports work from any location in the package
4. **3-step smoke test** — direct import, re-export via `__init__`, consumer CLI import
5. **Stage specific files** — exclude `.claude-prompt-*.md` and temp files from commit
6. **Verify zero dangling refs** — `grep -rn "from scylla.orchestrator"` must return nothing
