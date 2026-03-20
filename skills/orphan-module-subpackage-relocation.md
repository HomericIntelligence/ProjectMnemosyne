---
name: orphan-module-subpackage-relocation
description: Relocate an orphaned root-level module into the correct sub-package using
  copy, import update, re-export, and deletion workflow.
category: architecture
date: 2026-02-22
version: 1.0.0
user-invocable: false
---
# Orphan Module Sub-Package Relocation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Move an orphaned module from the package root into the correct sub-package to restore consistent structure |
| **Outcome** | Complete success — tests pass, all pre-commit hooks pass, PR created and auto-merge enabled |
| **Category** | Architecture / Structural Refactor |

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
   grep -rn "importlib\|__import__" --include="*.py" <package>/
   ```

2. **Find all consumers** of the current module:

   ```bash
   grep -rn "from <package>.<module>\|import <package>.<module>" --include="*.py" .
   ```

3. **Run baseline tests** to confirm clean starting state:

   ```bash
   <package-manager> run python -m pytest tests/ -v --tb=short -x
   ```

4. **Read current `__init__.py`** files for both the root package and target sub-package.

### Phase 2: Create New Location

Copy the file with no content changes:

```bash
cp <package>/<module>.py <package>/<subpackage>/<module>.py
```

**Key insight**: The file content needs zero changes — all existing imports within the file remain valid because Python resolves them absolutely.

### Phase 3: Update All Consumers

For each file found in Phase 1, update the import path:

```python
# FROM (old location)
from <package>.<module> import ClassA, ClassB

# TO (new canonical location)
from <package>.<subpackage>.<module> import ClassA, ClassB
```

### Phase 4: Update Package Exports

**In `<package>/<subpackage>/__init__.py`**, add import and `__all__` entries.

**In `<package>/__init__.py`**, remove the stale root-level entry from `__all__`.

### Phase 5: Verify Before Deletion

Run 3 smoke tests to confirm all access paths work:

```bash
# 1. Direct new canonical import
<package-manager> run python -c "from <package>.<subpackage>.<module> import ClassA; print('OK')"

# 2. Re-export via sub-package __init__
<package-manager> run python -c "from <package>.<subpackage> import ClassA; print('OK')"

# 3. CLI consumer still works
<package-manager> run python -c "from <package>.cli.main import cli; print('OK')"
```

### Phase 6: Delete Old File

Use `git rm` (not plain `rm`) to track the deletion:

```bash
git rm <package>/<module>.py
```

### Phase 7: Final Verification

1. Confirm zero dangling references:

   ```bash
   grep -rn "from <package>.<module>\|import <package>.<module>" --include="*.py" .
   # Should produce no output
   ```

2. Run full test suite and pre-commit hooks.

### Phase 8: Commit and PR

Stage only implementation files:

```bash
git add <new-file> <updated-__init__> <updated-consumers>
git commit -m "refactor(structure): Relocate <package>/<module>.py into <package>/<subpackage>/

- Copy <module>.py → <subpackage>/<module>.py (no content changes)
- Update all consumers to import from <package>.<subpackage>.<module>
- Add re-exports to <subpackage>/__init__.py
- Remove stale entry from <package>/__init__.__all__
- Delete <package>/<module>.py via git rm

Closes #<issue-number>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Metric | Value |
|--------|-------|
| Files changed | 6 (new file, 2 consumers, 2 `__init__.py`, deleted old) |
| Content changes | Zero in the moved file |
| Git detection | Rename (100% similarity) — preserves full file history |
| Commit type | `refactor(structure):` |

## Key Decisions

### Option A vs Option B: Always Prefer Existing Sub-Package

When an issue offers:
- **Option A**: Move into existing sub-package
- **Option B**: Create new sub-package

**Always choose Option A** (KISS/YAGNI) unless no existing sub-package is semantically appropriate.

### No Backward-Compat Shim Needed

The old import path is removed entirely when all consumers are internal. A shim would create technical debt.

## Key Takeaways

1. **Read `gh issue view --comments` first** — detailed plans are often posted there
2. **`git rm` preserves history as a rename** — git detects 100% similarity automatically
3. **No content changes needed** — absolute imports work from any location in the package
4. **3-step smoke test** — direct import, re-export via `__init__`, consumer CLI import
5. **Verify zero dangling refs** — grep must return nothing after deletion

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #847, PR #958 | [notes.md](../../references/notes.md) |
